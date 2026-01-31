# ADR-006: Memory Normalization Process

## Status

Accepted

## Context

Over time, memory quality degrades due to:
- Duplicate memories with slight variations
- Orphaned references (deleted code, removed components)
- Stale embeddings (from older model versions or fallback)
- Accumulated soft-deleted items
- Fragmentation in storage

The normalization process must:
- Clean and optimize memory storage
- Maintain data integrity throughout
- Support rollback on failure
- Report progress to users

Requirements addressed:
- REQ-MEM-FN-070: Normalization via temp store, rebuild, swap
- REQ-MEM-FN-071: Deduplicate above 0.95 similarity
- REQ-MEM-FN-072: Remove orphaned references
- REQ-MEM-FN-073: Recompute stale embeddings
- REQ-MEM-FN-074: Rollback on failure
- REQ-MEM-FN-075: Progress reporting
- REQ-MEM-REL-005: Atomic normalization

## Options Considered

### Option 1: In-Place Normalization

- **Pros**:
  - No extra storage needed
  - Simpler implementation
- **Cons**:
  - Cannot rollback partial changes
  - System unavailable during normalization
  - Risk of data corruption

### Option 2: Copy-on-Write with Instant Swap

- **Pros**:
  - Original data preserved until complete
  - Atomic swap at end
  - System available during most of process
- **Cons**:
  - Requires 2x storage temporarily
  - Need to handle writes during normalization

### Option 3: Shadow Copy with Write Forwarding

- **Pros**:
  - System fully available during normalization
  - Original preserved for rollback
  - Writes captured and applied to new store
  - Clean atomic swap
- **Cons**:
  - Most complex implementation
  - Write forwarding adds latency
  - Need careful conflict resolution

## Decision

**Option 2: Copy-on-Write with Instant Swap** - Build normalized store alongside original, swap atomically on completion.

Option 3's write forwarding complexity is not justified for a single-user system where normalization can run during low-activity periods.

### Normalization Pipeline

```
[Initiate Normalization]
        |
        v
[Create Job Record]
        |
        v
[Phase 1: Snapshot]
  - Create temp Qdrant collections (suffixed _norm)
  - Create temp Neo4j database/labels
  - Block new writes (short window)
  - Copy current state
  - Resume writes to original
        |
        v
[Phase 2: Deduplication]
  - For each collection:
    - Cluster memories by embedding similarity
    - Merge clusters above 0.95 threshold
    - Keep most complete version
    - Preserve all metadata (union)
        |
        v
[Phase 3: Orphan Detection]
  - Query all Neo4j references
  - Verify each reference target exists
  - Mark orphaned for removal
        |
        v
[Phase 4: Embedding Refresh]
  - Find memories with:
    - is_fallback = true
    - embedding_model != current model
    - content_hash != stored hash
  - Re-embed content
  - Update vectors
        |
        v
[Phase 5: Cleanup]
  - Remove soft-deleted items past retention
  - Remove orphaned references
  - Compact storage
        |
        v
[Phase 6: Validation]
  - Count records (should match or be less)
  - Verify referential integrity
  - Sample queries for sanity
        |
        v
[Phase 7: Swap]
  - Acquire write lock
  - Rename original -> _backup
  - Rename _norm -> primary
  - Release write lock
        |
        v
[Phase 8: Cleanup]
  - Keep backup for configured period (default 24h)
  - Remove backup after period
        |
        v
[Complete]
```

### Job State Management

```python
class NormalizationJob:
    job_id: UUID
    status: Literal["pending", "running", "completed", "failed", "rolled_back"]
    phase: str
    progress_percent: int
    started_at: datetime
    completed_at: Optional[datetime]
    error: Optional[str]
    stats: NormalizationStats

class NormalizationStats:
    memories_processed: int
    duplicates_merged: int
    orphans_removed: int
    embeddings_refreshed: int
    soft_deletes_purged: int
    original_size_bytes: int
    normalized_size_bytes: int
```

### Deduplication Algorithm

```python
def deduplicate_collection(collection: str, threshold: float = 0.95):
    # Get all memories with embeddings
    memories = qdrant.scroll(collection, with_vectors=True)

    # Build similarity clusters using DBSCAN-like approach
    clusters = []
    processed = set()

    for memory in memories:
        if memory.id in processed:
            continue

        # Find all similar memories
        similar = qdrant.search(
            collection,
            vector=memory.vector,
            limit=100,
            score_threshold=threshold
        )

        cluster = [m for m in similar if m.id not in processed]
        if len(cluster) > 1:
            clusters.append(cluster)
            processed.update(m.id for m in cluster)
        else:
            # Single memory, keep as-is
            processed.add(memory.id)

    # Merge clusters
    for cluster in clusters:
        merged = merge_memories(cluster)
        # Write merged to normalized collection
```

### Merge Strategy

When merging duplicate memories:
1. **Content**: Keep longest/most complete
2. **Metadata**: Union of all keys, latest values for conflicts
3. **Timestamps**: Earliest created_at, latest updated_at
4. **Access count**: Sum of all
5. **Importance**: Maximum
6. **Relationships**: Union (re-point to merged ID)

### Rollback Procedure

If normalization fails at any phase:

1. **Phase 1-6 failure**: Simply drop temp collections/labels, original untouched
2. **Phase 7 failure (during swap)**:
   - If original renamed: rename back
   - If norm renamed: rename to temp
   - Log for manual verification
3. **Phase 8 failure**: Non-critical, backup cleanup can be manual

### Progress Reporting

Via MCP tool `normalize_status`:

```json
{
  "job_id": "uuid",
  "status": "running",
  "phase": "deduplication",
  "progress_percent": 45,
  "current_collection": "function_index",
  "stats": {
    "memories_processed": 5432,
    "duplicates_merged": 234,
    "orphans_removed": 0,
    "embeddings_refreshed": 0
  },
  "estimated_remaining_seconds": 120
}
```

### Write Handling During Normalization

During normalization (phases 2-6):
- **Reads**: Served from original store
- **Writes**: Accepted to original store, flagged as `post_snapshot=true`
- **Swap phase**: Brief write lock (typically < 1 second)
- **Post-swap**: Process flagged writes against normalized store

## Consequences

### Positive
- Full rollback capability until swap
- Original data preserved during process
- Progress visibility throughout
- Minimal downtime (only swap phase)
- Deduplication significantly reduces storage

### Negative
- Requires 2x storage during normalization
- Writes during normalization need reconciliation
- Long-running process for large databases

### Risks
- **Risk**: Insufficient disk space for temp store
- **Mitigation**: Pre-check available space before starting; abort if < 2x current size

- **Risk**: Normalization takes too long
- **Mitigation**: Can be run incrementally by collection; progress saved per phase

- **Risk**: Swap fails leaving system in inconsistent state
- **Mitigation**: Detailed logging; manual recovery procedure documented; backup preserved

## Requirements Addressed

- REQ-MEM-FN-070 through REQ-MEM-FN-075 (normalization)
- REQ-MEM-REL-005 (atomicity)
- REQ-MEM-INT-050, REQ-MEM-INT-051 (normalization tools)

## References

- Qdrant collection management: https://qdrant.tech/documentation/concepts/collections/
- Neo4j database management: https://neo4j.com/docs/operations-manual/
