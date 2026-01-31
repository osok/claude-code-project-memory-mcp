"""MCP tools for search operations."""

from datetime import datetime
from typing import Any
from uuid import UUID

from memory_service.models import MemoryType, RelationshipType
from memory_service.core.query_engine import QueryEngine
from memory_service.utils.logging import get_logger

logger = get_logger(__name__)


async def memory_search(params: dict[str, Any]) -> dict[str, Any]:
    """Search memories using semantic similarity.

    Args:
        params: Tool parameters including:
            - query: Search query text
            - memory_types: Filter by memory types (optional)
            - time_range: Filter by time range (optional)
            - limit: Maximum results (default: 10)
            - _context: Injected service context

    Returns:
        Search results with relevance scores
    """
    context = params["_context"]
    query_engine: QueryEngine = context["query_engine"]

    query = params["query"]
    memory_types_str = params.get("memory_types")
    time_range_data = params.get("time_range")
    limit = params.get("limit", 10)

    # Parse memory types
    memory_types = None
    if memory_types_str:
        memory_types = [MemoryType(t) for t in memory_types_str]

    # Parse time range
    time_range = None
    if time_range_data:
        start = datetime.fromisoformat(time_range_data["start"])
        end = datetime.fromisoformat(time_range_data["end"])
        time_range = (start, end)

    try:
        results = await query_engine.semantic_search(
            query=query,
            memory_types=memory_types,
            time_range=time_range,
            limit=limit,
        )

        return {
            "query": query,
            "result_count": len(results),
            "results": [
                {
                    "id": r.id,
                    "memory_type": r.memory_type.value,
                    "content": r.content[:500],  # Truncate for response
                    "score": round(r.score, 4),
                    "metadata": {
                        k: v
                        for k, v in r.payload.items()
                        if k not in ("content", "embedding")
                    },
                }
                for r in results
            ],
        }

    except Exception as e:
        logger.error("memory_search_failed", error=str(e))
        return {"error": str(e)}


async def code_search(params: dict[str, Any]) -> dict[str, Any]:
    """Search for similar code patterns.

    Args:
        params: Tool parameters including:
            - query: Code snippet or description
            - language: Programming language filter (optional)
            - limit: Maximum results (default: 10)
            - _context: Injected service context

    Returns:
        Matching functions and code patterns
    """
    context = params["_context"]
    query_engine: QueryEngine = context["query_engine"]

    query = params["query"]
    language = params.get("language")
    limit = params.get("limit", 10)

    # Search function and code_pattern types
    memory_types = [MemoryType.FUNCTION, MemoryType.CODE_PATTERN]

    # Build filters
    filters: dict[str, Any] | None = None
    if language:
        filters = {"language": language}

    try:
        results = await query_engine.semantic_search(
            query=query,
            memory_types=memory_types,
            filters=filters,
            limit=limit,
        )

        return {
            "query": query[:100],  # Truncate query in response
            "language_filter": language,
            "result_count": len(results),
            "results": [
                {
                    "id": r.id,
                    "type": r.memory_type.value,
                    "name": r.payload.get("name") or r.payload.get("pattern_name"),
                    "file_path": r.payload.get("file_path"),
                    "signature": r.payload.get("signature"),
                    "content": r.content[:300],
                    "score": round(r.score, 4),
                    "start_line": r.payload.get("start_line"),
                    "end_line": r.payload.get("end_line"),
                }
                for r in results
            ],
        }

    except Exception as e:
        logger.error("code_search_failed", error=str(e))
        return {"error": str(e)}


async def graph_query(params: dict[str, Any]) -> dict[str, Any]:
    """Execute a Cypher graph query.

    Args:
        params: Tool parameters including:
            - cypher: Cypher query (read-only operations only)
            - parameters: Query parameters (optional)
            - _context: Injected service context

    Returns:
        Query results
    """
    context = params["_context"]
    query_engine: QueryEngine = context["query_engine"]

    cypher = params["cypher"]
    parameters = params.get("parameters", {})

    try:
        results = await query_engine.graph_query(cypher, parameters)

        return {
            "result_count": len(results),
            "results": results,
        }

    except ValueError as e:
        # Query validation error
        return {"error": str(e)}
    except Exception as e:
        logger.error("graph_query_failed", error=str(e))
        return {"error": str(e)}


async def find_duplicates(params: dict[str, Any]) -> dict[str, Any]:
    """Find duplicate functions or code patterns.

    Args:
        params: Tool parameters including:
            - code: Code to check for duplicates
            - language: Programming language (optional)
            - threshold: Similarity threshold (default: 0.85)
            - _context: Injected service context

    Returns:
        List of potential duplicates with similarity scores
    """
    context = params["_context"]
    query_engine: QueryEngine = context["query_engine"]
    embedding_service = context["embedding_service"]
    qdrant = context["qdrant"]

    code = params["code"]
    language = params.get("language")
    threshold = params.get("threshold", 0.85)

    # Validate threshold
    if not 0.7 <= threshold <= 0.95:
        return {"error": "Threshold must be between 0.70 and 0.95"}

    try:
        # Generate embedding for the code
        embedding = await embedding_service.embed_for_query(code)

        # Search in function collection
        collection = qdrant.get_collection_name(MemoryType.FUNCTION)

        filters: dict[str, Any] = {"deleted": False}
        if language:
            filters["language"] = language

        results = await qdrant.search(
            collection=collection,
            vector=embedding,
            limit=10,
            filters=filters,
            score_threshold=threshold,
        )

        duplicates = []
        for result in results:
            duplicates.append({
                "id": result["id"],
                "name": result["payload"].get("name"),
                "file_path": result["payload"].get("file_path"),
                "signature": result["payload"].get("signature"),
                "start_line": result["payload"].get("start_line"),
                "end_line": result["payload"].get("end_line"),
                "similarity": round(result["score"], 4),
            })

        return {
            "threshold": threshold,
            "language_filter": language,
            "duplicate_count": len(duplicates),
            "duplicates": duplicates,
        }

    except Exception as e:
        logger.error("find_duplicates_failed", error=str(e))
        return {"error": str(e)}


async def get_related(params: dict[str, Any]) -> dict[str, Any]:
    """Get entities related by graph relationships.

    Args:
        params: Tool parameters including:
            - entity_id: Starting entity ID
            - relationship_types: Filter by relationship types (optional)
            - direction: "outgoing", "incoming", or "both" (default: "both")
            - depth: Traversal depth (default: 1, max: 5)
            - _context: Injected service context

    Returns:
        Related entities with relationship information
    """
    context = params["_context"]
    query_engine: QueryEngine = context["query_engine"]

    entity_id = params["entity_id"]
    relationship_types_str = params.get("relationship_types")
    direction = params.get("direction", "both")
    depth = min(params.get("depth", 1), 5)

    # Parse relationship types
    relationship_types = None
    if relationship_types_str:
        relationship_types = [RelationshipType(t) for t in relationship_types_str]

    try:
        results = await query_engine.get_related(
            entity_id=entity_id,
            relationship_types=relationship_types,
            direction=direction,
            depth=depth,
        )

        return {
            "entity_id": entity_id,
            "direction": direction,
            "depth": depth,
            "related_count": len(results),
            "related": [
                {
                    "id": r["id"],
                    "labels": r["labels"],
                    "relationship_type": r.get("relationship_type"),
                    "properties": {
                        k: v
                        for k, v in r.get("properties", {}).items()
                        if k not in ("embedding", "content") or len(str(v)) < 200
                    },
                }
                for r in results
            ],
        }

    except Exception as e:
        logger.error("get_related_failed", error=str(e))
        return {"error": str(e)}
