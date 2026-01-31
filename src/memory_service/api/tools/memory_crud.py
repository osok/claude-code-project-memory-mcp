"""MCP tools for memory CRUD operations."""

from typing import Any
from uuid import UUID

from memory_service.models import MemoryType
from memory_service.models.memories import (
    CodePatternMemory,
    ComponentMemory,
    DesignMemory,
    FunctionMemory,
    RequirementsMemory,
    SessionMemory,
    TestHistoryMemory,
    UserPreferenceMemory,
)
from memory_service.core.memory_manager import MemoryManager
from memory_service.utils.logging import get_logger

logger = get_logger(__name__)

# Memory type to class mapping
MEMORY_CLASSES = {
    "requirements": RequirementsMemory,
    "design": DesignMemory,
    "code_pattern": CodePatternMemory,
    "component": ComponentMemory,
    "function": FunctionMemory,
    "test_history": TestHistoryMemory,
    "session": SessionMemory,
    "user_preference": UserPreferenceMemory,
}


async def memory_add(params: dict[str, Any]) -> dict[str, Any]:
    """Add a new memory to the system.

    Args:
        params: Tool parameters including:
            - memory_type: Type of memory to create
            - content: Primary content for embedding
            - metadata: Type-specific metadata
            - relationships: Relationships to create
            - _context: Injected service context

    Returns:
        Result with memory_id and any conflicts
    """
    context = params["_context"]
    memory_manager: MemoryManager = context["memory_manager"]

    memory_type_str = params["memory_type"]
    content = params["content"]
    metadata = params.get("metadata", {})
    relationships = params.get("relationships", [])

    # Get memory class
    memory_class = MEMORY_CLASSES.get(memory_type_str)
    if not memory_class:
        return {"error": f"Unknown memory type: {memory_type_str}"}

    # Build memory data
    memory_data = {
        "content": content,
        **metadata,
    }

    try:
        # Create memory instance
        memory = memory_class(**memory_data)

        # Add to system
        memory_id, conflicts = await memory_manager.add_memory(memory)

        # Create relationships if specified
        if relationships:
            neo4j = context["neo4j"]
            for rel in relationships:
                await neo4j.create_relationship(
                    source_id=memory_id,
                    target_id=rel["target_id"],
                    relationship_type=rel["type"],
                    properties=rel.get("properties"),
                )

        return {
            "memory_id": str(memory_id),
            "memory_type": memory_type_str,
            "conflicts": conflicts,
            "status": "created",
        }

    except Exception as e:
        logger.error("memory_add_failed", error=str(e))
        return {"error": str(e)}


async def memory_update(params: dict[str, Any]) -> dict[str, Any]:
    """Update an existing memory.

    Args:
        params: Tool parameters including:
            - memory_id: ID of memory to update
            - memory_type: Type of memory
            - content: New content (optional)
            - metadata: Fields to update (optional)
            - _context: Injected service context

    Returns:
        Result with updated memory details
    """
    context = params["_context"]
    memory_manager: MemoryManager = context["memory_manager"]

    memory_id = UUID(params["memory_id"])
    memory_type = MemoryType(params["memory_type"])

    # Build updates
    updates: dict[str, Any] = {}
    if "content" in params:
        updates["content"] = params["content"]
    if "metadata" in params:
        updates.update(params["metadata"])

    if not updates:
        return {"error": "No updates provided"}

    try:
        updated = await memory_manager.update_memory(
            memory_id=memory_id,
            memory_type=memory_type,
            updates=updates,
        )

        if updated:
            return {
                "memory_id": str(memory_id),
                "memory_type": memory_type.value,
                "status": "updated",
            }
        else:
            return {"error": "Memory not found"}

    except Exception as e:
        logger.error("memory_update_failed", error=str(e))
        return {"error": str(e)}


async def memory_delete(params: dict[str, Any]) -> dict[str, Any]:
    """Delete a memory.

    Args:
        params: Tool parameters including:
            - memory_id: ID of memory to delete
            - memory_type: Type of memory
            - hard_delete: Whether to hard delete (default: soft delete)
            - _context: Injected service context

    Returns:
        Result with deletion status
    """
    context = params["_context"]
    memory_manager: MemoryManager = context["memory_manager"]

    memory_id = UUID(params["memory_id"])
    memory_type = MemoryType(params["memory_type"])
    hard_delete = params.get("hard_delete", False)

    try:
        deleted = await memory_manager.delete_memory(
            memory_id=memory_id,
            memory_type=memory_type,
            soft_delete=not hard_delete,
        )

        return {
            "memory_id": str(memory_id),
            "status": "deleted" if deleted else "not_found",
            "hard_delete": hard_delete,
        }

    except Exception as e:
        logger.error("memory_delete_failed", error=str(e))
        return {"error": str(e)}


async def memory_get(params: dict[str, Any]) -> dict[str, Any]:
    """Retrieve a memory by ID.

    Args:
        params: Tool parameters including:
            - memory_id: ID of memory to retrieve
            - memory_type: Type of memory
            - include_relationships: Whether to include relationships
            - _context: Injected service context

    Returns:
        Memory data or error
    """
    context = params["_context"]
    memory_manager: MemoryManager = context["memory_manager"]
    neo4j = context["neo4j"]

    memory_id = UUID(params["memory_id"])
    memory_type = MemoryType(params["memory_type"])
    include_relationships = params.get("include_relationships", False)

    try:
        memory = await memory_manager.get_memory(
            memory_id=memory_id,
            memory_type=memory_type,
            include_embedding=False,
        )

        if not memory:
            return {"error": "Memory not found"}

        result = memory.model_dump(mode="json", exclude={"embedding"})

        # Get relationships if requested
        if include_relationships:
            related = await neo4j.get_related(
                node_id=memory_id,
                direction="both",
                depth=1,
                limit=50,
            )
            result["relationships"] = related

        return result

    except Exception as e:
        logger.error("memory_get_failed", error=str(e))
        return {"error": str(e)}


async def memory_bulk_add(params: dict[str, Any]) -> dict[str, Any]:
    """Add multiple memories in batch.

    Args:
        params: Tool parameters including:
            - memories: List of memory objects to add
            - _context: Injected service context

    Returns:
        Result with added IDs and errors
    """
    context = params["_context"]
    memory_manager: MemoryManager = context["memory_manager"]

    memories_data = params.get("memories", [])
    if not memories_data:
        return {"error": "No memories provided"}

    # Parse memories
    memories = []
    parse_errors = []

    for i, mem_data in enumerate(memories_data):
        memory_type_str = mem_data.get("memory_type")
        memory_class = MEMORY_CLASSES.get(memory_type_str)

        if not memory_class:
            parse_errors.append({
                "index": i,
                "error": f"Unknown memory type: {memory_type_str}",
            })
            continue

        try:
            # Build memory from data
            memory = memory_class(**{k: v for k, v in mem_data.items() if k != "memory_type"})
            memories.append(memory)
        except Exception as e:
            parse_errors.append({
                "index": i,
                "error": str(e),
            })

    if not memories:
        return {
            "added_count": 0,
            "errors": parse_errors,
        }

    try:
        added_ids, add_errors = await memory_manager.bulk_add_memories(memories)

        return {
            "added_count": len(added_ids),
            "added_ids": [str(id) for id in added_ids],
            "errors": parse_errors + add_errors,
        }

    except Exception as e:
        logger.error("memory_bulk_add_failed", error=str(e))
        return {"error": str(e)}
