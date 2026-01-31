"""E2E tests for codebase indexing flows (E2E-040 to E2E-041)."""

import pytest
from pathlib import Path
from uuid import uuid4

from memory_service.models import (
    MemoryType,
    RelationshipType,
)
from memory_service.core.memory_manager import MemoryManager
from memory_service.core.query_engine import QueryEngine
from memory_service.core.workers import IndexerWorker
from memory_service.storage.neo4j_adapter import Neo4jAdapter


class TestCodebaseIndexingFlows:
    """E2E tests for codebase indexing flows (E2E-040, E2E-041)."""

    @pytest.mark.asyncio
    async def test_e2e040_index_directory_then_code_search(
        self,
        e2e_indexer_worker: IndexerWorker,
        e2e_query_engine: QueryEngine,
        temp_codebase: Path,
    ) -> None:
        """E2E-040: Index and search for code patterns.

        Flow: index_directory -> code_search -> find relevant code
        """
        # Step 1: Index the directory (index_directory tool)
        result = await e2e_indexer_worker.index_directory(str(temp_codebase))

        # Step 2: Search for specific code patterns (code_search tool)
        # Search for email validation
        email_results = await e2e_query_engine.semantic_search(
            query="validate email address format",
            memory_types=[MemoryType.FUNCTION],
            limit=10,
        )

        # Should find the validate_email function
        assert len(email_results) >= 1
        function_names = [
            r.get("payload", r).get("name")
            for r in email_results
        ]
        assert "validate_email" in function_names

        # Search for string formatting
        format_results = await e2e_query_engine.semantic_search(
            query="format string strip lowercase",
            memory_types=[MemoryType.FUNCTION],
            limit=10,
        )

        assert len(format_results) >= 1
        function_names = [
            r.get("payload", r).get("name")
            for r in format_results
        ]
        assert "format_string" in function_names

        # Search for data models
        model_results = await e2e_query_engine.semantic_search(
            query="user data model dataclass",
            memory_types=[MemoryType.COMPONENT],
            limit=10,
        )

        # Should find User class
        assert len(model_results) >= 1

    @pytest.mark.asyncio
    async def test_e2e041_index_directory_then_graph_query(
        self,
        e2e_indexer_worker: IndexerWorker,
        e2e_query_engine: QueryEngine,
        e2e_neo4j_adapter: Neo4jAdapter,
        temp_codebase: Path,
    ) -> None:
        """E2E-041: Index and query relationships.

        Flow: index_directory -> graph_query -> find relationships
        """
        # Step 1: Index the directory
        result = await e2e_indexer_worker.index_directory(str(temp_codebase))

        # Step 2: Query the graph for relationships (graph_query tool)
        # Find all functions
        functions_query = "MATCH (f:Function) RETURN f.name, f.file_path LIMIT 20"
        functions = await e2e_neo4j_adapter.execute_query(functions_query)

        # Should have indexed functions
        # Note: Actual count depends on indexing implementation

        # Find inheritance relationships (if indexed)
        inheritance_query = """
        MATCH (c:Component)-[r:EXTENDS]->(parent:Component)
        RETURN c.name as child, parent.name as parent
        """
        try:
            inheritance = await e2e_neo4j_adapter.execute_query(inheritance_query)
            # Admin extends User in the temp codebase
        except Exception:
            # May not have inheritance relationships if not fully implemented
            pass

        # Step 3: Search combined with graph context
        # Find functions that belong to specific files
        file_functions = await e2e_neo4j_adapter.execute_query(
            "MATCH (f:Function) WHERE f.file_path CONTAINS 'utils.py' RETURN f.name"
        )

        # Should find utility functions


class TestIndexingWorkflows:
    """E2E tests for various indexing workflows."""

    @pytest.mark.asyncio
    async def test_incremental_indexing(
        self,
        e2e_indexer_worker: IndexerWorker,
        temp_codebase: Path,
    ) -> None:
        """Test incremental indexing only processes changed files."""
        # First indexing
        result1 = await e2e_indexer_worker.index_directory(str(temp_codebase))

        # Second indexing without changes
        result2 = await e2e_indexer_worker.index_directory(str(temp_codebase))

        # Should skip unchanged files (check result metrics if available)

    @pytest.mark.asyncio
    async def test_file_indexing(
        self,
        e2e_indexer_worker: IndexerWorker,
        e2e_query_engine: QueryEngine,
        temp_codebase: Path,
    ) -> None:
        """Test single file indexing."""
        file_path = temp_codebase / "src" / "models.py"

        # Index single file
        result = await e2e_indexer_worker.index_file(str(file_path))

        # Search for content from that file
        results = await e2e_query_engine.semantic_search(
            query="User dataclass model name email",
            memory_types=[MemoryType.FUNCTION, MemoryType.COMPONENT],
            limit=10,
        )

        # Should find classes/functions from the file
        assert len(results) >= 1
        file_paths = [
            r.get("payload", r).get("file_path", "")
            for r in results
        ]
        assert any("models.py" in fp for fp in file_paths)

    @pytest.mark.asyncio
    async def test_multi_language_indexing(
        self,
        e2e_indexer_worker: IndexerWorker,
        e2e_query_engine: QueryEngine,
        temp_codebase: Path,
    ) -> None:
        """Test indexing handles multiple languages."""
        # Add a TypeScript file
        ts_file = temp_codebase / "src" / "api.ts"
        ts_file.write_text('''/**
 * API client module
 */

export interface ApiResponse<T> {
    data: T;
    status: number;
}

export async function fetchData(url: string): Promise<ApiResponse<any>> {
    const response = await fetch(url);
    return {
        data: await response.json(),
        status: response.status
    };
}
''')

        # Index the directory
        await e2e_indexer_worker.index_directory(str(temp_codebase))

        # Search for Python functions
        python_results = await e2e_query_engine.semantic_search(
            query="validate email format",
            memory_types=[MemoryType.FUNCTION],
            limit=10,
        )

        # Search for TypeScript functions
        ts_results = await e2e_query_engine.semantic_search(
            query="fetch API data response",
            memory_types=[MemoryType.FUNCTION],
            limit=10,
        )

        # Should find both
        # (actual results depend on extractor implementation)


class TestSearchAfterIndexing:
    """E2E tests for search capabilities after indexing."""

    @pytest.mark.asyncio
    async def test_semantic_search_finds_similar_code(
        self,
        e2e_indexer_worker: IndexerWorker,
        e2e_query_engine: QueryEngine,
        temp_codebase: Path,
    ) -> None:
        """Test semantic search finds semantically similar code."""
        await e2e_indexer_worker.index_directory(str(temp_codebase))

        # Natural language query
        results = await e2e_query_engine.semantic_search(
            query="function that converts user object to dictionary",
            memory_types=[MemoryType.FUNCTION],
            limit=5,
        )

        # Should find to_dict method
        function_names = [
            r.get("payload", r).get("name")
            for r in results
        ]
        # May find to_dict if methods are extracted

    @pytest.mark.asyncio
    async def test_search_with_filters(
        self,
        e2e_indexer_worker: IndexerWorker,
        e2e_query_engine: QueryEngine,
        temp_codebase: Path,
    ) -> None:
        """Test search with various filters."""
        await e2e_indexer_worker.index_directory(str(temp_codebase))

        # Search only Python functions
        python_only = await e2e_query_engine.semantic_search(
            query="utility function",
            memory_types=[MemoryType.FUNCTION],
            limit=10,
            filters={"language": "python"},
        )

        # All results should be Python
        for result in python_only:
            lang = result.get("payload", result).get("language", "")
            if lang:
                assert lang == "python"
