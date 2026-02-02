"""Background workers for sync, indexing, and maintenance tasks."""

import asyncio
from pathlib import Path
from typing import Any
from uuid import UUID

from memory_service.models import MemoryType
from memory_service.models.memories import (
    ComponentMemory,
    ComponentType,
    FunctionMemory,
)
from memory_service.models.code_elements import ParseResult, FunctionInfo, ClassInfo
from memory_service.storage.qdrant_adapter import QdrantAdapter
from memory_service.storage.neo4j_adapter import Neo4jAdapter
from memory_service.storage.sync import SyncManager
from memory_service.utils.logging import get_logger
from memory_service.utils.metrics import get_metrics
from memory_service.utils.hashing import file_content_hash

logger = get_logger(__name__)
metrics = get_metrics()


class SyncWorker:
    """Background worker for cross-store synchronization.

    Periodically processes pending sync entries and retries failed ones.
    """

    def __init__(
        self,
        qdrant: QdrantAdapter,
        neo4j: Neo4jAdapter,
        interval_seconds: int = 300,
        batch_size: int = 50,
    ) -> None:
        """Initialize sync worker.

        Args:
            qdrant: Qdrant adapter
            neo4j: Neo4j adapter
            interval_seconds: Interval between sync runs
            batch_size: Number of entries to process per run
        """
        self.sync_manager = SyncManager(qdrant, neo4j)
        self.interval_seconds = interval_seconds
        self.batch_size = batch_size

        logger.info(
            "sync_worker_initialized",
            interval_seconds=interval_seconds,
            batch_size=batch_size,
        )

    async def run(self, shutdown_event: asyncio.Event) -> None:
        """Run the sync worker until shutdown.

        Args:
            shutdown_event: Event to signal shutdown
        """
        logger.info("sync_worker_started")

        while not shutdown_event.is_set():
            try:
                # Process pending syncs
                success, failures = await self.sync_manager.process_pending(
                    batch_size=self.batch_size
                )

                if success > 0 or failures > 0:
                    logger.info(
                        "sync_worker_processed",
                        success=success,
                        failures=failures,
                    )

                # Retry failed syncs (less frequently)
                if not shutdown_event.is_set():
                    retry_success, retry_failures = await self.sync_manager.retry_failed(
                        batch_size=self.batch_size // 2
                    )

                    if retry_success > 0 or retry_failures > 0:
                        logger.info(
                            "sync_worker_retried",
                            success=retry_success,
                            failures=retry_failures,
                        )

            except Exception as e:
                logger.error("sync_worker_error", error=str(e))

            # Wait for next interval or shutdown
            try:
                await asyncio.wait_for(
                    shutdown_event.wait(),
                    timeout=self.interval_seconds,
                )
            except asyncio.TimeoutError:
                pass  # Continue to next iteration

        logger.info("sync_worker_stopped")


class JobManager:
    """Manages background jobs for indexing and normalization."""

    def __init__(self) -> None:
        """Initialize job manager."""
        self._jobs: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def create_job(
        self,
        job_type: str,
        parameters: dict[str, Any] | None = None,
    ) -> str:
        """Create a new job.

        Args:
            job_type: Type of job (e.g., "index", "normalize")
            parameters: Job parameters

        Returns:
            Job ID
        """
        import uuid
        from datetime import datetime, timezone

        job_id = str(uuid.uuid4())

        async with self._lock:
            self._jobs[job_id] = {
                "id": job_id,
                "type": job_type,
                "status": "pending",
                "parameters": parameters or {},
                "created_at": datetime.now(timezone.utc).isoformat(),
                "started_at": None,
                "completed_at": None,
                "progress": 0,
                "phase": None,
                "result": None,
                "error": None,
            }

        logger.info("job_created", job_id=job_id, job_type=job_type)
        return job_id

    async def update_job(
        self,
        job_id: str,
        status: str | None = None,
        progress: int | None = None,
        phase: str | None = None,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> bool:
        """Update job status.

        Args:
            job_id: Job ID
            status: New status
            progress: Progress percentage (0-100)
            phase: Current phase name
            result: Job result (when completed)
            error: Error message (when failed)

        Returns:
            True if updated
        """
        from datetime import datetime, timezone

        async with self._lock:
            if job_id not in self._jobs:
                return False

            job = self._jobs[job_id]

            if status:
                job["status"] = status
                if status == "running" and not job["started_at"]:
                    job["started_at"] = datetime.now(timezone.utc).isoformat()
                elif status in ("completed", "failed"):
                    job["completed_at"] = datetime.now(timezone.utc).isoformat()

            if progress is not None:
                job["progress"] = progress

            if phase:
                job["phase"] = phase

            if result:
                job["result"] = result

            if error:
                job["error"] = error

        return True

    async def get_job(self, job_id: str) -> dict[str, Any] | None:
        """Get job status.

        Args:
            job_id: Job ID

        Returns:
            Job data or None if not found
        """
        async with self._lock:
            return self._jobs.get(job_id)

    async def list_jobs(
        self,
        job_type: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List jobs with optional filtering.

        Args:
            job_type: Filter by job type
            status: Filter by status
            limit: Maximum jobs to return

        Returns:
            List of jobs
        """
        async with self._lock:
            jobs = list(self._jobs.values())

            if job_type:
                jobs = [j for j in jobs if j["type"] == job_type]

            if status:
                jobs = [j for j in jobs if j["status"] == status]

            # Sort by created_at descending
            jobs.sort(key=lambda j: j["created_at"], reverse=True)

            return jobs[:limit]

    async def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        """Remove completed jobs older than max_age_hours.

        Args:
            max_age_hours: Maximum age for completed jobs

        Returns:
            Number of jobs removed
        """
        from datetime import datetime, timedelta, timezone

        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        removed = 0

        async with self._lock:
            to_remove = []
            for job_id, job in self._jobs.items():
                if job["status"] in ("completed", "failed"):
                    completed_at = job.get("completed_at")
                    if completed_at:
                        completed_dt = datetime.fromisoformat(completed_at)
                        if completed_dt < cutoff:
                            to_remove.append(job_id)

            for job_id in to_remove:
                del self._jobs[job_id]
                removed += 1

        if removed > 0:
            logger.info("jobs_cleaned_up", count=removed)

        return removed


class IndexerWorker:
    """Worker for indexing codebase files.

    Parses source files, extracts functions and classes, and stores them
    as memories for semantic search and relationship tracking.
    """

    def __init__(
        self,
        qdrant: QdrantAdapter,
        neo4j: Neo4jAdapter,
        job_manager: JobManager,
        embedding_service: Any | None = None,
    ) -> None:
        """Initialize indexer worker.

        Args:
            qdrant: Qdrant adapter for storing memories
            neo4j: Neo4j adapter for storing relationships
            job_manager: Job manager for tracking progress
            embedding_service: Optional embedding service (created lazily if not provided)
        """
        from memory_service.parsing.parser import ParserOrchestrator
        from memory_service.embedding.service import EmbeddingService
        from memory_service.core.memory_manager import MemoryManager

        self.qdrant = qdrant
        self.neo4j = neo4j
        self.job_manager = job_manager
        self.parser = ParserOrchestrator()

        # Will be initialized lazily when needed, unless injected
        self._embedding_service: EmbeddingService | None = embedding_service
        self._memory_manager: MemoryManager | None = None

        # Cache of file hashes for incremental indexing
        self._file_hashes: dict[str, str] = {}

        logger.info("indexer_worker_initialized")

    @property
    def embedding_service(self) -> Any:
        """Get or create embedding service."""
        if self._embedding_service is None:
            from memory_service.embedding.service import EmbeddingService
            from memory_service.config import get_settings

            settings = get_settings()
            self._embedding_service = EmbeddingService(
                api_key=settings.voyage_api_key,
                model=settings.voyage_model,
            )
        return self._embedding_service

    @property
    def memory_manager(self) -> Any:
        """Get or create memory manager."""
        if self._memory_manager is None:
            from memory_service.core.memory_manager import MemoryManager

            self._memory_manager = MemoryManager(
                qdrant=self.qdrant,
                neo4j=self.neo4j,
                embedding_service=self.embedding_service,
            )
        return self._memory_manager

    async def index_file(
        self,
        file_path: str | Path,
        force: bool = False,
        content: str | None = None,
    ) -> dict[str, Any]:
        """Index a single source file.

        Parses the file, extracts functions and classes, and stores them
        as FunctionMemory and ComponentMemory objects.

        Args:
            file_path: Path to file to index
            force: Force re-index even if content unchanged
            content: File content (read from disk if not provided)

        Returns:
            Indexing result with counts of extracted entities
        """
        file_path = Path(file_path)
        relative_path = str(file_path)

        # Read content if not provided
        if content is None:
            try:
                content = file_path.read_text(encoding="utf-8")
            except Exception as e:
                logger.error("index_file_read_failed", file_path=relative_path, error=str(e))
                return {
                    "status": "error",
                    "file_path": relative_path,
                    "error": f"Failed to read file: {e}",
                }

        # Check if file has changed (incremental indexing)
        content_hash = file_content_hash(relative_path, content)
        if not force and relative_path in self._file_hashes:
            if self._file_hashes[relative_path] == content_hash:
                logger.debug("index_file_skipped_unchanged", file_path=relative_path)
                return {
                    "status": "skipped",
                    "file_path": relative_path,
                    "reason": "unchanged",
                }

        # Parse the file
        parse_result = await self.parser.parse_file(file_path, content)

        if parse_result.errors:
            logger.warning(
                "index_file_parse_errors",
                file_path=relative_path,
                errors=parse_result.errors,
            )

        # Track counts
        functions_indexed = 0
        components_indexed = 0
        errors: list[str] = []

        # Index top-level functions
        for func_info in parse_result.functions:
            try:
                func_memory = self._create_function_memory(func_info, parse_result.language)
                await self.memory_manager.add_memory(
                    func_memory,
                    check_conflicts=False,  # Skip conflict detection for bulk indexing
                    sync_to_neo4j=True,
                )
                functions_indexed += 1
            except Exception as e:
                errors.append(f"Function {func_info.name}: {e}")
                logger.error("index_function_failed", function=func_info.name, error=str(e))

        # Index classes as components with their methods
        for class_info in parse_result.classes:
            try:
                # Create component for the class
                component_memory = self._create_component_memory(class_info, parse_result.language)
                await self.memory_manager.add_memory(
                    component_memory,
                    check_conflicts=False,
                    sync_to_neo4j=True,
                )
                components_indexed += 1

                # Index methods as functions
                for method_info in class_info.methods:
                    try:
                        method_memory = self._create_function_memory(
                            method_info,
                            parse_result.language,
                            containing_class_id=component_memory.id,
                        )
                        await self.memory_manager.add_memory(
                            method_memory,
                            check_conflicts=False,
                            sync_to_neo4j=True,
                        )
                        functions_indexed += 1
                    except Exception as e:
                        errors.append(f"Method {class_info.name}.{method_info.name}: {e}")
                        logger.error(
                            "index_method_failed",
                            class_name=class_info.name,
                            method=method_info.name,
                            error=str(e),
                        )

            except Exception as e:
                errors.append(f"Class {class_info.name}: {e}")
                logger.error("index_class_failed", class_name=class_info.name, error=str(e))

        # Update file hash cache
        self._file_hashes[relative_path] = content_hash

        # Create relationships for imports
        await self._create_import_relationships(parse_result)

        result = {
            "status": "success" if not errors else "partial",
            "file_path": relative_path,
            "language": parse_result.language,
            "functions_indexed": functions_indexed,
            "components_indexed": components_indexed,
            "errors": errors if errors else None,
        }

        logger.info(
            "index_file_complete",
            file_path=relative_path,
            functions=functions_indexed,
            components=components_indexed,
            errors=len(errors),
        )

        return result

    async def index_directory(
        self,
        directory: str | Path,
        job_id: str | None = None,
        extensions: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """Index a directory of source files.

        Args:
            directory: Directory path to index
            job_id: Job ID for progress tracking
            extensions: File extensions to include (default: all supported)
            exclude_patterns: Patterns to exclude
            force: Force re-index all files

        Returns:
            Indexing summary with file counts
        """
        directory = Path(directory)

        if not directory.exists():
            return {
                "status": "error",
                "directory": str(directory),
                "error": "Directory does not exist",
            }

        # Update job status if tracking
        if job_id:
            await self.job_manager.update_job(
                job_id,
                status="running",
                phase="scanning",
                progress=0,
            )

        # Parse all files in directory
        parse_results = await self.parser.parse_directory(
            directory,
            extensions=extensions,
            exclude_patterns=exclude_patterns,
        )

        total_files = len(parse_results)
        files_processed = 0
        files_skipped = 0
        files_errored = 0
        total_functions = 0
        total_components = 0
        all_errors: list[dict[str, Any]] = []

        # Update job status
        if job_id:
            await self.job_manager.update_job(
                job_id,
                phase="indexing",
                progress=5,
            )

        # Index each file
        for i, parse_result in enumerate(parse_results):
            try:
                # Check if file has changed
                file_path = parse_result.file_path
                try:
                    content = Path(file_path).read_text(encoding="utf-8")
                except Exception:
                    content = ""

                content_hash = file_content_hash(file_path, content)

                if not force and file_path in self._file_hashes:
                    if self._file_hashes[file_path] == content_hash:
                        files_skipped += 1
                        continue

                # Index the file using parse result directly
                result = await self._index_parse_result(parse_result, content_hash)

                if result["status"] == "success":
                    files_processed += 1
                    total_functions += result.get("functions_indexed", 0)
                    total_components += result.get("components_indexed", 0)
                elif result["status"] == "partial":
                    files_processed += 1
                    total_functions += result.get("functions_indexed", 0)
                    total_components += result.get("components_indexed", 0)
                    all_errors.append({
                        "file": file_path,
                        "errors": result.get("errors", []),
                    })
                else:
                    files_errored += 1
                    all_errors.append({
                        "file": file_path,
                        "errors": [result.get("error", "Unknown error")],
                    })

            except Exception as e:
                files_errored += 1
                all_errors.append({
                    "file": parse_result.file_path,
                    "errors": [str(e)],
                })
                logger.error("index_file_exception", file=parse_result.file_path, error=str(e))

            # Update progress
            if job_id and total_files > 0:
                progress = 5 + int((i + 1) / total_files * 90)
                await self.job_manager.update_job(job_id, progress=progress)

        # Create cross-file relationships
        if job_id:
            await self.job_manager.update_job(job_id, phase="relationships", progress=95)

        await self._create_call_relationships()

        # Complete job
        if job_id:
            await self.job_manager.update_job(
                job_id,
                status="completed",
                phase="complete",
                progress=100,
                result={
                    "files_processed": files_processed,
                    "files_skipped": files_skipped,
                    "files_errored": files_errored,
                    "functions_indexed": total_functions,
                    "components_indexed": total_components,
                },
            )

        result = {
            "status": "success" if files_errored == 0 else "partial",
            "directory": str(directory),
            "files_found": total_files,
            "files_processed": files_processed,
            "files_skipped": files_skipped,
            "files_errored": files_errored,
            "functions_indexed": total_functions,
            "components_indexed": total_components,
            "errors": all_errors if all_errors else None,
        }

        logger.info(
            "index_directory_complete",
            directory=str(directory),
            files_processed=files_processed,
            files_skipped=files_skipped,
            functions=total_functions,
            components=total_components,
        )

        return result

    async def _index_parse_result(
        self,
        parse_result: ParseResult,
        content_hash: str,
    ) -> dict[str, Any]:
        """Index a pre-parsed file result.

        Args:
            parse_result: Parsed file result
            content_hash: Hash of file content

        Returns:
            Indexing result
        """
        functions_indexed = 0
        components_indexed = 0
        errors: list[str] = []

        # Index top-level functions
        for func_info in parse_result.functions:
            try:
                func_memory = self._create_function_memory(func_info, parse_result.language)
                await self.memory_manager.add_memory(
                    func_memory,
                    check_conflicts=False,
                    sync_to_neo4j=True,
                )
                functions_indexed += 1
            except Exception as e:
                errors.append(f"Function {func_info.name}: {e}")

        # Index classes
        for class_info in parse_result.classes:
            try:
                component_memory = self._create_component_memory(class_info, parse_result.language)
                await self.memory_manager.add_memory(
                    component_memory,
                    check_conflicts=False,
                    sync_to_neo4j=True,
                )
                components_indexed += 1

                # Index methods
                for method_info in class_info.methods:
                    try:
                        method_memory = self._create_function_memory(
                            method_info,
                            parse_result.language,
                            containing_class_id=component_memory.id,
                        )
                        await self.memory_manager.add_memory(
                            method_memory,
                            check_conflicts=False,
                            sync_to_neo4j=True,
                        )
                        functions_indexed += 1
                    except Exception as e:
                        errors.append(f"Method {class_info.name}.{method_info.name}: {e}")

            except Exception as e:
                errors.append(f"Class {class_info.name}: {e}")

        # Update file hash cache
        self._file_hashes[parse_result.file_path] = content_hash

        # Create import relationships
        await self._create_import_relationships(parse_result)

        return {
            "status": "success" if not errors else "partial",
            "file_path": parse_result.file_path,
            "functions_indexed": functions_indexed,
            "components_indexed": components_indexed,
            "errors": errors if errors else None,
        }

    def _create_function_memory(
        self,
        func_info: FunctionInfo,
        language: str,
        containing_class_id: UUID | None = None,
    ) -> FunctionMemory:
        """Create a FunctionMemory from parsed function info.

        Args:
            func_info: Parsed function information
            language: Programming language
            containing_class_id: Parent class ID if this is a method

        Returns:
            FunctionMemory object
        """
        # Build content for embedding (signature + docstring)
        content_parts = [func_info.signature]
        if func_info.docstring:
            content_parts.append(func_info.docstring)
        content = "\n".join(content_parts)

        return FunctionMemory(
            content=content,
            name=func_info.name,
            signature=func_info.signature,
            file_path=func_info.file_path,
            start_line=func_info.start_line,
            end_line=func_info.end_line,
            language=language,
            docstring=func_info.docstring,
            containing_class=containing_class_id,
            source="indexer",
            metadata={
                "is_async": func_info.is_async,
                "is_method": func_info.is_method,
                "is_static": func_info.is_static,
                "is_classmethod": func_info.is_classmethod,
                "is_property": func_info.is_property,
                "decorators": list(func_info.decorators),
                "return_type": func_info.return_type,
            },
        )

    def _create_component_memory(
        self,
        class_info: ClassInfo,
        language: str,
    ) -> ComponentMemory:
        """Create a ComponentMemory from parsed class info.

        Args:
            class_info: Parsed class information
            language: Programming language

        Returns:
            ComponentMemory object
        """
        # Build content for embedding (class name + docstring + methods)
        content_parts = [f"class {class_info.name}"]
        if class_info.bases:
            content_parts[0] += f"({', '.join(class_info.bases)})"
        if class_info.docstring:
            content_parts.append(class_info.docstring)

        # Add method signatures for context
        for method in class_info.methods:
            content_parts.append(method.signature)

        content = "\n".join(content_parts)

        # Determine component type based on class characteristics
        component_type = ComponentType.LIBRARY
        if class_info.is_abstract:
            component_type = ComponentType.LIBRARY
        elif "Service" in class_info.name:
            component_type = ComponentType.SERVICE
        elif "Agent" in class_info.name or "Worker" in class_info.name:
            component_type = ComponentType.AGENT

        # Build public interface
        public_interface = {
            "methods": [
                {
                    "name": m.name,
                    "signature": m.signature,
                    "is_async": m.is_async,
                }
                for m in class_info.methods
                if not m.name.startswith("_") or m.name.startswith("__")
            ],
            "class_variables": [
                {"name": name, "type": type_ann}
                for name, type_ann in class_info.class_variables
            ],
        }

        return ComponentMemory(
            content=content,
            component_id=class_info.name,
            component_type=component_type,
            name=class_info.name,
            file_path=class_info.file_path,
            public_interface=public_interface,
            source="indexer",
            metadata={
                "bases": list(class_info.bases),
                "decorators": list(class_info.decorators),
                "is_dataclass": class_info.is_dataclass,
                "is_abstract": class_info.is_abstract,
                "start_line": class_info.start_line,
                "end_line": class_info.end_line,
                "language": language,
            },
        )

    async def _create_import_relationships(self, parse_result: ParseResult) -> None:
        """Create Neo4j relationships for imports.

        Args:
            parse_result: Parsed file result
        """
        # For each import, we try to find the target component/function
        # and create an IMPORTS relationship
        for import_info in parse_result.imports:
            try:
                # Find target by module/name
                # This is a simplified version - full implementation would
                # resolve imports to actual components
                module = import_info.module
                name = import_info.name or module.split(".")[-1]

                # Use scroll with filter instead of search to avoid needing a vector
                # This is a filter-only lookup by component_id
                points, _ = await self.qdrant.scroll(
                    collection=self.qdrant.get_collection_name(MemoryType.COMPONENT),
                    filters={"component_id": name, "deleted": False},
                    limit=1,
                    with_vectors=False,
                )

                if points:
                    target_id = points[0]["id"]
                    # Create IMPORTS relationship
                    # Source: file path, Target: component
                    await self.neo4j.create_relationship(
                        source_id=parse_result.file_path,
                        target_id=UUID(target_id) if isinstance(target_id, str) else target_id,
                        relationship_type="IMPORTS",
                        properties={
                            "module": module,
                            "name": name,
                            "alias": import_info.alias,
                            "is_relative": import_info.is_relative,
                            "line": import_info.line,
                        },
                    )
            except Exception as e:
                # Import relationship creation is best-effort
                logger.debug("create_import_relationship_failed", import_info=str(import_info), error=str(e))

    async def _create_call_relationships(self) -> None:
        """Create Neo4j relationships for function calls.

        This is called after all files are indexed to create CALLS relationships
        between functions.
        """
        # Get all function memories using scroll (filter-only, no vector needed)
        try:
            all_results = []
            offset = None

            # Scroll through all functions
            while True:
                points, next_offset = await self.qdrant.scroll(
                    collection=self.qdrant.get_collection_name(MemoryType.FUNCTION),
                    filters={"deleted": False},
                    limit=100,
                    offset=offset,
                    with_vectors=False,
                )

                all_results.extend(points)

                if not next_offset:
                    break
                offset = next_offset

            # Build name -> id mapping
            function_map: dict[str, str] = {}
            for result in all_results:
                payload = result.get("payload", {})
                name = payload.get("name", "")
                if name:
                    function_map[name] = str(result["id"])

            # For each function, find calls and create relationships
            for result in all_results:
                payload = result.get("payload", {})
                metadata = payload.get("metadata", {})
                # Note: calls would need to be extracted during parsing and stored
                # This is a simplified version
                calls = metadata.get("calls", [])

                for call_name in calls:
                    if call_name in function_map:
                        target_id = function_map[call_name]
                        try:
                            await self.neo4j.create_relationship(
                                source_id=UUID(str(result["id"])),
                                target_id=UUID(target_id),
                                relationship_type="CALLS",
                                properties={"call_name": call_name},
                            )
                        except Exception as e:
                            # Log failed relationship creation instead of silent pass
                            logger.debug(
                                "create_call_relationship_failed",
                                source_id=str(result["id"]),
                                target_id=target_id,
                                call_name=call_name,
                                error=str(e),
                            )

        except Exception as e:
            logger.warning("create_call_relationships_failed", error=str(e))

    async def clear_index(self) -> dict[str, int]:
        """Clear all indexed memories.

        Returns:
            Counts of deleted memories by type
        """
        deleted_counts = {}

        # Delete all functions
        func_collection = self.qdrant.get_collection_name(MemoryType.FUNCTION)
        func_count = await self.qdrant.count(func_collection, filters={"source": "indexer"})
        await self.qdrant.delete_by_filter(func_collection, filters={"source": "indexer"})
        deleted_counts["functions"] = func_count

        # Delete all components from indexer
        comp_collection = self.qdrant.get_collection_name(MemoryType.COMPONENT)
        comp_count = await self.qdrant.count(comp_collection, filters={"source": "indexer"})
        await self.qdrant.delete_by_filter(comp_collection, filters={"source": "indexer"})
        deleted_counts["components"] = comp_count

        # Clear hash cache
        self._file_hashes.clear()

        logger.info("index_cleared", deleted=deleted_counts)
        return deleted_counts

    def get_file_hash(self, file_path: str) -> str | None:
        """Get cached hash for a file.

        Args:
            file_path: File path

        Returns:
            Cached hash or None if not indexed
        """
        return self._file_hashes.get(file_path)


class NormalizerWorker:
    """Worker for memory normalization and cleanup.

    Performs multi-phase normalization:
    1. snapshot - Create snapshot of current state
    2. deduplication - Merge similar memories (>0.95 similarity)
    3. orphan_detection - Remove orphaned references
    4. embedding_refresh - Recompute embeddings for changed content
    5. cleanup - Remove soft-deleted items past retention
    6. validation - Validate normalized data
    7. swap - Swap normalized data into production
    8. rollback - Restore from snapshot on failure
    """

    # Normalization phases in order
    PHASES = [
        "snapshot",
        "deduplication",
        "orphan_detection",
        "embedding_refresh",
        "cleanup",
        "validation",
        "swap",
    ]

    def __init__(
        self,
        qdrant: QdrantAdapter,
        neo4j: Neo4jAdapter,
        job_manager: JobManager,
    ) -> None:
        """Initialize normalizer worker.

        Args:
            qdrant: Qdrant adapter
            neo4j: Neo4j adapter
            job_manager: Job manager for progress tracking
        """
        from memory_service.config import get_settings

        self.qdrant = qdrant
        self.neo4j = neo4j
        self.job_manager = job_manager
        self.settings = get_settings()

        # Snapshot storage for rollback
        self._snapshot: dict[str, list[dict[str, Any]]] = {}
        self._snapshot_job_id: str | None = None

        logger.info("normalizer_worker_initialized")

    async def normalize(
        self,
        job_id: str | None = None,
        phases: list[str] | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Run memory normalization.

        Args:
            job_id: Job ID for progress tracking
            phases: Specific phases to run (default: all)
            dry_run: If True, report changes without applying

        Returns:
            Normalization result with statistics
        """
        phases_to_run = phases or self.PHASES
        result: dict[str, Any] = {
            "status": "success",
            "phases_completed": [],
            "phases_skipped": [],
            "statistics": {},
            "dry_run": dry_run,
        }

        try:
            if job_id:
                await self.job_manager.update_job(
                    job_id,
                    status="running",
                    phase="starting",
                    progress=0,
                )

            total_phases = len(phases_to_run)

            for i, phase in enumerate(phases_to_run):
                if phase not in self.PHASES:
                    result["phases_skipped"].append(phase)
                    continue

                if job_id:
                    progress = int((i / total_phases) * 100)
                    await self.job_manager.update_job(
                        job_id,
                        phase=phase,
                        progress=progress,
                    )

                logger.info("normalization_phase_starting", phase=phase)

                try:
                    phase_result = await self._run_phase(phase, dry_run)
                    result["statistics"][phase] = phase_result
                    result["phases_completed"].append(phase)

                    logger.info(
                        "normalization_phase_complete",
                        phase=phase,
                        result=phase_result,
                    )

                except Exception as e:
                    logger.error("normalization_phase_failed", phase=phase, error=str(e))
                    result["status"] = "failed"
                    result["error"] = f"Phase {phase} failed: {e}"
                    result["failed_phase"] = phase

                    # Attempt rollback if we have a snapshot
                    if self._snapshot and phase != "snapshot":
                        rollback_result = await self._rollback()
                        result["rollback"] = rollback_result

                    break

            if job_id:
                final_status = "completed" if result["status"] == "success" else "failed"
                await self.job_manager.update_job(
                    job_id,
                    status=final_status,
                    phase="complete",
                    progress=100,
                    result=result,
                )

        except Exception as e:
            logger.error("normalization_failed", error=str(e))
            result["status"] = "failed"
            result["error"] = str(e)

            if job_id:
                await self.job_manager.update_job(
                    job_id,
                    status="failed",
                    error=str(e),
                )

        return result

    async def _run_phase(self, phase: str, dry_run: bool) -> dict[str, Any]:
        """Run a single normalization phase.

        Args:
            phase: Phase name
            dry_run: Whether to only report changes

        Returns:
            Phase result statistics
        """
        if phase == "snapshot":
            return await self._phase_snapshot()
        elif phase == "deduplication":
            return await self._phase_deduplication(dry_run)
        elif phase == "orphan_detection":
            return await self._phase_orphan_detection(dry_run)
        elif phase == "embedding_refresh":
            return await self._phase_embedding_refresh(dry_run)
        elif phase == "cleanup":
            return await self._phase_cleanup(dry_run)
        elif phase == "validation":
            return await self._phase_validation()
        elif phase == "swap":
            return await self._phase_swap(dry_run)
        else:
            raise ValueError(f"Unknown phase: {phase}")

    async def _phase_snapshot(self) -> dict[str, Any]:
        """Create snapshot of current memory state.

        Returns:
            Snapshot statistics
        """
        self._snapshot.clear()
        counts = {}

        for memory_type in MemoryType:
            collection = self.qdrant.get_collection_name(memory_type)
            memories = []

            # Scroll through all non-deleted memories
            offset = None
            while True:
                points, next_offset = await self.qdrant.scroll(
                    collection=collection,
                    filters={"deleted": False},
                    limit=1000,
                    offset=offset,
                    with_vectors=True,
                )

                memories.extend(points)

                if not next_offset:
                    break
                offset = next_offset

            self._snapshot[memory_type.value] = memories
            counts[memory_type.value] = len(memories)

        logger.info("snapshot_created", counts=counts)
        return {"snapshot_counts": counts, "total": sum(counts.values())}

    async def _phase_deduplication(self, dry_run: bool) -> dict[str, Any]:
        """Deduplicate memories with high similarity.

        Args:
            dry_run: Whether to only report changes

        Returns:
            Deduplication statistics
        """
        from memory_service.config import get_settings

        settings = get_settings()
        threshold = settings.conflict_threshold  # 0.95

        duplicates_found = 0
        duplicates_merged = 0
        by_type: dict[str, int] = {}

        for memory_type in MemoryType:
            collection = self.qdrant.get_collection_name(memory_type)
            type_duplicates = 0

            # Get all memories for this type
            offset = None
            all_memories: list[dict[str, Any]] = []
            while True:
                points, next_offset = await self.qdrant.scroll(
                    collection=collection,
                    filters={"deleted": False},
                    limit=1000,
                    offset=offset,
                    with_vectors=True,
                )
                all_memories.extend(points)
                if not next_offset:
                    break
                offset = next_offset

            # Track which IDs have been processed as duplicates
            processed_ids: set[str] = set()

            for memory in all_memories:
                memory_id = str(memory["id"])
                if memory_id in processed_ids:
                    continue

                vector = memory.get("vector", [])
                if not vector:
                    continue

                # Search for similar memories
                similar = await self.qdrant.search(
                    collection=collection,
                    vector=vector,
                    limit=10,
                    filters={"deleted": False},
                    score_threshold=threshold,
                )

                # Filter out self and already processed
                duplicates = [
                    s for s in similar
                    if str(s["id"]) != memory_id and str(s["id"]) not in processed_ids
                ]

                if duplicates:
                    duplicates_found += len(duplicates)
                    type_duplicates += len(duplicates)

                    if not dry_run:
                        # Mark duplicates as deleted (keep the current one)
                        for dup in duplicates:
                            dup_id = str(dup["id"])
                            await self.qdrant.update_payload(
                                collection=collection,
                                point_id=dup_id,
                                payload={
                                    "deleted": True,
                                    "deleted_reason": "deduplication",
                                    "merged_into": memory_id,
                                },
                            )
                            processed_ids.add(dup_id)
                            duplicates_merged += 1
                    else:
                        for dup in duplicates:
                            processed_ids.add(str(dup["id"]))

                processed_ids.add(memory_id)

            if type_duplicates > 0:
                by_type[memory_type.value] = type_duplicates

        return {
            "duplicates_found": duplicates_found,
            "duplicates_merged": duplicates_merged if not dry_run else 0,
            "by_type": by_type,
        }

    async def _phase_orphan_detection(self, dry_run: bool) -> dict[str, Any]:
        """Detect and remove orphaned references.

        Args:
            dry_run: Whether to only report changes

        Returns:
            Orphan detection statistics
        """
        orphans_found = 0
        orphans_removed = 0

        # Check function references to classes
        func_collection = self.qdrant.get_collection_name(MemoryType.FUNCTION)
        comp_collection = self.qdrant.get_collection_name(MemoryType.COMPONENT)

        offset = None
        while True:
            functions, next_offset = await self.qdrant.scroll(
                collection=func_collection,
                filters={"deleted": False},
                limit=1000,
                offset=offset,
            )

            for func in functions:
                payload = func.get("payload", {})
                containing_class = payload.get("containing_class")

                if containing_class:
                    # Check if class still exists
                    class_data = await self.qdrant.get(
                        collection=comp_collection,
                        point_id=containing_class,
                    )

                    if not class_data or class_data.get("deleted"):
                        orphans_found += 1

                        if not dry_run:
                            # Clear the orphaned reference
                            await self.qdrant.update_payload(
                                collection=func_collection,
                                point_id=func["id"],
                                payload={"containing_class": None},
                            )
                            orphans_removed += 1

            if not next_offset:
                break
            offset = next_offset

        # Check Neo4j for orphaned relationships
        try:
            # Find relationships pointing to non-existent nodes
            orphaned_rels = await self.neo4j.execute_cypher(
                """
                MATCH (n)-[r]->(m)
                WHERE m.deleted = true
                RETURN count(r) as orphan_count
                """
            )

            if orphaned_rels:
                neo4j_orphans = orphaned_rels[0].get("orphan_count", 0)
                orphans_found += neo4j_orphans

                if not dry_run and neo4j_orphans > 0:
                    # Delete orphaned relationships
                    await self.neo4j.execute_cypher(
                        """
                        MATCH (n)-[r]->(m)
                        WHERE m.deleted = true
                        DELETE r
                        """
                    )
                    orphans_removed += neo4j_orphans

        except Exception as e:
            logger.warning("orphan_detection_neo4j_error", error=str(e))

        return {
            "orphans_found": orphans_found,
            "orphans_removed": orphans_removed if not dry_run else 0,
        }

    async def _phase_embedding_refresh(self, dry_run: bool) -> dict[str, Any]:
        """Refresh embeddings for changed content.

        Args:
            dry_run: Whether to only report changes

        Returns:
            Embedding refresh statistics
        """
        from memory_service.embedding.service import EmbeddingService
        from memory_service.config import get_settings

        settings = get_settings()

        needs_refresh = 0
        refreshed = 0

        if dry_run:
            # In dry run, we just count memories that might need refresh
            # (those with fallback embeddings or missing embeddings)
            for memory_type in MemoryType:
                collection = self.qdrant.get_collection_name(memory_type)

                offset = None
                while True:
                    points, next_offset = await self.qdrant.scroll(
                        collection=collection,
                        filters={"deleted": False},
                        limit=1000,
                        offset=offset,
                    )

                    for point in points:
                        payload = point.get("payload", {})
                        metadata = payload.get("metadata", {})
                        if metadata.get("embedding_is_fallback"):
                            needs_refresh += 1

                    if not next_offset:
                        break
                    offset = next_offset

            return {"needs_refresh": needs_refresh, "refreshed": 0}

        # Actually refresh embeddings
        embedding_service = EmbeddingService(
            api_key=settings.voyage_api_key,
            model=settings.voyage_model,
        )

        for memory_type in MemoryType:
            collection = self.qdrant.get_collection_name(memory_type)

            offset = None
            while True:
                points, next_offset = await self.qdrant.scroll(
                    collection=collection,
                    filters={"deleted": False},
                    limit=100,
                    offset=offset,
                    with_vectors=True,
                )

                for point in points:
                    payload = point.get("payload", {})
                    metadata = payload.get("metadata", {})
                    content = payload.get("content", "")

                    # Refresh if marked as fallback
                    if metadata.get("embedding_is_fallback") and content:
                        needs_refresh += 1
                        try:
                            embedding, is_fallback = await embedding_service.embed(content)

                            if not is_fallback:
                                await self.qdrant.upsert(
                                    collection=collection,
                                    point_id=point["id"],
                                    vector=embedding,
                                    payload={
                                        **payload,
                                        "metadata": {
                                            **metadata,
                                            "embedding_is_fallback": False,
                                        },
                                    },
                                )
                                refreshed += 1
                        except Exception as e:
                            logger.warning(
                                "embedding_refresh_failed",
                                point_id=point["id"],
                                error=str(e),
                            )

                if not next_offset:
                    break
                offset = next_offset

        return {"needs_refresh": needs_refresh, "refreshed": refreshed}

    async def _phase_cleanup(self, dry_run: bool) -> dict[str, Any]:
        """Remove soft-deleted items past retention period.

        Args:
            dry_run: Whether to only report changes

        Returns:
            Cleanup statistics
        """
        from datetime import datetime, timedelta, timezone

        retention_days = self.settings.soft_delete_retention_days
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        cutoff_str = cutoff.isoformat()

        to_delete = 0
        deleted = 0

        for memory_type in MemoryType:
            collection = self.qdrant.get_collection_name(memory_type)

            # Find soft-deleted items older than cutoff
            offset = None
            while True:
                points, next_offset = await self.qdrant.scroll(
                    collection=collection,
                    filters={"deleted": True},
                    limit=1000,
                    offset=offset,
                )

                for point in points:
                    payload = point.get("payload", {})
                    deleted_at = payload.get("deleted_at", "")

                    if deleted_at and deleted_at < cutoff_str:
                        to_delete += 1

                        if not dry_run:
                            await self.qdrant.delete(
                                collection=collection,
                                point_id=point["id"],
                            )
                            deleted += 1

                if not next_offset:
                    break
                offset = next_offset

        return {
            "items_eligible": to_delete,
            "items_deleted": deleted if not dry_run else 0,
            "retention_days": retention_days,
        }

    async def _phase_validation(self) -> dict[str, Any]:
        """Validate normalized memory state.

        Returns:
            Validation results
        """
        issues: list[str] = []
        counts: dict[str, int] = {}

        for memory_type in MemoryType:
            collection = self.qdrant.get_collection_name(memory_type)

            try:
                count = await self.qdrant.count(
                    collection=collection,
                    filters={"deleted": False},
                )
                counts[memory_type.value] = count

                # Validate a sample of memories
                points, _ = await self.qdrant.scroll(
                    collection=collection,
                    filters={"deleted": False},
                    limit=10,
                    with_vectors=True,
                )

                for point in points:
                    vector = point.get("vector", [])
                    if not vector:
                        issues.append(f"Missing vector for {memory_type.value}:{point['id']}")

                    payload = point.get("payload", {})
                    if not payload.get("content"):
                        issues.append(f"Missing content for {memory_type.value}:{point['id']}")

            except Exception as e:
                issues.append(f"Validation error for {memory_type.value}: {e}")

        # Check Neo4j connectivity
        try:
            neo4j_healthy = await self.neo4j.health_check()
            if not neo4j_healthy:
                issues.append("Neo4j health check failed")
        except Exception as e:
            issues.append(f"Neo4j error: {e}")

        return {
            "valid": len(issues) == 0,
            "counts": counts,
            "total_memories": sum(counts.values()),
            "issues": issues if issues else None,
        }

    async def _phase_swap(self, dry_run: bool) -> dict[str, Any]:
        """Swap normalized data (no-op as we modify in place).

        In this implementation, normalization modifies data in place,
        so swap just clears the snapshot.

        Args:
            dry_run: Whether to only report changes

        Returns:
            Swap statistics
        """
        if dry_run:
            return {"swapped": False, "reason": "dry_run"}

        # Clear snapshot after successful normalization
        snapshot_size = sum(len(v) for v in self._snapshot.values())
        self._snapshot.clear()

        return {
            "swapped": True,
            "snapshot_cleared": True,
            "snapshot_size": snapshot_size,
        }

    async def _rollback(self) -> dict[str, Any]:
        """Rollback to snapshot state.

        Returns:
            Rollback result
        """
        if not self._snapshot:
            return {"rolled_back": False, "reason": "no_snapshot"}

        restored = 0
        errors = 0

        try:
            for memory_type_str, memories in self._snapshot.items():
                memory_type = MemoryType(memory_type_str)
                collection = self.qdrant.get_collection_name(memory_type)

                for memory in memories:
                    try:
                        vector = memory.get("vector", [])
                        payload = memory.get("payload", {})

                        if vector:
                            await self.qdrant.upsert(
                                collection=collection,
                                point_id=memory["id"],
                                vector=vector,
                                payload=payload,
                            )
                            restored += 1
                    except Exception as e:
                        errors += 1
                        logger.error(
                            "rollback_item_failed",
                            memory_id=memory.get("id"),
                            error=str(e),
                        )

            self._snapshot.clear()

            return {
                "rolled_back": True,
                "restored": restored,
                "errors": errors,
            }

        except Exception as e:
            logger.error("rollback_failed", error=str(e))
            return {
                "rolled_back": False,
                "error": str(e),
            }

    async def get_status(self) -> dict[str, Any]:
        """Get current normalizer status.

        Returns:
            Status information
        """
        return {
            "has_snapshot": bool(self._snapshot),
            "snapshot_size": sum(len(v) for v in self._snapshot.values()),
            "phases": self.PHASES,
        }
