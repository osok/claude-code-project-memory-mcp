# ADR-005: Hybrid Query Engine Design

## Status

Accepted

## Context

The memory system must support three query types:
1. **Semantic search**: Find memories similar to a query (Qdrant)
2. **Graph traversal**: Find related entities by relationships (Neo4j)
3. **Hybrid queries**: Combine semantic similarity with graph relationships

Hybrid queries are essential for scenarios like:
- "Find functions similar to X that are called by component Y"
- "Find requirements related to component Z and its dependencies"
- "Find patterns used by classes extending BaseAgent"

Requirements addressed:
- REQ-MEM-FN-080: Semantic search with filters
- REQ-MEM-FN-081: Graph traversal queries
- REQ-MEM-FN-082: Hybrid queries combining similarity and relationships
- REQ-MEM-FN-084: Ranked results combining factors
- REQ-MEM-INT-022: Graph query tool (Cypher)
- REQ-MEM-INT-024: Get related entities tool

## Options Considered

### Option 1: Application-Level Join

- **Pros**:
  - Simple - query each store, join in application
  - No coupling between stores
  - Flexible join logic
- **Cons**:
  - N+1 query problem for large result sets
  - Memory overhead for intermediate results
  - Complex pagination across joined results

### Option 2: Neo4j Vector Index (GDS)

- **Pros**:
  - Single query to Neo4j handles both
  - Native graph + vector in one system
  - Simpler architecture
- **Cons**:
  - Neo4j vector search less mature than Qdrant
  - Would duplicate embeddings in Neo4j
  - Loses Qdrant's optimized HNSW implementation
  - Vendor lock-in to Neo4j for all operations

### Option 3: Query Planner with Two-Phase Execution

- **Pros**:
  - Best of both worlds - optimized stores for each query type
  - Intelligent query planning based on query structure
  - Can optimize based on selectivity
  - Clear separation of concerns
- **Cons**:
  - More complex implementation
  - Query planning logic needed
  - Two round trips for hybrid queries

## Decision

**Option 3: Query Planner** - Implement a query planner that decomposes hybrid queries into optimal execution plans.

### Query Engine Architecture

```
Query Request
    |
    v
[Query Parser]
    |
    v
[Query Planner]
    |
    +-- Pure Vector Query --> [Qdrant Executor] --> Results
    |
    +-- Pure Graph Query --> [Neo4j Executor] --> Results
    |
    +-- Hybrid Query --> [Hybrid Executor]
                              |
                              v
                         [Determine Primary Store]
                              |
                              +-- Graph-First: Neo4j -> filter by IDs -> Qdrant
                              |
                              +-- Vector-First: Qdrant -> filter by IDs -> Neo4j
                              |
                              v
                         [Result Merger & Ranker]
                              |
                              v
                         Results
```

### Query Types and Execution Strategies

1. **Pure Semantic Search**
   - Input: query text, optional filters (type, time range)
   - Execution: Direct Qdrant query
   - Example: `memory_search(query="authentication handler", type="function")`

2. **Pure Graph Traversal**
   - Input: entity ID, relationship types, depth
   - Execution: Direct Neo4j Cypher query
   - Example: `get_related(entity="AuthService", relationships=["DEPENDS_ON"], depth=2)`

3. **Graph-Constrained Semantic Search**
   - Use case: "Functions similar to X within component Y"
   - Strategy: Graph-first
   - Execution:
     1. Query Neo4j for entity IDs within scope
     2. Pass IDs to Qdrant as filter
     3. Qdrant returns similarity-ranked results

4. **Semantic-Constrained Graph Traversal**
   - Use case: "Dependencies of components matching 'auth*'"
   - Strategy: Vector-first
   - Execution:
     1. Query Qdrant for matching memories
     2. Extract entity IDs
     3. Query Neo4j for relationships from those entities

5. **Multi-Hop Semantic**
   - Use case: "Patterns used by implementations of functions similar to X"
   - Strategy: Iterative
   - Execution:
     1. Qdrant: Find similar functions
     2. Neo4j: Get implementations
     3. Neo4j: Get patterns used

### Query Planner Heuristics

The planner chooses strategy based on:

1. **Selectivity estimation**:
   - If graph constraint is highly selective (specific component), go graph-first
   - If semantic query is specific, go vector-first

2. **Query structure**:
   - Presence of relationship constraints -> graph-first bias
   - Presence of similarity threshold -> vector-first bias

3. **Result size hints**:
   - Small expected result set -> graph-first (fewer IDs to filter)
   - Large scope -> vector-first (let Qdrant rank and limit)

### Result Ranking

Combined ranking score formula:

```
score = (
    w_similarity * cosine_similarity +
    w_importance * importance_score +
    w_recency * recency_decay +
    w_access * access_frequency_normalized +
    w_relationship * relationship_relevance
)

where:
  recency_decay = exp(-lambda * days_since_update)
  relationship_relevance = 1 / (1 + hop_distance)
```

Default weights:
- w_similarity = 0.5
- w_importance = 0.2
- w_recency = 0.1
- w_access = 0.1
- w_relationship = 0.1

### Query Interface

```python
class QueryEngine:
    async def semantic_search(
        self,
        query: str,
        memory_types: Optional[List[MemoryType]] = None,
        time_range: Optional[TimeRange] = None,
        limit: int = 10,
        min_similarity: float = 0.0
    ) -> List[SearchResult]

    async def graph_query(
        self,
        cypher: str,
        params: Optional[Dict] = None
    ) -> List[Dict]

    async def get_related(
        self,
        entity_id: str,
        relationship_types: Optional[List[str]] = None,
        direction: Direction = Direction.BOTH,
        depth: int = 1
    ) -> List[RelatedEntity]

    async def hybrid_search(
        self,
        query: str,
        graph_constraint: GraphConstraint,
        limit: int = 10
    ) -> List[HybridResult]
```

### Caching Strategy

- **Query result cache**: Short-lived (5 min TTL) for repeated queries
- **Entity cache**: Frequently accessed entities cached in memory
- **Graph structure cache**: Common traversal paths cached

## Consequences

### Positive
- Optimal query execution for each query type
- Flexible hybrid queries without data duplication
- Clear ranking strategy combining multiple factors
- Extensible planner for new query patterns

### Negative
- Two round trips for hybrid queries
- Query planner complexity
- Need to maintain cache coherence

### Risks
- **Risk**: Query planner makes suboptimal choices
- **Mitigation**: Logging and metrics to identify slow queries; manual hints for known patterns

- **Risk**: Cache staleness causes incorrect results
- **Mitigation**: Short TTLs; invalidation on writes to affected entities

## Requirements Addressed

- REQ-MEM-FN-080 (semantic search)
- REQ-MEM-FN-081 (graph traversal)
- REQ-MEM-FN-082 (hybrid queries)
- REQ-MEM-FN-084 (ranked results)
- REQ-MEM-INT-022 (Cypher support)
- REQ-MEM-INT-024 (related entities)
- REQ-MEM-PERF-001 (500ms search latency)
- REQ-MEM-PERF-002 (200ms graph latency)

## References

- Qdrant filtering: https://qdrant.tech/documentation/concepts/filtering/
- Neo4j Cypher: https://neo4j.com/docs/cypher-manual/
