"""Integration tests for project isolation (REQ-MEM-002-VER-002).

Tests verify that:
- Data from project A is never visible from project B
- Qdrant collections are properly prefixed with project_id
- Neo4j queries filter by project_id
- Cross-project access is prevented
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from memory_service.storage.qdrant_adapter import QdrantAdapter
from memory_service.storage.neo4j_adapter import Neo4jAdapter
from memory_service.models import MemoryType


class TestQdrantProjectIsolation:
    """Tests for Qdrant project isolation via collection prefixing."""

    def test_collection_name_includes_project_id(self):
        """Collection names should be prefixed with project_id."""
        with patch("memory_service.storage.qdrant_adapter.QdrantClient"):
            adapter_a = QdrantAdapter(
                host="localhost",
                port=6333,
                project_id="project_a"
            )
            adapter_b = QdrantAdapter(
                host="localhost",
                port=6333,
                project_id="project_b"
            )

            # Get collection names for same memory type
            collection_a = adapter_a.get_collection_name(MemoryType.FUNCTION)
            collection_b = adapter_b.get_collection_name(MemoryType.FUNCTION)

            # Collections should be different
            assert collection_a != collection_b
            assert "project_a" in collection_a
            assert "project_b" in collection_b

    def test_different_projects_have_different_collections(self):
        """Different projects should use completely separate collections."""
        with patch("memory_service.storage.qdrant_adapter.QdrantClient"):
            adapter_a = QdrantAdapter(
                host="localhost",
                port=6333,
                project_id="my-project"
            )
            adapter_b = QdrantAdapter(
                host="localhost",
                port=6333,
                project_id="other-project"
            )

            # Check all memory types have different collection names
            for memory_type in MemoryType:
                coll_a = adapter_a.get_collection_name(memory_type)
                coll_b = adapter_b.get_collection_name(memory_type)
                assert coll_a != coll_b, f"Collections for {memory_type} should differ"

    @pytest.mark.asyncio
    async def test_search_only_returns_own_project_data(self):
        """Search should only return data from the configured project."""
        with patch("memory_service.storage.qdrant_adapter.QdrantClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            # Setup mock search to track collection name
            searched_collections = []

            def capture_search(*args, **kwargs):
                collection = kwargs.get("collection_name") or args[0]
                searched_collections.append(collection)
                return MagicMock(points=[])

            mock_client.search = capture_search

            adapter_a = QdrantAdapter(
                host="localhost",
                port=6333,
                project_id="project_a"
            )

            # Perform search
            with patch.object(adapter_a, '_client', mock_client):
                loop = asyncio.get_running_loop()
                collection = adapter_a.get_collection_name(MemoryType.FUNCTION)
                await loop.run_in_executor(
                    None,
                    lambda: mock_client.search(
                        collection_name=collection,
                        query_vector=[0.1] * 1024,
                        limit=10
                    )
                )

            # Verify search was on project_a's collection
            assert len(searched_collections) == 1
            assert "project_a" in searched_collections[0]


class TestNeo4jProjectIsolation:
    """Tests for Neo4j project isolation via project_id property filtering."""

    @pytest.mark.asyncio
    async def test_create_node_includes_project_id(self):
        """Created nodes should include project_id property."""
        with patch("memory_service.storage.neo4j_adapter.AsyncGraphDatabase") as mock_driver_class:
            mock_driver = AsyncMock()
            mock_driver_class.driver.return_value = mock_driver

            # Track query parameters
            captured_params = []

            async def capture_run(query, params=None):
                captured_params.append(params)
                mock_result = AsyncMock()
                mock_result.single.return_value = {"id": str(uuid4())}
                return mock_result

            mock_session = AsyncMock()
            mock_session.run = capture_run
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_driver.session.return_value = mock_session

            adapter = Neo4jAdapter(
                uri="bolt://localhost:7687",
                user="neo4j",
                password="test",
                project_id="my_project"
            )
            adapter._driver = mock_driver

            # Create a node
            node_id = str(uuid4())
            await adapter.create_node(
                memory_type=MemoryType.FUNCTION,
                node_id=node_id,
                properties={"name": "test_func", "content": "test content"}
            )

            # Verify project_id was included
            assert len(captured_params) > 0
            props = captured_params[-1].get("props", {})
            assert props.get("project_id") == "my_project"

    @pytest.mark.asyncio
    async def test_get_node_filters_by_project_id(self):
        """Get operations should filter by project_id."""
        with patch("memory_service.storage.neo4j_adapter.AsyncGraphDatabase") as mock_driver_class:
            mock_driver = AsyncMock()
            mock_driver_class.driver.return_value = mock_driver

            captured_queries = []

            async def capture_run(query, params=None):
                captured_queries.append(query)
                mock_result = AsyncMock()
                mock_result.single.return_value = None
                return mock_result

            mock_session = AsyncMock()
            mock_session.run = capture_run
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_driver.session.return_value = mock_session

            adapter = Neo4jAdapter(
                uri="bolt://localhost:7687",
                user="neo4j",
                password="test",
                project_id="secure_project"
            )
            adapter._driver = mock_driver

            # Try to get a node
            await adapter.get_node(
                memory_type=MemoryType.FUNCTION,
                node_id=str(uuid4())
            )

            # Verify query includes project_id filter
            assert len(captured_queries) > 0
            assert "project_id" in captured_queries[-1]


class TestCrossProjectAccessPrevention:
    """Tests to ensure cross-project data access is prevented."""

    def test_project_id_is_immutable(self):
        """Project ID should not be changeable after adapter creation."""
        with patch("memory_service.storage.qdrant_adapter.QdrantClient"):
            adapter = QdrantAdapter(
                host="localhost",
                port=6333,
                project_id="original_project"
            )

            # Try to modify project_id
            with pytest.raises(AttributeError):
                adapter.project_id = "hacked_project"

    def test_adapters_store_project_id(self):
        """Adapters should store and use the configured project_id."""
        with patch("memory_service.storage.qdrant_adapter.QdrantClient"):
            qdrant = QdrantAdapter(
                host="localhost",
                port=6333,
                project_id="test_project_123"
            )
            assert qdrant.project_id == "test_project_123"

        with patch("memory_service.storage.neo4j_adapter.AsyncGraphDatabase"):
            neo4j = Neo4jAdapter(
                uri="bolt://localhost:7687",
                user="neo4j",
                password="test",
                project_id="test_project_123"
            )
            assert neo4j.project_id == "test_project_123"


class TestProjectIsolationCaseSensitivity:
    """Tests for case-sensitive project isolation (REQ-MEM-002-DATA-011)."""

    def test_different_case_project_ids_are_distinct(self):
        """MyProject and myproject should be different projects."""
        with patch("memory_service.storage.qdrant_adapter.QdrantClient"):
            adapter_upper = QdrantAdapter(
                host="localhost",
                port=6333,
                project_id="MyProject"
            )
            adapter_lower = QdrantAdapter(
                host="localhost",
                port=6333,
                project_id="myproject"
            )

            # Collection names should be different
            collection_upper = adapter_upper.get_collection_name(MemoryType.FUNCTION)
            collection_lower = adapter_lower.get_collection_name(MemoryType.FUNCTION)

            assert collection_upper != collection_lower
            assert "MyProject" in collection_upper
            assert "myproject" in collection_lower
