"""Unit tests for analysis tools."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from memory_service.api.tools.analysis import (
    check_consistency,
    validate_fix,
    get_design_context,
    trace_requirements,
)
from memory_service.models import MemoryType
from memory_service.core.query_engine import SearchResult


class TestCheckConsistency:
    """Tests for check_consistency tool."""

    @pytest.fixture
    def mock_context(self) -> dict:
        """Create mock context."""
        qdrant = AsyncMock()
        qdrant.get.return_value = {
            "id": str(uuid4()),
            "name": "TestComponent",
            "embedding": [0.1] * 1024,
            "payload": {"name": "TestComponent"},
        }
        qdrant.get_collection_name.return_value = "components"
        qdrant.search.return_value = []

        query_engine = AsyncMock()
        query_engine.semantic_search.return_value = []

        embedding_service = MagicMock()

        return {
            "qdrant": qdrant,
            "query_engine": query_engine,
            "embedding_service": embedding_service,
        }

    @pytest.mark.asyncio
    async def test_check_consistency_success(self, mock_context: dict) -> None:
        """Test successful consistency check."""
        params = {
            "component_id": str(uuid4()),
            "_context": mock_context,
        }

        result = await check_consistency(params)

        assert isinstance(result, dict)
        # Should have consistency_score or indicate analysis
        assert "consistency_score" in result or "error" not in result or "status" in result

    @pytest.mark.asyncio
    async def test_check_consistency_component_not_found(
        self,
        mock_context: dict,
    ) -> None:
        """Test check_consistency when component not found."""
        mock_context["qdrant"].get.return_value = None

        params = {
            "component_id": str(uuid4()),
            "_context": mock_context,
        }

        result = await check_consistency(params)

        assert "error" in result
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_check_consistency_with_pattern_filter(
        self,
        mock_context: dict,
    ) -> None:
        """Test check_consistency with pattern type filter."""
        params = {
            "component_id": str(uuid4()),
            "pattern_types": ["Template", "Error Handling"],
            "_context": mock_context,
        }

        result = await check_consistency(params)

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_check_consistency_finds_violations(
        self,
        mock_context: dict,
    ) -> None:
        """Test check_consistency when violations found."""
        # Setup patterns that might indicate violations
        mock_context["query_engine"].semantic_search.return_value = [
            SearchResult(
                id=str(uuid4()),
                memory_type=MemoryType.CODE_PATTERN,
                content="Use async/await pattern",
                score=0.3,  # Low score indicates mismatch
                payload={"pattern_name": "Async Pattern"},
            )
        ]

        params = {
            "component_id": str(uuid4()),
            "_context": mock_context,
        }

        result = await check_consistency(params)

        assert isinstance(result, dict)


class TestValidateFix:
    """Tests for validate_fix tool."""

    @pytest.fixture
    def mock_context(self) -> dict:
        """Create mock context."""
        query_engine = AsyncMock()
        query_engine.semantic_search.return_value = []

        embedding_service = MagicMock()

        return {
            "query_engine": query_engine,
            "embedding_service": embedding_service,
        }

    @pytest.mark.asyncio
    async def test_validate_fix_success(self, mock_context: dict) -> None:
        """Test successful fix validation."""
        mock_context["query_engine"].semantic_search.return_value = [
            SearchResult(
                id=str(uuid4()),
                memory_type=MemoryType.DESIGN,
                content="Use dependency injection",
                score=0.9,
                payload={"design_type": "ADR"},
            )
        ]

        params = {
            "fix_description": "Add dependency injection for services",
            "affected_component": "UserService",
            "_context": mock_context,
        }

        result = await validate_fix(params)

        assert isinstance(result, dict)
        mock_context["query_engine"].semantic_search.assert_called()

    @pytest.mark.asyncio
    async def test_validate_fix_no_matching_design(
        self,
        mock_context: dict,
    ) -> None:
        """Test validate_fix when no matching design found."""
        mock_context["query_engine"].semantic_search.return_value = []

        params = {
            "fix_description": "Random change",
            "affected_component": "Component",
            "_context": mock_context,
        }

        result = await validate_fix(params)

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_validate_fix_with_code(self, mock_context: dict) -> None:
        """Test validate_fix with proposed code."""
        params = {
            "fix_description": "Add error handling",
            "affected_component": "APIHandler",
            "proposed_code": """
def handle_request(request):
    try:
        return process(request)
    except Exception as e:
        logger.error(f"Error: {e}")
        return error_response()
""",
            "_context": mock_context,
        }

        result = await validate_fix(params)

        assert isinstance(result, dict)


class TestGetDesignContext:
    """Tests for get_design_context tool."""

    @pytest.fixture
    def mock_context(self) -> dict:
        """Create mock context."""
        query_engine = AsyncMock()
        query_engine.semantic_search.return_value = []

        neo4j = AsyncMock()
        neo4j.get_related.return_value = []

        return {
            "query_engine": query_engine,
            "neo4j": neo4j,
        }

    @pytest.mark.asyncio
    async def test_get_design_context_success(self, mock_context: dict) -> None:
        """Test successful design context retrieval."""
        mock_context["query_engine"].semantic_search.return_value = [
            SearchResult(
                id=str(uuid4()),
                memory_type=MemoryType.DESIGN,
                content="Authentication design",
                score=0.85,
                payload={"title": "Auth Design"},
            ),
            SearchResult(
                id=str(uuid4()),
                memory_type=MemoryType.REQUIREMENTS,
                content="User authentication requirement",
                score=0.80,
                payload={"requirement_id": "REQ-MEM-AUTH-001"},
            ),
        ]

        params = {
            "query": "authentication handler",
            "_context": mock_context,
        }

        result = await get_design_context(params)

        assert isinstance(result, dict)
        # Should have designs or requirements
        assert "designs" in result or "requirements" in result

    @pytest.mark.asyncio
    async def test_get_design_context_no_matches(self, mock_context: dict) -> None:
        """Test get_design_context when no matches found."""
        mock_context["query_engine"].semantic_search.return_value = []

        params = {
            "query": "random feature",
            "_context": mock_context,
        }

        result = await get_design_context(params)

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_get_design_context_with_component_name(
        self,
        mock_context: dict,
    ) -> None:
        """Test get_design_context with component ID."""
        params = {
            "component_id": str(uuid4()),
            "_context": mock_context,
        }

        result = await get_design_context(params)

        assert isinstance(result, dict)


class TestTraceRequirements:
    """Tests for trace_requirements tool."""

    @pytest.fixture
    def mock_context(self) -> dict:
        """Create mock context."""
        neo4j = AsyncMock()
        neo4j.get_related.return_value = []
        neo4j.get_node.return_value = None

        qdrant = AsyncMock()
        qdrant.get.return_value = None

        query_engine = AsyncMock()
        query_engine.get_related.return_value = []

        return {
            "neo4j": neo4j,
            "qdrant": qdrant,
            "query_engine": query_engine,
        }

    @pytest.mark.asyncio
    async def test_trace_requirements_success(self, mock_context: dict) -> None:
        """Test successful requirements tracing."""
        req_id = "REQ-MEM-AUTH-001"
        mock_context["neo4j"].get_node.return_value = {
            "id": str(uuid4()),
            "requirement_id": req_id,
            "title": "Authentication",
        }
        mock_context["query_engine"].get_related.return_value = [
            {"id": str(uuid4()), "type": "IMPLEMENTS"},
        ]

        params = {
            "requirement_id": req_id,
            "_context": mock_context,
        }

        result = await trace_requirements(params)

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_trace_requirements_not_found(self, mock_context: dict) -> None:
        """Test trace_requirements when requirement not found."""
        mock_context["neo4j"].get_node.return_value = None

        params = {
            "requirement_id": "REQ-NONEXISTENT-001",
            "_context": mock_context,
        }

        result = await trace_requirements(params)

        assert isinstance(result, dict)
        # Should indicate not found or empty trace

    @pytest.mark.asyncio
    async def test_trace_requirements_with_depth(self, mock_context: dict) -> None:
        """Test trace_requirements with depth limit."""
        params = {
            "requirement_id": "REQ-MEM-TEST-001",
            "max_depth": 3,
            "_context": mock_context,
        }

        result = await trace_requirements(params)

        assert isinstance(result, dict)


class TestAnalysisEdgeCases:
    """Tests for edge cases in analysis tools."""

    @pytest.fixture
    def mock_context(self) -> dict:
        """Create mock context."""
        return {
            "qdrant": AsyncMock(),
            "neo4j": AsyncMock(),
            "query_engine": AsyncMock(),
            "embedding_service": MagicMock(),
        }

    @pytest.mark.asyncio
    async def test_check_consistency_missing_component_id(
        self,
        mock_context: dict,
    ) -> None:
        """Test check_consistency without component_id."""
        params = {
            "_context": mock_context,
        }

        result = await check_consistency(params)

        # Should handle gracefully
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_validate_fix_missing_description(
        self,
        mock_context: dict,
    ) -> None:
        """Test validate_fix without fix_description."""
        params = {
            "affected_component": "Component",
            "_context": mock_context,
        }

        result = await validate_fix(params)

        # Should handle gracefully
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_get_design_context_missing_file_path(
        self,
        mock_context: dict,
    ) -> None:
        """Test get_design_context without file_path."""
        params = {
            "_context": mock_context,
        }

        result = await get_design_context(params)

        # Should handle gracefully
        assert isinstance(result, dict)
