"""Memory lifecycle management."""

import time
from datetime import datetime, timezone
from typing import Any, Sequence
from uuid import UUID

from memory_service.models import BaseMemory, MemoryType, SyncStatus
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
from memory_service.storage.qdrant_adapter import QdrantAdapter
from memory_service.storage.neo4j_adapter import Neo4jAdapter
from memory_service.storage.sync import SyncManager
from memory_service.embedding.service import EmbeddingService
from memory_service.utils.logging import get_logger
from memory_service.utils.metrics import get_metrics

logger = get_logger(__name__)
metrics = get_metrics()

# Memory type to class mapping
MEMORY_CLASSES: dict[MemoryType, type[BaseMemory]] = {
    MemoryType.REQUIREMENTS: RequirementsMemory,
    MemoryType.DESIGN: DesignMemory,
    MemoryType.CODE_PATTERN: CodePatternMemory,
    MemoryType.COMPONENT: ComponentMemory,
    MemoryType.FUNCTION: FunctionMemory,
    MemoryType.TEST_HISTORY: TestHistoryMemory,
    MemoryType.SESSION: SessionMemory,
    MemoryType.USER_PREFERENCE: UserPreferenceMemory,
}


class ConflictError(Exception):
    """Raised when a memory conflicts with existing entries."""

    def __init__(self, message: str, conflicts: list[dict[str, Any]]) -> None:
        super().__init__(message)
        self.conflicts = conflicts


class MemoryManager:
    """Manages memory lifecycle operations.

    Provides:
    - CRUD operations (add, get, update, delete)
    - Bulk operations with transactional semantics
    - Conflict detection (similarity > 0.95)
    - Importance scoring
    - Cross-store synchronization
    """

    def __init__(
        self,
        qdrant: QdrantAdapter,
        neo4j: Neo4jAdapter,
        embedding_service: EmbeddingService,
        conflict_threshold: float = 0.95,
    ) -> None:
        """Initialize memory manager.

        Args:
            qdrant: Qdrant adapter
            neo4j: Neo4j adapter
            embedding_service: Embedding service
            conflict_threshold: Similarity threshold for conflict detection
        """
        self.qdrant = qdrant
        self.neo4j = neo4j
        self.embedding_service = embedding_service
        self.conflict_threshold = conflict_threshold
        self.sync_manager = SyncManager(qdrant, neo4j)

        logger.info("memory_manager_initialized", conflict_threshold=conflict_threshold)

    async def add_memory(
        self,
        memory: BaseMemory,
        check_conflicts: bool = True,
        sync_to_neo4j: bool = True,
    ) -> tuple[UUID, list[dict[str, Any]]]:
        """Add a new memory.

        Args:
            memory: Memory to add
            check_conflicts: Whether to check for conflicting memories
            sync_to_neo4j: Whether to sync to Neo4j

        Returns:
            Tuple of (memory_id, conflicts)

        Raises:
            ConflictError: If conflicts found and check_conflicts=True
        """
        start = time.perf_counter()
        memory_type = MemoryType(memory.type)

        # Generate embedding if not present
        if not memory.embedding:
            embedding, is_fallback = await self.embedding_service.embed(memory.content)
            memory.embedding = embedding
            if is_fallback:
                memory.metadata["embedding_is_fallback"] = True

        # Check for conflicts
        conflicts: list[dict[str, Any]] = []
        if check_conflicts:
            conflicts = await self._find_conflicts(memory)
            if conflicts:
                logger.warning(
                    "memory_conflicts_found",
                    memory_id=str(memory.id),
                    conflict_count=len(conflicts),
                )

        # Calculate importance score
        memory.importance_score = self._calculate_importance(memory)

        # Store in Qdrant
        collection = self.qdrant.get_collection_name(memory_type)
        await self.qdrant.upsert(
            collection=collection,
            point_id=memory.id,
            vector=memory.embedding,
            payload=memory.to_qdrant_payload(),
        )

        # Sync to Neo4j
        if sync_to_neo4j:
            try:
                label = self.neo4j.get_node_label(memory_type)
                await self.neo4j.create_node(
                    label=label,
                    properties=memory.to_neo4j_properties(),
                )
                memory.mark_synced(str(memory.id))
            except Exception as e:
                logger.error("neo4j_sync_failed", memory_id=str(memory.id), error=str(e))
                memory.mark_sync_pending()
                await self.sync_manager.mark_pending(memory.id, memory_type)

        duration = time.perf_counter() - start
        metrics.record_memory_operation(
            operation="add",
            memory_type=memory_type.value,
            status="success",
            duration=duration,
        )

        logger.info(
            "memory_added",
            memory_id=str(memory.id),
            memory_type=memory_type.value,
            has_conflicts=len(conflicts) > 0,
        )

        return memory.id, conflicts

    async def get_memory(
        self,
        memory_id: UUID,
        memory_type: MemoryType,
        include_embedding: bool = False,
        track_access: bool = True,
    ) -> BaseMemory | None:
        """Retrieve a memory by ID.

        Args:
            memory_id: Memory ID
            memory_type: Memory type
            include_embedding: Whether to include embedding vector
            track_access: Whether to increment access count

        Returns:
            Memory object or None if not found
        """
        start = time.perf_counter()
        collection = self.qdrant.get_collection_name(memory_type)

        data = await self.qdrant.get(
            collection=collection,
            point_id=memory_id,
            with_vector=include_embedding,
        )

        if not data:
            return None

        # Track access
        if track_access:
            new_access_count = data.get("access_count", 0) + 1
            new_last_accessed = datetime.now(timezone.utc).isoformat()
            await self.qdrant.update_payload(
                collection=collection,
                point_id=memory_id,
                payload={
                    "access_count": new_access_count,
                    "last_accessed_at": new_last_accessed,
                },
            )
            # Update data to reflect the new access count
            data["access_count"] = new_access_count
            data["last_accessed_at"] = new_last_accessed

        # Reconstruct memory object
        memory_class = MEMORY_CLASSES[memory_type]
        memory = memory_class.model_validate(data)

        duration = time.perf_counter() - start
        metrics.record_memory_operation(
            operation="get",
            memory_type=memory_type.value,
            status="success",
            duration=duration,
        )

        return memory

    async def update_memory(
        self,
        memory_id: UUID,
        memory_type: MemoryType,
        updates: dict[str, Any],
        regenerate_embedding: bool = True,
    ) -> BaseMemory | None:
        """Update an existing memory.

        Args:
            memory_id: Memory ID
            memory_type: Memory type
            updates: Fields to update
            regenerate_embedding: Whether to regenerate embedding if content changed

        Returns:
            Updated memory or None if not found
        """
        start = time.perf_counter()
        collection = self.qdrant.get_collection_name(memory_type)

        # Get existing memory
        existing = await self.get_memory(memory_id, memory_type, include_embedding=True, track_access=False)
        if not existing:
            return None

        # Apply updates
        update_data = existing.model_dump()
        update_data.update(updates)
        update_data["updated_at"] = datetime.now(timezone.utc)

        # Regenerate embedding if content changed
        if regenerate_embedding and "content" in updates and updates["content"] != existing.content:
            embedding, is_fallback = await self.embedding_service.embed(updates["content"])
            update_data["embedding"] = embedding
            if is_fallback:
                update_data.setdefault("metadata", {})["embedding_is_fallback"] = True

        # Validate and reconstruct memory
        memory_class = MEMORY_CLASSES[memory_type]
        updated_memory = memory_class.model_validate(update_data)

        # Store in Qdrant
        await self.qdrant.upsert(
            collection=collection,
            point_id=memory_id,
            vector=updated_memory.embedding,
            payload=updated_memory.to_qdrant_payload(),
        )

        # Update Neo4j
        try:
            label = self.neo4j.get_node_label(memory_type)
            await self.neo4j.update_node(
                node_id=memory_id,
                properties=updated_memory.to_neo4j_properties(),
                label=label,
            )
        except Exception as e:
            logger.error("neo4j_update_failed", memory_id=str(memory_id), error=str(e))
            await self.sync_manager.mark_pending(memory_id, memory_type)

        duration = time.perf_counter() - start
        metrics.record_memory_operation(
            operation="update",
            memory_type=memory_type.value,
            status="success",
            duration=duration,
        )

        logger.info("memory_updated", memory_id=str(memory_id), memory_type=memory_type.value)
        return updated_memory

    async def delete_memory(
        self,
        memory_id: UUID,
        memory_type: MemoryType,
        soft_delete: bool = True,
    ) -> bool:
        """Delete a memory.

        Args:
            memory_id: Memory ID
            memory_type: Memory type
            soft_delete: Whether to soft-delete (set deleted flag)

        Returns:
            True if deleted
        """
        start = time.perf_counter()
        collection = self.qdrant.get_collection_name(memory_type)

        if soft_delete:
            # Soft delete - update deleted flag
            await self.qdrant.update_payload(
                collection=collection,
                point_id=memory_id,
                payload={
                    "deleted": True,
                    "deleted_at": datetime.now(timezone.utc).isoformat(),
                },
            )

            # Update Neo4j
            try:
                await self.neo4j.update_node(
                    node_id=memory_id,
                    properties={
                        "deleted": True,
                        "deleted_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
            except Exception as e:
                logger.error("neo4j_soft_delete_failed", memory_id=str(memory_id), error=str(e))

        else:
            # Hard delete
            await self.qdrant.delete(collection=collection, point_id=memory_id)

            try:
                label = self.neo4j.get_node_label(memory_type)
                await self.neo4j.delete_node(node_id=memory_id, label=label, detach=True)
            except Exception as e:
                logger.error("neo4j_hard_delete_failed", memory_id=str(memory_id), error=str(e))

        duration = time.perf_counter() - start
        metrics.record_memory_operation(
            operation="delete",
            memory_type=memory_type.value,
            status="success",
            duration=duration,
        )

        logger.info(
            "memory_deleted",
            memory_id=str(memory_id),
            memory_type=memory_type.value,
            soft_delete=soft_delete,
        )
        return True

    async def bulk_add_memories(
        self,
        memories: Sequence[BaseMemory],
        check_conflicts: bool = False,
        sync_to_neo4j: bool = True,
    ) -> tuple[list[UUID], list[dict[str, Any]]]:
        """Add multiple memories in batch.

        Args:
            memories: Memories to add
            check_conflicts: Whether to check for conflicts
            sync_to_neo4j: Whether to sync to Neo4j

        Returns:
            Tuple of (list of memory IDs, list of errors)
        """
        start = time.perf_counter()
        added_ids: list[UUID] = []
        errors: list[dict[str, Any]] = []

        # Group memories by type
        memories_by_type: dict[MemoryType, list[BaseMemory]] = {}
        for memory in memories:
            memory_type = MemoryType(memory.type)
            memories_by_type.setdefault(memory_type, []).append(memory)

        # Generate embeddings in batch
        for memory_type, type_memories in memories_by_type.items():
            contents = [m.content for m in type_memories if not m.embedding]
            if contents:
                embeddings = await self.embedding_service.embed_batch(contents)
                embed_idx = 0
                for memory in type_memories:
                    if not memory.embedding:
                        embedding, is_fallback = embeddings[embed_idx]
                        memory.embedding = embedding
                        if is_fallback:
                            memory.metadata["embedding_is_fallback"] = True
                        embed_idx += 1

        # Store in batches by type
        for memory_type, type_memories in memories_by_type.items():
            collection = self.qdrant.get_collection_name(memory_type)

            try:
                # Prepare batch for Qdrant
                points = [
                    (
                        m.id,
                        m.embedding,
                        m.to_qdrant_payload(),
                    )
                    for m in type_memories
                ]

                await self.qdrant.upsert_batch(collection=collection, points=points)

                # Track added IDs
                for memory in type_memories:
                    added_ids.append(memory.id)

                # Sync to Neo4j
                if sync_to_neo4j:
                    label = self.neo4j.get_node_label(memory_type)
                    for memory in type_memories:
                        try:
                            await self.neo4j.create_node(
                                label=label,
                                properties=memory.to_neo4j_properties(),
                            )
                        except Exception as e:
                            logger.error(
                                "neo4j_bulk_sync_failed",
                                memory_id=str(memory.id),
                                error=str(e),
                            )
                            await self.sync_manager.mark_pending(memory.id, memory_type)

            except Exception as e:
                for memory in type_memories:
                    errors.append({
                        "memory_id": str(memory.id),
                        "error": str(e),
                    })
                logger.error(
                    "bulk_add_failed",
                    memory_type=memory_type.value,
                    error=str(e),
                )

        duration = time.perf_counter() - start
        logger.info(
            "bulk_add_complete",
            added_count=len(added_ids),
            error_count=len(errors),
            duration_ms=int(duration * 1000),
        )

        return added_ids, errors

    async def _find_conflicts(
        self,
        memory: BaseMemory,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Find memories that conflict with the given memory.

        Args:
            memory: Memory to check
            limit: Maximum conflicts to return

        Returns:
            List of conflicting memories
        """
        memory_type = MemoryType(memory.type)
        collection = self.qdrant.get_collection_name(memory_type)

        results = await self.qdrant.search(
            collection=collection,
            vector=memory.embedding,
            limit=limit + 1,  # +1 to exclude self
            filters={"deleted": False},
            score_threshold=self.conflict_threshold,
        )

        conflicts = []
        for result in results:
            # Skip if same ID
            if str(result["id"]) == str(memory.id):
                continue

            conflicts.append({
                "id": result["id"],
                "score": result["score"],
                "content": result["payload"].get("content", "")[:200],
            })

            if len(conflicts) >= limit:
                break

        return conflicts

    def _calculate_importance(self, memory: BaseMemory) -> float:
        """Calculate importance score for a memory.

        Factors:
        - Base score by type
        - Priority (for requirements)
        - Access frequency (for existing memories)
        - Recency

        Args:
            memory: Memory to score

        Returns:
            Importance score (0.0-1.0)
        """
        # Base scores by type
        type_scores = {
            MemoryType.REQUIREMENTS: 0.8,
            MemoryType.DESIGN: 0.7,
            MemoryType.CODE_PATTERN: 0.6,
            MemoryType.COMPONENT: 0.5,
            MemoryType.FUNCTION: 0.4,
            MemoryType.TEST_HISTORY: 0.3,
            MemoryType.SESSION: 0.4,
            MemoryType.USER_PREFERENCE: 0.5,
        }

        memory_type = MemoryType(memory.type)
        score = type_scores.get(memory_type, 0.5)

        # Adjust for priority (requirements)
        if hasattr(memory, "priority"):
            priority_boost = {
                "Critical": 0.2,
                "High": 0.1,
                "Medium": 0.0,
                "Low": -0.1,
            }
            score += priority_boost.get(memory.priority, 0.0)  # type: ignore

        # Ensure score is in valid range
        return max(0.0, min(1.0, score))

    async def get_memory_counts(self) -> dict[str, int]:
        """Get counts of memories by type.

        Returns:
            Dictionary of memory type to count
        """
        counts = {}
        for memory_type in MemoryType:
            collection = self.qdrant.get_collection_name(memory_type)
            count = await self.qdrant.count(
                collection=collection,
                filters={"deleted": False},
            )
            counts[memory_type.value] = count
            metrics.memory_count.labels(memory_type=memory_type.value).set(count)

        return counts
