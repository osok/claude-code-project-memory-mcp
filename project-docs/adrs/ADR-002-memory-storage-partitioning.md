# ADR-002: Memory Storage Partitioning Strategy

## Status

Accepted

## Context

The memory system requires both vector similarity search (for semantic queries) and graph traversal (for relationship queries). Two storage systems are mandated:
- **Qdrant**: Vector database for embeddings and similarity search
- **Neo4j**: Graph database for relationships and traversals

The key question is how to partition data between these stores and maintain consistency.

Requirements addressed:
- REQ-MEM-FN-003: Episodic memory in Qdrant with temporal metadata
- REQ-MEM-FN-004: Semantic memory as hybrid of Qdrant embeddings and Neo4j nodes
- REQ-MEM-INT-073: Bidirectional references between Qdrant and Neo4j
- REQ-MEM-DATA-030: Referential integrity between stores

## Options Considered

### Option 1: Qdrant Primary with Neo4j for Relationships Only

- **Pros**:
  - Single source of truth for memory content
  - Neo4j only stores lightweight relationship data
  - Simpler consistency model
  - Smaller Neo4j footprint
- **Cons**:
  - Requires joining data across stores for rich queries
  - Cannot leverage Neo4j's full-text or property search
  - All content queries go through Qdrant

### Option 2: Full Duplication (Content in Both Stores)

- **Pros**:
  - Both stores fully self-contained for their query types
  - Can leverage Neo4j's graph-aware text search
  - Redundancy provides backup
- **Cons**:
  - Storage duplication
  - Complex consistency management
  - Higher write latency (dual writes)
  - Version conflicts possible

### Option 3: Qdrant for Content/Embeddings, Neo4j for Structure/Relationships

- **Pros**:
  - Clear separation of concerns
  - Each store optimized for its purpose
  - Minimal duplication (only IDs and essential metadata shared)
  - Neo4j stores derived structure (functions, classes) extracted during indexing
  - Qdrant stores raw content and embeddings
- **Cons**:
  - Hybrid queries require coordination
  - Need to maintain ID mappings

## Decision

**Option 3: Clear Separation** - Qdrant stores content and embeddings; Neo4j stores code structure and relationships.

### Data Distribution

**Qdrant Collections** (one per memory type):
- `episodic_memory` - Session histories, events with temporal metadata
- `semantic_memory` - Facts, patterns, abstractions
- `procedural_memory` - Workflows, rules, procedures
- `requirements_memory` - Requirement documents and specifications
- `design_memory` - ADRs, architecture decisions, design docs
- `code_patterns` - Implementation templates and conventions
- `function_index` - Function embeddings for duplicate detection
- `test_history` - Test execution records
- `session_history` - Session summaries
- `user_preferences` - Coding style preferences

Each collection stores:
- Full content text
- Embedding vector (1024 dimensions from Voyage-Code-3)
- Metadata (timestamps, importance scores, etc.)
- `neo4j_node_id` reference (if applicable)

**Neo4j Nodes**:
- `Function` - Extracted functions with name, signature, location
- `Class` - Extracted classes with name, methods, attributes
- `Module` - Modules/packages
- `File` - Source files
- `Component` - Registered system components
- `Requirement` - Requirement references
- `Design` - Design document references
- `Pattern` - Code pattern references
- `Test` - Test references

Each node stores:
- Essential identifying metadata
- `qdrant_memory_id` reference to full content
- Searchable properties (name, path, type)

**Neo4j Relationships**:
- `CALLS` - Function call relationships
- `IMPORTS` - Import/dependency relationships
- `EXTENDS` - Inheritance relationships
- `IMPLEMENTS` - Interface implementation
- `DEPENDS_ON` - Component dependencies
- `IMPLEMENTS_REQ` - Code implementing requirement
- `FOLLOWS_DESIGN` - Code following design
- `USES_PATTERN` - Code using pattern
- `TESTS` - Test coverage relationships

### Synchronization Strategy

1. **Write Operations**: Write to Qdrant first, then Neo4j. If Neo4j fails, mark Qdrant entry as `pending_sync` and retry.
2. **Delete Operations**: Soft-delete in Qdrant, then remove Neo4j relationships, then remove Neo4j node. Use transaction for Neo4j operations.
3. **Reference Integrity**: Store bidirectional IDs. Validate during normalization.

## Consequences

### Positive
- Clear ownership of data types
- Optimized storage for each use case
- Qdrant handles all similarity search efficiently
- Neo4j handles all graph traversal efficiently
- Minimal data duplication
- Easier to reason about consistency

### Negative
- Hybrid queries require two-phase execution
- Need robust sync mechanism for cross-store references
- Orphaned references possible if sync fails

### Risks
- **Risk**: Qdrant and Neo4j get out of sync
- **Mitigation**: Pending sync queue with background reconciliation; normalization process validates and repairs references

## Requirements Addressed

- REQ-MEM-FN-003, REQ-MEM-FN-004, REQ-MEM-FN-005 (memory storage)
- REQ-MEM-INT-061, REQ-MEM-INT-073 (cross-store references)
- REQ-MEM-DATA-030 (referential integrity)
- REQ-MEM-REL-002 (transaction semantics)

## References

- Qdrant Documentation: https://qdrant.tech/documentation
- Neo4j Documentation: https://neo4j.com/docs
