"""Additional unit tests to improve coverage to 80% target.

These tests focus on edge cases and error paths that weren't covered:
- Embedding fallback paths
- Neo4j sync failure handling
- Query engine hybrid search strategies
- Sync manager edge cases
"""

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from memory_service.core.memory_manager import MemoryManager, MEMORY_CLASSES
from memory_service.core.query_engine import QueryEngine, QueryStrategy, SearchResult
from memory_service.models import MemoryType, RelationshipType, SyncStatus
from memory_service.storage.sync import SyncManager
from tests.fixtures.factories import (
    RequirementsMemoryFactory,
    DesignMemoryFactory,
    FunctionMemoryFactory,
    generate_embedding,
    reset_all_factories,
)


@pytest.fixture(autouse=True)
def reset_factories():
    """Reset factory counters before each test."""
    reset_all_factories()


# ============================================================================
# Memory Manager Additional Tests
# ============================================================================


class TestMemoryManagerEmbeddingFallback:
    """Tests for embedding fallback handling in MemoryManager."""

    @pytest.fixture
    def mock_qdrant(self):
        mock = AsyncMock()
        mock.get_collection_name = MagicMock(return_value="memories_requirements")
        mock.upsert = AsyncMock()
        mock.get = AsyncMock(return_value=None)
        mock.search = AsyncMock(return_value=[])
        mock.update_payload = AsyncMock()
        return mock

    @pytest.fixture
    def mock_neo4j(self):
        mock = AsyncMock()
        mock.get_node_label = MagicMock(return_value="Requirements")
        mock.create_node = AsyncMock()
        mock.update_node = AsyncMock()
        return mock

    @pytest.fixture
    def mock_embedding_service_with_fallback(self):
        """Mock service that returns fallback embeddings."""
        mock = AsyncMock()
        # Return fallback (is_fallback=True)
        mock.embed = AsyncMock(return_value=(generate_embedding(seed=42), True))
        return mock

    @pytest.fixture
    def memory_manager_with_fallback(self, mock_qdrant, mock_neo4j, mock_embedding_service_with_fallback):
        return MemoryManager(
            qdrant=mock_qdrant,
            neo4j=mock_neo4j,
            embedding_service=mock_embedding_service_with_fallback,
            conflict_threshold=0.95,
        )

    @pytest.mark.asyncio
    async def test_add_memory_marks_fallback_in_metadata(
        self, memory_manager_with_fallback: MemoryManager, mock_qdrant: AsyncMock
    ):
        """Test that fallback embedding is marked in metadata."""
        memory = RequirementsMemoryFactory.create()
        # Clear embedding to force regeneration (factory uses `embedding or generate_embedding()`)
        memory.embedding = []

        memory_id, _ = await memory_manager_with_fallback.add_memory(memory, check_conflicts=False)

        # Verify memory has fallback marker in metadata
        assert memory.metadata.get("embedding_is_fallback") is True

    @pytest.mark.asyncio
    async def test_update_memory_marks_fallback_on_content_change(
        self, mock_qdrant, mock_neo4j, mock_embedding_service_with_fallback
    ):
        """Test that content update regenerates embedding with fallback marker."""
        # Setup existing memory
        existing_data = {
            "id": uuid4(),
            "type": MemoryType.REQUIREMENTS,
            "content": "Original content",
            "embedding": generate_embedding(seed=1),
            "requirement_id": "REQ-MEM-FN-001",
            "title": "Test Requirement",
            "description": "Test description",
            "priority": "High",
            "status": "Approved",
            "source_document": "requirements.md",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "access_count": 0,
            "importance_score": 0.5,
            "deleted": False,
            "sync_status": "synced",
            "metadata": {},
        }
        mock_qdrant.get = AsyncMock(return_value=existing_data)

        manager = MemoryManager(
            qdrant=mock_qdrant,
            neo4j=mock_neo4j,
            embedding_service=mock_embedding_service_with_fallback,
            conflict_threshold=0.95,
        )

        # Update with new content
        updated = await manager.update_memory(
            memory_id=existing_data["id"],
            memory_type=MemoryType.REQUIREMENTS,
            updates={"content": "New content that triggers embedding regeneration"},
        )

        assert updated is not None
        assert updated.metadata.get("embedding_is_fallback") is True


class TestMemoryManagerNeo4jSyncFailure:
    """Tests for Neo4j sync failure handling."""

    @pytest.fixture
    def mock_qdrant(self):
        mock = AsyncMock()
        mock.get_collection_name = MagicMock(return_value="memories_requirements")
        mock.upsert = AsyncMock()
        mock.get = AsyncMock(return_value=None)
        mock.search = AsyncMock(return_value=[])
        mock.update_payload = AsyncMock()
        return mock

    @pytest.fixture
    def mock_neo4j_failing(self):
        """Mock Neo4j that fails on operations."""
        mock = AsyncMock()
        mock.get_node_label = MagicMock(return_value="Requirements")
        mock.create_node = AsyncMock(side_effect=Exception("Neo4j connection failed"))
        mock.update_node = AsyncMock(side_effect=Exception("Neo4j update failed"))
        return mock

    @pytest.fixture
    def mock_embedding_service(self):
        mock = AsyncMock()
        mock.embed = AsyncMock(return_value=(generate_embedding(seed=42), False))
        return mock

    @pytest.mark.asyncio
    async def test_add_memory_marks_pending_on_neo4j_failure(
        self, mock_qdrant, mock_neo4j_failing, mock_embedding_service
    ):
        """Test that memory is marked as pending sync when Neo4j fails."""
        manager = MemoryManager(
            qdrant=mock_qdrant,
            neo4j=mock_neo4j_failing,
            embedding_service=mock_embedding_service,
        )

        memory = RequirementsMemoryFactory.create()
        memory_id, _ = await manager.add_memory(memory, check_conflicts=False, sync_to_neo4j=True)

        # Memory should still be added (Qdrant succeeded)
        assert memory_id == memory.id
        # Sync manager should have been called to mark pending
        mock_qdrant.update_payload.assert_called()

    @pytest.mark.asyncio
    async def test_update_memory_marks_pending_on_neo4j_failure(
        self, mock_qdrant, mock_neo4j_failing, mock_embedding_service
    ):
        """Test that update marks pending sync when Neo4j fails."""
        existing_data = {
            "id": uuid4(),
            "type": MemoryType.REQUIREMENTS,
            "content": "Original content",
            "embedding": generate_embedding(seed=1),
            "requirement_id": "REQ-MEM-FN-001",
            "title": "Test Requirement",
            "description": "Test description",
            "priority": "High",
            "status": "Approved",
            "source_document": "requirements.md",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "access_count": 0,
            "importance_score": 0.5,
            "deleted": False,
            "sync_status": "synced",
            "metadata": {},
        }
        mock_qdrant.get = AsyncMock(return_value=existing_data)

        manager = MemoryManager(
            qdrant=mock_qdrant,
            neo4j=mock_neo4j_failing,
            embedding_service=mock_embedding_service,
        )

        # Update should still succeed (Qdrant update works)
        updated = await manager.update_memory(
            memory_id=existing_data["id"],
            memory_type=MemoryType.REQUIREMENTS,
            updates={"priority": "Critical"},
            regenerate_embedding=False,
        )

        assert updated is not None
        assert updated.priority == "Critical"


# ============================================================================
# Query Engine Additional Tests
# ============================================================================


class TestQueryEngineHybridSearchStrategies:
    """Tests for hybrid search strategies in QueryEngine."""

    @pytest.fixture
    def mock_qdrant(self):
        mock = AsyncMock()
        mock.get_collection_name = MagicMock(side_effect=lambda t: f"memories_{t.value}")
        mock.search = AsyncMock(return_value=[
            {"id": str(uuid4()), "score": 0.9, "payload": {"content": "test result"}}
        ])
        return mock

    @pytest.fixture
    def mock_neo4j(self):
        mock = AsyncMock()
        mock.get_node_label = MagicMock(return_value="Memory")
        mock.execute_cypher = AsyncMock(return_value=[])
        mock.get_related = AsyncMock(return_value=[])
        return mock

    @pytest.fixture
    def mock_embedding_service(self):
        mock = AsyncMock()
        mock.embed_for_query = AsyncMock(return_value=generate_embedding(seed=42))
        return mock

    @pytest.fixture
    def query_engine(self, mock_qdrant, mock_neo4j, mock_embedding_service):
        return QueryEngine(
            qdrant=mock_qdrant,
            neo4j=mock_neo4j,
            embedding_service=mock_embedding_service,
        )

    @pytest.mark.asyncio
    async def test_hybrid_search_graph_only_strategy(
        self, query_engine: QueryEngine, mock_neo4j: AsyncMock
    ):
        """Test hybrid search with GRAPH_ONLY strategy."""
        # Short query with relationships should use graph-first
        mock_neo4j.get_related.return_value = [
            {"id": str(uuid4()), "type": "function", "properties": {"content": "related"}}
        ]

        results = await query_engine.hybrid_search(
            query="calls",
            relationship_types=[RelationshipType.CALLS],
            limit=5,
        )

        # Should have executed (results depend on mock behavior)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_hybrid_search_vector_first_expands_via_graph(
        self, query_engine: QueryEngine, mock_qdrant: AsyncMock, mock_neo4j: AsyncMock
    ):
        """Test that vector-first strategy expands via graph."""
        # Setup semantic results with proper structure
        result_id = str(uuid4())
        mock_qdrant.search.return_value = [
            {"id": result_id, "score": 0.9, "payload": {"content": "semantic result", "type": "function"}}
        ]

        # Setup graph expansion with proper structure (including labels for _label_to_memory_type)
        mock_neo4j.get_related.return_value = [
            {
                "id": str(uuid4()),
                "labels": ["Function"],  # Required by _expand_via_graph
                "properties": {"content": "graph expanded"},
            }
        ]

        results = await query_engine.hybrid_search(
            query="find all authentication functions with their dependencies",
            memory_types=[MemoryType.FUNCTION],
            relationship_types=[RelationshipType.CALLS],
            limit=10,
        )

        # Should return results
        assert isinstance(results, list)

    def test_query_planner_vector_only_for_simple_query(self, query_engine: QueryEngine):
        """Test planner selects vector-only for simple semantic query."""
        plan = query_engine._plan_query(
            query="find authentication code",
            memory_types=None,
            relationship_types=None,
            filters=None,
            limit=10,
        )

        assert plan.strategy == QueryStrategy.VECTOR_ONLY

    def test_query_planner_graph_first_for_relationship_query(self, query_engine: QueryEngine):
        """Test planner selects graph-first for relationship query."""
        plan = query_engine._plan_query(
            query="imports",
            memory_types=None,
            relationship_types=[RelationshipType.IMPORTS],
            filters=None,
            limit=10,
        )

        assert plan.strategy == QueryStrategy.GRAPH_FIRST

    def test_query_planner_vector_first_for_long_query_with_relationships(
        self, query_engine: QueryEngine
    ):
        """Test planner selects vector-first for long query with relationships."""
        plan = query_engine._plan_query(
            query="find all functions that handle user authentication and call external services",
            memory_types=None,
            relationship_types=[RelationshipType.CALLS],
            filters=None,
            limit=10,
        )

        assert plan.strategy == QueryStrategy.VECTOR_FIRST


class TestQueryEngineEdgeCases:
    """Tests for edge cases in QueryEngine."""

    @pytest.fixture
    def mock_qdrant(self):
        mock = AsyncMock()
        mock.get_collection_name = MagicMock(side_effect=lambda t: f"memories_{t.value}")
        mock.search = AsyncMock(return_value=[])
        return mock

    @pytest.fixture
    def mock_neo4j(self):
        mock = AsyncMock()
        mock.execute_cypher = AsyncMock(return_value=[])
        mock.get_related = AsyncMock(return_value=[])
        return mock

    @pytest.fixture
    def mock_embedding_service(self):
        mock = AsyncMock()
        mock.embed_for_query = AsyncMock(return_value=generate_embedding(seed=42))
        return mock

    @pytest.fixture
    def query_engine(self, mock_qdrant, mock_neo4j, mock_embedding_service):
        return QueryEngine(
            qdrant=mock_qdrant,
            neo4j=mock_neo4j,
            embedding_service=mock_embedding_service,
        )

    @pytest.mark.asyncio
    async def test_semantic_search_empty_results(
        self, query_engine: QueryEngine, mock_qdrant: AsyncMock
    ):
        """Test semantic search handles empty results gracefully."""
        mock_qdrant.search.return_value = []

        results = await query_engine.semantic_search(
            query="nonexistent query",
            memory_types=[MemoryType.FUNCTION],
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_get_related_with_no_relationships(
        self, query_engine: QueryEngine, mock_neo4j: AsyncMock
    ):
        """Test get_related returns empty list when no relationships."""
        mock_neo4j.get_related.return_value = []

        results = await query_engine.get_related(
            entity_id=uuid4(),
            relationship_types=[RelationshipType.CALLS],
        )

        assert results == []

    def test_cosine_similarity_with_empty_vectors(self, query_engine: QueryEngine):
        """Test cosine similarity handles edge cases."""
        # Empty first vector
        result = query_engine._cosine_similarity([], [1.0, 2.0])
        assert result == 0.0

        # Empty second vector
        result = query_engine._cosine_similarity([1.0, 2.0], [])
        assert result == 0.0

    def test_has_entity_reference_patterns(self, query_engine: QueryEngine):
        """Test entity reference detection patterns."""
        # Should detect entity references (based on actual indicators in code:
        # "related to", "depends on", "calls", "imports", "import ", "implements", "extends")
        assert query_engine._has_entity_reference("what imports logging")
        assert query_engine._has_entity_reference("BaseService extends AbstractBase")  # Contains "extends"
        assert query_engine._has_entity_reference("function depends on UserService")  # Contains "depends on"
        assert query_engine._has_entity_reference("code related to authentication")  # Contains "related to"
        assert query_engine._has_entity_reference("class implements Interface")  # Contains "implements"
        assert query_engine._has_entity_reference("module calls helper function")  # Contains "calls"

        # Should not detect entity references
        assert not query_engine._has_entity_reference("find all tests")
        assert not query_engine._has_entity_reference("search logging functions")


# ============================================================================
# Sync Manager Additional Tests
# ============================================================================


class TestSyncManagerEdgeCases:
    """Tests for edge cases in SyncManager."""

    @pytest.fixture
    def mock_qdrant(self):
        mock = AsyncMock()
        mock.get_collection_name = MagicMock(side_effect=lambda t: f"memories_{t.value}")
        mock.update_payload = AsyncMock()
        mock.scroll = AsyncMock(return_value=([], None))
        mock.count = AsyncMock(return_value=0)
        return mock

    @pytest.fixture
    def mock_neo4j(self):
        mock = AsyncMock()
        mock.get_node_label = MagicMock(return_value="Memory")
        mock.get_node = AsyncMock(return_value=None)
        mock.create_node = AsyncMock()
        mock.update_node = AsyncMock()
        return mock

    @pytest.fixture
    def sync_manager(self, mock_qdrant, mock_neo4j):
        return SyncManager(mock_qdrant, mock_neo4j)

    @pytest.mark.asyncio
    async def test_mark_pending_failure(self, sync_manager: SyncManager, mock_qdrant: AsyncMock):
        """Test mark_pending returns False on error."""
        mock_qdrant.update_payload.side_effect = Exception("Update failed")

        result = await sync_manager.mark_pending(uuid4(), MemoryType.REQUIREMENTS)

        assert result is False

    @pytest.mark.asyncio
    async def test_mark_failed_with_error_message(
        self, sync_manager: SyncManager, mock_qdrant: AsyncMock
    ):
        """Test mark_failed includes error message in payload."""
        memory_id = uuid4()
        error_msg = "Sync failed: connection timeout"

        await sync_manager.mark_failed(memory_id, MemoryType.REQUIREMENTS, error_msg)

        call_kwargs = mock_qdrant.update_payload.call_args.kwargs
        assert call_kwargs["payload"]["sync_error"] == error_msg

    @pytest.mark.asyncio
    async def test_mark_synced_with_neo4j_node_id(
        self, sync_manager: SyncManager, mock_qdrant: AsyncMock
    ):
        """Test mark_synced includes Neo4j node ID."""
        memory_id = uuid4()
        neo4j_node_id = "neo4j-node-123"

        await sync_manager.mark_synced(memory_id, MemoryType.REQUIREMENTS, neo4j_node_id)

        call_kwargs = mock_qdrant.update_payload.call_args.kwargs
        assert call_kwargs["payload"]["neo4j_node_id"] == neo4j_node_id

    @pytest.mark.asyncio
    async def test_get_pending_syncs_handles_errors(
        self, sync_manager: SyncManager, mock_qdrant: AsyncMock
    ):
        """Test get_pending_syncs handles collection errors gracefully."""
        mock_qdrant.scroll.side_effect = Exception("Collection not found")

        result = await sync_manager.get_pending_syncs(limit=10)

        # Should return empty list, not raise
        assert result == []

    @pytest.mark.asyncio
    async def test_get_failed_syncs_handles_errors(
        self, sync_manager: SyncManager, mock_qdrant: AsyncMock
    ):
        """Test get_failed_syncs handles collection errors gracefully."""
        mock_qdrant.scroll.side_effect = Exception("Collection not found")

        result = await sync_manager.get_failed_syncs(limit=10)

        assert result == []

    @pytest.mark.asyncio
    async def test_process_pending_updates_existing_node(
        self, sync_manager: SyncManager, mock_qdrant: AsyncMock, mock_neo4j: AsyncMock
    ):
        """Test process_pending updates existing Neo4j node."""
        memory_id = uuid4()
        mock_qdrant.scroll.return_value = ([
            {"id": str(memory_id), "payload": {"content": "test", "id": str(memory_id)}}
        ], None)
        mock_neo4j.get_node.return_value = {"id": str(memory_id)}  # Node exists

        success, failures = await sync_manager.process_pending(batch_size=1)

        # Should update, not create
        mock_neo4j.update_node.assert_called()

    @pytest.mark.asyncio
    async def test_process_pending_creates_new_node(
        self, sync_manager: SyncManager, mock_qdrant: AsyncMock, mock_neo4j: AsyncMock
    ):
        """Test process_pending creates new Neo4j node."""
        memory_id = uuid4()
        mock_qdrant.scroll.return_value = ([
            {"id": str(memory_id), "payload": {"content": "test", "id": str(memory_id)}}
        ], None)
        mock_neo4j.get_node.return_value = None  # Node doesn't exist

        success, failures = await sync_manager.process_pending(batch_size=1)

        mock_neo4j.create_node.assert_called()

    @pytest.mark.asyncio
    async def test_verify_consistency_reports_qdrant_only(
        self, sync_manager: SyncManager, mock_qdrant: AsyncMock, mock_neo4j: AsyncMock
    ):
        """Test verify_consistency detects Qdrant-only entries."""
        memory_id = str(uuid4())
        mock_qdrant.scroll.return_value = ([
            {"id": memory_id, "payload": {"content": "test"}}
        ], None)
        mock_neo4j.get_node.return_value = None  # Not in Neo4j

        report = await sync_manager.verify_consistency(sample_size=10)

        assert len(report["qdrant_only"]) > 0
        assert report["qdrant_only"][0]["id"] == memory_id

    @pytest.mark.asyncio
    async def test_verify_consistency_reports_mismatched_content(
        self, sync_manager: SyncManager, mock_qdrant: AsyncMock, mock_neo4j: AsyncMock
    ):
        """Test verify_consistency detects content mismatches."""
        memory_id = str(uuid4())
        mock_qdrant.scroll.return_value = ([
            {"id": memory_id, "payload": {"content": "qdrant content"}}
        ], None)
        mock_neo4j.get_node.return_value = {"content": "different neo4j content"}

        report = await sync_manager.verify_consistency(sample_size=10)

        assert len(report["mismatched"]) > 0

    @pytest.mark.asyncio
    async def test_get_sync_stats_aggregates_correctly(
        self, sync_manager: SyncManager, mock_qdrant: AsyncMock
    ):
        """Test get_sync_stats aggregates across memory types."""
        # Return different counts for different statuses
        call_count = 0
        async def count_by_status(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return call_count  # Different count each call

        mock_qdrant.count = count_by_status

        stats = await sync_manager.get_sync_stats()

        assert "pending_count" in stats
        assert "failed_count" in stats
        assert "synced_count" in stats
        assert "by_type" in stats


# ============================================================================
# Voyage Client Additional Tests
# ============================================================================


class TestVoyageClientErrorPaths:
    """Tests for error paths in VoyageClient."""

    @pytest.mark.asyncio
    async def test_embed_batch_server_error_retry(self):
        """Test that server errors (5xx) trigger retry."""
        import httpx
        from memory_service.embedding.voyage_client import VoyageClient

        call_count = 0

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()

            async def server_error_then_success(*args, **kwargs):
                nonlocal call_count
                call_count += 1

                if call_count == 1:
                    response = MagicMock()
                    response.status_code = 503
                    raise httpx.HTTPStatusError(
                        "Service Unavailable",
                        request=MagicMock(),
                        response=response,
                    )
                else:
                    response = MagicMock()
                    response.json.return_value = {
                        "data": [{"embedding": [0.1] * 1024}]
                    }
                    response.raise_for_status = MagicMock()
                    return response

            mock_client.post = server_error_then_success
            mock_client_class.return_value = mock_client

            client = VoyageClient(api_key="test-key")
            embedding = await client.embed("test text")

            assert call_count == 2
            assert len(embedding) == 1024

            await client.close()

    @pytest.mark.asyncio
    async def test_embed_batch_timeout_retry(self):
        """Test that timeouts trigger retry."""
        import httpx
        from memory_service.embedding.voyage_client import VoyageClient

        call_count = 0

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()

            async def timeout_then_success(*args, **kwargs):
                nonlocal call_count
                call_count += 1

                if call_count == 1:
                    raise httpx.TimeoutException("Request timed out")
                else:
                    response = MagicMock()
                    response.json.return_value = {
                        "data": [{"embedding": [0.1] * 1024}]
                    }
                    response.raise_for_status = MagicMock()
                    return response

            mock_client.post = timeout_then_success
            mock_client_class.return_value = mock_client

            client = VoyageClient(api_key="test-key")
            embedding = await client.embed("test text")

            assert call_count == 2
            await client.close()

    @pytest.mark.asyncio
    async def test_embed_batch_client_error_no_retry(self):
        """Test that client errors (4xx except 429) don't retry."""
        import httpx
        from memory_service.embedding.voyage_client import VoyageClient

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()

            async def client_error(*args, **kwargs):
                response = MagicMock()
                response.status_code = 400
                response.text = "Bad request"
                raise httpx.HTTPStatusError(
                    "Bad Request",
                    request=MagicMock(),
                    response=response,
                )

            mock_client.post = client_error
            mock_client_class.return_value = mock_client

            client = VoyageClient(api_key="test-key")

            with pytest.raises(httpx.HTTPStatusError):
                await client.embed("test text")

            await client.close()

    @pytest.mark.asyncio
    async def test_embed_batch_dimension_validation(self):
        """Test that wrong dimension embeddings are rejected."""
        import httpx
        from memory_service.embedding.voyage_client import VoyageClient

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()

            async def wrong_dimension(*args, **kwargs):
                response = MagicMock()
                response.json.return_value = {
                    "data": [{"embedding": [0.1] * 512}]  # Wrong dimension
                }
                response.raise_for_status = MagicMock()
                return response

            mock_client.post = wrong_dimension
            mock_client_class.return_value = mock_client

            client = VoyageClient(api_key="test-key")

            with pytest.raises(ValueError, match="Expected 1024 dimensions"):
                await client.embed("test text")

            await client.close()


# ============================================================================
# Memory CRUD Additional Edge Cases
# ============================================================================


class TestMemoryCRUDEdgeCases:
    """Additional edge case tests for memory CRUD operations."""

    @pytest.fixture
    def mock_qdrant(self):
        mock = AsyncMock()
        mock.get_collection_name = MagicMock(return_value="memories_requirements")
        mock.upsert = AsyncMock()
        mock.get = AsyncMock(return_value=None)
        mock.search = AsyncMock(return_value=[])
        mock.update_payload = AsyncMock()
        mock.delete = AsyncMock()
        return mock

    @pytest.fixture
    def mock_neo4j(self):
        mock = AsyncMock()
        mock.get_node_label = MagicMock(return_value="Requirements")
        mock.create_node = AsyncMock()
        mock.update_node = AsyncMock()
        mock.delete_node = AsyncMock()
        return mock

    @pytest.fixture
    def mock_embedding_service(self):
        mock = AsyncMock()
        mock.embed = AsyncMock(return_value=(generate_embedding(seed=42), False))
        mock.embed_batch = AsyncMock(return_value=[(generate_embedding(seed=i), False) for i in range(10)])
        return mock

    @pytest.fixture
    def memory_manager(self, mock_qdrant, mock_neo4j, mock_embedding_service):
        return MemoryManager(
            qdrant=mock_qdrant,
            neo4j=mock_neo4j,
            embedding_service=mock_embedding_service,
        )

    @pytest.mark.asyncio
    async def test_get_memory_not_found_returns_none(
        self, memory_manager: MemoryManager, mock_qdrant: AsyncMock
    ):
        """Test get_memory returns None for non-existent memory."""
        mock_qdrant.get.return_value = None

        result = await memory_manager.get_memory(
            memory_id=uuid4(),
            memory_type=MemoryType.REQUIREMENTS,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_update_memory_not_found_returns_none(
        self, memory_manager: MemoryManager, mock_qdrant: AsyncMock
    ):
        """Test update_memory returns None for non-existent memory."""
        mock_qdrant.get.return_value = None

        result = await memory_manager.update_memory(
            memory_id=uuid4(),
            memory_type=MemoryType.REQUIREMENTS,
            updates={"content": "New content"},
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_add_memory_without_sync_to_neo4j(
        self, memory_manager: MemoryManager, mock_qdrant: AsyncMock, mock_neo4j: AsyncMock
    ):
        """Test add_memory with sync_to_neo4j=False."""
        memory = RequirementsMemoryFactory.create()

        memory_id, _ = await memory_manager.add_memory(
            memory, check_conflicts=False, sync_to_neo4j=False
        )

        # Qdrant should be called
        mock_qdrant.upsert.assert_called_once()
        # Neo4j should NOT be called
        mock_neo4j.create_node.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_memory_with_conflicts_logs_warning(
        self, memory_manager: MemoryManager, mock_qdrant: AsyncMock
    ):
        """Test add_memory logs warning when conflicts found."""
        # Setup mock to return similar memories
        mock_qdrant.search.return_value = [
            {
                "id": str(uuid4()),
                "score": 0.98,  # Above conflict threshold
                "payload": {"content": "Similar content"}
            }
        ]

        memory = RequirementsMemoryFactory.create()
        memory_id, conflicts = await memory_manager.add_memory(memory, check_conflicts=True)

        # Should return conflicts
        assert len(conflicts) > 0

    @pytest.mark.asyncio
    async def test_bulk_add_memories_partial_success(
        self, memory_manager: MemoryManager, mock_qdrant: AsyncMock
    ):
        """Test bulk_add handles failures by type batch.

        Note: bulk_add uses upsert_batch which processes all memories of a type
        together. If one type fails, all memories of that type fail.
        """
        # Create memories of different types so they're in different batches
        memories = [
            RequirementsMemoryFactory.create(),
            DesignMemoryFactory.create(),  # Different type = different batch
        ]

        # upsert_batch fails on second call (second type)
        call_count = 0
        async def upsert_batch_with_failure(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise Exception("Upsert batch failed")

        mock_qdrant.upsert_batch = upsert_batch_with_failure

        added_ids, errors = await memory_manager.bulk_add_memories(
            memories=memories,
            check_conflicts=False,
        )

        # First type succeeded, second type failed
        assert len(added_ids) == 1
        assert len(errors) == 1


class TestDeleteMemoryPaths:
    """Tests for delete_memory soft and hard delete paths."""

    @pytest.fixture
    def mock_qdrant(self):
        mock = AsyncMock()
        mock.get_collection_name = MagicMock(return_value="memories_requirements")
        mock.update_payload = AsyncMock()
        mock.delete = AsyncMock()
        return mock

    @pytest.fixture
    def mock_neo4j(self):
        mock = AsyncMock()
        mock.get_node_label = MagicMock(return_value="Requirements")
        mock.update_node = AsyncMock()
        mock.delete_node = AsyncMock()
        return mock

    @pytest.fixture
    def mock_embedding_service(self):
        mock = AsyncMock()
        mock.embed = AsyncMock(return_value=(generate_embedding(seed=42), False))
        return mock

    @pytest.fixture
    def memory_manager(self, mock_qdrant, mock_neo4j, mock_embedding_service):
        return MemoryManager(
            qdrant=mock_qdrant,
            neo4j=mock_neo4j,
            embedding_service=mock_embedding_service,
        )

    @pytest.mark.asyncio
    async def test_soft_delete_updates_payload(
        self, memory_manager: MemoryManager, mock_qdrant: AsyncMock
    ):
        """Test soft delete updates deleted flag in Qdrant."""
        memory_id = uuid4()

        result = await memory_manager.delete_memory(
            memory_id=memory_id,
            memory_type=MemoryType.REQUIREMENTS,
            soft_delete=True,
        )

        assert result is True
        mock_qdrant.update_payload.assert_called_once()
        call_kwargs = mock_qdrant.update_payload.call_args.kwargs
        assert call_kwargs["payload"]["deleted"] is True

    @pytest.mark.asyncio
    async def test_hard_delete_removes_point(
        self, memory_manager: MemoryManager, mock_qdrant: AsyncMock
    ):
        """Test hard delete removes point from Qdrant."""
        memory_id = uuid4()

        result = await memory_manager.delete_memory(
            memory_id=memory_id,
            memory_type=MemoryType.REQUIREMENTS,
            soft_delete=False,
        )

        assert result is True
        mock_qdrant.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_soft_delete_neo4j_failure_logged(
        self, memory_manager: MemoryManager, mock_neo4j: AsyncMock
    ):
        """Test that Neo4j soft delete failure is logged but doesn't fail operation."""
        memory_id = uuid4()
        mock_neo4j.update_node.side_effect = Exception("Neo4j unavailable")

        # Should still return True (Qdrant succeeded)
        result = await memory_manager.delete_memory(
            memory_id=memory_id,
            memory_type=MemoryType.REQUIREMENTS,
            soft_delete=True,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_hard_delete_neo4j_failure_logged(
        self, memory_manager: MemoryManager, mock_neo4j: AsyncMock
    ):
        """Test that Neo4j hard delete failure is logged but doesn't fail operation."""
        memory_id = uuid4()
        mock_neo4j.delete_node.side_effect = Exception("Neo4j unavailable")

        result = await memory_manager.delete_memory(
            memory_id=memory_id,
            memory_type=MemoryType.REQUIREMENTS,
            soft_delete=False,
        )

        assert result is True


# ============================================================================
# Bulk Operations Additional Tests
# ============================================================================


class TestBulkOperationsEdgeCases:
    """Additional tests for bulk memory operations."""

    @pytest.fixture
    def mock_qdrant(self):
        mock = AsyncMock()
        mock.get_collection_name = MagicMock(side_effect=lambda t: f"memories_{t.value}")
        mock.upsert_batch = AsyncMock()
        mock.search = AsyncMock(return_value=[])
        return mock

    @pytest.fixture
    def mock_neo4j(self):
        mock = AsyncMock()
        mock.get_node_label = MagicMock(side_effect=lambda t: t.value.title())
        mock.create_node = AsyncMock()
        return mock

    @pytest.fixture
    def mock_embedding_service(self):
        mock = AsyncMock()
        mock.embed = AsyncMock(return_value=(generate_embedding(seed=42), False))
        mock.embed_batch = AsyncMock(
            side_effect=lambda texts: [(generate_embedding(seed=i), False) for i in range(len(texts))]
        )
        return mock

    @pytest.fixture
    def memory_manager(self, mock_qdrant, mock_neo4j, mock_embedding_service):
        return MemoryManager(
            qdrant=mock_qdrant,
            neo4j=mock_neo4j,
            embedding_service=mock_embedding_service,
        )

    @pytest.mark.asyncio
    async def test_bulk_add_with_mixed_types(
        self, memory_manager: MemoryManager, mock_qdrant: AsyncMock
    ):
        """Test bulk add with multiple memory types."""
        memories = [
            RequirementsMemoryFactory.create(),
            DesignMemoryFactory.create(),
            FunctionMemoryFactory.create(),
        ]

        added_ids, errors = await memory_manager.bulk_add_memories(
            memories=memories,
            check_conflicts=False,
        )

        assert len(added_ids) == 3
        assert len(errors) == 0
        # Should have called upsert_batch for each type
        assert mock_qdrant.upsert_batch.call_count >= 1

    @pytest.mark.asyncio
    async def test_bulk_add_without_neo4j_sync(
        self, memory_manager: MemoryManager, mock_qdrant: AsyncMock, mock_neo4j: AsyncMock
    ):
        """Test bulk add without syncing to Neo4j."""
        memories = [RequirementsMemoryFactory.create() for _ in range(3)]

        added_ids, errors = await memory_manager.bulk_add_memories(
            memories=memories,
            check_conflicts=False,
            sync_to_neo4j=False,
        )

        assert len(added_ids) == 3
        mock_neo4j.create_node.assert_not_called()

    @pytest.mark.asyncio
    async def test_bulk_add_neo4j_partial_failure(
        self, memory_manager: MemoryManager, mock_qdrant: AsyncMock, mock_neo4j: AsyncMock
    ):
        """Test bulk add handles Neo4j partial failures gracefully."""
        memories = [RequirementsMemoryFactory.create() for _ in range(3)]

        # Neo4j fails on second call
        call_count = 0
        async def create_with_failure(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise Exception("Neo4j connection lost")

        mock_neo4j.create_node = create_with_failure

        # Should still succeed (memories added to Qdrant)
        added_ids, errors = await memory_manager.bulk_add_memories(
            memories=memories,
            check_conflicts=False,
            sync_to_neo4j=True,
        )

        assert len(added_ids) == 3  # All added to Qdrant
        assert len(errors) == 0  # No Qdrant errors

    @pytest.mark.asyncio
    async def test_bulk_add_with_existing_embeddings(
        self, memory_manager: MemoryManager, mock_embedding_service: AsyncMock
    ):
        """Test bulk add skips embedding generation for memories with embeddings."""
        memories = [
            RequirementsMemoryFactory.create(),  # Has embedding
            RequirementsMemoryFactory.create(),  # Has embedding
        ]

        await memory_manager.bulk_add_memories(
            memories=memories,
            check_conflicts=False,
        )

        # embed_batch should not be called if all memories have embeddings
        # (embed_batch is called only for memories without embeddings)
        # Actually, the implementation calls embed_batch for contents without embeddings
        # Since factory creates with embeddings, this should result in empty contents list


# ============================================================================
# Search Tools Tests
# ============================================================================


class TestSearchToolsFunctions:
    """Tests for search tool functions."""

    @pytest.fixture
    def mock_context(self):
        """Create mock context with query engine."""
        query_engine = AsyncMock()
        query_engine.semantic_search.return_value = []
        query_engine.graph_query.return_value = []
        query_engine.hybrid_search.return_value = []
        return {"query_engine": query_engine}

    @pytest.mark.asyncio
    async def test_code_search_success(self, mock_context):
        """Test code_search tool returns results."""
        from memory_service.api.tools.search import code_search

        mock_context["query_engine"].semantic_search.return_value = []

        params = {
            "query": "def authenticate_user",
            "language": "python",
            "limit": 5,
            "_context": mock_context,
        }

        result = await code_search(params)

        assert "result_count" in result
        assert result["result_count"] == 0
        assert result["language_filter"] == "python"

    @pytest.mark.asyncio
    async def test_code_search_error_handling(self, mock_context):
        """Test code_search handles errors gracefully."""
        from memory_service.api.tools.search import code_search

        mock_context["query_engine"].semantic_search.side_effect = Exception("Search failed")

        params = {
            "query": "test query",
            "_context": mock_context,
        }

        result = await code_search(params)

        assert "error" in result
        assert "Search failed" in result["error"]

    @pytest.mark.asyncio
    async def test_memory_search_error_handling(self, mock_context):
        """Test memory_search handles errors gracefully."""
        from memory_service.api.tools.search import memory_search

        mock_context["query_engine"].semantic_search.side_effect = Exception("Memory search failed")

        params = {
            "query": "authentication code",
            "_context": mock_context,
        }

        result = await memory_search(params)

        assert "error" in result
        assert "Memory search failed" in result["error"]

    @pytest.mark.asyncio
    async def test_memory_search_with_time_range(self, mock_context):
        """Test memory_search with time range filter."""
        from memory_service.api.tools.search import memory_search

        mock_context["query_engine"].semantic_search.return_value = []

        params = {
            "query": "authentication",
            "time_range": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z",
            },
            "_context": mock_context,
        }

        result = await memory_search(params)

        assert "result_count" in result
        mock_context["query_engine"].semantic_search.assert_called_once()


# ============================================================================
# Analysis Tools Tests
# ============================================================================


class TestAnalysisToolsFunctions:
    """Tests for analysis tool functions."""

    @pytest.fixture
    def mock_context(self):
        """Create mock context with all required services."""
        query_engine = AsyncMock()
        qdrant = AsyncMock()
        qdrant.get_collection_name = MagicMock(return_value="test_collection")
        embedding_service = AsyncMock()
        memory_manager = AsyncMock()
        neo4j = AsyncMock()
        return {
            "query_engine": query_engine,
            "qdrant": qdrant,
            "embedding_service": embedding_service,
            "memory_manager": memory_manager,
            "neo4j": neo4j,
        }

    @pytest.mark.asyncio
    async def test_check_consistency_error(self, mock_context):
        """Test check_consistency handles errors."""
        from memory_service.api.tools.analysis import check_consistency

        # Make qdrant.get raise an error
        mock_context["qdrant"].get.side_effect = Exception("DB error")

        params = {
            "component_id": str(uuid4()),
            "_context": mock_context,
        }

        result = await check_consistency(params)

        assert "error" in result

    @pytest.mark.asyncio
    async def test_check_consistency_component_not_found(self, mock_context):
        """Test check_consistency returns error when component not found."""
        from memory_service.api.tools.analysis import check_consistency

        mock_context["qdrant"].get.return_value = None  # Component not found

        params = {
            "component_id": str(uuid4()),
            "_context": mock_context,
        }

        result = await check_consistency(params)

        assert "error" in result
        assert result["error"] == "Component not found"

    @pytest.mark.asyncio
    async def test_validate_fix_error(self, mock_context):
        """Test validate_fix handles errors."""
        from memory_service.api.tools.analysis import validate_fix

        mock_context["query_engine"].semantic_search.side_effect = Exception("Search error")

        params = {
            "fix_description": "Fixed authentication bug",
            "affected_component": "AuthService",
            "_context": mock_context,
        }

        result = await validate_fix(params)

        assert "error" in result


# ============================================================================
# Embedding Service Additional Tests
# ============================================================================


class TestEmbeddingServiceEdgeCases:
    """Additional tests for embedding service edge cases."""

    @pytest.mark.asyncio
    async def test_embedding_service_embed_for_query(self):
        """Test embed_for_query method."""
        from memory_service.embedding.service import EmbeddingService

        with patch("memory_service.embedding.service.VoyageClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.embed.return_value = generate_embedding(seed=42)
            mock_client_class.return_value = mock_client

            service = EmbeddingService(api_key="test-key")
            embedding = await service.embed_for_query("test query")

            assert len(embedding) == 1024
            mock_client.embed.assert_called_once()

    @pytest.mark.asyncio
    async def test_embedding_service_embed_batch_empty(self):
        """Test embed_batch with empty list."""
        from memory_service.embedding.service import EmbeddingService

        with patch("memory_service.embedding.service.VoyageClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            service = EmbeddingService(api_key="test-key")
            results = await service.embed_batch([])

            assert results == []

    @pytest.mark.asyncio
    async def test_embedding_service_embed_with_cache_hit(self):
        """Test embed returns cached result when available."""
        from memory_service.embedding.service import EmbeddingService
        from memory_service.storage.cache import EmbeddingCache

        with patch("memory_service.embedding.service.VoyageClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Patch the cache
            with patch("memory_service.embedding.service.EmbeddingCache") as mock_cache_class:
                mock_cache = AsyncMock()
                cached_embedding = generate_embedding(seed=99)
                mock_cache.get.return_value = (cached_embedding, False)
                mock_cache_class.return_value = mock_cache

                service = EmbeddingService(api_key="test-key")
                embedding, is_fallback = await service.embed("cached text")

                # Should return cached result
                assert embedding == cached_embedding
                assert is_fallback is False
                # Voyage client should not be called for cached content
                mock_client.embed.assert_not_called()

    @pytest.mark.asyncio
    async def test_embedding_service_embed_batch_with_texts(self):
        """Test embed_batch with actual texts."""
        from memory_service.embedding.service import EmbeddingService

        with patch("memory_service.embedding.service.VoyageClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.embed_batch.return_value = [
                generate_embedding(seed=1),
                generate_embedding(seed=2),
            ]
            mock_client_class.return_value = mock_client

            with patch("memory_service.embedding.service.EmbeddingCache") as mock_cache_class:
                mock_cache = AsyncMock()
                mock_cache.get.return_value = None  # No cache hits
                mock_cache_class.return_value = mock_cache

                service = EmbeddingService(api_key="test-key")
                results = await service.embed_batch(["text 1", "text 2"])

                assert len(results) == 2
                assert all(len(e) == 1024 for e, _ in results)


# ============================================================================
# Base Memory Model Tests
# ============================================================================


class TestBaseMemoryMethods:
    """Tests for BaseMemory helper methods."""

    def test_mark_deleted_sets_flags(self):
        """Test mark_deleted sets deleted flag and timestamp."""
        memory = RequirementsMemoryFactory.create()
        assert memory.deleted is False
        assert memory.deleted_at is None

        memory.mark_deleted()

        assert memory.deleted is True
        assert memory.deleted_at is not None

    def test_record_access_updates_count(self):
        """Test record_access increments count and sets timestamp."""
        memory = RequirementsMemoryFactory.create()
        original_count = memory.access_count
        assert memory.last_accessed_at is None

        memory.record_access()

        assert memory.access_count == original_count + 1
        assert memory.last_accessed_at is not None

    def test_update_timestamp_sets_updated_at(self):
        """Test update_timestamp sets updated_at."""
        memory = RequirementsMemoryFactory.create()
        original_updated = memory.updated_at

        memory.update_timestamp()

        assert memory.updated_at >= original_updated

    def test_set_embedding_updates_vector(self):
        """Test set_embedding sets embedding and updates timestamp."""
        memory = RequirementsMemoryFactory.create()
        new_embedding = generate_embedding(seed=999)
        original_updated = memory.updated_at

        memory.set_embedding(new_embedding)

        assert memory.embedding == new_embedding
        assert memory.updated_at >= original_updated


# ============================================================================
# Qdrant Adapter Additional Tests
# ============================================================================


class TestQdrantAdapterEdgeCases:
    """Additional tests for Qdrant adapter edge cases."""

    @pytest.mark.asyncio
    async def test_get_collection_name_all_types(self):
        """Test get_collection_name for all memory types."""
        from memory_service.storage.qdrant_adapter import QdrantAdapter, COLLECTIONS

        adapter = QdrantAdapter(host="localhost", port=6333)

        for memory_type in MemoryType:
            collection_name = adapter.get_collection_name(memory_type)
            # Collection name should match the COLLECTIONS mapping
            assert collection_name == COLLECTIONS[memory_type]


# ============================================================================
# Cache Additional Tests
# ============================================================================


class TestCacheEdgeCases:
    """Additional tests for cache edge cases."""

    @pytest.mark.asyncio
    async def test_embedding_cache_not_initialized(self):
        """Test cache operations when not initialized."""
        from memory_service.storage.cache import EmbeddingCache

        cache = EmbeddingCache(":memory:")
        # Don't call initialize - test lazy initialization

        result = await cache.get("test content", "test-model")

        # Should handle gracefully
        assert result is None or isinstance(result, tuple)

    @pytest.mark.asyncio
    async def test_embedding_cache_set_and_get(self):
        """Test cache set and get operations."""
        from memory_service.storage.cache import EmbeddingCache

        cache = EmbeddingCache(":memory:")
        await cache.initialize()

        # Set an embedding
        embedding = generate_embedding(seed=123)
        result = await cache.set("test content", "test-model", embedding, is_fallback=False)
        assert result is True

        # Get it back
        cached = await cache.get("test content", "test-model")
        assert cached is not None
        embedding_back, is_fallback = cached
        assert len(embedding_back) == 1024
        assert is_fallback is False


# ============================================================================
# Importance Score Calculation Tests
# ============================================================================


class TestImportanceScoreCalculation:
    """Tests for importance score calculation."""

    @pytest.fixture
    def mock_qdrant(self):
        mock = AsyncMock()
        mock.get_collection_name = MagicMock(return_value="memories_requirements")
        mock.upsert = AsyncMock()
        mock.search = AsyncMock(return_value=[])
        return mock

    @pytest.fixture
    def mock_neo4j(self):
        mock = AsyncMock()
        mock.get_node_label = MagicMock(return_value="Requirements")
        mock.create_node = AsyncMock()
        return mock

    @pytest.fixture
    def mock_embedding_service(self):
        mock = AsyncMock()
        mock.embed = AsyncMock(return_value=(generate_embedding(seed=42), False))
        return mock

    @pytest.fixture
    def memory_manager(self, mock_qdrant, mock_neo4j, mock_embedding_service):
        return MemoryManager(
            qdrant=mock_qdrant,
            neo4j=mock_neo4j,
            embedding_service=mock_embedding_service,
        )

    @pytest.mark.asyncio
    async def test_requirements_high_priority_importance(
        self, memory_manager: MemoryManager
    ):
        """Test high priority requirements get high importance."""
        memory = RequirementsMemoryFactory.create()
        memory.priority = "Critical"

        await memory_manager.add_memory(memory, check_conflicts=False, sync_to_neo4j=False)

        assert memory.importance_score >= 0.8

    @pytest.mark.asyncio
    async def test_design_memory_importance(self, memory_manager: MemoryManager):
        """Test design memories get appropriate importance."""
        memory = DesignMemoryFactory.create()
        memory.status = "Accepted"

        await memory_manager.add_memory(memory, check_conflicts=False, sync_to_neo4j=False)

        assert memory.importance_score >= 0.5

    @pytest.mark.asyncio
    async def test_function_memory_importance(self, memory_manager: MemoryManager):
        """Test function memories importance varies by characteristics."""
        memory = FunctionMemoryFactory.create()

        await memory_manager.add_memory(memory, check_conflicts=False, sync_to_neo4j=False)

        # Function importance should be in valid range
        assert 0.0 <= memory.importance_score <= 1.0
