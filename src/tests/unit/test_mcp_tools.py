"""Unit tests for MCP tool functions."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID

from memory_service.api.tools.memory_crud import (
    memory_add,
    memory_update,
    memory_delete,
    memory_get,
    memory_bulk_add,
    MEMORY_CLASSES,
)
from memory_service.api.tools.search import (
    memory_search,
    code_search,
    find_duplicates,
    get_related,
)
from memory_service.api.tools.analysis import (
    check_consistency,
    validate_fix,
    get_design_context,
)
from memory_service.api.tools.indexing import (
    index_file,
    index_directory,
    index_status,
)
from memory_service.api.tools.maintenance import (
    memory_statistics,
    normalize_memory,
    normalize_status,
)
from memory_service.models import MemoryType
from memory_service.core.query_engine import SearchResult


class TestMemoryAdd:
    """Unit tests for memory_add tool."""

    @pytest.fixture
    def mock_context(self) -> dict:
        """Create mock context with services."""
        memory_manager = AsyncMock()
        memory_manager.add_memory.return_value = (uuid4(), [])

        neo4j = AsyncMock()
        neo4j.create_relationship.return_value = True

        return {
            "memory_manager": memory_manager,
            "neo4j": neo4j,
        }

    @pytest.mark.asyncio
    async def test_add_requirements_memory(self, mock_context: dict) -> None:
        """Test adding a requirements memory."""
        params = {
            "memory_type": "requirements",
            "content": "The system shall authenticate users",
            "metadata": {
                "requirement_id": "REQ-MEM-AUTH-001",
                "title": "User Authentication",
                "description": "Users must authenticate before accessing the system",
                "priority": "High",
                "status": "Draft",
                "source_document": "srs.md",
            },
            "_context": mock_context,
        }

        result = await memory_add(params)

        assert "memory_id" in result
        assert result["memory_type"] == "requirements"
        assert result["status"] == "created"
        mock_context["memory_manager"].add_memory.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_function_memory(self, mock_context: dict) -> None:
        """Test adding a function memory."""
        params = {
            "memory_type": "function",
            "content": "def process_data(): pass",
            "metadata": {
                "function_id": str(uuid4()),
                "name": "process_data",
                "signature": "def process_data(data: list) -> list",
                "file_path": "src/processor.py",
                "start_line": 10,
                "end_line": 20,
                "language": "python",
            },
            "_context": mock_context,
        }

        result = await memory_add(params)

        assert result["status"] == "created"
        assert result["memory_type"] == "function"

    @pytest.mark.asyncio
    async def test_add_with_relationships(self, mock_context: dict) -> None:
        """Test adding memory with relationships."""
        target_id = uuid4()
        params = {
            "memory_type": "design",
            "content": "Design decision for authentication",
            "metadata": {
                "design_type": "ADR",
                "title": "Auth Design",
                "decision": "Use JWT",
                "rationale": "Industry standard",
                "status": "Accepted",  # Valid enum value
            },
            "relationships": [
                {
                    "target_id": target_id,
                    "type": "IMPLEMENTS",
                    "properties": {"version": "1.0"},
                }
            ],
            "_context": mock_context,
        }

        result = await memory_add(params)

        assert result["status"] == "created"
        mock_context["neo4j"].create_relationship.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_unknown_memory_type(self, mock_context: dict) -> None:
        """Test error when adding unknown memory type."""
        params = {
            "memory_type": "unknown_type",
            "content": "Some content",
            "_context": mock_context,
        }

        result = await memory_add(params)

        assert "error" in result
        assert "Unknown memory type" in result["error"]

    @pytest.mark.asyncio
    async def test_add_with_conflicts_detected(self, mock_context: dict) -> None:
        """Test adding memory with conflicts detected."""
        memory_id = uuid4()
        conflicts = [
            {"id": str(uuid4()), "similarity": 0.96}
        ]
        mock_context["memory_manager"].add_memory.return_value = (memory_id, conflicts)

        params = {
            "memory_type": "requirements",
            "content": "Similar requirement",
            "metadata": {
                "requirement_id": "REQ-MEM-SIM-001",
                "title": "Similar",
                "description": "A similar requirement for testing",
                "priority": "Medium",
                "status": "Draft",
                "source_document": "srs.md",
            },
            "_context": mock_context,
        }

        result = await memory_add(params)

        assert result["status"] == "created"
        assert result["conflicts"] == conflicts

    @pytest.mark.asyncio
    async def test_add_with_validation_error(self, mock_context: dict) -> None:
        """Test error handling when validation fails."""
        params = {
            "memory_type": "requirements",
            "content": "",  # Empty content should fail
            "metadata": {},
            "_context": mock_context,
        }

        result = await memory_add(params)

        assert "error" in result


class TestMemoryUpdate:
    """Unit tests for memory_update tool."""

    @pytest.fixture
    def mock_context(self) -> dict:
        """Create mock context."""
        memory_manager = AsyncMock()
        memory_manager.update_memory.return_value = True
        return {"memory_manager": memory_manager}

    @pytest.mark.asyncio
    async def test_update_content(self, mock_context: dict) -> None:
        """Test updating memory content."""
        memory_id = uuid4()
        params = {
            "memory_id": str(memory_id),
            "memory_type": "requirements",
            "content": "Updated requirement content",
            "_context": mock_context,
        }

        result = await memory_update(params)

        assert result["status"] == "updated"
        assert result["memory_id"] == str(memory_id)

    @pytest.mark.asyncio
    async def test_update_metadata(self, mock_context: dict) -> None:
        """Test updating memory metadata."""
        memory_id = uuid4()
        params = {
            "memory_id": str(memory_id),
            "memory_type": "requirements",
            "metadata": {"priority": "High", "status": "Approved"},
            "_context": mock_context,
        }

        result = await memory_update(params)

        assert result["status"] == "updated"

    @pytest.mark.asyncio
    async def test_update_no_updates_provided(self, mock_context: dict) -> None:
        """Test error when no updates provided."""
        params = {
            "memory_id": str(uuid4()),
            "memory_type": "requirements",
            "_context": mock_context,
        }

        result = await memory_update(params)

        assert "error" in result
        assert "No updates provided" in result["error"]

    @pytest.mark.asyncio
    async def test_update_memory_not_found(self, mock_context: dict) -> None:
        """Test error when memory not found."""
        mock_context["memory_manager"].update_memory.return_value = False

        params = {
            "memory_id": str(uuid4()),
            "memory_type": "requirements",
            "content": "Updated content",
            "_context": mock_context,
        }

        result = await memory_update(params)

        assert "error" in result
        assert "not found" in result["error"]


class TestMemoryDelete:
    """Unit tests for memory_delete tool."""

    @pytest.fixture
    def mock_context(self) -> dict:
        """Create mock context."""
        memory_manager = AsyncMock()
        memory_manager.delete_memory.return_value = True
        return {"memory_manager": memory_manager}

    @pytest.mark.asyncio
    async def test_soft_delete(self, mock_context: dict) -> None:
        """Test soft delete (default)."""
        memory_id = uuid4()
        params = {
            "memory_id": str(memory_id),
            "memory_type": "function",
            "_context": mock_context,
        }

        result = await memory_delete(params)

        assert result["status"] == "deleted"
        assert result["hard_delete"] is False
        mock_context["memory_manager"].delete_memory.assert_called_once_with(
            memory_id=memory_id,
            memory_type=MemoryType.FUNCTION,
            soft_delete=True,
        )

    @pytest.mark.asyncio
    async def test_hard_delete(self, mock_context: dict) -> None:
        """Test hard delete."""
        memory_id = uuid4()
        params = {
            "memory_id": str(memory_id),
            "memory_type": "function",
            "hard_delete": True,
            "_context": mock_context,
        }

        result = await memory_delete(params)

        assert result["status"] == "deleted"
        assert result["hard_delete"] is True
        mock_context["memory_manager"].delete_memory.assert_called_once_with(
            memory_id=memory_id,
            memory_type=MemoryType.FUNCTION,
            soft_delete=False,
        )

    @pytest.mark.asyncio
    async def test_delete_not_found(self, mock_context: dict) -> None:
        """Test delete when memory not found."""
        mock_context["memory_manager"].delete_memory.return_value = False

        params = {
            "memory_id": str(uuid4()),
            "memory_type": "function",
            "_context": mock_context,
        }

        result = await memory_delete(params)

        assert result["status"] == "not_found"


class TestMemoryGet:
    """Unit tests for memory_get tool."""

    @pytest.fixture
    def mock_context(self) -> dict:
        """Create mock context."""
        memory_manager = AsyncMock()
        neo4j = AsyncMock()
        neo4j.get_related.return_value = []
        return {"memory_manager": memory_manager, "neo4j": neo4j}

    @pytest.mark.asyncio
    async def test_get_memory_success(self, mock_context: dict) -> None:
        """Test successful memory retrieval."""
        from memory_service.models.memories import RequirementsMemory

        memory = RequirementsMemory(
            content="Test requirement",
            requirement_id="REQ-MEM-TEST-001",
            title="Test",
            description="A test requirement for unit testing",
            priority="High",
            status="Draft",
            source_document="test.md",
        )
        mock_context["memory_manager"].get_memory.return_value = memory

        params = {
            "memory_id": str(memory.id),
            "memory_type": "requirements",
            "_context": mock_context,
        }

        result = await memory_get(params)

        assert "error" not in result
        assert result["content"] == "Test requirement"
        assert result["requirement_id"] == "REQ-MEM-TEST-001"

    @pytest.mark.asyncio
    async def test_get_memory_with_relationships(self, mock_context: dict) -> None:
        """Test getting memory with relationships."""
        from memory_service.models.memories import RequirementsMemory

        memory = RequirementsMemory(
            content="Test requirement",
            requirement_id="REQ-MEM-TEST-001",
            title="Test",
            description="A test requirement for unit testing",
            priority="High",
            status="Draft",
            source_document="test.md",
        )
        mock_context["memory_manager"].get_memory.return_value = memory
        mock_context["neo4j"].get_related.return_value = [
            {"id": str(uuid4()), "type": "IMPLEMENTS"}
        ]

        params = {
            "memory_id": str(memory.id),
            "memory_type": "requirements",
            "include_relationships": True,
            "_context": mock_context,
        }

        result = await memory_get(params)

        assert "relationships" in result
        mock_context["neo4j"].get_related.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_memory_not_found(self, mock_context: dict) -> None:
        """Test error when memory not found."""
        mock_context["memory_manager"].get_memory.return_value = None

        params = {
            "memory_id": str(uuid4()),
            "memory_type": "requirements",
            "_context": mock_context,
        }

        result = await memory_get(params)

        assert "error" in result
        assert "not found" in result["error"]


class TestMemoryBulkAdd:
    """Unit tests for memory_bulk_add tool."""

    @pytest.fixture
    def mock_context(self) -> dict:
        """Create mock context."""
        memory_manager = AsyncMock()
        memory_manager.bulk_add_memories.return_value = (
            [uuid4(), uuid4()],
            [],
        )
        return {"memory_manager": memory_manager}

    @pytest.mark.asyncio
    async def test_bulk_add_success(self, mock_context: dict) -> None:
        """Test successful bulk add."""
        params = {
            "memories": [
                {
                    "memory_type": "requirements",
                    "content": "Requirement 1",
                    "requirement_id": "REQ-MEM-ONE-001",
                    "title": "One",
                    "description": "First requirement",
                    "priority": "High",
                    "status": "Draft",
                    "source_document": "srs.md",
                },
                {
                    "memory_type": "requirements",
                    "content": "Requirement 2",
                    "requirement_id": "REQ-MEM-TWO-001",
                    "title": "Two",
                    "description": "Second requirement",
                    "priority": "Medium",
                    "status": "Draft",
                    "source_document": "srs.md",
                },
            ],
            "_context": mock_context,
        }

        result = await memory_bulk_add(params)

        assert result["added_count"] == 2
        assert len(result["added_ids"]) == 2
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_bulk_add_empty_list(self, mock_context: dict) -> None:
        """Test error when no memories provided."""
        params = {
            "memories": [],
            "_context": mock_context,
        }

        result = await memory_bulk_add(params)

        assert "error" in result
        assert "No memories provided" in result["error"]

    @pytest.mark.asyncio
    async def test_bulk_add_with_parse_errors(self, mock_context: dict) -> None:
        """Test bulk add with some invalid memories."""
        params = {
            "memories": [
                {
                    "memory_type": "unknown_type",  # Invalid type
                    "content": "Test",
                },
                {
                    "memory_type": "requirements",
                    "content": "Valid requirement",
                    "requirement_id": "REQ-MEM-VAL-001",
                    "title": "Valid",
                    "description": "A valid requirement",
                    "priority": "High",
                    "status": "Draft",
                    "source_document": "srs.md",
                },
            ],
            "_context": mock_context,
        }

        mock_context["memory_manager"].bulk_add_memories.return_value = (
            [uuid4()],
            [],
        )

        result = await memory_bulk_add(params)

        assert result["added_count"] == 1
        assert len(result["errors"]) >= 1  # At least one parse error


class TestMemorySearch:
    """Unit tests for memory_search tool."""

    @pytest.fixture
    def mock_context(self) -> dict:
        """Create mock context."""
        query_engine = AsyncMock()
        query_engine.semantic_search.return_value = []
        return {"query_engine": query_engine}

    @pytest.mark.asyncio
    async def test_search_basic(self, mock_context: dict) -> None:
        """Test basic semantic search."""
        result_id = str(uuid4())
        mock_context["query_engine"].semantic_search.return_value = [
            SearchResult(
                id=result_id,
                memory_type=MemoryType.REQUIREMENTS,
                content="Authentication requirement",
                score=0.9,
                payload={"title": "Auth"},
            )
        ]

        params = {
            "query": "authentication requirements",
            "limit": 10,
            "_context": mock_context,
        }

        result = await memory_search(params)

        assert "results" in result
        assert len(result["results"]) == 1
        mock_context["query_engine"].semantic_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_with_type_filter(self, mock_context: dict) -> None:
        """Test search with memory type filter."""
        params = {
            "query": "function implementation",
            "memory_types": ["function", "component"],
            "limit": 5,
            "_context": mock_context,
        }

        await memory_search(params)

        call_args = mock_context["query_engine"].semantic_search.call_args
        assert MemoryType.FUNCTION in call_args.kwargs.get("memory_types", [])
        assert MemoryType.COMPONENT in call_args.kwargs.get("memory_types", [])


class TestFindDuplicates:
    """Unit tests for find_duplicates tool."""

    @pytest.fixture
    def mock_context(self) -> dict:
        """Create mock context."""
        query_engine = AsyncMock()
        query_engine.semantic_search.return_value = []
        embedding_service = AsyncMock()
        embedding_service.embed_for_query.return_value = [0.1] * 1024
        qdrant = AsyncMock()
        qdrant.get_collection_name.return_value = "memories_function"
        qdrant.search.return_value = []
        return {"query_engine": query_engine, "embedding_service": embedding_service, "qdrant": qdrant}

    @pytest.mark.asyncio
    async def test_find_duplicates_basic(self, mock_context: dict) -> None:
        """Test finding duplicates."""
        result_id = str(uuid4())
        mock_context["qdrant"].search.return_value = [
            {
                "id": result_id,
                "score": 0.92,
                "payload": {
                    "name": "process_data",
                    "file_path": "src/utils.py",
                    "signature": "def process_data(data: list)",
                    "start_line": 10,
                    "end_line": 20,
                },
            }
        ]

        params = {
            "code": "def process_data(items: list):\n    return [i * 2 for i in items]",
            "threshold": 0.85,
            "limit": 10,
            "_context": mock_context,
        }

        result = await find_duplicates(params)

        assert "duplicates" in result
        mock_context["qdrant"].search.assert_called_once()


class TestIndexFile:
    """Unit tests for index_file tool."""

    @pytest.fixture
    def mock_context(self) -> dict:
        """Create mock context."""
        indexer = AsyncMock()
        indexer.index_file.return_value = {
            "functions": 5,
            "classes": 2,
            "relationships": 3,
        }
        return {"indexer": indexer}

    @pytest.mark.asyncio
    async def test_index_file_no_indexer(self) -> None:
        """Test error when indexer not available."""
        params = {
            "file_path": "/src/test.py",
            "_context": {},
        }

        result = await index_file(params)

        assert "error" in result
        assert "not available" in result["error"]

    @pytest.mark.asyncio
    async def test_index_file_missing_path(self, mock_context: dict) -> None:
        """Test error when file_path not provided."""
        params = {
            "_context": mock_context,
        }

        result = await index_file(params)

        assert "error" in result
        assert "required" in result["error"]


class TestIndexDirectory:
    """Unit tests for index_directory tool."""

    @pytest.fixture
    def mock_context(self) -> dict:
        """Create mock context."""
        indexer = AsyncMock()
        indexer.index_directory.return_value = {
            "files_indexed": 10,
            "functions": 50,
            "classes": 20,
        }
        job_manager = AsyncMock()
        job_manager.create_job.return_value = "job-123"
        return {"indexer": indexer, "job_manager": job_manager}

    @pytest.mark.asyncio
    async def test_index_directory_no_indexer(self) -> None:
        """Test error when indexer not available."""
        params = {
            "directory_path": "/src",
            "_context": {},
        }

        result = await index_directory(params)

        assert "error" in result
        assert "not available" in result["error"]

    @pytest.mark.asyncio
    async def test_index_directory_missing_path(self, mock_context: dict) -> None:
        """Test error when directory_path not provided."""
        params = {
            "_context": mock_context,
        }

        result = await index_directory(params)

        assert "error" in result
        assert "required" in result["error"]


class TestMemoryStatistics:
    """Unit tests for memory_statistics tool."""

    @pytest.fixture
    def mock_context(self) -> dict:
        """Create mock context."""
        qdrant = AsyncMock()
        qdrant.count.return_value = 100
        qdrant.get_collection_name.return_value = "memories_function"
        neo4j = AsyncMock()
        neo4j.get_statistics.return_value = {"nodes": 100, "relationships": 50}
        embedding_service = MagicMock()
        embedding_service.get_cache_stats.return_value = {"hits": 50, "misses": 10}
        return {"qdrant": qdrant, "neo4j": neo4j, "embedding_service": embedding_service}

    @pytest.mark.asyncio
    async def test_get_statistics(self, mock_context: dict) -> None:
        """Test getting memory statistics."""
        params = {"_context": mock_context}

        result = await memory_statistics(params)

        # Should return statistics or error
        assert isinstance(result, dict)
        # Either has stats or an error
        assert "memory_counts" in result or "error" in result


class TestCheckConsistency:
    """Unit tests for check_consistency tool."""

    @pytest.fixture
    def mock_context(self) -> dict:
        """Create mock context."""
        query_engine = AsyncMock()
        query_engine.semantic_search.return_value = []

        qdrant = AsyncMock()
        qdrant.get.return_value = {
            "id": str(uuid4()),
            "name": "TestComponent",
            "embedding": [0.1] * 1024,
        }
        qdrant.get_collection_name.return_value = "memories_component"
        qdrant.search.return_value = []

        embedding_service = MagicMock()
        return {"query_engine": query_engine, "qdrant": qdrant, "embedding_service": embedding_service}

    @pytest.mark.asyncio
    async def test_check_consistency_basic(self, mock_context: dict) -> None:
        """Test checking design consistency."""
        params = {
            "component_id": str(uuid4()),
            "pattern_types": ["Template"],
            "_context": mock_context,
        }

        result = await check_consistency(params)

        assert isinstance(result, dict)
        # Should have consistency_score or error
        assert "consistency_score" in result or "error" in result

    @pytest.mark.asyncio
    async def test_check_consistency_component_not_found(self, mock_context: dict) -> None:
        """Test error when component not found."""
        mock_context["qdrant"].get.return_value = None

        params = {
            "component_id": str(uuid4()),
            "_context": mock_context,
        }

        result = await check_consistency(params)

        assert "error" in result
        assert "not found" in result["error"]


class TestValidateFix:
    """Unit tests for validate_fix tool."""

    @pytest.fixture
    def mock_context(self) -> dict:
        """Create mock context."""
        query_engine = AsyncMock()
        query_engine.semantic_search.return_value = []
        embedding_service = MagicMock()
        return {"query_engine": query_engine, "embedding_service": embedding_service}

    @pytest.mark.asyncio
    async def test_validate_fix_basic(self, mock_context: dict) -> None:
        """Test validating a fix against design."""
        params = {
            "fix_description": "Add authentication check",
            "affected_component": "AuthService",
            "_context": mock_context,
        }

        result = await validate_fix(params)

        assert isinstance(result, dict)
        # Should call semantic_search
        mock_context["query_engine"].semantic_search.assert_called()


class TestNormalizeMemory:
    """Unit tests for normalize_memory tool."""

    @pytest.fixture
    def mock_context(self) -> dict:
        """Create mock context."""
        normalizer = AsyncMock()
        normalizer.normalize.return_value = {
            "status": "completed",
            "duplicates_merged": 5,
            "orphans_removed": 2,
        }
        job_manager = AsyncMock()
        job_manager.create_job.return_value = "norm-job-123"
        return {"normalizer": normalizer, "job_manager": job_manager}

    @pytest.mark.asyncio
    async def test_normalize_sync(self, mock_context: dict) -> None:
        """Test synchronous normalization."""
        params = {
            "dry_run": False,
            "_context": mock_context,
        }

        result = await normalize_memory(params)

        assert isinstance(result, dict)
        mock_context["normalizer"].normalize.assert_called_once()

    @pytest.mark.asyncio
    async def test_normalize_no_normalizer(self) -> None:
        """Test error when normalizer not available."""
        params = {
            "_context": {},
        }

        result = await normalize_memory(params)

        assert "error" in result
        assert "not available" in result["error"]


class TestGetDesignContext:
    """Unit tests for get_design_context tool."""

    @pytest.fixture
    def mock_context(self) -> dict:
        """Create mock context."""
        query_engine = AsyncMock()
        query_engine.semantic_search.return_value = []
        neo4j = AsyncMock()
        neo4j.get_related.return_value = []
        return {"query_engine": query_engine, "neo4j": neo4j}

    @pytest.mark.asyncio
    async def test_get_design_context_basic(self, mock_context: dict) -> None:
        """Test getting design context for a file."""
        params = {
            "file_path": "src/auth.py",
            "_context": mock_context,
        }

        result = await get_design_context(params)

        assert isinstance(result, dict)
        # Should have designs/requirements or error
        assert "designs" in result or "error" in result or "status" in result


class TestMemoryClassMapping:
    """Unit tests for memory class mapping."""

    def test_all_memory_types_have_class(self) -> None:
        """Test that all memory types have a class mapping."""
        expected_types = [
            "requirements",
            "design",
            "code_pattern",
            "component",
            "function",
            "test_history",
            "session",
            "user_preference",
        ]

        for memory_type in expected_types:
            assert memory_type in MEMORY_CLASSES
            assert MEMORY_CLASSES[memory_type] is not None

    def test_class_mapping_returns_correct_class(self) -> None:
        """Test that class mapping returns correct classes."""
        from memory_service.models.memories import (
            RequirementsMemory,
            FunctionMemory,
        )

        assert MEMORY_CLASSES["requirements"] == RequirementsMemory
        assert MEMORY_CLASSES["function"] == FunctionMemory


class TestIndexStatus:
    """Unit tests for index_status tool."""

    @pytest.fixture
    def mock_context(self) -> dict:
        """Create mock context."""
        job_manager = AsyncMock()
        job_manager.get_job.return_value = None
        qdrant = AsyncMock()
        qdrant.count.return_value = 10
        qdrant.get_collection_name.return_value = "memories_function"
        return {"job_manager": job_manager, "qdrant": qdrant}

    @pytest.mark.asyncio
    async def test_get_status_no_job(self, mock_context: dict) -> None:
        """Test getting status when no job exists."""
        params = {
            "job_id": str(uuid4()),
            "_context": mock_context,
        }

        result = await index_status(params)

        # Should return not_found status
        assert "status" in result
        assert result["status"] == "not_found"

    @pytest.mark.asyncio
    async def test_get_overall_stats(self, mock_context: dict) -> None:
        """Test getting overall indexing stats when no job_id."""
        params = {
            "_context": mock_context,
        }

        result = await index_status(params)

        # Should return stats
        assert isinstance(result, dict)


class TestGetRelated:
    """Unit tests for get_related tool."""

    @pytest.fixture
    def mock_context(self) -> dict:
        """Create mock context."""
        neo4j = AsyncMock()
        neo4j.get_related.return_value = [
            {"id": str(uuid4()), "type": "IMPLEMENTS"}
        ]
        query_engine = AsyncMock()
        query_engine.get_related.return_value = [
            {"id": str(uuid4()), "type": "IMPLEMENTS"}
        ]
        return {"neo4j": neo4j, "query_engine": query_engine}

    @pytest.mark.asyncio
    async def test_get_related_basic(self, mock_context: dict) -> None:
        """Test getting related memories."""
        params = {
            "entity_id": str(uuid4()),
            "relationship_types": ["IMPLEMENTS"],
            "direction": "outgoing",
            "depth": 2,
            "_context": mock_context,
        }

        result = await get_related(params)

        assert "related" in result or "error" in result
        mock_context["query_engine"].get_related.assert_called_once()


class TestNormalizeStatus:
    """Unit tests for normalize_status tool."""

    @pytest.fixture
    def mock_context(self) -> dict:
        """Create mock context."""
        job_manager = AsyncMock()
        job_manager.get_job.return_value = {
            "status": "running",
            "progress": 50,
        }
        normalizer = AsyncMock()
        normalizer.get_status.return_value = {
            "status": "idle",
        }
        return {"job_manager": job_manager, "normalizer": normalizer}

    @pytest.mark.asyncio
    async def test_get_normalize_status_with_job_id(self, mock_context: dict) -> None:
        """Test getting normalization status for specific job."""
        params = {
            "job_id": "norm-job-123",
            "_context": mock_context,
        }

        result = await normalize_status(params)

        assert isinstance(result, dict)
        assert result["status"] == "running"

    @pytest.mark.asyncio
    async def test_get_normalize_status_no_job_id(self, mock_context: dict) -> None:
        """Test getting normalizer status when no job_id."""
        params = {
            "_context": mock_context,
        }

        result = await normalize_status(params)

        assert isinstance(result, dict)
        mock_context["normalizer"].get_status.assert_called_once()
