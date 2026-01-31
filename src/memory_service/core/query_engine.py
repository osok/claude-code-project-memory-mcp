"""Query planning and execution engine."""

import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from memory_service.models import MemoryType, RelationshipType
from memory_service.storage.qdrant_adapter import QdrantAdapter
from memory_service.storage.neo4j_adapter import Neo4jAdapter
from memory_service.embedding.service import EmbeddingService
from memory_service.utils.logging import get_logger
from memory_service.utils.metrics import get_metrics

logger = get_logger(__name__)
metrics = get_metrics()


class QueryStrategy(str, Enum):
    """Query execution strategy."""

    VECTOR_ONLY = "vector_only"
    GRAPH_ONLY = "graph_only"
    VECTOR_FIRST = "vector_first"
    GRAPH_FIRST = "graph_first"


@dataclass
class SearchResult:
    """A single search result."""

    id: str
    memory_type: MemoryType
    content: str
    score: float
    payload: dict[str, Any]
    relationship_path: list[str] | None = None


@dataclass
class QueryPlan:
    """Execution plan for a query."""

    strategy: QueryStrategy
    vector_collections: list[str]
    graph_query: str | None
    filters: dict[str, Any]
    limit: int
    use_reranking: bool


class QueryEngine:
    """Query planning and execution engine.

    Provides:
    - Semantic vector search
    - Graph traversal queries
    - Hybrid search combining both
    - Query planning for optimal execution
    - Result ranking and deduplication
    """

    def __init__(
        self,
        qdrant: QdrantAdapter,
        neo4j: Neo4jAdapter,
        embedding_service: EmbeddingService,
        default_limit: int = 10,
        max_limit: int = 100,
    ) -> None:
        """Initialize query engine.

        Args:
            qdrant: Qdrant adapter
            neo4j: Neo4j adapter
            embedding_service: Embedding service
            default_limit: Default result limit
            max_limit: Maximum result limit
        """
        self.qdrant = qdrant
        self.neo4j = neo4j
        self.embedding_service = embedding_service
        self.default_limit = default_limit
        self.max_limit = max_limit

        logger.info("query_engine_initialized")

    async def semantic_search(
        self,
        query: str,
        memory_types: list[MemoryType] | None = None,
        filters: dict[str, Any] | None = None,
        time_range: tuple[datetime, datetime] | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[SearchResult]:
        """Perform semantic search across memories.

        Args:
            query: Search query text
            memory_types: Filter by memory types (None = all)
            filters: Additional filter conditions
            time_range: Filter by time range (start, end)
            limit: Maximum results
            offset: Result offset for pagination

        Returns:
            List of search results ranked by relevance
        """
        start = time.perf_counter()
        limit = min(limit or self.default_limit, self.max_limit)

        # Generate query embedding
        query_embedding = await self.embedding_service.embed_for_query(query)

        # Build filter conditions
        search_filters = self._build_filters(filters, time_range)

        # Search specified memory types or all
        types_to_search = memory_types or list(MemoryType)
        all_results: list[SearchResult] = []

        for memory_type in types_to_search:
            collection = self.qdrant.get_collection_name(memory_type)

            results = await self.qdrant.search(
                collection=collection,
                vector=query_embedding,
                limit=limit + offset,  # Get extra for offset
                filters=search_filters,
            )

            for result in results:
                all_results.append(
                    SearchResult(
                        id=str(result["id"]),
                        memory_type=memory_type,
                        content=result["payload"].get("content", ""),
                        score=result["score"],
                        payload=result["payload"],
                    )
                )

        # Sort by score and apply pagination
        all_results.sort(key=lambda r: r.score, reverse=True)
        paginated_results = all_results[offset : offset + limit]

        duration = time.perf_counter() - start
        metrics.record_search(
            search_type="semantic",
            status="success",
            duration=duration,
            result_count=len(paginated_results),
        )

        logger.debug(
            "semantic_search_complete",
            query_len=len(query),
            result_count=len(paginated_results),
            duration_ms=int(duration * 1000),
        )

        return paginated_results

    async def graph_query(
        self,
        cypher: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a Cypher graph query.

        Args:
            cypher: Cypher query string
            parameters: Query parameters

        Returns:
            Query results
        """
        start = time.perf_counter()

        # Validate query (basic security check)
        self._validate_cypher(cypher)

        results = await self.neo4j.execute_cypher(cypher, parameters)

        duration = time.perf_counter() - start
        metrics.record_search(
            search_type="graph",
            status="success",
            duration=duration,
            result_count=len(results),
        )

        return results

    async def get_related(
        self,
        entity_id: UUID | str,
        relationship_types: list[RelationshipType] | None = None,
        direction: str = "both",
        depth: int = 1,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get entities related to the given entity.

        Args:
            entity_id: Starting entity ID
            relationship_types: Filter by relationship types
            direction: "outgoing", "incoming", or "both"
            depth: Maximum traversal depth
            limit: Maximum results

        Returns:
            List of related entities with relationship info
        """
        start = time.perf_counter()
        limit = min(limit or self.default_limit, self.max_limit)

        results = await self.neo4j.get_related(
            node_id=entity_id,
            relationship_types=relationship_types,
            direction=direction,
            depth=depth,
            limit=limit,
        )

        duration = time.perf_counter() - start
        metrics.record_search(
            search_type="graph_traversal",
            status="success",
            duration=duration,
            result_count=len(results),
        )

        return results

    async def hybrid_search(
        self,
        query: str,
        memory_types: list[MemoryType] | None = None,
        relationship_types: list[RelationshipType] | None = None,
        filters: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> list[SearchResult]:
        """Perform hybrid search combining semantic and graph queries.

        Uses query planner to determine optimal strategy.

        Args:
            query: Search query text
            memory_types: Filter by memory types
            relationship_types: Filter by relationship types
            filters: Additional filter conditions
            limit: Maximum results

        Returns:
            Combined and ranked results
        """
        start = time.perf_counter()
        limit = min(limit or self.default_limit, self.max_limit)

        # Plan the query
        plan = self._plan_query(
            query=query,
            memory_types=memory_types,
            relationship_types=relationship_types,
            filters=filters,
            limit=limit,
        )

        results: list[SearchResult] = []

        if plan.strategy == QueryStrategy.VECTOR_ONLY:
            results = await self.semantic_search(
                query=query,
                memory_types=memory_types,
                filters=filters,
                limit=limit,
            )

        elif plan.strategy == QueryStrategy.GRAPH_ONLY:
            # Extract entity IDs from query if possible
            graph_results = await self._execute_graph_search(query, relationship_types, limit)
            results = await self._enrich_with_vector_scores(graph_results, query)

        elif plan.strategy == QueryStrategy.VECTOR_FIRST:
            # Start with semantic search
            semantic_results = await self.semantic_search(
                query=query,
                memory_types=memory_types,
                filters=filters,
                limit=limit * 2,  # Get more for graph expansion
            )

            # Expand via graph
            expanded = await self._expand_via_graph(
                results=semantic_results,
                relationship_types=relationship_types,
                limit=limit,
            )
            results = expanded

        elif plan.strategy == QueryStrategy.GRAPH_FIRST:
            # Start with graph search
            graph_results = await self._execute_graph_search(query, relationship_types, limit * 2)

            # Enrich with vector scores
            results = await self._enrich_with_vector_scores(graph_results, query)
            results.sort(key=lambda r: r.score, reverse=True)
            results = results[:limit]

        duration = time.perf_counter() - start
        metrics.record_search(
            search_type="hybrid",
            status="success",
            duration=duration,
            result_count=len(results),
        )

        return results

    def _plan_query(
        self,
        query: str,
        memory_types: list[MemoryType] | None,
        relationship_types: list[RelationshipType] | None,
        filters: dict[str, Any] | None,
        limit: int,
    ) -> QueryPlan:
        """Plan query execution strategy.

        Args:
            query: Search query
            memory_types: Memory type filters
            relationship_types: Relationship type filters
            filters: Additional filters
            limit: Result limit

        Returns:
            Query execution plan
        """
        # Determine strategy based on query characteristics
        has_relationship_filter = relationship_types is not None and len(relationship_types) > 0
        has_entity_reference = self._has_entity_reference(query)

        if has_relationship_filter or has_entity_reference:
            if len(query.split()) < 3:
                # Short query with relationship - graph first
                strategy = QueryStrategy.GRAPH_FIRST
            else:
                # Longer query - vector first, expand with graph
                strategy = QueryStrategy.VECTOR_FIRST
        else:
            # No relationship context - vector only
            strategy = QueryStrategy.VECTOR_ONLY

        # Determine collections to search
        collections = []
        for mt in (memory_types or list(MemoryType)):
            collections.append(self.qdrant.get_collection_name(mt))

        return QueryPlan(
            strategy=strategy,
            vector_collections=collections,
            graph_query=None,
            filters=filters or {},
            limit=limit,
            use_reranking=limit > 20,
        )

    def _has_entity_reference(self, query: str) -> bool:
        """Check if query contains entity references.

        Args:
            query: Search query

        Returns:
            True if query appears to reference specific entities
        """
        # Check for common entity reference patterns
        indicators = [
            "related to",
            "depends on",
            "calls",
            "imports",
            "import ",  # "import" followed by space (singular form)
            "implements",
            "extends",
        ]
        query_lower = query.lower()
        return any(ind in query_lower for ind in indicators)

    async def _execute_graph_search(
        self,
        query: str,
        relationship_types: list[RelationshipType] | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Execute graph-based search.

        Args:
            query: Search query
            relationship_types: Relationship type filters
            limit: Maximum results

        Returns:
            Graph search results
        """
        # Build Cypher query to find relevant nodes
        rel_filter = ""
        if relationship_types:
            type_strs = [r.value for r in relationship_types]
            rel_filter = ":" + "|".join(type_strs)

        cypher = f"""
        MATCH (n:Memory)
        WHERE n.deleted = false
        AND (n.content CONTAINS $query OR n.title CONTAINS $query)
        OPTIONAL MATCH (n)-[r{rel_filter}]-(related:Memory)
        WHERE related.deleted = false
        RETURN n.id as id, labels(n) as labels, properties(n) as properties,
               collect(DISTINCT related.id) as related_ids
        LIMIT $limit
        """

        return await self.neo4j.execute_cypher(
            cypher,
            {"query": query, "limit": limit},
        )

    async def _expand_via_graph(
        self,
        results: list[SearchResult],
        relationship_types: list[RelationshipType] | None,
        limit: int,
    ) -> list[SearchResult]:
        """Expand search results using graph relationships.

        Args:
            results: Initial search results
            relationship_types: Relationship types to follow
            limit: Maximum results

        Returns:
            Expanded results with graph context
        """
        seen_ids = {r.id for r in results}
        expanded = list(results)

        for result in results[:limit // 2]:  # Expand from top results
            related = await self.neo4j.get_related(
                node_id=result.id,
                relationship_types=relationship_types,
                direction="both",
                depth=1,
                limit=3,
            )

            for rel in related:
                rel_id = rel["id"]
                if rel_id not in seen_ids:
                    seen_ids.add(rel_id)

                    # Create result with reduced score
                    expanded.append(
                        SearchResult(
                            id=rel_id,
                            memory_type=self._label_to_memory_type(rel["labels"]),
                            content=rel["properties"].get("content", ""),
                            score=result.score * 0.8,  # Reduce score for expanded
                            payload=rel["properties"],
                            relationship_path=[result.id, rel_id],
                        )
                    )

        # Sort and limit
        expanded.sort(key=lambda r: r.score, reverse=True)
        return expanded[:limit]

    async def _enrich_with_vector_scores(
        self,
        graph_results: list[dict[str, Any]],
        query: str,
    ) -> list[SearchResult]:
        """Enrich graph results with vector similarity scores.

        Args:
            graph_results: Results from graph query
            query: Original search query

        Returns:
            Results with vector scores
        """
        if not graph_results:
            return []

        # Generate query embedding
        query_embedding = await self.embedding_service.embed_for_query(query)

        results = []
        for gr in graph_results:
            memory_type = self._label_to_memory_type(gr.get("labels", []))
            collection = self.qdrant.get_collection_name(memory_type)

            # Get vector for this point
            point = await self.qdrant.get(
                collection=collection,
                point_id=gr["id"],
                with_vector=True,
            )

            if point and "embedding" in point:
                # Calculate similarity
                score = self._cosine_similarity(query_embedding, point["embedding"])
            else:
                score = 0.5  # Default score if no vector

            results.append(
                SearchResult(
                    id=str(gr["id"]),
                    memory_type=memory_type,
                    content=gr.get("properties", {}).get("content", ""),
                    score=score,
                    payload=gr.get("properties", {}),
                )
            )

        return results

    def _label_to_memory_type(self, labels: list[str]) -> MemoryType:
        """Convert Neo4j labels to memory type.

        Args:
            labels: Node labels

        Returns:
            Memory type
        """
        label_map = {
            "Requirement": MemoryType.REQUIREMENTS,
            "Design": MemoryType.DESIGN,
            "CodePattern": MemoryType.CODE_PATTERN,
            "Component": MemoryType.COMPONENT,
            "Function": MemoryType.FUNCTION,
            "TestHistory": MemoryType.TEST_HISTORY,
            "Session": MemoryType.SESSION,
            "UserPreference": MemoryType.USER_PREFERENCE,
        }

        for label in labels:
            if label in label_map:
                return label_map[label]

        return MemoryType.COMPONENT  # Default

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Calculate cosine similarity between two vectors.

        Args:
            a: First vector
            b: Second vector

        Returns:
            Cosine similarity score
        """
        import math

        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    def _build_filters(
        self,
        filters: dict[str, Any] | None,
        time_range: tuple[datetime, datetime] | None,
    ) -> dict[str, Any]:
        """Build filter dictionary for Qdrant.

        Args:
            filters: Base filters
            time_range: Optional time range filter

        Returns:
            Combined filter dictionary
        """
        result = {"deleted": False}

        if filters:
            result.update(filters)

        if time_range:
            start_time, end_time = time_range
            result["created_at"] = {
                "gte": start_time.isoformat(),
                "lte": end_time.isoformat(),
            }

        return result

    def _validate_cypher(self, cypher: str) -> None:
        """Validate Cypher query for security using allowlist approach.

        Only allows read-only MATCH queries with RETURN clauses.
        Blocks all write operations and procedure calls.

        Args:
            cypher: Cypher query string

        Raises:
            ValueError: If query contains dangerous operations or invalid structure
        """
        import re

        # Normalize query - remove comments and extra whitespace
        # Remove single-line comments
        normalized = re.sub(r"//[^\n]*", "", cypher)
        # Remove block comments (careful with nested)
        normalized = re.sub(r"/\*.*?\*/", "", normalized, flags=re.DOTALL)
        # Normalize whitespace
        normalized = " ".join(normalized.split())

        # Security checks
        if len(normalized) > 10000:
            raise ValueError("Query too long (max 10000 characters)")

        # Use a more robust check by tokenizing the query
        # Normalize to uppercase for keyword matching
        upper_normalized = normalized.upper()

        # Remove string literals to avoid false positives
        # Match both single and double quoted strings
        upper_no_strings = re.sub(r"'[^']*'", "''", upper_normalized)
        upper_no_strings = re.sub(r'"[^"]*"', '""', upper_no_strings)

        # Blocked keywords - these should NEVER appear outside string literals
        blocked_keywords = {
            # Write operations
            "CREATE", "DELETE", "DETACH DELETE", "SET", "REMOVE", "MERGE",
            # Schema operations
            "DROP", "CREATE INDEX", "CREATE CONSTRAINT", "CREATE DATABASE",
            # Procedure calls (can execute arbitrary code)
            "CALL", "YIELD",
            # Other dangerous operations
            "LOAD CSV", "USING PERIODIC COMMIT", "FOREACH",
        }

        # Check for blocked keywords using word boundaries
        for keyword in blocked_keywords:
            # Use word boundary matching to avoid false positives
            pattern = r"\b" + keyword.replace(" ", r"\s+") + r"\b"
            if re.search(pattern, upper_no_strings):
                raise ValueError(f"Query contains forbidden operation: {keyword}")

        # Verify query starts with MATCH or OPTIONAL MATCH or WITH
        # (allowing for leading whitespace)
        allowed_start_patterns = [
            r"^\s*MATCH\b",
            r"^\s*OPTIONAL\s+MATCH\b",
            r"^\s*WITH\b",
            r"^\s*UNWIND\b",  # UNWIND is read-only
        ]
        starts_valid = any(
            re.match(pattern, upper_no_strings, re.IGNORECASE)
            for pattern in allowed_start_patterns
        )
        if not starts_valid:
            raise ValueError("Query must start with MATCH, OPTIONAL MATCH, WITH, or UNWIND")

        # Verify query contains RETURN (read queries should return data)
        if not re.search(r"\bRETURN\b", upper_no_strings):
            raise ValueError("Query must contain RETURN clause")

        # Check for potential injection via unicode lookalikes
        # Only allow ASCII characters in keywords
        ascii_pattern = re.compile(r"^[\x00-\x7F]*$")
        if not ascii_pattern.match(normalized):
            # Check if non-ASCII is only in string literals
            no_strings = re.sub(r"'[^']*'", "", normalized)
            no_strings = re.sub(r'"[^"]*"', "", no_strings)
            if not ascii_pattern.match(no_strings):
                raise ValueError("Query contains non-ASCII characters outside string literals")

    def compute_ranking_score(
        self,
        similarity: float,
        importance: float,
        recency_days: int,
        access_count: int,
    ) -> float:
        """Compute final ranking score for a result.

        Args:
            similarity: Vector similarity score (0-1)
            importance: Memory importance score (0-1)
            recency_days: Days since last update
            access_count: Number of accesses

        Returns:
            Combined ranking score
        """
        # Weights for each factor
        w_similarity = 0.5
        w_importance = 0.25
        w_recency = 0.15
        w_access = 0.10

        # Normalize recency (decay over 365 days)
        recency_score = max(0.0, 1.0 - (recency_days / 365.0))

        # Normalize access (log scale, capped at 100)
        import math

        access_score = min(1.0, math.log(access_count + 1) / math.log(101))

        return (
            w_similarity * similarity
            + w_importance * importance
            + w_recency * recency_score
            + w_access * access_score
        )
