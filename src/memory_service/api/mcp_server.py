"""MCP (Model Context Protocol) server implementation."""

import asyncio
import json
import sys
from collections.abc import Callable, Coroutine
from typing import Any

from pydantic import ValidationError

from memory_service.core.memory_manager import MemoryManager
from memory_service.core.query_engine import QueryEngine
from memory_service.core.workers import IndexerWorker, JobManager, NormalizerWorker
from memory_service.embedding.service import EmbeddingService
from memory_service.storage.neo4j_adapter import Neo4jAdapter
from memory_service.storage.qdrant_adapter import QdrantAdapter
from memory_service.utils.logging import get_logger
from memory_service.utils.metrics import get_metrics

logger = get_logger(__name__)
metrics = get_metrics()

# Tool handler type
ToolHandler = Callable[[dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]


class MCPError(Exception):
    """MCP protocol error."""

    def __init__(self, code: int, message: str, data: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


class MCPServer:
    """MCP server using stdio transport.

    Implements the Model Context Protocol for Claude Code integration,
    providing tools for memory management, search, indexing, and analysis.
    """

    def __init__(
        self,
        qdrant: QdrantAdapter,
        neo4j: Neo4jAdapter,
        embedding_service: EmbeddingService,
    ) -> None:
        """Initialize MCP server.

        Args:
            qdrant: Qdrant adapter
            neo4j: Neo4j adapter
            embedding_service: Embedding service
        """
        self.qdrant = qdrant
        self.neo4j = neo4j
        self.embedding_service = embedding_service
        self._current_project_id = qdrant.project_id

        # Initialize core services
        self.memory_manager = MemoryManager(
            qdrant=qdrant,
            neo4j=neo4j,
            embedding_service=embedding_service,
        )
        self.query_engine = QueryEngine(
            qdrant=qdrant,
            neo4j=neo4j,
            embedding_service=embedding_service,
        )

        # Initialize job manager, indexer, and normalizer
        self.job_manager = JobManager()
        self.indexer = IndexerWorker(
            qdrant=qdrant,
            neo4j=neo4j,
            job_manager=self.job_manager,
        )
        self.normalizer = NormalizerWorker(
            qdrant=qdrant,
            neo4j=neo4j,
            job_manager=self.job_manager,
        )

        # Tool registry
        self._tools: dict[str, ToolHandler] = {}
        self._tool_schemas: dict[str, dict[str, Any]] = {}

        # Register built-in tools
        self._register_tools()

        logger.info("mcp_server_initialized")

    def _register_tools(self) -> None:
        """Register all MCP tools."""
        from memory_service.api.tools.memory_crud import (
            memory_add,
            memory_bulk_add,
            memory_delete,
            memory_get,
            memory_update,
        )
        from memory_service.api.tools.search import (
            code_search,
            find_duplicates,
            get_related,
            graph_query,
            memory_search,
        )

        # Memory CRUD tools
        self._register_tool(
            "memory_add",
            memory_add,
            {
                "type": "object",
                "properties": {
                    "memory_type": {"type": "string", "enum": ["requirements", "design", "code_pattern", "component", "function", "test_history", "session", "user_preference"]},
                    "content": {"type": "string", "description": "Primary content for embedding"},
                    "metadata": {"type": "object", "description": "Type-specific metadata"},
                    "relationships": {"type": "array", "items": {"type": "object"}, "description": "Relationships to create"},
                },
                "required": ["memory_type", "content"],
            },
        )

        self._register_tool(
            "memory_update",
            memory_update,
            {
                "type": "object",
                "properties": {
                    "memory_id": {"type": "string", "format": "uuid"},
                    "memory_type": {"type": "string"},
                    "content": {"type": "string"},
                    "metadata": {"type": "object"},
                },
                "required": ["memory_id", "memory_type"],
            },
        )

        self._register_tool(
            "memory_delete",
            memory_delete,
            {
                "type": "object",
                "properties": {
                    "memory_id": {"type": "string", "format": "uuid"},
                    "memory_type": {"type": "string"},
                    "hard_delete": {"type": "boolean", "default": False},
                },
                "required": ["memory_id", "memory_type"],
            },
        )

        self._register_tool(
            "memory_get",
            memory_get,
            {
                "type": "object",
                "properties": {
                    "memory_id": {"type": "string", "format": "uuid"},
                    "memory_type": {"type": "string"},
                    "include_relationships": {"type": "boolean", "default": False},
                },
                "required": ["memory_id", "memory_type"],
            },
        )

        self._register_tool(
            "memory_bulk_add",
            memory_bulk_add,
            {
                "type": "object",
                "properties": {
                    "memories": {"type": "array", "items": {"type": "object"}},
                },
                "required": ["memories"],
            },
        )

        # Search tools
        self._register_tool(
            "memory_search",
            memory_search,
            {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query text"},
                    "memory_types": {"type": "array", "items": {"type": "string"}},
                    "time_range": {"type": "object", "properties": {"start": {"type": "string"}, "end": {"type": "string"}}},
                    "limit": {"type": "integer", "default": 10, "maximum": 100},
                },
                "required": ["query"],
            },
        )

        self._register_tool(
            "code_search",
            code_search,
            {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Code snippet or description"},
                    "language": {"type": "string"},
                    "limit": {"type": "integer", "default": 10},
                },
                "required": ["query"],
            },
        )

        self._register_tool(
            "graph_query",
            graph_query,
            {
                "type": "object",
                "properties": {
                    "cypher": {"type": "string", "description": "Cypher query (read-only)"},
                    "parameters": {"type": "object"},
                },
                "required": ["cypher"],
            },
        )

        self._register_tool(
            "find_duplicates",
            find_duplicates,
            {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Code to check for duplicates"},
                    "language": {"type": "string"},
                    "threshold": {"type": "number", "default": 0.85, "minimum": 0.7, "maximum": 0.95},
                },
                "required": ["code"],
            },
        )

        self._register_tool(
            "get_related",
            get_related,
            {
                "type": "object",
                "properties": {
                    "entity_id": {"type": "string", "format": "uuid"},
                    "relationship_types": {"type": "array", "items": {"type": "string"}},
                    "direction": {"type": "string", "enum": ["outgoing", "incoming", "both"], "default": "both"},
                    "depth": {"type": "integer", "default": 1, "maximum": 5},
                },
                "required": ["entity_id"],
            },
        )

        # Indexing tools
        from memory_service.api.tools.indexing import (
            index_directory,
            index_file,
            index_status,
            reindex,
        )

        self._register_tool(
            "index_file",
            index_file,
            {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to file to index"},
                    "force": {"type": "boolean", "default": False, "description": "Force re-index even if unchanged"},
                },
                "required": ["file_path"],
            },
        )

        self._register_tool(
            "index_directory",
            index_directory,
            {
                "type": "object",
                "properties": {
                    "directory_path": {"type": "string", "description": "Path to directory to index"},
                    "extensions": {"type": "array", "items": {"type": "string"}, "description": "File extensions to include"},
                    "exclude": {"type": "array", "items": {"type": "string"}, "description": "Patterns to exclude"},
                    "force": {"type": "boolean", "default": False, "description": "Force re-index all files"},
                },
                "required": ["directory_path"],
            },
        )

        self._register_tool(
            "index_status",
            index_status,
            {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Job ID to check (optional)"},
                },
            },
        )

        self._register_tool(
            "reindex",
            reindex,
            {
                "type": "object",
                "properties": {
                    "directory_path": {"type": "string", "description": "Directory to reindex"},
                    "scope": {"type": "string", "enum": ["full", "changed"], "default": "changed"},
                    "extensions": {"type": "array", "items": {"type": "string"}},
                    "exclude": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["directory_path"],
            },
        )

        # Maintenance tools
        from memory_service.api.tools.maintenance import (
            export_memory,
            import_memory,
            memory_statistics,
            normalize_memory,
            normalize_status,
        )

        self._register_tool(
            "normalize_memory",
            normalize_memory,
            {
                "type": "object",
                "properties": {
                    "phases": {"type": "array", "items": {"type": "string"}, "description": "Specific phases to run"},
                    "dry_run": {"type": "boolean", "default": False, "description": "Report changes without applying"},
                },
            },
        )

        self._register_tool(
            "normalize_status",
            normalize_status,
            {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Job ID to check (optional)"},
                },
            },
        )

        self._register_tool(
            "memory_statistics",
            memory_statistics,
            {
                "type": "object",
                "properties": {},
            },
        )

        self._register_tool(
            "export_memory",
            export_memory,
            {
                "type": "object",
                "properties": {
                    "memory_types": {"type": "array", "items": {"type": "string"}, "description": "Types to export"},
                    "filters": {"type": "object", "description": "Additional filters"},
                    "output_path": {"type": "string", "description": "Path to write JSONL export"},
                },
            },
        )

        self._register_tool(
            "import_memory",
            import_memory,
            {
                "type": "object",
                "properties": {
                    "input_path": {"type": "string", "description": "Path to JSONL file"},
                    "data": {"type": "string", "description": "JSONL data as string"},
                    "conflict_resolution": {"type": "string", "enum": ["skip", "overwrite", "error"], "default": "skip"},
                },
            },
        )

        # Analysis tools
        from memory_service.api.tools.analysis import (
            check_consistency,
            get_design_context,
            trace_requirements,
            validate_fix,
        )

        self._register_tool(
            "check_consistency",
            check_consistency,
            {
                "type": "object",
                "properties": {
                    "component_id": {"type": "string", "description": "Component ID to check"},
                    "code_snippet": {"type": "string", "description": "Code to validate against design"},
                },
                "required": ["component_id"],
            },
        )

        self._register_tool(
            "validate_fix",
            validate_fix,
            {
                "type": "object",
                "properties": {
                    "fix_description": {"type": "string", "description": "Description of the proposed fix"},
                    "affected_component": {"type": "string", "description": "Component ID being fixed"},
                    "related_requirements": {"type": "array", "items": {"type": "string"}, "description": "Requirement IDs"},
                },
                "required": ["fix_description"],
            },
        )

        self._register_tool(
            "get_design_context",
            get_design_context,
            {
                "type": "object",
                "properties": {
                    "component_id": {"type": "string", "description": "Component ID"},
                    "query": {"type": "string", "description": "Context query"},
                    "include_patterns": {"type": "boolean", "default": True},
                    "include_requirements": {"type": "boolean", "default": True},
                },
            },
        )

        self._register_tool(
            "trace_requirements",
            trace_requirements,
            {
                "type": "object",
                "properties": {
                    "requirement_id": {"type": "string", "description": "Requirement ID to trace"},
                    "direction": {"type": "string", "enum": ["upstream", "downstream", "both"], "default": "both"},
                },
                "required": ["requirement_id"],
            },
        )

        # Note: set_project and get_project tools removed per REQ-MEM-002-FN-034
        # Project ID is now immutable, set via --project-id CLI argument at server startup.
        # To switch projects, restart the server with a different --project-id.

    def _register_tool(
        self,
        name: str,
        handler: ToolHandler,
        schema: dict[str, Any],
    ) -> None:
        """Register a tool with its handler and schema.

        Args:
            name: Tool name
            handler: Async handler function
            schema: JSON Schema for input validation
        """
        self._tools[name] = handler
        self._tool_schemas[name] = schema
        logger.debug("tool_registered", name=name)

    async def run(self) -> None:
        """Run the MCP server using stdio transport."""
        logger.info("mcp_server_starting")

        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)

        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)
        writer_transport, writer_protocol = await asyncio.get_event_loop().connect_write_pipe(
            asyncio.streams.FlowControlMixin, sys.stdout
        )
        writer = asyncio.StreamWriter(writer_transport, writer_protocol, reader, asyncio.get_event_loop())

        try:
            while True:
                # Read JSON-RPC message
                line = await reader.readline()
                if not line:
                    break

                try:
                    message = json.loads(line.decode())
                    response = await self._handle_message(message)

                    if response:
                        writer.write((json.dumps(response) + "\n").encode())
                        await writer.drain()

                except json.JSONDecodeError as e:
                    error_response = self._error_response(None, -32700, f"Parse error: {e}")
                    writer.write((json.dumps(error_response) + "\n").encode())
                    await writer.drain()

        except asyncio.CancelledError:
            logger.info("mcp_server_cancelled")
        finally:
            writer.close()
            logger.info("mcp_server_stopped")

    async def _handle_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        """Handle an incoming JSON-RPC message.

        Args:
            message: JSON-RPC message

        Returns:
            Response message or None for notifications
        """
        msg_id = message.get("id")
        method = message.get("method", "")
        params = message.get("params", {})

        try:
            if method == "initialize":
                return self._handle_initialize(msg_id, params)

            elif method == "tools/list":
                return self._handle_tools_list(msg_id)

            elif method == "tools/call":
                return await self._handle_tool_call(msg_id, params)

            elif method == "shutdown":
                return self._success_response(msg_id, {"status": "ok"})

            else:
                return self._error_response(msg_id, -32601, f"Method not found: {method}")

        except MCPError as e:
            return self._error_response(msg_id, e.code, e.message, e.data)
        except Exception as e:
            logger.error("mcp_handler_error", method=method, error=str(e))
            return self._error_response(msg_id, -32603, f"Internal error: {e}")

    def _handle_initialize(self, msg_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """Handle initialize request.

        Args:
            msg_id: Message ID
            params: Initialize parameters

        Returns:
            Initialize response with project_id
        """
        return self._success_response(
            msg_id,
            {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": "claude-memory-mcp",
                    "version": "0.2.0",
                    "project_id": self._current_project_id,
                },
                "capabilities": {
                    "tools": {"listChanged": False},
                },
            },
        )

    def _handle_tools_list(self, msg_id: Any) -> dict[str, Any]:
        """Handle tools/list request.

        Args:
            msg_id: Message ID

        Returns:
            Tools list response
        """
        tools = []
        for name, schema in self._tool_schemas.items():
            tools.append({
                "name": name,
                "description": self._get_tool_description(name),
                "inputSchema": schema,
            })

        return self._success_response(msg_id, {"tools": tools})

    async def _handle_tool_call(self, msg_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """Handle tools/call request.

        Args:
            msg_id: Message ID
            params: Tool call parameters

        Returns:
            Tool call response
        """
        import time

        start = time.perf_counter()
        tool_name = params.get("name", "")
        tool_args = params.get("arguments", {})

        if tool_name not in self._tools:
            raise MCPError(-32602, f"Unknown tool: {tool_name}")

        # Validate input against schema
        try:
            self._validate_input(tool_name, tool_args)
        except ValidationError as e:
            raise MCPError(-32602, f"Invalid parameters: {e}") from e

        # Execute tool
        handler = self._tools[tool_name]

        # Inject services into context
        context = {
            "memory_manager": self.memory_manager,
            "query_engine": self.query_engine,
            "qdrant": self.qdrant,
            "neo4j": self.neo4j,
            "embedding_service": self.embedding_service,
            "indexer": self.indexer,
            "normalizer": self.normalizer,
            "job_manager": self.job_manager,
        }

        try:
            result = await handler({**tool_args, "_context": context})

            duration = time.perf_counter() - start
            metrics.record_mcp_tool_call(tool_name, "success", duration)

            return self._success_response(
                msg_id,
                {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, default=str),
                        }
                    ],
                },
            )

        except Exception as e:
            duration = time.perf_counter() - start
            metrics.record_mcp_tool_call(tool_name, "error", duration)

            logger.error("tool_call_failed", tool=tool_name, error=str(e))
            raise MCPError(-32603, f"Tool execution failed: {e}") from e

    def _validate_input(self, tool_name: str, args: dict[str, Any]) -> None:
        """Validate tool input against schema.

        Args:
            tool_name: Tool name
            args: Input arguments

        Raises:
            ValidationError: If validation fails
        """
        schema = self._tool_schemas.get(tool_name, {})
        required = schema.get("required", [])

        for field in required:
            if field not in args:
                raise ValidationError(f"Missing required field: {field}")

    def _get_tool_description(self, name: str) -> str:
        """Get description for a tool.

        Args:
            name: Tool name

        Returns:
            Tool description
        """
        descriptions = {
            # Memory CRUD
            "memory_add": "Add a new memory to the system",
            "memory_update": "Update an existing memory",
            "memory_delete": "Delete a memory (soft delete by default)",
            "memory_get": "Retrieve a memory by ID",
            "memory_bulk_add": "Add multiple memories in batch",
            # Search
            "memory_search": "Search memories using semantic similarity",
            "code_search": "Search for similar code patterns",
            "graph_query": "Execute a Cypher graph query",
            "find_duplicates": "Find duplicate functions/code",
            "get_related": "Get entities related by graph relationships",
            # Indexing
            "index_file": "Index a single source file",
            "index_directory": "Index all source files in a directory",
            "index_status": "Get indexing job status or statistics",
            "reindex": "Trigger reindexing of the codebase",
            # Maintenance
            "normalize_memory": "Run memory normalization (deduplication, cleanup, etc.)",
            "normalize_status": "Get normalization job status",
            "memory_statistics": "Get comprehensive memory system statistics",
            "export_memory": "Export memories to JSONL format",
            "import_memory": "Import memories from JSONL format",
            # Analysis
            "check_consistency": "Check if code is consistent with design",
            "validate_fix": "Validate a proposed fix against design patterns",
            "get_design_context": "Get design context for a component",
            "trace_requirements": "Trace requirement to implementations",
        }
        return descriptions.get(name, f"Execute {name} tool")

    def _success_response(self, msg_id: Any, result: Any) -> dict[str, Any]:
        """Create a success response.

        Args:
            msg_id: Message ID
            result: Result data

        Returns:
            JSON-RPC response
        """
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": result,
        }

    def _error_response(
        self,
        msg_id: Any,
        code: int,
        message: str,
        data: Any = None,
    ) -> dict[str, Any]:
        """Create an error response.

        Args:
            msg_id: Message ID
            code: Error code
            message: Error message
            data: Additional error data

        Returns:
            JSON-RPC error response
        """
        error: dict[str, Any] = {
            "code": code,
            "message": message,
        }
        if data:
            error["data"] = data

        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": error,
        }
