"""Unit tests for Duplicate Detection Logic (UT-090 to UT-096)."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from memory_service.api.tools.search import find_duplicates
from memory_service.models import MemoryType
from tests.fixtures.factories import generate_embedding


@pytest.fixture
def mock_query_engine():
    """Create mock QueryEngine."""
    mock = AsyncMock()
    mock.semantic_search = AsyncMock(return_value=[])
    return mock


@pytest.fixture
def mock_embedding_service():
    """Create mock EmbeddingService."""
    mock = AsyncMock()
    mock.embed_for_query = AsyncMock(return_value=generate_embedding(seed=42))
    return mock


@pytest.fixture
def mock_qdrant():
    """Create mock QdrantAdapter."""
    mock = AsyncMock()
    mock.get_collection_name = MagicMock(return_value="memories_function")
    mock.search = AsyncMock(return_value=[])
    return mock


@pytest.fixture
def tool_context(mock_query_engine, mock_embedding_service, mock_qdrant):
    """Create tool context with mocked dependencies."""
    return {
        "query_engine": mock_query_engine,
        "embedding_service": mock_embedding_service,
        "qdrant": mock_qdrant,
    }


class TestFindDuplicates:
    """Tests for find_duplicates tool (UT-090 to UT-096)."""

    @pytest.mark.asyncio
    async def test_ut090_return_matches_above_threshold(
        self, tool_context: dict, mock_qdrant: AsyncMock
    ):
        """UT-090: Return matches above threshold (0.85 default)."""
        # Setup mock to return matches
        mock_qdrant.search.return_value = [
            {
                "id": str(uuid4()),
                "score": 0.92,
                "payload": {
                    "name": "authenticate_user",
                    "file_path": "src/auth.py",
                    "signature": "def authenticate_user(username, password)",
                    "start_line": 10,
                    "end_line": 25,
                },
            },
            {
                "id": str(uuid4()),
                "score": 0.88,
                "payload": {
                    "name": "verify_user",
                    "file_path": "src/verify.py",
                    "signature": "def verify_user(user, pwd)",
                    "start_line": 5,
                    "end_line": 18,
                },
            },
        ]

        code = """
        def authenticate_user(username, password):
            user = get_user(username)
            if user and user.check_password(password):
                return user
            return None
        """

        result = await find_duplicates({
            "code": code,
            "_context": tool_context,
        })

        assert "error" not in result
        assert result["duplicate_count"] == 2
        assert len(result["duplicates"]) == 2
        # Verify search was called with default threshold
        mock_qdrant.search.assert_called_once()
        call_kwargs = mock_qdrant.search.call_args.kwargs
        assert call_kwargs["score_threshold"] == 0.85

    @pytest.mark.asyncio
    async def test_ut091_filter_by_language(
        self, tool_context: dict, mock_qdrant: AsyncMock
    ):
        """UT-091: Filter by language."""
        code = "def example(): pass"

        await find_duplicates({
            "code": code,
            "language": "python",
            "_context": tool_context,
        })

        # Verify language filter was applied
        call_kwargs = mock_qdrant.search.call_args.kwargs
        assert call_kwargs["filters"]["language"] == "python"

    @pytest.mark.asyncio
    async def test_ut092_respect_limit_parameter(
        self, tool_context: dict, mock_qdrant: AsyncMock
    ):
        """UT-092: Respect limit parameter.

        Note: The current implementation uses a fixed limit of 10.
        This test documents the current behavior.
        """
        code = "def example(): pass"

        await find_duplicates({
            "code": code,
            "_context": tool_context,
        })

        # Current implementation uses limit=10
        call_kwargs = mock_qdrant.search.call_args.kwargs
        assert call_kwargs["limit"] == 10

    @pytest.mark.asyncio
    async def test_ut093_return_empty_list_when_no_matches(
        self, tool_context: dict, mock_qdrant: AsyncMock
    ):
        """UT-093: Return empty list when no matches."""
        mock_qdrant.search.return_value = []

        code = "def unique_function(): pass"

        result = await find_duplicates({
            "code": code,
            "_context": tool_context,
        })

        assert "error" not in result
        assert result["duplicate_count"] == 0
        assert result["duplicates"] == []

    @pytest.mark.asyncio
    async def test_ut094_accept_configurable_threshold(
        self, tool_context: dict, mock_qdrant: AsyncMock
    ):
        """UT-094: Accept configurable threshold (0.70-0.95)."""
        code = "def example(): pass"

        # Test lower bound
        await find_duplicates({
            "code": code,
            "threshold": 0.70,
            "_context": tool_context,
        })
        call_kwargs = mock_qdrant.search.call_args.kwargs
        assert call_kwargs["score_threshold"] == 0.70

        # Test upper bound
        await find_duplicates({
            "code": code,
            "threshold": 0.95,
            "_context": tool_context,
        })
        call_kwargs = mock_qdrant.search.call_args.kwargs
        assert call_kwargs["score_threshold"] == 0.95

        # Test mid-range
        await find_duplicates({
            "code": code,
            "threshold": 0.80,
            "_context": tool_context,
        })
        call_kwargs = mock_qdrant.search.call_args.kwargs
        assert call_kwargs["score_threshold"] == 0.80

    @pytest.mark.asyncio
    async def test_ut094_reject_threshold_out_of_range(
        self, tool_context: dict
    ):
        """UT-094: Reject threshold outside 0.70-0.95 range."""
        code = "def example(): pass"

        # Too low
        result = await find_duplicates({
            "code": code,
            "threshold": 0.50,
            "_context": tool_context,
        })
        assert "error" in result
        assert "0.70" in result["error"] and "0.95" in result["error"]

        # Too high
        result = await find_duplicates({
            "code": code,
            "threshold": 0.99,
            "_context": tool_context,
        })
        assert "error" in result
        assert "0.70" in result["error"] and "0.95" in result["error"]

    @pytest.mark.asyncio
    async def test_ut095_return_existing_function_details(
        self, tool_context: dict, mock_qdrant: AsyncMock
    ):
        """UT-095: Return existing function details."""
        function_id = str(uuid4())
        mock_qdrant.search.return_value = [
            {
                "id": function_id,
                "score": 0.91,
                "payload": {
                    "name": "process_data",
                    "file_path": "src/processor.py",
                    "signature": "def process_data(data: dict) -> dict",
                    "start_line": 100,
                    "end_line": 150,
                    "language": "python",
                    "docstring": "Process input data and return results.",
                },
            },
        ]

        result = await find_duplicates({
            "code": "def process_data(data): return data",
            "_context": tool_context,
        })

        assert result["duplicate_count"] == 1
        duplicate = result["duplicates"][0]

        # Verify all expected details are returned
        assert duplicate["id"] == function_id
        assert duplicate["name"] == "process_data"
        assert "file_path" in duplicate
        assert "signature" in duplicate
        assert "start_line" in duplicate
        assert "end_line" in duplicate

    @pytest.mark.asyncio
    async def test_ut096_include_file_path_signature_location(
        self, tool_context: dict, mock_qdrant: AsyncMock
    ):
        """UT-096: Include file_path, signature, location."""
        mock_qdrant.search.return_value = [
            {
                "id": str(uuid4()),
                "score": 0.89,
                "payload": {
                    "name": "calculate_total",
                    "file_path": "src/calculations/totals.py",
                    "signature": "def calculate_total(items: list[Item]) -> Decimal",
                    "start_line": 45,
                    "end_line": 60,
                },
            },
        ]

        result = await find_duplicates({
            "code": "def calculate_total(items): pass",
            "_context": tool_context,
        })

        duplicate = result["duplicates"][0]

        # Verify file_path
        assert duplicate["file_path"] == "src/calculations/totals.py"

        # Verify signature
        assert duplicate["signature"] == "def calculate_total(items: list[Item]) -> Decimal"

        # Verify location (start_line and end_line)
        assert duplicate["start_line"] == 45
        assert duplicate["end_line"] == 60


class TestDuplicateDetectionEdgeCases:
    """Edge case tests for duplicate detection."""

    @pytest.mark.asyncio
    async def test_handles_api_error_gracefully(
        self, tool_context: dict, mock_qdrant: AsyncMock
    ):
        """Test graceful handling of API errors."""
        mock_qdrant.search.side_effect = Exception("Database connection failed")

        result = await find_duplicates({
            "code": "def example(): pass",
            "_context": tool_context,
        })

        assert "error" in result
        assert "Database connection failed" in result["error"]

    @pytest.mark.asyncio
    async def test_handles_empty_code_input(
        self, tool_context: dict, mock_embedding_service: AsyncMock
    ):
        """Test handling of empty code input."""
        # Even empty code should generate an embedding and search
        await find_duplicates({
            "code": "",
            "_context": tool_context,
        })

        # Embedding service should still be called
        mock_embedding_service.embed_for_query.assert_called_once_with("")

    @pytest.mark.asyncio
    async def test_excludes_deleted_functions(
        self, tool_context: dict, mock_qdrant: AsyncMock
    ):
        """Test that deleted functions are excluded from results."""
        code = "def example(): pass"

        await find_duplicates({
            "code": code,
            "_context": tool_context,
        })

        # Verify deleted=False filter
        call_kwargs = mock_qdrant.search.call_args.kwargs
        assert call_kwargs["filters"]["deleted"] is False

    @pytest.mark.asyncio
    async def test_similarity_score_rounded(
        self, tool_context: dict, mock_qdrant: AsyncMock
    ):
        """Test that similarity scores are rounded to 4 decimal places."""
        mock_qdrant.search.return_value = [
            {
                "id": str(uuid4()),
                "score": 0.876543219876,  # Many decimals
                "payload": {
                    "name": "test_func",
                    "file_path": "test.py",
                    "signature": "def test_func()",
                    "start_line": 1,
                    "end_line": 5,
                },
            },
        ]

        result = await find_duplicates({
            "code": "def test_func(): pass",
            "_context": tool_context,
        })

        # Similarity should be rounded to 4 decimal places
        assert result["duplicates"][0]["similarity"] == 0.8765

    @pytest.mark.asyncio
    async def test_handles_missing_payload_fields(
        self, tool_context: dict, mock_qdrant: AsyncMock
    ):
        """Test handling of missing payload fields."""
        mock_qdrant.search.return_value = [
            {
                "id": str(uuid4()),
                "score": 0.90,
                "payload": {
                    "name": "minimal_func",
                    # Missing file_path, signature, start_line, end_line
                },
            },
        ]

        result = await find_duplicates({
            "code": "def test(): pass",
            "_context": tool_context,
        })

        duplicate = result["duplicates"][0]
        # Should have None for missing fields
        assert duplicate["name"] == "minimal_func"
        assert duplicate["file_path"] is None
        assert duplicate["signature"] is None
        assert duplicate["start_line"] is None
        assert duplicate["end_line"] is None

    @pytest.mark.asyncio
    async def test_multiple_languages_without_filter(
        self, tool_context: dict, mock_qdrant: AsyncMock
    ):
        """Test that without language filter, all languages are searched."""
        code = "function example() {}"

        await find_duplicates({
            "code": code,
            "_context": tool_context,
        })

        # No language filter in search
        call_kwargs = mock_qdrant.search.call_args.kwargs
        assert "language" not in call_kwargs["filters"]

    @pytest.mark.asyncio
    async def test_result_format(
        self, tool_context: dict, mock_qdrant: AsyncMock
    ):
        """Test the complete result format."""
        mock_qdrant.search.return_value = [
            {
                "id": "test-id-1",
                "score": 0.91,
                "payload": {
                    "name": "func1",
                    "file_path": "a.py",
                    "signature": "def func1()",
                    "start_line": 1,
                    "end_line": 5,
                },
            },
        ]

        result = await find_duplicates({
            "code": "def test(): pass",
            "threshold": 0.85,
            "language": "python",
            "_context": tool_context,
        })

        # Verify result structure
        assert "threshold" in result
        assert result["threshold"] == 0.85
        assert "language_filter" in result
        assert result["language_filter"] == "python"
        assert "duplicate_count" in result
        assert result["duplicate_count"] == 1
        assert "duplicates" in result
        assert isinstance(result["duplicates"], list)


class TestDuplicateSearchIntegration:
    """Tests for duplicate detection integration with other components."""

    @pytest.mark.asyncio
    async def test_embedding_generation_called_correctly(
        self, tool_context: dict, mock_embedding_service: AsyncMock
    ):
        """Test that embedding is generated for the input code."""
        code = """
        def complex_function(a, b, c):
            result = a + b * c
            return result / 2
        """

        await find_duplicates({
            "code": code,
            "_context": tool_context,
        })

        # Embedding should be generated for the exact code provided
        mock_embedding_service.embed_for_query.assert_called_once_with(code)

    @pytest.mark.asyncio
    async def test_searches_function_collection(
        self, tool_context: dict, mock_qdrant: AsyncMock
    ):
        """Test that search is performed on the function collection."""
        await find_duplicates({
            "code": "def test(): pass",
            "_context": tool_context,
        })

        # Should get collection name for FUNCTION type
        mock_qdrant.get_collection_name.assert_called_once_with(MemoryType.FUNCTION)
