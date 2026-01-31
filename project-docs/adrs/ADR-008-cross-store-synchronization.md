# ADR-008: Cross-Store Synchronization Strategy

## Status

Accepted

## Context

The memory system stores data in both Qdrant (content + embeddings) and Neo4j (structure + relationships). Maintaining consistency between these stores is critical for:
- Referential integrity (no orphaned pointers)
- Query correctness (hybrid queries rely on both stores)
- Data durability (no data loss on partial failures)

Requirements addressed:
- REQ-MEM-DATA-030: Referential integrity between stores
- REQ-MEM-REL-002: Transaction semantics with rollback
- REQ-MEM-INT-073: Bidirectional references

## Options Considered

### Option 1: Synchronous Dual-Write with Distributed Transaction

- **Pros**:
  - Strong consistency guaranteed
  - ACID across both stores
- **Cons**:
  - Neither Qdrant nor Neo4j supports XA/2PC
  - Would require custom implementation
  - High latency
  - Complex failure handling

### Option 2: Event Sourcing with Eventual Consistency

- **Pros**:
  - Decoupled writes
  - Audit trail built-in
  - Can replay events
- **Cons**:
  - Eventual consistency not ideal for immediate queries
  - Additional infrastructure (event store)
  - Over-engineered for single-user system

### Option 3: Ordered Writes with Compensation

- **Pros**:
  - Simple implementation
  - Predictable failure modes
  - Compensation handles partial failures
  - No additional infrastructure
- **Cons**:
  - Brief inconsistency window
  - Compensation logic needed per operation

## Decision

**Option 3: Ordered Writes with Compensation** - Write to primary store first, then secondary, with compensation on failure.

### Write Order Strategy

For most operations, Qdrant is the **primary store** because:
- Content and embeddings are the core data
- Qdrant IDs are referenced by Neo4j nodes
- Vector search is the most common query type

**Write Order:**
1. Write to Qdrant (get memory_id)
2. Write to Neo4j (using memory_id as reference)
3. If step 2 fails, mark Qdrant entry for sync retry

**Exception - Relationship-Only Operations:**
For operations that only affect relationships (e.g., linking existing entities):
1. Write to Neo4j
2. No Qdrant write needed

### Operation Patterns

#### Create Memory

```python
async def create_memory(content: str, metadata: dict) -> MemoryId:
    # 1. Generate embedding
    embedding = await embedding_service.get_embedding(content)

    # 2. Write to Qdrant
    memory_id = await qdrant.upsert(
        collection=metadata["type"],
        id=uuid4(),
        vector=embedding,
        payload={**metadata, "sync_status": "pending"}
    )

    # 3. Write to Neo4j
    try:
        neo4j_node_id = await neo4j.create_node(
            labels=[metadata["type"]],
            properties={
                "memory_id": str(memory_id),
                **extract_node_properties(metadata)
            }
        )

        # 4. Update Qdrant with Neo4j reference
        await qdrant.update_payload(
            collection=metadata["type"],
            id=memory_id,
            payload={
                "neo4j_node_id": neo4j_node_id,
                "sync_status": "synced"
            }
        )

    except Neo4jError as e:
        # Mark for retry, don't fail the operation
        await qdrant.update_payload(
            collection=metadata["type"],
            id=memory_id,
            payload={"sync_status": "pending", "sync_error": str(e)}
        )
        logger.warning(f"Neo4j sync failed, queued for retry: {memory_id}")

    return memory_id
```

#### Update Memory

```python
async def update_memory(memory_id: MemoryId, updates: dict) -> None:
    # 1. Update Qdrant
    if "content" in updates:
        embedding = await embedding_service.get_embedding(updates["content"])
        await qdrant.update_vectors(memory_id, embedding)

    await qdrant.update_payload(memory_id, updates)

    # 2. Update Neo4j (if node exists)
    memory = await qdrant.get(memory_id)
    if memory.payload.get("neo4j_node_id"):
        try:
            await neo4j.update_node(
                memory.payload["neo4j_node_id"],
                extract_node_properties(updates)
            )
        except Neo4jError:
            await mark_for_sync(memory_id)
```

#### Delete Memory

```python
async def delete_memory(memory_id: MemoryId) -> None:
    memory = await qdrant.get(memory_id)

    # 1. Delete from Neo4j first (relationships then node)
    if memory.payload.get("neo4j_node_id"):
        try:
            await neo4j.delete_relationships(memory.payload["neo4j_node_id"])
            await neo4j.delete_node(memory.payload["neo4j_node_id"])
        except Neo4jError as e:
            logger.error(f"Neo4j delete failed: {e}")
            # Continue to Qdrant deletion - orphan cleanup will handle Neo4j

    # 2. Soft-delete in Qdrant
    await qdrant.update_payload(memory_id, {
        "deleted": True,
        "deleted_at": datetime.utcnow().isoformat()
    })
```

### Sync Recovery Process

Background task runs periodically (every 5 minutes):

```python
async def sync_pending_memories():
    # Find all pending sync entries
    pending = await qdrant.search_by_payload(
        filter={"sync_status": "pending"},
        limit=100
    )

    for memory in pending:
        try:
            if memory.payload.get("neo4j_node_id"):
                # Update existing node
                await neo4j.update_node(...)
            else:
                # Create new node
                neo4j_node_id = await neo4j.create_node(...)
                await qdrant.update_payload(memory.id, {
                    "neo4j_node_id": neo4j_node_id,
                    "sync_status": "synced"
                })

            await qdrant.update_payload(memory.id, {
                "sync_status": "synced",
                "sync_error": None
            })

        except Exception as e:
            retry_count = memory.payload.get("sync_retry_count", 0) + 1
            await qdrant.update_payload(memory.id, {
                "sync_retry_count": retry_count,
                "sync_error": str(e),
                "sync_last_attempt": datetime.utcnow().isoformat()
            })

            if retry_count > 10:
                logger.error(f"Sync permanently failed for {memory.id}")
```

### Sync Status Payload

Every Qdrant entry includes:

```json
{
  "sync_status": "synced | pending | failed",
  "neo4j_node_id": "neo4j-internal-id or null",
  "sync_error": "error message or null",
  "sync_retry_count": 0,
  "sync_last_attempt": "ISO timestamp or null"
}
```

### Consistency Checks

During normalization and on-demand:

```python
async def verify_consistency():
    issues = []

    # 1. Find Qdrant entries without Neo4j nodes
    for collection in COLLECTIONS:
        entries = await qdrant.scroll(collection)
        for entry in entries:
            if entry.payload.get("neo4j_node_id"):
                exists = await neo4j.node_exists(entry.payload["neo4j_node_id"])
                if not exists:
                    issues.append(("orphaned_qdrant_ref", entry.id))

    # 2. Find Neo4j nodes without Qdrant entries
    nodes = await neo4j.query("MATCH (n) WHERE n.memory_id IS NOT NULL RETURN n")
    for node in nodes:
        exists = await qdrant.exists(node["memory_id"])
        if not exists:
            issues.append(("orphaned_neo4j_node", node.id))

    return issues
```

## Consequences

### Positive
- Simple, predictable write patterns
- No external transaction coordinator needed
- Graceful degradation - system works with Neo4j temporarily unavailable
- Self-healing via background sync

### Negative
- Brief inconsistency window possible
- Extra complexity for sync tracking
- Need monitoring for stuck syncs

### Risks
- **Risk**: Sync queue grows unbounded during extended Neo4j outage
- **Mitigation**: Alert on queue size; Neo4j health check; manual intervention capability

- **Risk**: Orphaned data accumulates
- **Mitigation**: Regular consistency checks; normalization process cleans orphans

## Requirements Addressed

- REQ-MEM-DATA-030 (referential integrity)
- REQ-MEM-REL-002 (transaction semantics)
- REQ-MEM-REL-003 (graceful unavailability handling)
- REQ-MEM-INT-073 (bidirectional references)

## References

- Saga pattern: https://microservices.io/patterns/data/saga.html
- Compensation patterns for distributed systems
