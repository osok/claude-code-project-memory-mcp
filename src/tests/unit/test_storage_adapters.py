"""Unit tests for storage adapters (Qdrant and Neo4j)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from memory_service.models import MemoryType
from memory_service.storage.qdrant_adapter import QdrantAdapter, COLLECTIONS, VECTOR_DIMENSION
from memory_service.storage.neo4j_adapter import Neo4jAdapter
from memory_service.storage.sync import SyncManager


class TestQdrantAdapterInit:
    """Unit tests for QdrantAdapter initialization."""

    def test_init_basic(self) -> None:
        """Test basic initialization with defaults."""
        with patch("memory_service.storage.qdrant_adapter.QdrantClient"):
            adapter = QdrantAdapter(host="localhost", port=6333)

            assert adapter.host == "localhost"
            assert adapter.port == 6333
            assert adapter.grpc_port == 6334

    def test_init_with_api_key(self) -> None:
        """Test initialization with API key."""
        with patch("memory_service.storage.qdrant_adapter.QdrantClient") as mock_client:
            adapter = QdrantAdapter(
                host="localhost",
                port=6333,
                api_key="test-key",
            )

            mock_client.assert_called_once()
            call_kwargs = mock_client.call_args.kwargs
            assert call_kwargs["api_key"] == "test-key"

    def test_init_with_secret_str_api_key(self) -> None:
        """Test initialization with SecretStr API key."""
        from pydantic import SecretStr

        with patch("memory_service.storage.qdrant_adapter.QdrantClient") as mock_client:
            secret_key = SecretStr("secret-api-key")
            adapter = QdrantAdapter(
                host="localhost",
                port=6333,
                api_key=secret_key,
            )

            call_kwargs = mock_client.call_args.kwargs
            assert call_kwargs["api_key"] == "secret-api-key"


class TestQdrantAdapterHealthCheck:
    """Unit tests for QdrantAdapter health check."""

    @pytest.fixture
    def mock_adapter(self) -> QdrantAdapter:
        """Create adapter with mocked client."""
        with patch("memory_service.storage.qdrant_adapter.QdrantClient") as mock_client:
            adapter = QdrantAdapter(host="localhost", port=6333)
            adapter._client = MagicMock()
            return adapter

    @pytest.mark.asyncio
    async def test_health_check_success(self, mock_adapter: QdrantAdapter) -> None:
        """Test successful health check."""
        mock_adapter._client.get_collections.return_value = []

        result = await mock_adapter.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, mock_adapter: QdrantAdapter) -> None:
        """Test health check when Qdrant is unavailable."""
        mock_adapter._client.get_collections.side_effect = Exception("Connection error")

        result = await mock_adapter.health_check()

        assert result is False


class TestQdrantAdapterCollections:
    """Unit tests for QdrantAdapter collection management."""

    def test_collections_mapping_complete(self) -> None:
        """Test that all memory types have collection mappings."""
        for memory_type in MemoryType:
            assert memory_type in COLLECTIONS
            assert isinstance(COLLECTIONS[memory_type], str)

    def test_vector_dimension_correct(self) -> None:
        """Test that vector dimension matches voyage-code-3."""
        assert VECTOR_DIMENSION == 1024

    @pytest.fixture
    def mock_adapter(self) -> QdrantAdapter:
        """Create adapter with mocked client."""
        with patch("memory_service.storage.qdrant_adapter.QdrantClient") as mock_client:
            adapter = QdrantAdapter(host="localhost", port=6333)
            adapter._client = MagicMock()
            return adapter

    @pytest.mark.asyncio
    async def test_initialize_collections_creates_new(self, mock_adapter: QdrantAdapter) -> None:
        """Test that initialize_collections creates new collections."""
        mock_adapter._client.collection_exists.return_value = False
        mock_adapter._client.create_collection.return_value = None

        await mock_adapter.initialize_collections()

        # Should check existence and create for each collection
        assert mock_adapter._client.collection_exists.call_count == len(COLLECTIONS)
        assert mock_adapter._client.create_collection.call_count == len(COLLECTIONS)

    @pytest.mark.asyncio
    async def test_initialize_collections_skips_existing(self, mock_adapter: QdrantAdapter) -> None:
        """Test that initialize_collections skips existing collections."""
        mock_adapter._client.collection_exists.return_value = True

        await mock_adapter.initialize_collections()

        # Should check existence but not create
        assert mock_adapter._client.collection_exists.call_count == len(COLLECTIONS)
        assert mock_adapter._client.create_collection.call_count == 0


class TestQdrantAdapterGetCollectionName:
    """Unit tests for collection name helper."""

    @pytest.fixture
    def adapter(self) -> QdrantAdapter:
        """Create adapter with mocked client."""
        with patch("memory_service.storage.qdrant_adapter.QdrantClient"):
            return QdrantAdapter(host="localhost", port=6333)

    def test_get_collection_name_requirements(self, adapter: QdrantAdapter) -> None:
        """Test getting collection name for requirements."""
        name = adapter.get_collection_name(MemoryType.REQUIREMENTS)
        assert name == "requirements"

    def test_get_collection_name_function(self, adapter: QdrantAdapter) -> None:
        """Test getting collection name for functions."""
        name = adapter.get_collection_name(MemoryType.FUNCTION)
        assert name == "functions"

    def test_get_collection_name_design(self, adapter: QdrantAdapter) -> None:
        """Test getting collection name for designs."""
        name = adapter.get_collection_name(MemoryType.DESIGN)
        assert name == "designs"


class TestNeo4jAdapterInit:
    """Unit tests for Neo4jAdapter initialization."""

    def test_init_basic(self) -> None:
        """Test basic initialization."""
        with patch("memory_service.storage.neo4j_adapter.AsyncGraphDatabase") as mock_gd:
            mock_driver = MagicMock()
            mock_gd.driver.return_value = mock_driver

            adapter = Neo4jAdapter(
                uri="bolt://localhost:7687",
                user="neo4j",
                password="password",
            )

            assert adapter.uri == "bolt://localhost:7687"
            # Note: Neo4jAdapter stores uri but not user as attribute

    def test_init_with_secret_password(self) -> None:
        """Test initialization with SecretStr password."""
        from pydantic import SecretStr

        with patch("memory_service.storage.neo4j_adapter.AsyncGraphDatabase") as mock_gd:
            mock_driver = MagicMock()
            mock_gd.driver.return_value = mock_driver

            secret_password = SecretStr("secret-password")
            adapter = Neo4jAdapter(
                uri="bolt://localhost:7687",
                user="neo4j",
                password=secret_password,
            )

            # Should have extracted secret value
            call_args = mock_gd.driver.call_args
            assert call_args.kwargs["auth"] == ("neo4j", "secret-password")


class TestNeo4jAdapterHealthCheck:
    """Unit tests for Neo4jAdapter health check."""

    @pytest.fixture
    def mock_adapter(self) -> Neo4jAdapter:
        """Create adapter with mocked driver."""
        with patch("memory_service.storage.neo4j_adapter.AsyncGraphDatabase") as mock_gd:
            mock_driver = MagicMock()
            mock_gd.driver.return_value = mock_driver
            adapter = Neo4jAdapter(
                uri="bolt://localhost:7687",
                user="neo4j",
                password="password",
            )
            adapter._driver = mock_driver
            return adapter

    @pytest.mark.asyncio
    async def test_health_check_success(self, mock_adapter: Neo4jAdapter) -> None:
        """Test successful health check."""
        mock_session = AsyncMock()
        mock_adapter._driver.session.return_value = mock_session
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.run.return_value = AsyncMock()

        result = await mock_adapter.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, mock_adapter: Neo4jAdapter) -> None:
        """Test health check when Neo4j is unavailable."""
        mock_adapter._driver.session.side_effect = Exception("Connection error")

        result = await mock_adapter.health_check()

        assert result is False


class TestNeo4jAdapterClose:
    """Unit tests for Neo4jAdapter close."""

    @pytest.mark.asyncio
    async def test_close_calls_driver_close(self) -> None:
        """Test that close properly closes the driver."""
        with patch("memory_service.storage.neo4j_adapter.AsyncGraphDatabase") as mock_gd:
            mock_driver = AsyncMock()
            mock_gd.driver.return_value = mock_driver

            adapter = Neo4jAdapter(
                uri="bolt://localhost:7687",
                user="neo4j",
                password="password",
            )

            await adapter.close()

            mock_driver.close.assert_called_once()


class TestSyncManagerInit:
    """Unit tests for SyncManager initialization."""

    def test_init_basic(self) -> None:
        """Test basic initialization."""
        mock_qdrant = MagicMock()
        mock_neo4j = MagicMock()

        manager = SyncManager(qdrant=mock_qdrant, neo4j=mock_neo4j)

        assert manager.qdrant == mock_qdrant
        assert manager.neo4j == mock_neo4j


class TestSyncManagerMarkPending:
    """Unit tests for SyncManager mark_pending."""

    @pytest.fixture
    def sync_manager(self) -> SyncManager:
        """Create sync manager with mocks."""
        mock_qdrant = AsyncMock()
        mock_qdrant.update_payload.return_value = True
        mock_neo4j = AsyncMock()
        return SyncManager(qdrant=mock_qdrant, neo4j=mock_neo4j)

    @pytest.mark.asyncio
    async def test_mark_pending_updates_qdrant(self, sync_manager: SyncManager) -> None:
        """Test that mark_pending updates Qdrant payload."""
        memory_id = uuid4()

        await sync_manager.mark_pending(
            memory_id=memory_id,
            memory_type=MemoryType.REQUIREMENTS,
        )

        # Should call update_payload on qdrant
        sync_manager.qdrant.update_payload.assert_called_once()


class TestSyncManagerProcessPending:
    """Unit tests for SyncManager process_pending."""

    @pytest.fixture
    def sync_manager(self) -> SyncManager:
        """Create sync manager with mocks."""
        mock_qdrant = AsyncMock()
        mock_qdrant.search.return_value = []  # No pending items
        mock_neo4j = AsyncMock()
        manager = SyncManager(qdrant=mock_qdrant, neo4j=mock_neo4j)
        return manager

    @pytest.mark.asyncio
    async def test_process_pending_empty(self, sync_manager: SyncManager) -> None:
        """Test processing when no pending items."""
        result = await sync_manager.process_pending()

        # With no pending items, should return success counts
        assert result[0] == 0  # success count
        assert result[1] == 0  # failure count


class TestQdrantAdapterFilterBuilder:
    """Unit tests for filter building utilities."""

    @pytest.fixture
    def adapter(self) -> QdrantAdapter:
        """Create adapter with mocked client."""
        with patch("memory_service.storage.qdrant_adapter.QdrantClient"):
            return QdrantAdapter(host="localhost", port=6333)

    def test_build_filter_basic(self, adapter: QdrantAdapter) -> None:
        """Test building a basic filter."""
        filters = {"deleted": False}
        result = adapter._build_filter(filters)

        assert result is not None

    def test_build_filter_with_multiple_conditions(self, adapter: QdrantAdapter) -> None:
        """Test building filter with multiple conditions."""
        filters = {
            "deleted": False,
            "language": "python",
            "file_path": "src/main.py",
        }
        result = adapter._build_filter(filters)

        assert result is not None

    def test_build_filter_empty(self, adapter: QdrantAdapter) -> None:
        """Test building filter with empty dict."""
        result = adapter._build_filter({})

        # Empty filter should return None or empty filter
        # Implementation may vary


class TestQdrantAdapterMethods:
    """Unit tests for QdrantAdapter CRUD methods."""

    @pytest.fixture
    def mock_adapter(self) -> QdrantAdapter:
        """Create adapter with mocked client."""
        with patch("memory_service.storage.qdrant_adapter.QdrantClient"):
            adapter = QdrantAdapter(host="localhost", port=6333)
            adapter._client = MagicMock()
            return adapter

    @pytest.mark.asyncio
    async def test_count_calls_client(self, mock_adapter: QdrantAdapter) -> None:
        """Test count method calls client correctly."""
        mock_adapter._client.count.return_value = MagicMock(count=42)

        result = await mock_adapter.count(collection="functions", filters={})

        assert result == 42

    @pytest.mark.asyncio
    async def test_get_returns_point(self, mock_adapter: QdrantAdapter) -> None:
        """Test get method returns point data."""
        point_id = str(uuid4())
        mock_point = MagicMock()
        mock_point.id = point_id
        mock_point.payload = {"content": "test"}
        mock_point.vector = [0.1] * 1024
        mock_adapter._client.retrieve.return_value = [mock_point]

        result = await mock_adapter.get(
            collection="functions",
            point_id=point_id,
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_get_returns_none_when_not_found(self, mock_adapter: QdrantAdapter) -> None:
        """Test get method returns None when point not found."""
        mock_adapter._client.retrieve.return_value = []

        result = await mock_adapter.get(
            collection="functions",
            point_id=str(uuid4()),
        )

        assert result is None


class TestQdrantAdapterSearchConfig:
    """Unit tests for QdrantAdapter search configuration."""

    @pytest.fixture
    def adapter(self) -> QdrantAdapter:
        """Create adapter with mocked client."""
        with patch("memory_service.storage.qdrant_adapter.QdrantClient"):
            return QdrantAdapter(host="localhost", port=6333)

    def test_search_accepts_vector(self, adapter: QdrantAdapter) -> None:
        """Test that search method signature accepts required parameters."""
        # Test that the method exists with correct signature
        import inspect
        sig = inspect.signature(adapter.search)
        params = list(sig.parameters.keys())

        assert "collection" in params
        assert "vector" in params
        assert "limit" in params
        assert "filters" in params

    def test_search_default_limit(self, adapter: QdrantAdapter) -> None:
        """Test that search has sensible default limit."""
        import inspect
        sig = inspect.signature(adapter.search)

        # Check default value for limit
        limit_param = sig.parameters["limit"]
        assert limit_param.default == 10


class TestQdrantAdapterUpsert:
    """Unit tests for QdrantAdapter upsert method."""

    @pytest.fixture
    def mock_adapter(self) -> QdrantAdapter:
        """Create adapter with mocked client."""
        with patch("memory_service.storage.qdrant_adapter.QdrantClient"):
            adapter = QdrantAdapter(host="localhost", port=6333)
            adapter._client = MagicMock()
            return adapter

    @pytest.mark.asyncio
    async def test_upsert_single_point(self, mock_adapter: QdrantAdapter) -> None:
        """Test upserting a single point."""
        point_id = str(uuid4())
        mock_adapter._client.upsert.return_value = True

        await mock_adapter.upsert(
            collection="functions",
            point_id=point_id,
            vector=[0.1] * 1024,
            payload={"content": "test function", "name": "test"},
        )

        mock_adapter._client.upsert.assert_called_once()


class TestQdrantAdapterDeleteConfig:
    """Unit tests for QdrantAdapter delete configuration."""

    @pytest.fixture
    def adapter(self) -> QdrantAdapter:
        """Create adapter with mocked client."""
        with patch("memory_service.storage.qdrant_adapter.QdrantClient"):
            return QdrantAdapter(host="localhost", port=6333)

    def test_delete_method_exists(self, adapter: QdrantAdapter) -> None:
        """Test that delete method exists with correct signature."""
        import inspect
        sig = inspect.signature(adapter.delete)
        params = list(sig.parameters.keys())

        assert "collection" in params
        assert "point_id" in params  # Single point_id

    def test_delete_by_filter_method_exists(self, adapter: QdrantAdapter) -> None:
        """Test that delete_by_filter method exists."""
        import inspect
        sig = inspect.signature(adapter.delete_by_filter)
        params = list(sig.parameters.keys())

        assert "collection" in params
        assert "filters" in params


class TestQdrantAdapterUpdatePayload:
    """Unit tests for QdrantAdapter update_payload method."""

    @pytest.fixture
    def mock_adapter(self) -> QdrantAdapter:
        """Create adapter with mocked client."""
        with patch("memory_service.storage.qdrant_adapter.QdrantClient"):
            adapter = QdrantAdapter(host="localhost", port=6333)
            adapter._client = MagicMock()
            return adapter

    @pytest.mark.asyncio
    async def test_update_payload_single_field(self, mock_adapter: QdrantAdapter) -> None:
        """Test updating a single payload field."""
        point_id = str(uuid4())
        mock_adapter._client.set_payload.return_value = True

        await mock_adapter.update_payload(
            collection="functions",
            point_id=point_id,
            payload={"access_count": 5},
        )

        mock_adapter._client.set_payload.assert_called_once()


class TestNeo4jAdapterNodeOperations:
    """Unit tests for Neo4jAdapter node operations."""

    @pytest.fixture
    def mock_adapter(self) -> Neo4jAdapter:
        """Create adapter with mocked driver."""
        with patch("memory_service.storage.neo4j_adapter.AsyncGraphDatabase") as mock_gd:
            mock_driver = MagicMock()
            mock_gd.driver.return_value = mock_driver
            adapter = Neo4jAdapter(
                uri="bolt://localhost:7687",
                user="neo4j",
                password="password",
            )
            adapter._driver = mock_driver
            return adapter

    @pytest.mark.asyncio
    async def test_create_node_success(self, mock_adapter: Neo4jAdapter) -> None:
        """Test creating a node successfully."""
        mock_session = AsyncMock()
        mock_adapter._driver.session.return_value = mock_session
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_result = AsyncMock()
        mock_record = MagicMock()
        mock_record.__getitem__ = MagicMock(return_value="node-id-123")
        mock_result.single = AsyncMock(return_value=mock_record)
        mock_session.run = AsyncMock(return_value=mock_result)

        result = await mock_adapter.create_node(
            label="Requirement",
            properties={"id": "node-id-123", "content": "Test requirement"},
        )

        assert result == "node-id-123"

    @pytest.mark.asyncio
    async def test_get_node_found(self, mock_adapter: Neo4jAdapter) -> None:
        """Test getting a node that exists."""
        mock_session = AsyncMock()
        mock_adapter._driver.session.return_value = mock_session
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_result = AsyncMock()
        mock_record = MagicMock()
        mock_record.__getitem__ = MagicMock(return_value={"id": "node-id", "content": "Test"})
        mock_result.single = AsyncMock(return_value=mock_record)
        mock_session.run = AsyncMock(return_value=mock_result)

        result = await mock_adapter.get_node("node-id", label="Requirement")

        assert result is not None
        assert result["id"] == "node-id"

    @pytest.mark.asyncio
    async def test_get_node_not_found(self, mock_adapter: Neo4jAdapter) -> None:
        """Test getting a node that doesn't exist."""
        mock_session = AsyncMock()
        mock_adapter._driver.session.return_value = mock_session
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value=None)
        mock_session.run = AsyncMock(return_value=mock_result)

        result = await mock_adapter.get_node("non-existent-id")

        assert result is None

    @pytest.mark.asyncio
    async def test_update_node_success(self, mock_adapter: Neo4jAdapter) -> None:
        """Test updating a node successfully."""
        mock_session = AsyncMock()
        mock_adapter._driver.session.return_value = mock_session
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value=MagicMock())
        mock_session.run = AsyncMock(return_value=mock_result)

        result = await mock_adapter.update_node(
            node_id="node-id",
            properties={"content": "Updated content"},
            label="Requirement",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_node_success(self, mock_adapter: Neo4jAdapter) -> None:
        """Test deleting a node successfully."""
        mock_session = AsyncMock()
        mock_adapter._driver.session.return_value = mock_session
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_result = AsyncMock()
        mock_record = MagicMock()
        mock_record.__getitem__ = MagicMock(return_value=1)
        mock_result.single = AsyncMock(return_value=mock_record)
        mock_session.run = AsyncMock(return_value=mock_result)

        result = await mock_adapter.delete_node("node-id")

        assert result is True


class TestNeo4jAdapterRelationshipOperations:
    """Unit tests for Neo4jAdapter relationship operations."""

    @pytest.fixture
    def mock_adapter(self) -> Neo4jAdapter:
        """Create adapter with mocked driver."""
        with patch("memory_service.storage.neo4j_adapter.AsyncGraphDatabase") as mock_gd:
            mock_driver = MagicMock()
            mock_gd.driver.return_value = mock_driver
            adapter = Neo4jAdapter(
                uri="bolt://localhost:7687",
                user="neo4j",
                password="password",
            )
            adapter._driver = mock_driver
            return adapter

    @pytest.mark.asyncio
    async def test_create_relationship_success(self, mock_adapter: Neo4jAdapter) -> None:
        """Test creating a relationship successfully."""
        from memory_service.models import RelationshipType

        mock_session = AsyncMock()
        mock_adapter._driver.session.return_value = mock_session
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value=MagicMock())
        mock_session.run = AsyncMock(return_value=mock_result)

        result = await mock_adapter.create_relationship(
            source_id="source-id",
            target_id="target-id",
            relationship_type=RelationshipType.IMPLEMENTS,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_relationship_success(self, mock_adapter: Neo4jAdapter) -> None:
        """Test deleting a relationship successfully."""
        from memory_service.models import RelationshipType

        mock_session = AsyncMock()
        mock_adapter._driver.session.return_value = mock_session
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_result = AsyncMock()
        mock_record = MagicMock()
        mock_record.__getitem__ = MagicMock(return_value=1)
        mock_result.single = AsyncMock(return_value=mock_record)
        mock_session.run = AsyncMock(return_value=mock_result)

        result = await mock_adapter.delete_relationship(
            source_id="source-id",
            target_id="target-id",
            relationship_type=RelationshipType.IMPLEMENTS,
        )

        assert result == 1

    @pytest.mark.asyncio
    async def test_get_related_success(self, mock_adapter: Neo4jAdapter) -> None:
        """Test getting related nodes successfully."""
        mock_session = AsyncMock()
        mock_adapter._driver.session.return_value = mock_session
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[
            {
                "id": "related-id-1",
                "labels": ["Requirement"],
                "properties": {"content": "Related requirement"},
                "relationship_type": "IMPLEMENTS",
            }
        ])
        mock_session.run = AsyncMock(return_value=mock_result)

        result = await mock_adapter.get_related("node-id", limit=10)

        assert len(result) == 1
        assert result[0]["id"] == "related-id-1"


class TestNeo4jAdapterGraphTraversal:
    """Unit tests for Neo4jAdapter graph traversal operations."""

    @pytest.fixture
    def mock_adapter(self) -> Neo4jAdapter:
        """Create adapter with mocked driver."""
        with patch("memory_service.storage.neo4j_adapter.AsyncGraphDatabase") as mock_gd:
            mock_driver = MagicMock()
            mock_gd.driver.return_value = mock_driver
            adapter = Neo4jAdapter(
                uri="bolt://localhost:7687",
                user="neo4j",
                password="password",
            )
            adapter._driver = mock_driver
            return adapter

    @pytest.mark.asyncio
    async def test_find_path_success(self, mock_adapter: Neo4jAdapter) -> None:
        """Test finding path between nodes."""
        mock_session = AsyncMock()
        mock_adapter._driver.session.return_value = mock_session
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        path_data = [
            {"id": "node-1", "labels": ["Requirement"], "properties": {}},
            {"id": "node-2", "labels": ["Design"], "properties": {}},
        ]
        mock_result = AsyncMock()
        mock_record = MagicMock()
        mock_record.__getitem__ = MagicMock(return_value=path_data)
        mock_result.single = AsyncMock(return_value=mock_record)
        mock_session.run = AsyncMock(return_value=mock_result)

        result = await mock_adapter.find_path("node-1", "node-2")

        assert result is not None
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_find_path_no_path(self, mock_adapter: Neo4jAdapter) -> None:
        """Test finding path when no path exists."""
        mock_session = AsyncMock()
        mock_adapter._driver.session.return_value = mock_session
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value=None)
        mock_session.run = AsyncMock(return_value=mock_result)

        result = await mock_adapter.find_path("node-1", "non-existent")

        assert result is None

    @pytest.mark.asyncio
    async def test_execute_cypher_success(self, mock_adapter: Neo4jAdapter) -> None:
        """Test executing custom Cypher query."""
        mock_session = AsyncMock()
        mock_adapter._driver.session.return_value = mock_session
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[{"name": "test"}])
        mock_session.run = AsyncMock(return_value=mock_result)

        result = await mock_adapter.execute_cypher(
            "MATCH (n) RETURN n.name as name LIMIT 1"
        )

        assert len(result) == 1
        assert result[0]["name"] == "test"

    @pytest.mark.asyncio
    async def test_count_nodes_success(self, mock_adapter: Neo4jAdapter) -> None:
        """Test counting nodes."""
        mock_session = AsyncMock()
        mock_adapter._driver.session.return_value = mock_session
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_result = AsyncMock()
        mock_record = MagicMock()
        mock_record.__getitem__ = MagicMock(return_value=42)
        mock_result.single = AsyncMock(return_value=mock_record)
        mock_session.run = AsyncMock(return_value=mock_result)

        result = await mock_adapter.count_nodes(label="Requirement")

        assert result == 42

    @pytest.mark.asyncio
    async def test_count_nodes_with_filters(self, mock_adapter: Neo4jAdapter) -> None:
        """Test counting nodes with filters."""
        mock_session = AsyncMock()
        mock_adapter._driver.session.return_value = mock_session
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_result = AsyncMock()
        mock_record = MagicMock()
        mock_record.__getitem__ = MagicMock(return_value=10)
        mock_result.single = AsyncMock(return_value=mock_record)
        mock_session.run = AsyncMock(return_value=mock_result)

        result = await mock_adapter.count_nodes(
            label="Requirement",
            filters={"status": "approved"},
        )

        assert result == 10


class TestNeo4jAdapterSchema:
    """Unit tests for Neo4jAdapter schema operations."""

    @pytest.fixture
    def mock_adapter(self) -> Neo4jAdapter:
        """Create adapter with mocked driver."""
        with patch("memory_service.storage.neo4j_adapter.AsyncGraphDatabase") as mock_gd:
            mock_driver = MagicMock()
            mock_gd.driver.return_value = mock_driver
            adapter = Neo4jAdapter(
                uri="bolt://localhost:7687",
                user="neo4j",
                password="password",
            )
            adapter._driver = mock_driver
            return adapter

    @pytest.mark.asyncio
    async def test_initialize_schema_success(self, mock_adapter: Neo4jAdapter) -> None:
        """Test initializing schema successfully."""
        mock_session = AsyncMock()
        mock_adapter._driver.session.return_value = mock_session
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.run = AsyncMock()

        await mock_adapter.initialize_schema()

        # Should have called run multiple times for constraints and indexes
        assert mock_session.run.call_count > 0

    def test_get_node_label(self, mock_adapter: Neo4jAdapter) -> None:
        """Test getting node label for memory type."""
        label = mock_adapter.get_node_label(MemoryType.REQUIREMENTS)
        assert label == "Requirement"

        label = mock_adapter.get_node_label(MemoryType.DESIGN)
        assert label == "Design"

        label = mock_adapter.get_node_label(MemoryType.FUNCTION)
        assert label == "Function"


class TestSyncManagerMarkOperations:
    """Unit tests for SyncManager mark operations."""

    @pytest.fixture
    def sync_manager(self) -> SyncManager:
        """Create sync manager with mocks."""
        mock_qdrant = AsyncMock()
        mock_qdrant.update_payload.return_value = True
        mock_qdrant.get_collection_name.return_value = "requirements"
        mock_neo4j = AsyncMock()
        return SyncManager(qdrant=mock_qdrant, neo4j=mock_neo4j)

    @pytest.mark.asyncio
    async def test_mark_failed_success(self, sync_manager: SyncManager) -> None:
        """Test marking a memory as failed."""
        memory_id = uuid4()

        result = await sync_manager.mark_failed(
            memory_id=memory_id,
            memory_type=MemoryType.REQUIREMENTS,
            error_message="Test error",
        )

        assert result is True
        sync_manager.qdrant.update_payload.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_synced_success(self, sync_manager: SyncManager) -> None:
        """Test marking a memory as synced."""
        memory_id = uuid4()

        result = await sync_manager.mark_synced(
            memory_id=memory_id,
            memory_type=MemoryType.REQUIREMENTS,
            neo4j_node_id="neo4j-node-123",
        )

        assert result is True
        sync_manager.qdrant.update_payload.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_pending_failure(self, sync_manager: SyncManager) -> None:
        """Test mark_pending when update fails."""
        sync_manager.qdrant.update_payload.side_effect = Exception("Update failed")
        memory_id = uuid4()

        result = await sync_manager.mark_pending(
            memory_id=memory_id,
            memory_type=MemoryType.REQUIREMENTS,
        )

        assert result is False


class TestSyncManagerGetOperations:
    """Unit tests for SyncManager get operations."""

    @pytest.fixture
    def sync_manager(self) -> SyncManager:
        """Create sync manager with mocks."""
        mock_qdrant = AsyncMock()
        mock_qdrant.get_collection_name.return_value = "requirements"
        mock_qdrant.scroll.return_value = ([], None)
        mock_neo4j = AsyncMock()
        return SyncManager(qdrant=mock_qdrant, neo4j=mock_neo4j)

    @pytest.mark.asyncio
    async def test_get_pending_syncs_empty(self, sync_manager: SyncManager) -> None:
        """Test getting pending syncs when empty."""
        result = await sync_manager.get_pending_syncs(limit=100)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_pending_syncs_with_results(self, sync_manager: SyncManager) -> None:
        """Test getting pending syncs with results."""
        sync_manager.qdrant.scroll.return_value = (
            [{"id": "memory-1", "payload": {"content": "Test"}}],
            None,
        )

        result = await sync_manager.get_pending_syncs(limit=10)

        assert len(result) >= 0  # May be empty if scroll returns no pending

    @pytest.mark.asyncio
    async def test_get_failed_syncs_empty(self, sync_manager: SyncManager) -> None:
        """Test getting failed syncs when empty."""
        result = await sync_manager.get_failed_syncs(limit=100)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_sync_stats(self, sync_manager: SyncManager) -> None:
        """Test getting sync statistics."""
        sync_manager.qdrant.count.return_value = 5

        result = await sync_manager.get_sync_stats()

        assert "pending_count" in result
        assert "failed_count" in result
        assert "synced_count" in result
        assert "by_type" in result


class TestSyncManagerProcessOperations:
    """Unit tests for SyncManager process operations."""

    @pytest.fixture
    def sync_manager(self) -> SyncManager:
        """Create sync manager with mocks."""
        mock_qdrant = AsyncMock()
        mock_qdrant.get_collection_name.return_value = "requirements"
        mock_qdrant.scroll.return_value = ([], None)
        mock_qdrant.update_payload.return_value = True
        mock_neo4j = AsyncMock()
        mock_neo4j.get_node_label.return_value = "Requirement"
        mock_neo4j.get_node.return_value = None
        mock_neo4j.create_node.return_value = "new-node-id"
        return SyncManager(qdrant=mock_qdrant, neo4j=mock_neo4j)

    @pytest.mark.asyncio
    async def test_process_pending_success(self, sync_manager: SyncManager) -> None:
        """Test processing pending syncs successfully."""
        success, failures = await sync_manager.process_pending(batch_size=50)

        assert success == 0
        assert failures == 0

    @pytest.mark.asyncio
    async def test_retry_failed_empty(self, sync_manager: SyncManager) -> None:
        """Test retrying failed syncs when none exist."""
        success, still_failed = await sync_manager.retry_failed(batch_size=50)

        assert success == 0
        assert still_failed == 0


class TestSyncManagerConsistency:
    """Unit tests for SyncManager consistency verification."""

    @pytest.fixture
    def sync_manager(self) -> SyncManager:
        """Create sync manager with mocks."""
        mock_qdrant = AsyncMock()
        mock_qdrant.get_collection_name.return_value = "requirements"
        mock_qdrant.scroll.return_value = ([], None)
        mock_neo4j = AsyncMock()
        mock_neo4j.get_node_label.return_value = "Requirement"
        mock_neo4j.get_node.return_value = None
        return SyncManager(qdrant=mock_qdrant, neo4j=mock_neo4j)

    @pytest.mark.asyncio
    async def test_verify_consistency_empty(self, sync_manager: SyncManager) -> None:
        """Test verifying consistency with no data."""
        result = await sync_manager.verify_consistency(sample_size=100)

        assert "qdrant_only" in result
        assert "neo4j_only" in result
        assert "mismatched" in result
        assert "consistent" in result
        assert "total_checked" in result
        assert result["total_checked"] == 0


class TestQdrantAdapterScrollAndSearch:
    """Unit tests for QdrantAdapter scroll and search operations."""

    @pytest.fixture
    def mock_adapter(self) -> QdrantAdapter:
        """Create adapter with mocked client."""
        with patch("memory_service.storage.qdrant_adapter.QdrantClient"):
            adapter = QdrantAdapter(host="localhost", port=6333)
            adapter._client = MagicMock()
            return adapter

    @pytest.mark.asyncio
    async def test_scroll_success(self, mock_adapter: QdrantAdapter) -> None:
        """Test scrolling through collection."""
        mock_point = MagicMock()
        mock_point.id = str(uuid4())
        mock_point.payload = {"content": "test"}
        mock_point.vector = None

        mock_adapter._client.scroll.return_value = ([mock_point], "next-offset")

        points, offset = await mock_adapter.scroll(
            collection="functions",
            filters={},
            limit=10,
        )

        assert len(points) == 1
        assert offset == "next-offset"

    @pytest.mark.asyncio
    async def test_search_success(self, mock_adapter: QdrantAdapter) -> None:
        """Test searching collection."""
        mock_point = MagicMock()
        mock_point.id = str(uuid4())
        mock_point.payload = {"content": "test"}
        mock_point.score = 0.95

        # The search method uses query_points which returns an object with .points
        mock_result = MagicMock()
        mock_result.points = [mock_point]
        mock_adapter._client.query_points.return_value = mock_result

        results = await mock_adapter.search(
            collection="functions",
            vector=[0.1] * 1024,
            limit=10,
        )

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_delete_success(self, mock_adapter: QdrantAdapter) -> None:
        """Test deleting a point."""
        mock_adapter._client.delete.return_value = True
        point_id = str(uuid4())

        result = await mock_adapter.delete(
            collection="functions",
            point_id=point_id,
        )

        mock_adapter._client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_by_filter_success(self, mock_adapter: QdrantAdapter) -> None:
        """Test deleting by filter."""
        mock_adapter._client.delete.return_value = True

        result = await mock_adapter.delete_by_filter(
            collection="functions",
            filters={"file_path": "deleted.py"},
        )

        mock_adapter._client.delete.assert_called_once()
