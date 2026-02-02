"""Unit tests for MCP server."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from memory_service.api.mcp_server import MCPServer, MCPError


class TestMCPServer:
    """Tests for MCPServer class."""

    @pytest.fixture
    def mock_qdrant(self) -> AsyncMock:
        """Create mock Qdrant adapter."""
        return AsyncMock()

    @pytest.fixture
    def mock_neo4j(self) -> AsyncMock:
        """Create mock Neo4j adapter."""
        return AsyncMock()

    @pytest.fixture
    def mock_embedding_service(self) -> MagicMock:
        """Create mock embedding service."""
        return MagicMock()

    def test_server_initialization(
        self,
        mock_qdrant: AsyncMock,
        mock_neo4j: AsyncMock,
        mock_embedding_service: MagicMock,
    ) -> None:
        """Test MCP server initialization."""
        server = MCPServer(
            qdrant=mock_qdrant,
            neo4j=mock_neo4j,
            embedding_service=mock_embedding_service,
        )

        assert server is not None
        assert server.qdrant == mock_qdrant
        assert server.neo4j == mock_neo4j

    def test_server_has_tools_registered(
        self,
        mock_qdrant: AsyncMock,
        mock_neo4j: AsyncMock,
        mock_embedding_service: MagicMock,
    ) -> None:
        """Test server has registered tools."""
        server = MCPServer(
            qdrant=mock_qdrant,
            neo4j=mock_neo4j,
            embedding_service=mock_embedding_service,
        )

        # Should have tools registered
        assert hasattr(server, '_tools')
        assert len(server._tools) > 0

    def test_server_has_tool_schemas(
        self,
        mock_qdrant: AsyncMock,
        mock_neo4j: AsyncMock,
        mock_embedding_service: MagicMock,
    ) -> None:
        """Test server has tool schemas."""
        server = MCPServer(
            qdrant=mock_qdrant,
            neo4j=mock_neo4j,
            embedding_service=mock_embedding_service,
        )

        assert hasattr(server, '_tool_schemas')
        assert "memory_add" in server._tool_schemas
        assert "memory_search" in server._tool_schemas

    def test_server_initializes_core_services(
        self,
        mock_qdrant: AsyncMock,
        mock_neo4j: AsyncMock,
        mock_embedding_service: MagicMock,
    ) -> None:
        """Test server initializes core services."""
        server = MCPServer(
            qdrant=mock_qdrant,
            neo4j=mock_neo4j,
            embedding_service=mock_embedding_service,
        )

        assert server.memory_manager is not None
        assert server.query_engine is not None
        assert server.job_manager is not None
        assert server.indexer is not None
        assert server.normalizer is not None


class TestMCPError:
    """Tests for MCPError class."""

    def test_error_creation(self) -> None:
        """Test creating MCP error."""
        error = MCPError(code=-32600, message="Invalid request")

        assert error.code == -32600
        assert error.message == "Invalid request"

    def test_error_with_data(self) -> None:
        """Test creating MCP error with data."""
        error = MCPError(code=-32602, message="Invalid params", data={"field": "name"})

        assert error.code == -32602
        assert error.message == "Invalid params"
        assert error.data == {"field": "name"}

    def test_error_inherits_exception(self) -> None:
        """Test MCP error inherits from Exception."""
        error = MCPError(code=-32600, message="Test error")

        assert isinstance(error, Exception)


class TestMCPServerMessages:
    """Tests for MCP server message handling."""

    @pytest.fixture
    def server(self) -> MCPServer:
        """Create MCP server with mocks."""
        mock_qdrant = AsyncMock()
        mock_neo4j = AsyncMock()
        mock_embedding = MagicMock()

        return MCPServer(
            qdrant=mock_qdrant,
            neo4j=mock_neo4j,
            embedding_service=mock_embedding,
        )

    @pytest.mark.asyncio
    async def test_handle_initialize(self, server: MCPServer) -> None:
        """Test handling initialize message."""
        response = server._handle_initialize(1, {})

        assert response["id"] == 1
        assert "result" in response
        assert "protocolVersion" in response["result"]
        assert "serverInfo" in response["result"]

    def test_handle_tools_list(self, server: MCPServer) -> None:
        """Test handling tools/list message."""
        response = server._handle_tools_list(1)

        assert response["id"] == 1
        assert "result" in response
        assert "tools" in response["result"]
        assert len(response["result"]["tools"]) > 0

    def test_success_response(self, server: MCPServer) -> None:
        """Test creating success response."""
        response = server._success_response(1, {"data": "test"})

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert response["result"] == {"data": "test"}

    def test_error_response(self, server: MCPServer) -> None:
        """Test creating error response."""
        response = server._error_response(1, -32600, "Invalid request")

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert response["error"]["code"] == -32600
        assert response["error"]["message"] == "Invalid request"

    def test_error_response_with_data(self, server: MCPServer) -> None:
        """Test creating error response with data."""
        response = server._error_response(1, -32602, "Invalid params", {"field": "name"})

        assert response["error"]["data"] == {"field": "name"}

    def test_get_tool_description(self, server: MCPServer) -> None:
        """Test getting tool description."""
        desc = server._get_tool_description("memory_add")

        assert "memory" in desc.lower() or "add" in desc.lower()

    def test_get_tool_description_unknown(self, server: MCPServer) -> None:
        """Test getting description for unknown tool."""
        desc = server._get_tool_description("unknown_tool")

        assert desc is not None  # Should return a default

    def test_validate_input_required_fields(self, server: MCPServer) -> None:
        """Test input validation checks required fields."""
        with pytest.raises(Exception):  # ValidationError or similar
            server._validate_input("memory_add", {})  # Missing required fields

    def test_validate_input_valid(self, server: MCPServer) -> None:
        """Test input validation passes for valid input."""
        server._validate_input("memory_add", {
            "memory_type": "requirements",
            "content": "Test content",
        })  # Should not raise


class TestToolSchemas:
    """Tests for tool JSON schemas."""

    def test_memory_add_schema(self) -> None:
        """Test memory_add has valid schema."""
        from memory_service.api.tools.memory_crud import memory_add

        # Tool should have schema information
        assert callable(memory_add)

    def test_memory_search_schema(self) -> None:
        """Test memory_search has valid schema."""
        from memory_service.api.tools.search import memory_search

        assert callable(memory_search)


class TestMCPProtocol:
    """Tests for MCP protocol handling."""

    @pytest.fixture
    def mock_context(self) -> dict:
        """Create mock context."""
        memory_manager = AsyncMock()
        memory_manager.add_memory.return_value = (uuid4(), [])
        memory_manager.get_memory.return_value = None

        query_engine = AsyncMock()
        query_engine.semantic_search.return_value = []

        return {
            "memory_manager": memory_manager,
            "query_engine": query_engine,
            "neo4j": AsyncMock(),
            "qdrant": AsyncMock(),
        }

    @pytest.mark.asyncio
    async def test_tool_receives_context(self, mock_context: dict) -> None:
        """Test that tools receive _context parameter."""
        from memory_service.api.tools.memory_crud import memory_add

        params = {
            "memory_type": "requirements",
            "content": "Test requirement",
            "metadata": {
                "requirement_id": "REQ-MEM-TEST-001",
                "title": "Test",
                "description": "A test requirement",
                "priority": "High",
                "status": "Draft",
                "source_document": "test.md",
            },
            "_context": mock_context,
        }

        result = await memory_add(params)

        # Should have used the context
        mock_context["memory_manager"].add_memory.assert_called_once()

    @pytest.mark.asyncio
    async def test_tool_handles_missing_context(self) -> None:
        """Test tool handles missing _context gracefully."""
        from memory_service.api.tools.search import memory_search

        params = {
            "query": "test",
            # Missing _context
        }

        # Should handle gracefully (error or exception)
        try:
            result = await memory_search(params)
            assert "error" in result
        except KeyError:
            pass  # Expected if context is required


class TestToolValidation:
    """Tests for tool input validation."""

    @pytest.fixture
    def mock_context(self) -> dict:
        """Create mock context."""
        return {
            "memory_manager": AsyncMock(),
            "query_engine": AsyncMock(),
            "neo4j": AsyncMock(),
            "qdrant": AsyncMock(),
        }

    @pytest.mark.asyncio
    async def test_memory_add_validates_type(self, mock_context: dict) -> None:
        """Test memory_add validates memory type."""
        from memory_service.api.tools.memory_crud import memory_add

        params = {
            "memory_type": "invalid_type",
            "content": "Test",
            "_context": mock_context,
        }

        result = await memory_add(params)

        assert "error" in result

    @pytest.mark.asyncio
    async def test_memory_search_validates_limit(self, mock_context: dict) -> None:
        """Test memory_search handles limit parameter."""
        from memory_service.api.tools.search import memory_search

        mock_context["query_engine"].semantic_search.return_value = []

        params = {
            "query": "test",
            "limit": 100,
            "_context": mock_context,
        }

        result = await memory_search(params)

        # Should work without error
        assert "results" in result or "error" not in result


class TestToolErrorHandling:
    """Tests for tool error handling."""

    @pytest.fixture
    def mock_context(self) -> dict:
        """Create mock context with failing services."""
        memory_manager = AsyncMock()
        memory_manager.add_memory.side_effect = Exception("Database error")

        return {
            "memory_manager": memory_manager,
            "query_engine": AsyncMock(),
            "neo4j": AsyncMock(),
            "qdrant": AsyncMock(),
        }

    @pytest.mark.asyncio
    async def test_memory_add_handles_service_error(self, mock_context: dict) -> None:
        """Test memory_add handles service errors."""
        from memory_service.api.tools.memory_crud import memory_add

        params = {
            "memory_type": "requirements",
            "content": "Test requirement",
            "metadata": {
                "requirement_id": "REQ-MEM-TEST-001",
                "title": "Test",
                "description": "A test requirement",
                "priority": "High",
                "status": "Draft",
                "source_document": "test.md",
            },
            "_context": mock_context,
        }

        result = await memory_add(params)

        # Should return error, not crash
        assert "error" in result
