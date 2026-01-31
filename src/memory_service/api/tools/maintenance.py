"""MCP tools for memory maintenance operations."""

import json
from datetime import datetime
from typing import Any
from uuid import UUID

from memory_service.config import get_settings
from memory_service.models import MemoryType
from memory_service.utils.logging import get_logger
from memory_service.utils.path_validation import PathTraversalError, validate_output_path, validate_path

logger = get_logger(__name__)


async def normalize_memory(params: dict[str, Any]) -> dict[str, Any]:
    """Start a normalization job.

    Runs multi-phase memory normalization including:
    - snapshot: Create backup of current state
    - deduplication: Merge similar memories (>0.95 similarity)
    - orphan_detection: Remove orphaned references
    - embedding_refresh: Recompute embeddings for changed content
    - cleanup: Remove soft-deleted items past retention
    - validation: Validate normalized data
    - swap: Finalize normalization

    Args:
        params: Tool parameters including:
            - phases: Specific phases to run (optional, default: all)
            - dry_run: If true, report changes without applying (default: false)
            - _context: Injected service context

    Returns:
        Job ID and initial status
    """
    context = params["_context"]
    normalizer = context.get("normalizer")
    job_manager = context.get("job_manager")

    phases = params.get("phases")
    dry_run = params.get("dry_run", False)

    if not normalizer:
        return {
            "status": "error",
            "error": "Normalizer worker not available",
        }

    try:
        # Create job for tracking
        job_id = None
        if job_manager:
            job_id = await job_manager.create_job(
                job_type="normalize",
                parameters={
                    "phases": phases,
                    "dry_run": dry_run,
                },
            )

        # Run normalization
        result = await normalizer.normalize(
            job_id=job_id,
            phases=phases,
            dry_run=dry_run,
        )

        if job_id:
            result["job_id"] = job_id

        return result

    except Exception as e:
        logger.error("normalize_memory_failed", error=str(e))
        return {
            "status": "error",
            "error": str(e),
        }


async def normalize_status(params: dict[str, Any]) -> dict[str, Any]:
    """Get normalization job status.

    Args:
        params: Tool parameters including:
            - job_id: Job ID to check (optional - returns normalizer status if not provided)
            - _context: Injected service context

    Returns:
        Job status with progress details
    """
    context = params["_context"]
    normalizer = context.get("normalizer")
    job_manager = context.get("job_manager")

    job_id = params.get("job_id")

    if job_id:
        # Look up specific job
        if job_manager:
            job = await job_manager.get_job(job_id)
            if job:
                return job
        return {
            "job_id": job_id,
            "status": "not_found",
        }

    # Return normalizer status
    if normalizer:
        status = await normalizer.get_status()

        # Also get recent normalize jobs
        if job_manager:
            recent_jobs = await job_manager.list_jobs(job_type="normalize", limit=5)
            status["recent_jobs"] = recent_jobs

        return status

    return {
        "status": "normalizer_not_available",
    }


async def memory_statistics(params: dict[str, Any]) -> dict[str, Any]:
    """Get memory system statistics.

    Args:
        params: Tool parameters including:
            - _context: Injected service context

    Returns:
        Comprehensive statistics
    """
    context = params["_context"]
    qdrant = context["qdrant"]
    neo4j = context["neo4j"]
    embedding_service = context["embedding_service"]

    try:
        stats: dict[str, Any] = {
            "memory_counts": {},
            "sync_status": {},
            "storage": {
                "qdrant": {"connected": False},
                "neo4j": {"connected": False},
            },
            "cache": {},
        }

        # Get memory counts by type
        for memory_type in MemoryType:
            collection = qdrant.get_collection_name(memory_type)
            total = await qdrant.count(collection)
            active = await qdrant.count(collection, filters={"deleted": False})
            deleted = total - active

            stats["memory_counts"][memory_type.value] = {
                "total": total,
                "active": active,
                "deleted": deleted,
            }

        # Get sync status counts
        from memory_service.models import SyncStatus

        for memory_type in MemoryType:
            collection = qdrant.get_collection_name(memory_type)
            for status in SyncStatus:
                count = await qdrant.count(
                    collection,
                    filters={"sync_status": status.value},
                )
                stats["sync_status"].setdefault(status.value, 0)
                stats["sync_status"][status.value] += count

        # Check storage health
        stats["storage"]["qdrant"]["connected"] = await qdrant.health_check()
        stats["storage"]["neo4j"]["connected"] = await neo4j.health_check()

        # Get cache stats
        stats["cache"] = await embedding_service.get_cache_stats()

        # Calculate totals
        stats["totals"] = {
            "memories": sum(
                c["active"] for c in stats["memory_counts"].values()
            ),
            "pending_sync": stats["sync_status"].get("pending", 0),
            "failed_sync": stats["sync_status"].get("failed", 0),
        }

        return stats

    except Exception as e:
        logger.error("memory_statistics_failed", error=str(e))
        return {"error": str(e)}


async def export_memory(params: dict[str, Any]) -> dict[str, Any]:
    """Export memories to JSONL format.

    Args:
        params: Tool parameters including:
            - memory_types: Types to export (optional, default: all)
            - filters: Additional filters
            - output_path: Path to write export (optional, must be within project dir)
            - _context: Injected service context

    Returns:
        Export results or JSONL data
    """
    context = params["_context"]
    qdrant = context["qdrant"]
    settings = get_settings()

    memory_types_str = params.get("memory_types")
    filters = params.get("filters", {})
    output_path = params.get("output_path")

    try:
        # Validate output path if provided
        validated_output_path = None
        if output_path:
            try:
                validated_output_path = validate_output_path(
                    output_path,
                    settings.project_path,
                    create_parent=True,
                )
            except PathTraversalError:
                logger.warning("export_memory_path_traversal", output_path=output_path)
                return {
                    "status": "error",
                    "error": f"Output path must be within project directory: {settings.project_path}",
                }

        # Determine types to export
        if memory_types_str:
            memory_types = [MemoryType(t) for t in memory_types_str]
        else:
            memory_types = list(MemoryType)

        export_data = []
        export_filters = {"deleted": False, **filters}

        for memory_type in memory_types:
            collection = qdrant.get_collection_name(memory_type)
            offset = None

            while True:
                points, next_offset = await qdrant.scroll(
                    collection=collection,
                    filters=export_filters,
                    limit=100,
                    offset=offset,
                    with_vectors=False,
                )

                for point in points:
                    export_data.append({
                        "id": point["id"],
                        "type": memory_type.value,
                        **point["payload"],
                    })

                if not next_offset:
                    break
                offset = next_offset

        if validated_output_path:
            # Write to validated file path
            with open(validated_output_path, "w") as f:
                for item in export_data:
                    f.write(json.dumps(item, default=str) + "\n")

            return {
                "status": "exported",
                "output_path": str(validated_output_path),
                "memory_count": len(export_data),
            }
        else:
            # Return first 100 items (to avoid huge response)
            return {
                "status": "success",
                "memory_count": len(export_data),
                "sample": export_data[:100],
                "truncated": len(export_data) > 100,
            }

    except Exception as e:
        logger.error("export_memory_failed", error=str(e))
        return {"error": str(e)}


async def import_memory(params: dict[str, Any]) -> dict[str, Any]:
    """Import memories from JSONL format.

    Args:
        params: Tool parameters including:
            - input_path: Path to JSONL file (must be within project dir)
            - or data: JSONL data as string
            - conflict_resolution: "skip", "overwrite", or "error" (default: "skip")
            - _context: Injected service context

    Returns:
        Import results
    """
    context = params["_context"]
    memory_manager = context["memory_manager"]
    settings = get_settings()

    input_path = params.get("input_path")
    data = params.get("data")
    conflict_resolution = params.get("conflict_resolution", "skip")

    try:
        # Parse input
        items = []
        if input_path:
            # Validate input path
            try:
                validated_input_path = validate_path(input_path, settings.project_path)
            except PathTraversalError:
                logger.warning("import_memory_path_traversal", input_path=input_path)
                return {
                    "status": "error",
                    "error": f"Input path must be within project directory: {settings.project_path}",
                }
            except FileNotFoundError:
                return {
                    "status": "error",
                    "error": f"File not found: {input_path}",
                }

            with open(validated_input_path) as f:
                for line in f:
                    if line.strip():
                        items.append(json.loads(line))
        elif data:
            for line in data.split("\n"):
                if line.strip():
                    items.append(json.loads(line))
        else:
            return {"error": "Either input_path or data is required"}

        # Import memories
        imported = 0
        skipped = 0
        overwritten = 0
        errors = []

        # Memory type to model class mapping
        from memory_service.models import (
            RequirementsMemory,
            DesignMemory,
            CodePatternMemory,
            ComponentMemory,
            FunctionMemory,
            TestHistoryMemory,
            SessionMemory,
            UserPreferenceMemory,
        )

        type_to_model = {
            MemoryType.REQUIREMENTS: RequirementsMemory,
            MemoryType.DESIGN: DesignMemory,
            MemoryType.CODE_PATTERN: CodePatternMemory,
            MemoryType.COMPONENT: ComponentMemory,
            MemoryType.FUNCTION: FunctionMemory,
            MemoryType.TEST_HISTORY: TestHistoryMemory,
            MemoryType.SESSION: SessionMemory,
            MemoryType.USER_PREFERENCE: UserPreferenceMemory,
        }

        for item in items:
            memory_type_str = item.pop("type", None)
            if not memory_type_str:
                errors.append({"item": str(item)[:100], "error": "Missing type"})
                continue

            try:
                memory_type = MemoryType(memory_type_str)
                model_class = type_to_model.get(memory_type)
                if not model_class:
                    errors.append({"item": str(item)[:100], "error": f"Unknown type: {memory_type_str}"})
                    continue

                # Handle UUID conversion
                if "id" in item:
                    item["id"] = UUID(item["id"]) if isinstance(item["id"], str) else item["id"]

                # Remove embedding if present (will be regenerated)
                item.pop("embedding", None)

                # Create memory model
                memory = model_class(type=memory_type, **item)

                # Check if memory already exists
                existing = await memory_manager.get_memory(str(memory.id), memory_type)

                if existing:
                    if conflict_resolution == "skip":
                        skipped += 1
                        continue
                    elif conflict_resolution == "error":
                        errors.append({"item": str(item)[:100], "error": "Memory already exists"})
                        continue
                    elif conflict_resolution == "overwrite":
                        # Update existing memory
                        await memory_manager.update_memory(
                            memory_id=str(memory.id),
                            memory_type=memory_type,
                            updates={k: v for k, v in item.items() if k not in ("id", "type")},
                        )
                        overwritten += 1
                        continue

                # Add new memory
                await memory_manager.add_memory(memory)
                imported += 1

            except Exception as e:
                if conflict_resolution == "skip":
                    skipped += 1
                elif conflict_resolution == "error":
                    errors.append({"item": str(item)[:100], "error": str(e)})
                else:
                    skipped += 1

        return {
            "status": "completed",
            "imported": imported,
            "skipped": skipped,
            "overwritten": overwritten,
            "errors": errors[:10],  # Limit error list
            "total_errors": len(errors),
        }

    except Exception as e:
        logger.error("import_memory_failed", error=str(e))
        return {"error": str(e)}
