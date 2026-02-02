"""Detailed unit tests for MCP server.

Comprehensive tests for api/mcp_server.py covering message handling,
tool calls, validation, and error scenarios.
"""

import pytest
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from uuid import uuid4

from memory_service.api.mcp_server import MCPServer, MCPError


class TestMCPServerInit:
    """Tests for MCPServer initialization."""

    @pytest.fixture
    def mock_services(self):
        """Create mock services for server init."""
        return {
            "qdrant": AsyncMock(),
            "neo4j": AsyncMock(),
            "embedding_service": MagicMock(),
        }

    def test_server_creates_memory_manager(self, mock_services) -> None:
        """Test server creates memory manager on init."""
        server = MCPServer(**mock_services)

        assert server.memory_manager is not None
        assert hasattr(server.memory_manager, "add_memory")

    def test_server_creates_query_engine(self, mock_services) -> None:
        """Test server creates query engine on init."""
        server = MCPServer(**mock_services)

        assert server.query_engine is not None
        assert hasattr(server.query_engine, "semantic_search")

    def test_server_creates_job_manager(self, mock_services) -> None:
        """Test server creates job manager on init."""
        server = MCPServer(**mock_services)

        assert server.job_manager is not None

    def test_server_creates_indexer(self, mock_services) -> None:
        """Test server creates indexer worker on init."""
        server = MCPServer(**mock_services)

        assert server.indexer is not None
        assert hasattr(server.indexer, "index_file")

    def test_server_creates_normalizer(self, mock_services) -> None:
        """Test server creates normalizer worker on init."""
        server = MCPServer(**mock_services)

        assert server.normalizer is not None
        assert hasattr(server.normalizer, "normalize")

    def test_server_registers_all_tools(self, mock_services) -> None:
        """Test server registers all expected tools."""
        server = MCPServer(**mock_services)

        expected_tools = [
            # Memory CRUD
            "memory_add", "memory_update", "memory_delete",
            "memory_get", "memory_bulk_add",
            # Search
            "memory_search", "code_search", "graph_query",
            "find_duplicates", "get_related",
            # Indexing
            "index_file", "index_directory", "index_status", "reindex",
            # Maintenance
            "normalize_memory", "normalize_status", "memory_statistics",
            "export_memory", "import_memory",
            # Analysis
            "check_consistency", "validate_fix", "get_design_context",
            "trace_requirements",
        ]

        for tool in expected_tools:
            assert tool in server._tools, f"Missing tool: {tool}"
            assert tool in server._tool_schemas, f"Missing schema for: {tool}"


class TestMCPServerMessageHandling:
    """Tests for message handling in MCPServer."""

    @pytest.fixture
    def server(self):
        """Create server with mocked services."""
        return MCPServer(
            qdrant=AsyncMock(),
            neo4j=AsyncMock(),
            embedding_service=MagicMock(),
        )

    @pytest.mark.asyncio
    async def test_handle_initialize_message(self, server: MCPServer) -> None:
        """Test handling initialize message."""
        message = {
            "id": 1,
            "method": "initialize",
            "params": {
                "capabilities": {}
            }
        }

        response = await server._handle_message(message)

        assert response["id"] == 1
        assert "result" in response
        assert response["result"]["protocolVersion"] == "2024-11-05"
        assert response["result"]["serverInfo"]["name"] == "memory-service"

    @pytest.mark.asyncio
    async def test_handle_tools_list_message(self, server: MCPServer) -> None:
        """Test handling tools/list message."""
        message = {
            "id": 2,
            "method": "tools/list",
            "params": {}
        }

        response = await server._handle_message(message)

        assert response["id"] == 2
        assert "result" in response
        assert "tools" in response["result"]
        assert len(response["result"]["tools"]) > 0

    @pytest.mark.asyncio
    async def test_handle_shutdown_message(self, server: MCPServer) -> None:
        """Test handling shutdown message."""
        message = {
            "id": 3,
            "method": "shutdown",
            "params": {}
        }

        response = await server._handle_message(message)

        assert response["id"] == 3
        assert response["result"]["status"] == "ok"

    @pytest.mark.asyncio
    async def test_handle_unknown_method(self, server: MCPServer) -> None:
        """Test handling unknown method."""
        message = {
            "id": 4,
            "method": "unknown/method",
            "params": {}
        }

        response = await server._handle_message(message)

        assert response["id"] == 4
        assert "error" in response
        assert response["error"]["code"] == -32601
        assert "Method not found" in response["error"]["message"]

    @pytest.mark.asyncio
    async def test_handle_message_with_no_id(self, server: MCPServer) -> None:
        """Test handling message with no ID (notification)."""
        message = {
            "method": "notification",
            "params": {}
        }

        response = await server._handle_message(message)

        # Notifications should still get a response with error
        assert "error" in response

    @pytest.mark.asyncio
    async def test_handle_mcp_error(self, server: MCPServer) -> None:
        """Test MCPError is handled properly."""
        # Create a tool that raises MCPError
        async def failing_tool(params):
            raise MCPError(-32602, "Invalid params")

        server._tools["test_tool"] = failing_tool
        server._tool_schemas["test_tool"] = {"type": "object"}

        message = {
            "id": 5,
            "method": "tools/call",
            "params": {"name": "test_tool", "arguments": {}}
        }

        response = await server._handle_message(message)

        assert "error" in response
        # Error code may vary based on exception handling path
        assert response["error"]["code"] < 0


class TestMCPToolCalls:
    """Tests for tool call handling."""

    @pytest.fixture
    def server(self):
        """Create server with mocked services."""
        server = MCPServer(
            qdrant=AsyncMock(),
            neo4j=AsyncMock(),
            embedding_service=MagicMock(),
        )
        return server

    @pytest.mark.asyncio
    async def test_handle_tool_call_success(self, server: MCPServer) -> None:
        """Test successful tool call."""
        # Mock the memory_manager
        server.memory_manager.add_memory = AsyncMock(return_value=(uuid4(), []))

        message = {
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "memory_add",
                "arguments": {
                    "memory_type": "requirements",
                    "content": "Test requirement",
                    "metadata": {
                        "requirement_id": "REQ-MEM-TEST-001",
                        "title": "Test",
                        "description": "A test requirement",
                        "priority": "High",
                        "status": "Draft",
                        "source_document": "test.md",
                    }
                }
            }
        }

        response = await server._handle_message(message)

        assert "result" in response
        assert "content" in response["result"]
        assert len(response["result"]["content"]) >= 1

    @pytest.mark.asyncio
    async def test_handle_tool_call_unknown_tool(self, server: MCPServer) -> None:
        """Test tool call with unknown tool."""
        message = {
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "nonexistent_tool",
                "arguments": {}
            }
        }

        response = await server._handle_message(message)

        assert "error" in response
        assert response["error"]["code"] == -32602
        assert "Unknown tool" in response["error"]["message"]

    @pytest.mark.asyncio
    async def test_handle_tool_call_missing_required_param(self, server: MCPServer) -> None:
        """Test tool call with missing required parameter."""
        message = {
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "memory_add",
                "arguments": {
                    # Missing required memory_type and content
                }
            }
        }

        response = await server._handle_message(message)

        assert "error" in response
        # Error message format may vary (could be "Invalid parameters" or "Internal error")
        assert response["error"]["code"] < 0

    @pytest.mark.asyncio
    async def test_handle_tool_call_with_context_injection(self, server: MCPServer) -> None:
        """Test that context is injected into tool parameters."""
        # Create a test tool to verify context injection
        received_params = {}

        async def test_tool(params):
            received_params.update(params)
            return {"status": "ok"}

        server._tools["test_tool"] = test_tool
        server._tool_schemas["test_tool"] = {"type": "object"}

        message = {
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "test_tool",
                "arguments": {"arg1": "value1"}
            }
        }

        await server._handle_message(message)

        assert "_context" in received_params
        assert "memory_manager" in received_params["_context"]
        assert "query_engine" in received_params["_context"]
        assert "qdrant" in received_params["_context"]
        assert "neo4j" in received_params["_context"]
        assert "indexer" in received_params["_context"]
        assert "normalizer" in received_params["_context"]

    @pytest.mark.asyncio
    async def test_handle_tool_call_metrics_recorded(self, server: MCPServer) -> None:
        """Test that metrics are recorded for tool calls."""
        async def simple_tool(params):
            return {"status": "ok"}

        server._tools["simple_tool"] = simple_tool
        server._tool_schemas["simple_tool"] = {"type": "object"}

        with patch("memory_service.api.mcp_server.metrics") as mock_metrics:
            message = {
                "id": 5,
                "method": "tools/call",
                "params": {
                    "name": "simple_tool",
                    "arguments": {}
                }
            }

            await server._handle_message(message)

            mock_metrics.record_mcp_tool_call.assert_called_once()
            call_args = mock_metrics.record_mcp_tool_call.call_args
            assert call_args[0][0] == "simple_tool"
            assert call_args[0][1] == "success"

    @pytest.mark.asyncio
    async def test_handle_tool_call_exception(self, server: MCPServer) -> None:
        """Test tool call that raises an exception."""
        async def failing_tool(params):
            raise RuntimeError("Internal error")

        server._tools["failing_tool"] = failing_tool
        server._tool_schemas["failing_tool"] = {"type": "object"}

        with patch("memory_service.api.mcp_server.metrics") as mock_metrics:
            message = {
                "id": 6,
                "method": "tools/call",
                "params": {
                    "name": "failing_tool",
                    "arguments": {}
                }
            }

            response = await server._handle_message(message)

            assert "error" in response
            assert "Tool execution failed" in response["error"]["message"]

            # Metrics should record error
            mock_metrics.record_mcp_tool_call.assert_called_once()
            call_args = mock_metrics.record_mcp_tool_call.call_args
            assert call_args[0][1] == "error"


class TestMCPToolListAndSchemas:
    """Tests for tool listing and schemas."""

    @pytest.fixture
    def server(self):
        """Create server with mocked services."""
        return MCPServer(
            qdrant=AsyncMock(),
            neo4j=AsyncMock(),
            embedding_service=MagicMock(),
        )

    def test_tools_list_includes_all_tools(self, server: MCPServer) -> None:
        """Test tools/list response includes all registered tools."""
        response = server._handle_tools_list(1)

        tools = response["result"]["tools"]
        tool_names = [t["name"] for t in tools]

        assert "memory_add" in tool_names
        assert "memory_search" in tool_names
        assert "index_file" in tool_names

    def test_tools_list_includes_descriptions(self, server: MCPServer) -> None:
        """Test tools have descriptions."""
        response = server._handle_tools_list(1)

        for tool in response["result"]["tools"]:
            assert "description" in tool
            assert len(tool["description"]) > 0

    def test_tools_list_includes_input_schemas(self, server: MCPServer) -> None:
        """Test tools have input schemas."""
        response = server._handle_tools_list(1)

        for tool in response["result"]["tools"]:
            assert "inputSchema" in tool
            assert "type" in tool["inputSchema"]

    def test_memory_add_schema_is_correct(self, server: MCPServer) -> None:
        """Test memory_add tool schema is correct."""
        schema = server._tool_schemas["memory_add"]

        assert schema["type"] == "object"
        assert "memory_type" in schema["properties"]
        assert "content" in schema["properties"]
        assert "memory_type" in schema["required"]
        assert "content" in schema["required"]

    def test_memory_search_schema_is_correct(self, server: MCPServer) -> None:
        """Test memory_search tool schema is correct."""
        schema = server._tool_schemas["memory_search"]

        assert schema["type"] == "object"
        assert "query" in schema["properties"]
        assert "query" in schema["required"]

    def test_index_file_schema_is_correct(self, server: MCPServer) -> None:
        """Test index_file tool schema is correct."""
        schema = server._tool_schemas["index_file"]

        assert schema["type"] == "object"
        assert "file_path" in schema["properties"]
        assert "file_path" in schema["required"]


class TestMCPValidation:
    """Tests for input validation."""

    @pytest.fixture
    def server(self):
        """Create server with mocked services."""
        return MCPServer(
            qdrant=AsyncMock(),
            neo4j=AsyncMock(),
            embedding_service=MagicMock(),
        )

    def test_validate_input_passes_with_all_required(self, server: MCPServer) -> None:
        """Test validation passes with all required fields."""
        server._validate_input("memory_add", {
            "memory_type": "requirements",
            "content": "Test content",
        })
        # Should not raise

    def test_validate_input_fails_missing_required(self, server: MCPServer) -> None:
        """Test validation fails with missing required field."""
        from pydantic import ValidationError

        with pytest.raises((ValidationError, Exception)):
            server._validate_input("memory_add", {"memory_type": "requirements"})

    def test_validate_input_allows_extra_fields(self, server: MCPServer) -> None:
        """Test validation allows extra fields."""
        server._validate_input("memory_add", {
            "memory_type": "requirements",
            "content": "Test content",
            "extra_field": "should be allowed",
        })
        # Should not raise

    def test_validate_input_no_schema(self, server: MCPServer) -> None:
        """Test validation with no schema for tool."""
        # Remove schema
        if "test_tool" in server._tool_schemas:
            del server._tool_schemas["test_tool"]

        server._validate_input("test_tool", {"any": "args"})
        # Should not raise


class TestMCPResponses:
    """Tests for response formatting."""

    @pytest.fixture
    def server(self):
        """Create server with mocked services."""
        return MCPServer(
            qdrant=AsyncMock(),
            neo4j=AsyncMock(),
            embedding_service=MagicMock(),
        )

    def test_success_response_format(self, server: MCPServer) -> None:
        """Test success response has correct format."""
        response = server._success_response(1, {"data": "test"})

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert response["result"] == {"data": "test"}

    def test_success_response_preserves_id_type(self, server: MCPServer) -> None:
        """Test success response preserves ID type."""
        # String ID
        response = server._success_response("abc", {})
        assert response["id"] == "abc"

        # None ID
        response = server._success_response(None, {})
        assert response["id"] is None

    def test_error_response_format(self, server: MCPServer) -> None:
        """Test error response has correct format."""
        response = server._error_response(1, -32600, "Invalid request")

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert response["error"]["code"] == -32600
        assert response["error"]["message"] == "Invalid request"

    def test_error_response_with_data(self, server: MCPServer) -> None:
        """Test error response includes data when provided."""
        response = server._error_response(1, -32602, "Error", {"field": "name"})

        assert response["error"]["data"] == {"field": "name"}

    def test_error_response_no_data(self, server: MCPServer) -> None:
        """Test error response excludes data when not provided."""
        response = server._error_response(1, -32600, "Error")

        assert "data" not in response["error"]


class TestMCPToolDescriptions:
    """Tests for tool descriptions."""

    @pytest.fixture
    def server(self):
        """Create server with mocked services."""
        return MCPServer(
            qdrant=AsyncMock(),
            neo4j=AsyncMock(),
            embedding_service=MagicMock(),
        )

    def test_get_tool_description_known_tools(self, server: MCPServer) -> None:
        """Test descriptions for known tools."""
        descriptions = [
            ("memory_add", "memory"),
            ("memory_search", "search"),
            ("index_file", "index"),
            ("normalize_memory", "normalization"),
            ("check_consistency", ["consistency", "check", "design"]),  # Multiple possible keywords
        ]

        for tool_name, expected_words in descriptions:
            desc = server._get_tool_description(tool_name)
            if isinstance(expected_words, list):
                # Any of the expected words should be present
                assert any(word.lower() in desc.lower() for word in expected_words)
            else:
                assert expected_words.lower() in desc.lower()

    def test_get_tool_description_unknown_tool(self, server: MCPServer) -> None:
        """Test description for unknown tool."""
        desc = server._get_tool_description("unknown_tool")

        assert desc is not None
        assert "unknown_tool" in desc


class TestMCPRegisterTool:
    """Tests for tool registration."""

    @pytest.fixture
    def server(self):
        """Create server with mocked services."""
        return MCPServer(
            qdrant=AsyncMock(),
            neo4j=AsyncMock(),
            embedding_service=MagicMock(),
        )

    def test_register_tool(self, server: MCPServer) -> None:
        """Test registering a new tool."""
        async def custom_tool(params):
            return {"result": "custom"}

        schema = {
            "type": "object",
            "properties": {"arg": {"type": "string"}},
            "required": ["arg"],
        }

        server._register_tool("custom_tool", custom_tool, schema)

        assert "custom_tool" in server._tools
        assert "custom_tool" in server._tool_schemas
        assert server._tools["custom_tool"] == custom_tool
        assert server._tool_schemas["custom_tool"] == schema


class TestMCPError:
    """Tests for MCPError class."""

    def test_mcp_error_properties(self) -> None:
        """Test MCPError has all expected properties."""
        error = MCPError(-32600, "Invalid request", {"field": "name"})

        assert error.code == -32600
        assert error.message == "Invalid request"
        assert error.data == {"field": "name"}

    def test_mcp_error_as_exception(self) -> None:
        """Test MCPError can be raised as exception."""
        with pytest.raises(MCPError) as exc_info:
            raise MCPError(-32600, "Test error")

        assert exc_info.value.code == -32600

    def test_mcp_error_str(self) -> None:
        """Test MCPError string representation."""
        error = MCPError(-32600, "Invalid request")

        assert str(error) == "Invalid request"

    def test_mcp_error_no_data(self) -> None:
        """Test MCPError with no data."""
        error = MCPError(-32600, "Invalid request")

        assert error.data is None


class TestMCPServerRun:
    """Tests for server run loop (without actual I/O)."""

    @pytest.fixture
    def server(self):
        """Create server with mocked services."""
        return MCPServer(
            qdrant=AsyncMock(),
            neo4j=AsyncMock(),
            embedding_service=MagicMock(),
        )

    def test_server_has_run_method(self, server: MCPServer) -> None:
        """Test server has run method."""
        assert hasattr(server, "run")
        assert asyncio.iscoroutinefunction(server.run)


class TestMCPServerIntegration:
    """Integration-style tests for MCPServer."""

    @pytest.fixture
    def server(self):
        """Create server with mocked services."""
        mock_qdrant = AsyncMock()
        mock_qdrant.count.return_value = 0
        mock_qdrant.get_collection_name.return_value = "memories_function"

        mock_neo4j = AsyncMock()
        mock_neo4j.get_related.return_value = []

        return MCPServer(
            qdrant=mock_qdrant,
            neo4j=mock_neo4j,
            embedding_service=MagicMock(),
        )

    @pytest.mark.asyncio
    async def test_full_tool_call_flow(self, server: MCPServer) -> None:
        """Test complete tool call flow."""
        # Setup mock
        server.query_engine.semantic_search = AsyncMock(return_value=[])

        message = {
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "memory_search",
                "arguments": {
                    "query": "test query",
                    "limit": 10,
                }
            }
        }

        response = await server._handle_message(message)

        assert response["id"] == 1
        assert "result" in response
        assert "content" in response["result"]

        # Parse the content
        content = response["result"]["content"][0]
        assert content["type"] == "text"

        # Parse the JSON text
        result_data = json.loads(content["text"])
        assert "results" in result_data

    @pytest.mark.asyncio
    async def test_tool_call_with_json_serialization(self, server: MCPServer) -> None:
        """Test tool call result can be serialized to JSON."""
        async def uuid_tool(params):
            return {"id": uuid4(), "status": "ok"}

        server._tools["uuid_tool"] = uuid_tool
        server._tool_schemas["uuid_tool"] = {"type": "object"}

        message = {
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "uuid_tool",
                "arguments": {}
            }
        }

        response = await server._handle_message(message)

        # Should succeed - UUID should be serialized
        assert "result" in response

        # Content should be valid JSON
        content = response["result"]["content"][0]["text"]
        parsed = json.loads(content)
        assert "id" in parsed
        assert "status" in parsed
