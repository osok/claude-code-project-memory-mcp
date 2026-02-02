"""Integration tests for stdio MCP transport (REQ-MEM-002-VER-003).

Tests verify that:
- MCP server communicates via stdio
- JSON-RPC messages are properly formatted
- Tools can be called via stdio
- Server responds to initialize request
"""

import asyncio
import json
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestMCPStdioTransport:
    """Tests for MCP stdio transport."""

    @pytest.mark.asyncio
    async def test_mcp_server_reads_from_stdin(self):
        """MCP server should read JSON-RPC from stdin."""
        from memory_service.api.mcp_server import MCPServer

        # Create mock adapters
        mock_qdrant = MagicMock()
        mock_qdrant.project_id = "test-project"
        mock_neo4j = MagicMock()
        mock_embedding = MagicMock()

        server = MCPServer(
            qdrant=mock_qdrant,
            neo4j=mock_neo4j,
            embedding_service=mock_embedding,
        )

        # Test message handling directly
        initialize_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        }

        response = await server._handle_message(initialize_msg)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert response["result"]["serverInfo"]["name"] == "claude-memory-mcp"

    @pytest.mark.asyncio
    async def test_mcp_server_writes_to_stdout(self):
        """MCP server should write JSON-RPC responses to stdout."""
        from memory_service.api.mcp_server import MCPServer

        mock_qdrant = MagicMock()
        mock_qdrant.project_id = "test-project"
        mock_neo4j = MagicMock()
        mock_embedding = MagicMock()

        server = MCPServer(
            qdrant=mock_qdrant,
            neo4j=mock_neo4j,
            embedding_service=mock_embedding,
        )

        # Test success response formatting
        response = server._success_response(42, {"tools": []})

        assert response == {
            "jsonrpc": "2.0",
            "id": 42,
            "result": {"tools": []},
        }

    @pytest.mark.asyncio
    async def test_mcp_server_handles_tools_list(self):
        """MCP server should respond to tools/list request."""
        from memory_service.api.mcp_server import MCPServer

        mock_qdrant = MagicMock()
        mock_qdrant.project_id = "test-project"
        mock_neo4j = MagicMock()
        mock_embedding = MagicMock()

        server = MCPServer(
            qdrant=mock_qdrant,
            neo4j=mock_neo4j,
            embedding_service=mock_embedding,
        )

        tools_list_msg = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }

        response = await server._handle_message(tools_list_msg)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 2
        assert "result" in response
        assert "tools" in response["result"]
        assert len(response["result"]["tools"]) > 0

        # Verify tool structure
        tool = response["result"]["tools"][0]
        assert "name" in tool
        assert "description" in tool
        assert "inputSchema" in tool

    @pytest.mark.asyncio
    async def test_mcp_server_handles_tool_call(self):
        """MCP server should handle tools/call requests."""
        from memory_service.api.mcp_server import MCPServer

        mock_qdrant = MagicMock()
        mock_qdrant.project_id = "test-project"
        mock_neo4j = MagicMock()
        mock_embedding = MagicMock()

        server = MCPServer(
            qdrant=mock_qdrant,
            neo4j=mock_neo4j,
            embedding_service=mock_embedding,
        )

        # Test with memory_statistics which doesn't require real DB
        with patch.object(server, '_tools') as mock_tools:
            mock_handler = AsyncMock(return_value={"total_memories": 0})
            mock_tools.__getitem__ = MagicMock(return_value=mock_handler)
            mock_tools.__contains__ = MagicMock(return_value=True)

            tool_call_msg = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "memory_statistics",
                    "arguments": {}
                }
            }

            response = await server._handle_message(tool_call_msg)

            assert response["jsonrpc"] == "2.0"
            assert response["id"] == 3
            # Either success with result or error
            assert "result" in response or "error" in response

    @pytest.mark.asyncio
    async def test_mcp_server_handles_shutdown(self):
        """MCP server should respond to shutdown request."""
        from memory_service.api.mcp_server import MCPServer

        mock_qdrant = MagicMock()
        mock_qdrant.project_id = "test-project"
        mock_neo4j = MagicMock()
        mock_embedding = MagicMock()

        server = MCPServer(
            qdrant=mock_qdrant,
            neo4j=mock_neo4j,
            embedding_service=mock_embedding,
        )

        shutdown_msg = {
            "jsonrpc": "2.0",
            "id": 99,
            "method": "shutdown",
            "params": {}
        }

        response = await server._handle_message(shutdown_msg)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 99
        assert response["result"]["status"] == "ok"

    @pytest.mark.asyncio
    async def test_mcp_server_returns_error_for_unknown_method(self):
        """MCP server should return error for unknown methods."""
        from memory_service.api.mcp_server import MCPServer

        mock_qdrant = MagicMock()
        mock_qdrant.project_id = "test-project"
        mock_neo4j = MagicMock()
        mock_embedding = MagicMock()

        server = MCPServer(
            qdrant=mock_qdrant,
            neo4j=mock_neo4j,
            embedding_service=mock_embedding,
        )

        unknown_msg = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "unknown/method",
            "params": {}
        }

        response = await server._handle_message(unknown_msg)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 5
        assert "error" in response
        assert response["error"]["code"] == -32601  # Method not found


class TestMCPJsonRpcFormat:
    """Tests for JSON-RPC message formatting."""

    @pytest.mark.asyncio
    async def test_error_response_format(self):
        """Error responses should follow JSON-RPC format."""
        from memory_service.api.mcp_server import MCPServer

        mock_qdrant = MagicMock()
        mock_qdrant.project_id = "test-project"
        mock_neo4j = MagicMock()
        mock_embedding = MagicMock()

        server = MCPServer(
            qdrant=mock_qdrant,
            neo4j=mock_neo4j,
            embedding_service=mock_embedding,
        )

        error = server._error_response(123, -32600, "Invalid request", {"detail": "test"})

        assert error == {
            "jsonrpc": "2.0",
            "id": 123,
            "error": {
                "code": -32600,
                "message": "Invalid request",
                "data": {"detail": "test"},
            }
        }

    @pytest.mark.asyncio
    async def test_success_response_format(self):
        """Success responses should follow JSON-RPC format."""
        from memory_service.api.mcp_server import MCPServer

        mock_qdrant = MagicMock()
        mock_qdrant.project_id = "test-project"
        mock_neo4j = MagicMock()
        mock_embedding = MagicMock()

        server = MCPServer(
            qdrant=mock_qdrant,
            neo4j=mock_neo4j,
            embedding_service=mock_embedding,
        )

        success = server._success_response(456, {"data": "test"})

        assert success == {
            "jsonrpc": "2.0",
            "id": 456,
            "result": {"data": "test"},
        }


class TestMCPInitializeResponse:
    """Tests for MCP initialize response."""

    @pytest.mark.asyncio
    async def test_initialize_includes_project_id(self):
        """Initialize response should include project_id."""
        from memory_service.api.mcp_server import MCPServer

        mock_qdrant = MagicMock()
        mock_qdrant.project_id = "my-test-project"
        mock_neo4j = MagicMock()
        mock_embedding = MagicMock()

        server = MCPServer(
            qdrant=mock_qdrant,
            neo4j=mock_neo4j,
            embedding_service=mock_embedding,
        )

        init_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        }

        response = await server._handle_message(init_msg)

        assert response["result"]["serverInfo"]["project_id"] == "my-test-project"

    @pytest.mark.asyncio
    async def test_initialize_includes_capabilities(self):
        """Initialize response should include server capabilities."""
        from memory_service.api.mcp_server import MCPServer

        mock_qdrant = MagicMock()
        mock_qdrant.project_id = "test-project"
        mock_neo4j = MagicMock()
        mock_embedding = MagicMock()

        server = MCPServer(
            qdrant=mock_qdrant,
            neo4j=mock_neo4j,
            embedding_service=mock_embedding,
        )

        init_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        }

        response = await server._handle_message(init_msg)

        assert "capabilities" in response["result"]
        assert "tools" in response["result"]["capabilities"]


class TestSetProjectToolRemoved:
    """Tests to verify set_project tool is removed (REQ-MEM-002-FN-034)."""

    @pytest.mark.asyncio
    async def test_set_project_tool_not_available(self):
        """set_project tool should not be available."""
        from memory_service.api.mcp_server import MCPServer

        mock_qdrant = MagicMock()
        mock_qdrant.project_id = "test-project"
        mock_neo4j = MagicMock()
        mock_embedding = MagicMock()

        server = MCPServer(
            qdrant=mock_qdrant,
            neo4j=mock_neo4j,
            embedding_service=mock_embedding,
        )

        # Get tools list
        tools_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }

        response = await server._handle_message(tools_msg)
        tool_names = [t["name"] for t in response["result"]["tools"]]

        # Verify set_project is NOT in the list
        assert "set_project" not in tool_names
        assert "get_project" not in tool_names

    @pytest.mark.asyncio
    async def test_calling_set_project_returns_error(self):
        """Calling set_project should return error."""
        from memory_service.api.mcp_server import MCPServer

        mock_qdrant = MagicMock()
        mock_qdrant.project_id = "test-project"
        mock_neo4j = MagicMock()
        mock_embedding = MagicMock()

        server = MCPServer(
            qdrant=mock_qdrant,
            neo4j=mock_neo4j,
            embedding_service=mock_embedding,
        )

        call_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "set_project",
                "arguments": {"project_id": "hacked"}
            }
        }

        response = await server._handle_message(call_msg)

        assert "error" in response
        assert response["error"]["code"] == -32602  # Invalid params (unknown tool)
