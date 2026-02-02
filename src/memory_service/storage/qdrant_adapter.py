"""Qdrant vector database adapter."""

import asyncio
from typing import Any, Sequence
from uuid import UUID

from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse

from memory_service.models import MemoryType
from memory_service.utils.logging import get_logger
from memory_service.utils.metrics import get_metrics

logger = get_logger(__name__)
metrics = get_metrics()

# Collection names for each memory type
COLLECTIONS = {
    MemoryType.REQUIREMENTS: "requirements",
    MemoryType.DESIGN: "designs",
    MemoryType.CODE_PATTERN: "code_patterns",
    MemoryType.COMPONENT: "components",
    MemoryType.FUNCTION: "functions",
    MemoryType.TEST_HISTORY: "test_history",
    MemoryType.SESSION: "sessions",
    MemoryType.USER_PREFERENCE: "user_preferences",
}

# Vector dimension for voyage-code-3
VECTOR_DIMENSION = 1024

# HNSW index configuration
HNSW_CONFIG = models.HnswConfigDiff(
    m=16,  # Number of edges per node
    ef_construct=200,  # Size of dynamic list during construction
    full_scan_threshold=10000,  # Threshold for full scan vs index
)


class QdrantAdapter:
    """Adapter for Qdrant vector database operations.

    Provides methods for:
    - Connection management with health checks
    - Collection initialization
    - CRUD operations (upsert, get, update, delete)
    - Vector similarity search with filtering
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        api_key: Any | None = None,
        grpc_port: int = 6334,
        prefer_grpc: bool = True,
        timeout: float = 60.0,
    ) -> None:
        """Initialize Qdrant adapter.

        Args:
            host: Qdrant server hostname
            port: Qdrant HTTP port
            api_key: API key for authentication (optional)
            grpc_port: Qdrant gRPC port
            prefer_grpc: Whether to prefer gRPC over HTTP
            timeout: Request timeout in seconds (default: 60)
        """
        self.host = host
        self.port = port
        self.grpc_port = grpc_port

        # Extract secret value if SecretStr
        api_key_value = api_key.get_secret_value() if hasattr(api_key, "get_secret_value") else api_key

        self._client = QdrantClient(
            host=host,
            port=port,
            grpc_port=grpc_port,
            api_key=api_key_value,
            prefer_grpc=prefer_grpc,
            timeout=timeout,
        )
        logger.info("qdrant_adapter_initialized", host=host, port=port)

    async def health_check(self) -> bool:
        """Check if Qdrant is healthy and responsive.

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Run synchronous client method in executor
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._client.get_collections)
            metrics.storage_connection_status.labels(storage="qdrant").set(1)
            return True
        except Exception as e:
            logger.error("qdrant_health_check_failed", error=str(e))
            metrics.storage_connection_status.labels(storage="qdrant").set(0)
            return False

    async def initialize_collections(self) -> None:
        """Initialize all collections with proper schema.

        Creates collections for each memory type if they don't exist.
        """
        loop = asyncio.get_running_loop()

        for memory_type, collection_name in COLLECTIONS.items():
            try:
                # Check if collection exists
                exists = await loop.run_in_executor(
                    None,
                    lambda name=collection_name: self._client.collection_exists(name),
                )

                if not exists:
                    # Create collection with HNSW index
                    await loop.run_in_executor(
                        None,
                        lambda name=collection_name: self._client.create_collection(
                            collection_name=name,
                            vectors_config=models.VectorParams(
                                size=VECTOR_DIMENSION,
                                distance=models.Distance.COSINE,
                            ),
                            hnsw_config=HNSW_CONFIG,
                        ),
                    )
                    logger.info("qdrant_collection_created", collection=collection_name)

                    # Create payload indexes for common query fields
                    await self._create_payload_indexes(collection_name)

            except Exception as e:
                logger.error(
                    "qdrant_collection_init_failed",
                    collection=collection_name,
                    error=str(e),
                )
                raise

    async def _create_payload_indexes(self, collection_name: str) -> None:
        """Create payload indexes for efficient filtering.

        Args:
            collection_name: Name of the collection
        """
        loop = asyncio.get_running_loop()

        indexes = [
            ("type", models.PayloadSchemaType.KEYWORD),
            ("deleted", models.PayloadSchemaType.BOOL),
            ("sync_status", models.PayloadSchemaType.KEYWORD),
            ("created_at", models.PayloadSchemaType.DATETIME),
            ("updated_at", models.PayloadSchemaType.DATETIME),
            ("importance_score", models.PayloadSchemaType.FLOAT),
        ]

        for field_name, field_type in indexes:
            try:
                await loop.run_in_executor(
                    None,
                    lambda: self._client.create_payload_index(
                        collection_name=collection_name,
                        field_name=field_name,
                        field_schema=field_type,
                    ),
                )
            except UnexpectedResponse:
                # Index may already exist
                pass

    async def upsert(
        self,
        collection: str,
        point_id: str | UUID,
        vector: list[float],
        payload: dict[str, Any],
    ) -> bool:
        """Insert or update a point in Qdrant.

        Args:
            collection: Collection name
            point_id: Point ID (UUID)
            vector: Embedding vector (1024 dimensions)
            payload: Point payload data

        Returns:
            True if successful
        """
        import time

        start = time.perf_counter()
        loop = asyncio.get_running_loop()

        try:
            point = models.PointStruct(
                id=str(point_id),
                vector=vector,
                payload=payload,
            )

            await loop.run_in_executor(
                None,
                lambda: self._client.upsert(
                    collection_name=collection,
                    points=[point],
                    wait=True,
                ),
            )

            duration = time.perf_counter() - start
            metrics.storage_operations_total.labels(
                storage="qdrant",
                operation="upsert",
                status="success",
            ).inc()
            metrics.storage_operation_duration_seconds.labels(
                storage="qdrant",
                operation="upsert",
            ).observe(duration)

            logger.debug("qdrant_upsert_success", collection=collection, point_id=str(point_id))
            return True

        except Exception as e:
            metrics.storage_operations_total.labels(
                storage="qdrant",
                operation="upsert",
                status="error",
            ).inc()
            logger.error("qdrant_upsert_failed", collection=collection, error=str(e))
            raise

    async def upsert_batch(
        self,
        collection: str,
        points: list[tuple[str | UUID, list[float], dict[str, Any]]],
    ) -> bool:
        """Insert or update multiple points in batch.

        Args:
            collection: Collection name
            points: List of (point_id, vector, payload) tuples

        Returns:
            True if successful
        """
        import time

        start = time.perf_counter()
        loop = asyncio.get_running_loop()

        try:
            qdrant_points = [
                models.PointStruct(
                    id=str(point_id),
                    vector=vector,
                    payload=payload,
                )
                for point_id, vector, payload in points
            ]

            await loop.run_in_executor(
                None,
                lambda: self._client.upsert(
                    collection_name=collection,
                    points=qdrant_points,
                    wait=True,
                ),
            )

            duration = time.perf_counter() - start
            metrics.storage_operations_total.labels(
                storage="qdrant",
                operation="upsert_batch",
                status="success",
            ).inc()
            metrics.storage_operation_duration_seconds.labels(
                storage="qdrant",
                operation="upsert_batch",
            ).observe(duration)

            logger.debug("qdrant_batch_upsert_success", collection=collection, count=len(points))
            return True

        except Exception as e:
            metrics.storage_operations_total.labels(
                storage="qdrant",
                operation="upsert_batch",
                status="error",
            ).inc()
            logger.error("qdrant_batch_upsert_failed", collection=collection, error=str(e))
            raise

    async def get(
        self,
        collection: str,
        point_id: str | UUID,
        with_vector: bool = False,
    ) -> dict[str, Any] | None:
        """Retrieve a point by ID.

        Args:
            collection: Collection name
            point_id: Point ID
            with_vector: Whether to include the vector

        Returns:
            Point payload or None if not found
        """
        loop = asyncio.get_running_loop()

        try:
            result = await loop.run_in_executor(
                None,
                lambda: self._client.retrieve(
                    collection_name=collection,
                    ids=[str(point_id)],
                    with_payload=True,
                    with_vectors=with_vector,
                ),
            )

            if result:
                point = result[0]
                data = dict(point.payload) if point.payload else {}
                if with_vector and point.vector:
                    data["embedding"] = point.vector
                return data

            return None

        except Exception as e:
            logger.error("qdrant_get_failed", collection=collection, error=str(e))
            raise

    async def delete(
        self,
        collection: str,
        point_id: str | UUID,
    ) -> bool:
        """Delete a point by ID.

        Args:
            collection: Collection name
            point_id: Point ID

        Returns:
            True if deleted
        """
        loop = asyncio.get_running_loop()

        try:
            await loop.run_in_executor(
                None,
                lambda: self._client.delete(
                    collection_name=collection,
                    points_selector=models.PointIdsList(
                        points=[str(point_id)],
                    ),
                    wait=True,
                ),
            )

            metrics.storage_operations_total.labels(
                storage="qdrant",
                operation="delete",
                status="success",
            ).inc()

            return True

        except Exception as e:
            metrics.storage_operations_total.labels(
                storage="qdrant",
                operation="delete",
                status="error",
            ).inc()
            logger.error("qdrant_delete_failed", collection=collection, error=str(e))
            raise

    async def search(
        self,
        collection: str,
        vector: list[float],
        limit: int = 10,
        filters: dict[str, Any] | None = None,
        score_threshold: float | None = None,
        with_vectors: bool = False,
    ) -> list[dict[str, Any]]:
        """Search for similar vectors.

        Args:
            collection: Collection name
            vector: Query vector
            limit: Maximum results to return
            filters: Filter conditions
            score_threshold: Minimum similarity score
            with_vectors: Whether to include vectors in results

        Returns:
            List of matching points with scores
        """
        import time

        start = time.perf_counter()
        loop = asyncio.get_running_loop()

        try:
            qdrant_filter = self._build_filter(filters) if filters else None

            results = await loop.run_in_executor(
                None,
                lambda: self._client.query_points(
                    collection_name=collection,
                    query=vector,
                    limit=limit,
                    query_filter=qdrant_filter,
                    score_threshold=score_threshold,
                    with_payload=True,
                    with_vectors=with_vectors,
                ).points,
            )

            duration = time.perf_counter() - start
            metrics.storage_operations_total.labels(
                storage="qdrant",
                operation="search",
                status="success",
            ).inc()
            metrics.storage_operation_duration_seconds.labels(
                storage="qdrant",
                operation="search",
            ).observe(duration)

            return [
                {
                    "id": result.id,
                    "score": result.score,
                    "payload": dict(result.payload) if result.payload else {},
                    **({"vector": result.vector} if with_vectors and result.vector else {}),
                }
                for result in results
            ]

        except Exception as e:
            metrics.storage_operations_total.labels(
                storage="qdrant",
                operation="search",
                status="error",
            ).inc()
            logger.error("qdrant_search_failed", collection=collection, error=str(e))
            raise

    def _build_filter(self, filters: dict[str, Any]) -> models.Filter:
        """Build Qdrant filter from dictionary.

        Supports:
        - Equality: {"field": value}
        - Range: {"field": {"gte": x, "lte": y}}
        - Contains: {"field": {"contains": value}}
        - Must not: {"field": {"not": value}}

        Args:
            filters: Filter dictionary

        Returns:
            Qdrant Filter object
        """
        conditions = []

        for field, value in filters.items():
            if isinstance(value, dict):
                # Complex filter
                if "gte" in value or "lte" in value or "gt" in value or "lt" in value:
                    # Range filter
                    conditions.append(
                        models.FieldCondition(
                            key=field,
                            range=models.Range(
                                gte=value.get("gte"),
                                lte=value.get("lte"),
                                gt=value.get("gt"),
                                lt=value.get("lt"),
                            ),
                        )
                    )
                elif "contains" in value:
                    # Text contains
                    conditions.append(
                        models.FieldCondition(
                            key=field,
                            match=models.MatchText(text=value["contains"]),
                        )
                    )
                elif "not" in value:
                    # Must not match
                    conditions.append(
                        models.FieldCondition(
                            key=field,
                            match=models.MatchExcept(**{"except": [value["not"]]}),
                        )
                    )
                elif "in" in value:
                    # Match any in list
                    conditions.append(
                        models.FieldCondition(
                            key=field,
                            match=models.MatchAny(any=value["in"]),
                        )
                    )
            elif isinstance(value, list):
                # Match any in list
                conditions.append(
                    models.FieldCondition(
                        key=field,
                        match=models.MatchAny(any=value),
                    )
                )
            elif isinstance(value, bool):
                # Boolean match
                conditions.append(
                    models.FieldCondition(
                        key=field,
                        match=models.MatchValue(value=value),
                    )
                )
            else:
                # Simple equality
                conditions.append(
                    models.FieldCondition(
                        key=field,
                        match=models.MatchValue(value=value),
                    )
                )

        return models.Filter(must=conditions)

    async def update_payload(
        self,
        collection: str,
        point_id: str | UUID,
        payload: dict[str, Any],
    ) -> bool:
        """Update payload for a point.

        Args:
            collection: Collection name
            point_id: Point ID
            payload: New payload fields to set

        Returns:
            True if updated
        """
        loop = asyncio.get_running_loop()

        try:
            await loop.run_in_executor(
                None,
                lambda: self._client.set_payload(
                    collection_name=collection,
                    payload=payload,
                    points=[str(point_id)],
                    wait=True,
                ),
            )
            return True

        except Exception as e:
            logger.error("qdrant_update_payload_failed", collection=collection, error=str(e))
            raise

    async def scroll(
        self,
        collection: str,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: str | None = None,
        with_vectors: bool = False,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Scroll through all points in a collection.

        Args:
            collection: Collection name
            filters: Optional filter conditions
            limit: Number of points per page
            offset: Offset for pagination
            with_vectors: Whether to include vectors

        Returns:
            Tuple of (points list, next offset)
        """
        loop = asyncio.get_running_loop()

        try:
            qdrant_filter = self._build_filter(filters) if filters else None

            result = await loop.run_in_executor(
                None,
                lambda: self._client.scroll(
                    collection_name=collection,
                    scroll_filter=qdrant_filter,
                    limit=limit,
                    offset=offset,
                    with_payload=True,
                    with_vectors=with_vectors,
                ),
            )

            points, next_offset = result

            return (
                [
                    {
                        "id": point.id,
                        "payload": dict(point.payload) if point.payload else {},
                        **({"vector": point.vector} if with_vectors and point.vector else {}),
                    }
                    for point in points
                ],
                next_offset,
            )

        except Exception as e:
            logger.error("qdrant_scroll_failed", collection=collection, error=str(e))
            raise

    async def count(
        self,
        collection: str,
        filters: dict[str, Any] | None = None,
    ) -> int:
        """Count points in a collection.

        Args:
            collection: Collection name
            filters: Optional filter conditions

        Returns:
            Number of points
        """
        loop = asyncio.get_running_loop()

        try:
            qdrant_filter = self._build_filter(filters) if filters else None

            result = await loop.run_in_executor(
                None,
                lambda: self._client.count(
                    collection_name=collection,
                    count_filter=qdrant_filter,
                    exact=True,
                ),
            )

            return result.count

        except Exception as e:
            logger.error("qdrant_count_failed", collection=collection, error=str(e))
            raise

    async def delete_by_filter(
        self,
        collection: str,
        filters: dict[str, Any],
    ) -> int:
        """Delete points matching a filter.

        Args:
            collection: Collection name
            filters: Filter conditions

        Returns:
            Number of deleted points
        """
        loop = asyncio.get_running_loop()

        try:
            # First count how many will be deleted
            count = await self.count(collection, filters)

            if count == 0:
                return 0

            qdrant_filter = self._build_filter(filters)

            await loop.run_in_executor(
                None,
                lambda: self._client.delete(
                    collection_name=collection,
                    points_selector=models.FilterSelector(
                        filter=qdrant_filter,
                    ),
                    wait=True,
                ),
            )

            metrics.storage_operations_total.labels(
                storage="qdrant",
                operation="delete_by_filter",
                status="success",
            ).inc()

            logger.info(
                "qdrant_delete_by_filter_success",
                collection=collection,
                deleted_count=count,
            )

            return count

        except Exception as e:
            metrics.storage_operations_total.labels(
                storage="qdrant",
                operation="delete_by_filter",
                status="error",
            ).inc()
            logger.error("qdrant_delete_by_filter_failed", collection=collection, error=str(e))
            raise

    async def close(self) -> None:
        """Close the Qdrant client connection."""
        try:
            self._client.close()
            logger.info("qdrant_connection_closed")
        except Exception as e:
            logger.error("qdrant_close_failed", error=str(e))

    def get_collection_name(self, memory_type: MemoryType) -> str:
        """Get collection name for a memory type.

        Args:
            memory_type: Memory type

        Returns:
            Collection name
        """
        return COLLECTIONS[memory_type]
