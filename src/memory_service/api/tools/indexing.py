"""MCP tools for codebase indexing."""

from typing import Any

from memory_service.config import get_settings
from memory_service.utils.logging import get_logger
from memory_service.utils.path_validation import PathTraversalError, validate_path

logger = get_logger(__name__)


async def index_file(params: dict[str, Any]) -> dict[str, Any]:
    """Index a single file.

    Parses the file, extracts functions and classes, and stores them
    as memories for semantic search and relationship tracking.

    Args:
        params: Tool parameters including:
            - file_path: Path to file to index
            - force: Force re-index even if unchanged (default: false)
            - _context: Injected service context

    Returns:
        Indexing result with extracted entity counts
    """
    context = params["_context"]
    indexer = context.get("indexer")
    settings = get_settings()

    file_path = params.get("file_path")
    force = params.get("force", False)

    if not file_path:
        return {"error": "file_path is required"}

    if not indexer:
        return {
            "status": "error",
            "error": "Indexer worker not available",
        }

    # Validate path is within project directory
    try:
        validated_path = validate_path(file_path, settings.project_path)
    except PathTraversalError:
        logger.warning("index_file_path_traversal", file_path=file_path)
        return {
            "status": "error",
            "error": f"Path must be within project directory: {settings.project_path}",
        }
    except FileNotFoundError:
        return {
            "status": "error",
            "error": f"File not found: {file_path}",
        }

    try:
        result = await indexer.index_file(str(validated_path), force=force)
        return result
    except Exception as e:
        logger.error("index_file_tool_failed", file_path=file_path, error=str(e))
        return {
            "status": "error",
            "file_path": file_path,
            "error": str(e),
        }


async def index_directory(params: dict[str, Any]) -> dict[str, Any]:
    """Index a directory recursively.

    Parses all supported source files, extracts code elements, and stores
    them as memories. Returns a job ID for tracking progress.

    Args:
        params: Tool parameters including:
            - directory_path: Path to directory to index
            - extensions: File extensions to include (optional)
            - exclude: Patterns to exclude (optional)
            - force: Force re-index all files (default: false)
            - _context: Injected service context

    Returns:
        Job ID for tracking progress or immediate result for small directories
    """
    context = params["_context"]
    indexer = context.get("indexer")
    job_manager = context.get("job_manager")
    settings = get_settings()

    directory_path = params.get("directory_path")
    extensions = params.get("extensions")
    exclude = params.get("exclude")
    force = params.get("force", False)

    if not directory_path:
        return {"error": "directory_path is required"}

    if not indexer:
        return {
            "status": "error",
            "error": "Indexer worker not available",
        }

    # Validate path is within project directory
    try:
        validated_path = validate_path(directory_path, settings.project_path)
    except PathTraversalError:
        logger.warning("index_directory_path_traversal", directory_path=directory_path)
        return {
            "status": "error",
            "error": f"Path must be within project directory: {settings.project_path}",
        }
    except FileNotFoundError:
        return {
            "status": "error",
            "error": f"Directory not found: {directory_path}",
        }

    try:
        # Create a job for tracking
        job_id = None
        if job_manager:
            job_id = await job_manager.create_job(
                job_type="index",
                parameters={
                    "directory_path": str(validated_path),
                    "extensions": extensions,
                    "exclude": exclude,
                    "force": force,
                },
            )

        # Run indexing
        result = await indexer.index_directory(
            directory=str(validated_path),
            job_id=job_id,
            extensions=extensions,
            exclude_patterns=exclude,
            force=force,
        )

        if job_id:
            result["job_id"] = job_id

        return result

    except Exception as e:
        logger.error("index_directory_tool_failed", directory=directory_path, error=str(e))
        return {
            "status": "error",
            "directory_path": directory_path,
            "error": str(e),
        }


async def index_status(params: dict[str, Any]) -> dict[str, Any]:
    """Get indexing job status or overall statistics.

    Args:
        params: Tool parameters including:
            - job_id: Optional job ID (returns overall stats if not provided)
            - _context: Injected service context

    Returns:
        Job status or overall indexing statistics
    """
    context = params["_context"]
    qdrant = context["qdrant"]
    job_manager = context.get("job_manager")

    job_id = params.get("job_id")

    if job_id:
        # Look up specific job status
        if job_manager:
            job = await job_manager.get_job(job_id)
            if job:
                return job
        return {
            "job_id": job_id,
            "status": "not_found",
            "message": "Job not found",
        }

    # Return overall stats
    try:
        from memory_service.models import MemoryType

        stats = {
            "function_count": 0,
            "component_count": 0,
            "total_indexed": 0,
        }

        # Count indexed functions
        function_count = await qdrant.count(
            collection=qdrant.get_collection_name(MemoryType.FUNCTION),
            filters={"deleted": False},
        )
        # Count indexed components
        component_count = await qdrant.count(
            collection=qdrant.get_collection_name(MemoryType.COMPONENT),
            filters={"deleted": False},
        )

        stats["function_count"] = function_count
        stats["component_count"] = component_count
        stats["total_indexed"] = function_count + component_count

        # Add job list if job manager available
        if job_manager:
            recent_jobs = await job_manager.list_jobs(job_type="index", limit=5)
            stats["recent_jobs"] = recent_jobs

        return stats

    except Exception as e:
        logger.error("index_status_failed", error=str(e))
        return {"error": str(e)}


async def reindex(params: dict[str, Any]) -> dict[str, Any]:
    """Trigger reindexing of the codebase.

    Args:
        params: Tool parameters including:
            - directory_path: Directory to reindex (required)
            - scope: "full" (clear and reindex) or "changed" (incremental, default)
            - extensions: File extensions to include (optional)
            - exclude: Patterns to exclude (optional)
            - _context: Injected service context

    Returns:
        Job ID for tracking progress
    """
    context = params["_context"]
    indexer = context.get("indexer")
    job_manager = context.get("job_manager")
    settings = get_settings()

    directory_path = params.get("directory_path")
    scope = params.get("scope", "changed")
    extensions = params.get("extensions")
    exclude = params.get("exclude")

    if not directory_path:
        return {"error": "directory_path is required"}

    if not indexer:
        return {
            "status": "error",
            "error": "Indexer worker not available",
        }

    # Validate path is within project directory
    try:
        validated_path = validate_path(directory_path, settings.project_path)
    except PathTraversalError:
        logger.warning("reindex_path_traversal", directory_path=directory_path)
        return {
            "status": "error",
            "error": f"Path must be within project directory: {settings.project_path}",
        }
    except FileNotFoundError:
        return {
            "status": "error",
            "error": f"Directory not found: {directory_path}",
        }

    try:
        # For full reindex, clear existing index first
        if scope == "full":
            deleted = await indexer.clear_index()
            logger.info("reindex_cleared_existing", deleted=deleted)

        # Create job for tracking
        job_id = None
        if job_manager:
            job_id = await job_manager.create_job(
                job_type="reindex",
                parameters={
                    "directory_path": str(validated_path),
                    "scope": scope,
                    "extensions": extensions,
                    "exclude": exclude,
                },
            )

        # Run indexing with force=True for full scope
        result = await indexer.index_directory(
            directory=str(validated_path),
            job_id=job_id,
            extensions=extensions,
            exclude_patterns=exclude,
            force=(scope == "full"),
        )

        if job_id:
            result["job_id"] = job_id

        result["scope"] = scope
        return result

    except Exception as e:
        logger.error("reindex_tool_failed", directory=directory_path, error=str(e))
        return {
            "status": "error",
            "directory_path": directory_path,
            "error": str(e),
        }
