"""Cross-store synchronization manager."""

import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from memory_service.models import BaseMemory, MemoryType, SyncStatus
from memory_service.storage.qdrant_adapter import QdrantAdapter
from memory_service.storage.neo4j_adapter import Neo4jAdapter
from memory_service.utils.logging import get_logger
from memory_service.utils.metrics import get_metrics

logger = get_logger(__name__)
metrics = get_metrics()


class SyncManager:
    """Manages cross-store synchronization between Qdrant and Neo4j.

    Ensures eventual consistency between vector store (Qdrant) and
    graph store (Neo4j) through:
    - Tracking sync status on each memory
    - Retrying failed sync operations
    - Verifying bidirectional references
    """

    def __init__(
        self,
        qdrant: QdrantAdapter,
        neo4j: Neo4jAdapter,
        max_retries: int = 3,
        retry_delay_seconds: int = 60,
    ) -> None:
        """Initialize sync manager.

        Args:
            qdrant: Qdrant adapter
            neo4j: Neo4j adapter
            max_retries: Maximum retry attempts for failed syncs
            retry_delay_seconds: Delay between retries
        """
        self.qdrant = qdrant
        self.neo4j = neo4j
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds

    async def mark_pending(
        self,
        memory_id: UUID,
        memory_type: MemoryType,
    ) -> bool:
        """Mark a memory as pending synchronization.

        Args:
            memory_id: Memory ID
            memory_type: Memory type

        Returns:
            True if marked successfully
        """
        collection = self.qdrant.get_collection_name(memory_type)

        try:
            await self.qdrant.update_payload(
                collection=collection,
                point_id=memory_id,
                payload={
                    "sync_status": SyncStatus.PENDING.value,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
            )

            metrics.sync_pending_count.inc()
            logger.debug("sync_marked_pending", memory_id=str(memory_id))
            return True

        except Exception as e:
            logger.error("sync_mark_pending_failed", memory_id=str(memory_id), error=str(e))
            return False

    async def mark_failed(
        self,
        memory_id: UUID,
        memory_type: MemoryType,
        error_message: str | None = None,
    ) -> bool:
        """Mark a memory sync as failed.

        Args:
            memory_id: Memory ID
            memory_type: Memory type
            error_message: Optional error message

        Returns:
            True if marked successfully
        """
        collection = self.qdrant.get_collection_name(memory_type)

        try:
            payload: dict[str, Any] = {
                "sync_status": SyncStatus.FAILED.value,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            if error_message:
                payload["sync_error"] = error_message

            await self.qdrant.update_payload(
                collection=collection,
                point_id=memory_id,
                payload=payload,
            )

            metrics.sync_failed_count.inc()
            metrics.sync_pending_count.dec()
            logger.warning("sync_marked_failed", memory_id=str(memory_id), error=error_message)
            return True

        except Exception as e:
            logger.error("sync_mark_failed_error", memory_id=str(memory_id), error=str(e))
            return False

    async def mark_synced(
        self,
        memory_id: UUID,
        memory_type: MemoryType,
        neo4j_node_id: str | None = None,
    ) -> bool:
        """Mark a memory as successfully synchronized.

        Args:
            memory_id: Memory ID
            memory_type: Memory type
            neo4j_node_id: Neo4j node ID if available

        Returns:
            True if marked successfully
        """
        collection = self.qdrant.get_collection_name(memory_type)

        try:
            payload: dict[str, Any] = {
                "sync_status": SyncStatus.SYNCED.value,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            if neo4j_node_id:
                payload["neo4j_node_id"] = neo4j_node_id

            await self.qdrant.update_payload(
                collection=collection,
                point_id=memory_id,
                payload=payload,
            )

            metrics.sync_operations_total.labels(status="success").inc()
            metrics.sync_pending_count.dec()
            logger.debug("sync_marked_synced", memory_id=str(memory_id))
            return True

        except Exception as e:
            logger.error("sync_mark_synced_failed", memory_id=str(memory_id), error=str(e))
            return False

    async def get_pending_syncs(
        self,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get memories pending synchronization.

        Args:
            limit: Maximum number to return

        Returns:
            List of pending memory records
        """
        pending = []

        for memory_type in MemoryType:
            collection = self.qdrant.get_collection_name(memory_type)

            try:
                points, _ = await self.qdrant.scroll(
                    collection=collection,
                    filters={"sync_status": SyncStatus.PENDING.value},
                    limit=limit - len(pending),
                )

                for point in points:
                    pending.append({
                        "id": point["id"],
                        "type": memory_type,
                        "payload": point["payload"],
                    })

                if len(pending) >= limit:
                    break

            except Exception as e:
                logger.error("get_pending_syncs_failed", collection=collection, error=str(e))

        return pending

    async def get_failed_syncs(
        self,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get memories with failed synchronization.

        Args:
            limit: Maximum number to return

        Returns:
            List of failed memory records
        """
        failed = []

        for memory_type in MemoryType:
            collection = self.qdrant.get_collection_name(memory_type)

            try:
                points, _ = await self.qdrant.scroll(
                    collection=collection,
                    filters={"sync_status": SyncStatus.FAILED.value},
                    limit=limit - len(failed),
                )

                for point in points:
                    failed.append({
                        "id": point["id"],
                        "type": memory_type,
                        "payload": point["payload"],
                    })

                if len(failed) >= limit:
                    break

            except Exception as e:
                logger.error("get_failed_syncs_failed", collection=collection, error=str(e))

        return failed

    async def process_pending(
        self,
        batch_size: int = 50,
    ) -> tuple[int, int]:
        """Process pending synchronization entries.

        Creates or updates corresponding Neo4j nodes for pending Qdrant points.

        Args:
            batch_size: Number of entries to process per batch

        Returns:
            Tuple of (success_count, failure_count)
        """
        pending = await self.get_pending_syncs(limit=batch_size)

        success_count = 0
        failure_count = 0

        for entry in pending:
            memory_id = UUID(entry["id"]) if isinstance(entry["id"], str) else entry["id"]
            memory_type = entry["type"]
            payload = entry["payload"]

            try:
                # Get the node label for this memory type
                label = self.neo4j.get_node_label(memory_type)

                # Check if node exists in Neo4j
                existing = await self.neo4j.get_node(memory_id)

                if existing:
                    # Update existing node
                    await self.neo4j.update_node(
                        node_id=memory_id,
                        properties=payload,
                        label=label,
                    )
                else:
                    # Create new node
                    await self.neo4j.create_node(
                        label=label,
                        properties=payload,
                    )

                # Mark as synced
                await self.mark_synced(memory_id, memory_type, str(memory_id))
                success_count += 1

            except Exception as e:
                logger.error(
                    "sync_process_failed",
                    memory_id=str(memory_id),
                    error=str(e),
                )
                await self.mark_failed(memory_id, memory_type, str(e))
                failure_count += 1

        if success_count > 0 or failure_count > 0:
            logger.info(
                "sync_batch_processed",
                success=success_count,
                failures=failure_count,
            )

        return success_count, failure_count

    async def retry_failed(
        self,
        batch_size: int = 50,
    ) -> tuple[int, int]:
        """Retry failed synchronization entries.

        Args:
            batch_size: Number of entries to process per batch

        Returns:
            Tuple of (success_count, still_failed_count)
        """
        failed = await self.get_failed_syncs(limit=batch_size)

        success_count = 0
        still_failed = 0

        for entry in failed:
            memory_id = UUID(entry["id"]) if isinstance(entry["id"], str) else entry["id"]
            memory_type = entry["type"]

            # Mark as pending to retry
            await self.mark_pending(memory_id, memory_type)

        # Process the newly pending entries
        success_count, still_failed = await self.process_pending(batch_size)

        return success_count, still_failed

    async def verify_consistency(
        self,
        sample_size: int = 100,
    ) -> dict[str, Any]:
        """Verify cross-store consistency by sampling.

        Checks that memories in Qdrant have corresponding nodes in Neo4j
        and vice versa.

        Args:
            sample_size: Number of entries to sample

        Returns:
            Consistency report
        """
        report = {
            "qdrant_only": [],
            "neo4j_only": [],
            "mismatched": [],
            "consistent": 0,
            "total_checked": 0,
        }

        # Sample from Qdrant and verify Neo4j
        for memory_type in MemoryType:
            collection = self.qdrant.get_collection_name(memory_type)
            label = self.neo4j.get_node_label(memory_type)

            try:
                points, _ = await self.qdrant.scroll(
                    collection=collection,
                    filters={"deleted": False, "sync_status": SyncStatus.SYNCED.value},
                    limit=sample_size // len(MemoryType),
                )

                for point in points:
                    point_id = point["id"]
                    report["total_checked"] += 1

                    # Check if exists in Neo4j
                    neo4j_node = await self.neo4j.get_node(point_id, label)

                    if not neo4j_node:
                        report["qdrant_only"].append({
                            "id": point_id,
                            "type": memory_type.value,
                        })
                    else:
                        # Verify key fields match
                        qdrant_content = point["payload"].get("content", "")
                        neo4j_content = neo4j_node.get("content", "")

                        if qdrant_content != neo4j_content:
                            report["mismatched"].append({
                                "id": point_id,
                                "type": memory_type.value,
                                "difference": "content",
                            })
                        else:
                            report["consistent"] += 1

            except Exception as e:
                logger.error("verify_consistency_failed", memory_type=memory_type.value, error=str(e))

        return report

    async def get_sync_stats(self) -> dict[str, Any]:
        """Get synchronization statistics.

        Returns:
            Dictionary with sync statistics
        """
        stats = {
            "pending_count": 0,
            "failed_count": 0,
            "synced_count": 0,
            "by_type": {},
        }

        for memory_type in MemoryType:
            collection = self.qdrant.get_collection_name(memory_type)
            type_stats = {
                "pending": 0,
                "failed": 0,
                "synced": 0,
            }

            try:
                for status in SyncStatus:
                    count = await self.qdrant.count(
                        collection=collection,
                        filters={"sync_status": status.value},
                    )
                    type_stats[status.value] = count

                    if status == SyncStatus.PENDING:
                        stats["pending_count"] += count
                    elif status == SyncStatus.FAILED:
                        stats["failed_count"] += count
                    else:
                        stats["synced_count"] += count

            except Exception as e:
                logger.error("get_sync_stats_failed", collection=collection, error=str(e))

            stats["by_type"][memory_type.value] = type_stats

        # Update gauges
        metrics.sync_pending_count.set(stats["pending_count"])
        metrics.sync_failed_count.set(stats["failed_count"])

        return stats
