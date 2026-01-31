"""MCP tools for design analysis and consistency checking."""

from typing import Any

from memory_service.models import MemoryType, RelationshipType
from memory_service.utils.logging import get_logger

logger = get_logger(__name__)


async def check_consistency(params: dict[str, Any]) -> dict[str, Any]:
    """Check if a component follows established patterns.

    Args:
        params: Tool parameters including:
            - component_id: Component to check
            - pattern_types: Types of patterns to check against
            - _context: Injected service context

    Returns:
        Consistency report with deviations
    """
    context = params["_context"]
    query_engine = context["query_engine"]
    qdrant = context["qdrant"]
    embedding_service = context["embedding_service"]

    component_id = params.get("component_id")
    pattern_types = params.get("pattern_types", ["Template", "Convention"])

    try:
        # Get the component
        component = await qdrant.get(
            collection=qdrant.get_collection_name(MemoryType.COMPONENT),
            point_id=component_id,
            with_vector=True,
        )

        if not component:
            return {"error": "Component not found"}

        # Find similar patterns
        results = await qdrant.search(
            collection=qdrant.get_collection_name(MemoryType.CODE_PATTERN),
            vector=component.get("embedding", []),
            limit=5,
            filters={
                "deleted": False,
                "pattern_type": {"in": pattern_types},
            },
            score_threshold=0.7,
        )

        matching_patterns = []
        potential_deviations = []

        for result in results:
            pattern_info = {
                "pattern_id": result["id"],
                "pattern_name": result["payload"].get("pattern_name"),
                "pattern_type": result["payload"].get("pattern_type"),
                "similarity": round(result["score"], 4),
            }

            if result["score"] >= 0.85:
                matching_patterns.append(pattern_info)
            else:
                potential_deviations.append({
                    **pattern_info,
                    "deviation_score": round(1 - result["score"], 4),
                })

        return {
            "component_id": component_id,
            "component_name": component.get("name"),
            "matching_patterns": matching_patterns,
            "potential_deviations": potential_deviations,
            "consistency_score": round(
                sum(r["score"] for r in results) / len(results) if results else 0,
                4,
            ),
        }

    except Exception as e:
        logger.error("check_consistency_failed", error=str(e))
        return {"error": str(e)}


async def validate_fix(params: dict[str, Any]) -> dict[str, Any]:
    """Validate that a proposed fix aligns with design.

    Args:
        params: Tool parameters including:
            - fix_description: Description of the fix
            - affected_component: Component being fixed
            - _context: Injected service context

    Returns:
        Validation result with alignment score
    """
    context = params["_context"]
    query_engine = context["query_engine"]
    embedding_service = context["embedding_service"]

    fix_description = params.get("fix_description")
    affected_component = params.get("affected_component")

    try:
        # Search for related design decisions
        design_results = await query_engine.semantic_search(
            query=fix_description,
            memory_types=[MemoryType.DESIGN],
            limit=5,
        )

        # Search for related requirements
        req_results = await query_engine.semantic_search(
            query=fix_description,
            memory_types=[MemoryType.REQUIREMENTS],
            limit=5,
        )

        # Calculate alignment scores
        design_alignment = (
            sum(r.score for r in design_results) / len(design_results)
            if design_results
            else 0
        )
        req_alignment = (
            sum(r.score for r in req_results) / len(req_results)
            if req_results
            else 0
        )

        overall_alignment = (design_alignment * 0.6 + req_alignment * 0.4)

        return {
            "fix_description": fix_description[:200],
            "affected_component": affected_component,
            "design_alignment_score": round(design_alignment, 4),
            "requirements_alignment_score": round(req_alignment, 4),
            "overall_alignment_score": round(overall_alignment, 4),
            "related_designs": [
                {
                    "id": r.id,
                    "title": r.payload.get("title"),
                    "design_type": r.payload.get("design_type"),
                    "relevance": round(r.score, 4),
                }
                for r in design_results[:3]
            ],
            "related_requirements": [
                {
                    "id": r.id,
                    "requirement_id": r.payload.get("requirement_id"),
                    "title": r.payload.get("title"),
                    "relevance": round(r.score, 4),
                }
                for r in req_results[:3]
            ],
            "recommendation": (
                "Fix aligns well with design"
                if overall_alignment >= 0.7
                else "Review fix against design documents"
            ),
        }

    except Exception as e:
        logger.error("validate_fix_failed", error=str(e))
        return {"error": str(e)}


async def get_design_context(params: dict[str, Any]) -> dict[str, Any]:
    """Get design context for a component or feature.

    Args:
        params: Tool parameters including:
            - component_id: Component to get context for
            - or
            - query: Description of feature/area
            - _context: Injected service context

    Returns:
        Related requirements, ADRs, and patterns
    """
    context = params["_context"]
    query_engine = context["query_engine"]
    neo4j = context["neo4j"]

    component_id = params.get("component_id")
    query = params.get("query")

    try:
        design_context: dict[str, Any] = {
            "requirements": [],
            "designs": [],
            "patterns": [],
        }

        if component_id:
            # Get by traversing relationships from component
            related = await neo4j.get_related(
                node_id=component_id,
                relationship_types=[
                    RelationshipType.SATISFIED_BY,
                    RelationshipType.AFFECTS,
                    RelationshipType.FOLLOWS_PATTERN,
                ],
                direction="incoming",
                depth=2,
            )

            for r in related:
                labels = r.get("labels", [])
                props = r.get("properties", {})

                if "Requirement" in labels:
                    design_context["requirements"].append({
                        "id": r["id"],
                        "requirement_id": props.get("requirement_id"),
                        "title": props.get("title"),
                        "priority": props.get("priority"),
                    })
                elif "Design" in labels:
                    design_context["designs"].append({
                        "id": r["id"],
                        "title": props.get("title"),
                        "design_type": props.get("design_type"),
                        "status": props.get("status"),
                    })
                elif "CodePattern" in labels:
                    design_context["patterns"].append({
                        "id": r["id"],
                        "pattern_name": props.get("pattern_name"),
                        "pattern_type": props.get("pattern_type"),
                    })

        elif query:
            # Search semantically
            req_results = await query_engine.semantic_search(
                query=query,
                memory_types=[MemoryType.REQUIREMENTS],
                limit=5,
            )
            design_results = await query_engine.semantic_search(
                query=query,
                memory_types=[MemoryType.DESIGN],
                limit=5,
            )
            pattern_results = await query_engine.semantic_search(
                query=query,
                memory_types=[MemoryType.CODE_PATTERN],
                limit=3,
            )

            design_context["requirements"] = [
                {
                    "id": r.id,
                    "requirement_id": r.payload.get("requirement_id"),
                    "title": r.payload.get("title"),
                    "relevance": round(r.score, 4),
                }
                for r in req_results
            ]
            design_context["designs"] = [
                {
                    "id": r.id,
                    "title": r.payload.get("title"),
                    "design_type": r.payload.get("design_type"),
                    "relevance": round(r.score, 4),
                }
                for r in design_results
            ]
            design_context["patterns"] = [
                {
                    "id": r.id,
                    "pattern_name": r.payload.get("pattern_name"),
                    "relevance": round(r.score, 4),
                }
                for r in pattern_results
            ]

        else:
            return {"error": "Either component_id or query is required"}

        return design_context

    except Exception as e:
        logger.error("get_design_context_failed", error=str(e))
        return {"error": str(e)}


async def trace_requirements(params: dict[str, Any]) -> dict[str, Any]:
    """Trace a requirement to its implementations and tests.

    Args:
        params: Tool parameters including:
            - requirement_id: Requirement ID to trace
            - _context: Injected service context

    Returns:
        Traceability report
    """
    context = params["_context"]
    query_engine = context["query_engine"]
    neo4j = context["neo4j"]
    qdrant = context["qdrant"]

    requirement_id = params.get("requirement_id")

    try:
        # Find the requirement
        results = await qdrant.scroll(
            collection=qdrant.get_collection_name(MemoryType.REQUIREMENTS),
            filters={
                "requirement_id": requirement_id,
                "deleted": False,
            },
            limit=1,
        )

        points, _ = results
        if not points:
            return {"error": f"Requirement not found: {requirement_id}"}

        req_point = points[0]
        req_memory_id = req_point["id"]

        # Get implementing components
        components = await neo4j.get_related(
            node_id=req_memory_id,
            relationship_types=[RelationshipType.SATISFIED_BY],
            direction="outgoing",
            depth=1,
        )

        # Get verifying tests
        tests = await neo4j.get_related(
            node_id=req_memory_id,
            relationship_types=[RelationshipType.TESTED_BY],
            direction="outgoing",
            depth=1,
        )

        # Get related designs
        designs = await neo4j.get_related(
            node_id=req_memory_id,
            relationship_types=[RelationshipType.ADDRESSES],
            direction="incoming",
            depth=1,
        )

        return {
            "requirement": {
                "id": req_memory_id,
                "requirement_id": requirement_id,
                "title": req_point["payload"].get("title"),
                "status": req_point["payload"].get("status"),
                "priority": req_point["payload"].get("priority"),
            },
            "implementing_components": [
                {
                    "id": c["id"],
                    "name": c["properties"].get("name"),
                    "file_path": c["properties"].get("file_path"),
                }
                for c in components
            ],
            "verifying_tests": [
                {
                    "id": t["id"],
                    "test_name": t["properties"].get("test_name"),
                    "test_file": t["properties"].get("test_file"),
                    "status": t["properties"].get("status"),
                }
                for t in tests
            ],
            "related_designs": [
                {
                    "id": d["id"],
                    "title": d["properties"].get("title"),
                    "design_type": d["properties"].get("design_type"),
                }
                for d in designs
            ],
            "coverage": {
                "implementation_count": len(components),
                "test_count": len(tests),
                "design_count": len(designs),
            },
        }

    except Exception as e:
        logger.error("trace_requirements_failed", error=str(e))
        return {"error": str(e)}
