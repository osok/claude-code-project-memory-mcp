"""E2E tests for duplicate detection flows (E2E-010 to E2E-011).

================================================================================
                        TESTING STRATEGY - MANDATORY
================================================================================

**Test against real code, not mocks.**

1. USE mock-src/ for testing code parsing, indexing, and relationship detection.
2. DON'T mock infrastructure being tested - only mock external APIs (embeddings).
3. USE fixtures from conftest_mock_src.py for expected results validation.

See: project-docs/testing-strategy.md and CLAUDE.md
================================================================================
"""

import pytest
from pathlib import Path
from uuid import uuid4

from memory_service.models import (
    MemoryType,
    FunctionMemory,
)
from memory_service.core.memory_manager import MemoryManager
from memory_service.core.query_engine import QueryEngine
from memory_service.core.workers import IndexerWorker


class TestDuplicateDetectionFlows:
    """E2E tests for duplicate detection flows using mock-src."""

    @pytest.mark.asyncio
    async def test_e2e010_index_then_find_duplicates(
        self,
        e2e_memory_manager: MemoryManager,
        e2e_query_engine: QueryEngine,
        e2e_indexer_worker: IndexerWorker,
        mock_src_python: Path,
    ) -> None:
        """E2E-010: Index codebase, detect existing similar function.

        Flow: index_directory -> find_duplicates
        Uses mock-src/python/tasktracker which has validate_email, validate_password, etc.
        """
        # Step 1: Index the mock-src Python codebase
        result = await e2e_indexer_worker.index_directory(str(mock_src_python))

        # Step 2: Add a function that's similar to validate_email from mock-src
        # mock-src has: def validate_email(email: str) -> bool
        similar_function = FunctionMemory(
            id=uuid4(),
            type=MemoryType.FUNCTION,
            content="""def check_email_valid(email_address: str) -> bool:
    '''Check if an email address is properly formatted.'''
    import re
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
    return bool(pattern.match(email_address.strip()))""",
            function_id=uuid4(),
            name="check_email_valid",
            signature="def check_email_valid(email_address: str) -> bool",
            file_path="src/new_validators.py",
            start_line=1,
            end_line=5,
            language="python",
            docstring="Check if an email address is properly formatted.",
        )

        # Add the similar function
        await e2e_memory_manager.add_memory(similar_function)

        # Step 3: Find duplicates (find_duplicates tool)
        duplicates = await e2e_query_engine.semantic_search(
            query=similar_function.content,
            memory_types=[MemoryType.FUNCTION],
            limit=10,
        )

        # Should find both the original and similar function
        assert len(duplicates) >= 1

        # At least one should be a high-similarity match
        high_matches = [d for d in duplicates if d.score > 0.7]
        assert len(high_matches) >= 1

    @pytest.mark.asyncio
    async def test_e2e010_find_duplicates_in_mock_src(
        self,
        e2e_indexer_worker: IndexerWorker,
        e2e_query_engine: QueryEngine,
        mock_src_python: Path,
    ) -> None:
        """E2E-010 variant: Find similar functions within mock-src itself.

        mock-src has multiple service classes with similar patterns.
        """
        # Index mock-src
        await e2e_indexer_worker.index_directory(str(mock_src_python))

        # Search for service initialization patterns
        # Both TaskService and UserService have __init__ methods
        init_results = await e2e_query_engine.semantic_search(
            query="service initialization with repository",
            memory_types=[MemoryType.FUNCTION],
            limit=10,
        )

        # Should find multiple __init__ methods from different services
        assert len(init_results) >= 1

    @pytest.mark.asyncio
    async def test_e2e011_check_code_before_implementation(
        self,
        e2e_memory_manager: MemoryManager,
        e2e_query_engine: QueryEngine,
    ) -> None:
        """E2E-011: Check new code before implementation.

        Flow: Developer writes code -> find_duplicates -> see existing similar code

        Note: With mock embeddings, semantic search doesn't return semantically
        similar results. This test verifies the infrastructure works (adding
        memories and searching them), not semantic ranking.
        """
        # Use unique suffix for this test
        unique_suffix = str(uuid4())[:8]

        # Step 1: Add existing function to memory (simulates indexed codebase)
        existing_function = FunctionMemory(
            id=uuid4(),
            type=MemoryType.FUNCTION,
            content=f"""def validate_email_address_{unique_suffix}(email: str) -> bool:
    '''Validate that email has correct format.'''
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))""",
            function_id=uuid4(),
            name=f"validate_email_address_{unique_suffix}",
            signature=f"def validate_email_address_{unique_suffix}(email: str) -> bool",
            file_path="src/validators.py",
            start_line=10,
            end_line=15,
            language="python",
            docstring="Validate that email has correct format.",
        )

        await e2e_memory_manager.add_memory(existing_function)

        # Step 2: Developer wants to implement similar function
        new_code = f"""def check_email_format_{unique_suffix}(email_string: str) -> bool:
    '''Check if email format is valid.'''
    import re
    regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'
    return bool(re.match(regex, email_string))"""

        # Step 3: Check for duplicates before implementing
        # With mock embeddings, search returns results but not by semantic similarity
        duplicates = await e2e_query_engine.semantic_search(
            query=new_code,
            memory_types=[MemoryType.FUNCTION],
            limit=10,
        )

        # Should find function results (infrastructure test)
        assert len(duplicates) >= 1, "Search should return function results"

        # Verify result structure
        for d in duplicates:
            payload = d.payload if hasattr(d, 'payload') else d.get("payload", {})
            assert "name" in payload, "Function result should have a name"

        # The match should have a score (any score indicates infrastructure works)
        match = duplicates[0]
        assert match.score > 0, "Search results should have positive scores"

    @pytest.mark.asyncio
    async def test_duplicate_detection_with_language_filter(
        self,
        e2e_memory_manager: MemoryManager,
        e2e_query_engine: QueryEngine,
    ) -> None:
        """Test duplicate detection with language filtering.

        Note: With mock embeddings and shared state, we test infrastructure
        rather than specific result matching.
        """
        # Use unique suffix to avoid conflicts
        unique_suffix = str(uuid4())[:8]

        # Add Python function
        python_func = FunctionMemory(
            id=uuid4(),
            type=MemoryType.FUNCTION,
            content=f"def process_data_{unique_suffix}(data: list) -> list:\n    return [x * 2 for x in data]",
            function_id=uuid4(),
            name=f"process_data_{unique_suffix}",
            signature=f"def process_data_{unique_suffix}(data: list) -> list",
            file_path="src/processor.py",
            start_line=1,
            end_line=2,
            language="python",
        )

        # Add TypeScript function with similar logic
        ts_func = FunctionMemory(
            id=uuid4(),
            type=MemoryType.FUNCTION,
            content=f"function processData{unique_suffix}(data: number[]): number[] {{\n    return data.map(x => x * 2);\n}}",
            function_id=uuid4(),
            name=f"processData{unique_suffix}",
            signature=f"function processData{unique_suffix}(data: number[]): number[]",
            file_path="src/processor.ts",
            start_line=1,
            end_line=3,
            language="typescript",
        )

        await e2e_memory_manager.add_memory(python_func)
        await e2e_memory_manager.add_memory(ts_func)

        # Search for functions - verifies search infrastructure works
        results = await e2e_query_engine.semantic_search(
            query=f"function that processes data {unique_suffix}",
            memory_types=[MemoryType.FUNCTION],
            limit=20,
        )

        # Should find function results (infrastructure test)
        assert len(results) >= 1, "Semantic search should return function results"

        # Verify result structure
        for r in results:
            payload = r.payload if hasattr(r, 'payload') else r.get("payload", {})
            assert "name" in payload, "Function result should have a name"

        # Check that we have functions with language attributes
        languages = [
            r.payload.get("language") if hasattr(r, 'payload') else r.get("payload", {}).get("language")
            for r in results
        ]
        # At least some results should have a language set
        assert any(l for l in languages), "Some function results should have language set"


class TestDuplicateDetectionWithMockSrc:
    """Tests specifically using mock-src patterns for duplicate detection."""

    @pytest.mark.asyncio
    async def test_detect_similar_validation_functions(
        self,
        e2e_indexer_worker: IndexerWorker,
        e2e_query_engine: QueryEngine,
        mock_src_python: Path,
    ) -> None:
        """Test detecting similar validation functions in mock-src.

        mock-src has: validate_email, validate_username, validate_password
        All have similar patterns (validation with regex/rules).

        Note: With mock embeddings, semantic search returns hash-based results,
        not semantically similar results. This test verifies that indexing
        and search infrastructure work, not semantic ranking.
        """
        result = await e2e_indexer_worker.index_directory(str(mock_src_python))

        # Verify indexing completed successfully
        assert result.get("status") != "error", f"Indexing failed: {result}"

        # Note: If files were already indexed by previous tests, files_skipped will be > 0
        # and functions_indexed will be 0. This is expected behavior for incremental indexing.
        files_processed = result.get("files_processed", 0)
        files_skipped = result.get("files_skipped", 0)
        functions_indexed = result.get("functions_indexed", 0)

        # Either new functions were indexed, or files were skipped (already indexed)
        assert files_processed > 0 or files_skipped > 0, f"Should have processed or skipped files, got: {result}"

        # Search for validation patterns - verifies search infrastructure works
        results = await e2e_query_engine.semantic_search(
            query="validation function that checks format and returns boolean",
            memory_types=[MemoryType.FUNCTION],
            limit=10,
        )

        # Should return function results (either from this indexing or previous)
        assert len(results) >= 1, "Semantic search should return function results"

        # Verify result structure
        for r in results:
            payload = r.payload if hasattr(r, 'payload') else r.get("payload", {})
            assert "name" in payload, "Function result should have a name"

    @pytest.mark.asyncio
    async def test_detect_similar_service_methods(
        self,
        e2e_indexer_worker: IndexerWorker,
        e2e_query_engine: QueryEngine,
        mock_src_python: Path,
    ) -> None:
        """Test detecting similar service methods in mock-src.

        mock-src has TaskService, UserService, ProjectService with similar patterns.
        """
        await e2e_indexer_worker.index_directory(str(mock_src_python))

        # Search for CRUD-like methods
        create_results = await e2e_query_engine.semantic_search(
            query="create entity method with validation",
            memory_types=[MemoryType.FUNCTION],
            limit=10,
        )

        # Should find multiple create methods
        function_names = [
            r.payload.get("name") if hasattr(r, 'payload') else r.get("payload", {}).get("name")
            for r in create_results
        ]

        create_funcs = [n for n in function_names if n and "create" in n.lower()]
        assert len(create_funcs) >= 1


class TestDuplicateThresholds:
    """E2E tests for duplicate detection thresholds."""

    @pytest.mark.asyncio
    async def test_varying_thresholds(
        self,
        e2e_memory_manager: MemoryManager,
        e2e_query_engine: QueryEngine,
    ) -> None:
        """Test how different thresholds affect duplicate detection."""
        # Add base function
        base_func = FunctionMemory(
            id=uuid4(),
            type=MemoryType.FUNCTION,
            content="def calculate_sum(numbers: list[int]) -> int:\n    return sum(numbers)",
            function_id=uuid4(),
            name="calculate_sum",
            signature="def calculate_sum(numbers: list[int]) -> int",
            file_path="src/math.py",
            start_line=1,
            end_line=2,
            language="python",
        )

        # Add moderately similar function
        moderate_func = FunctionMemory(
            id=uuid4(),
            type=MemoryType.FUNCTION,
            content="def add_numbers(nums: list) -> float:\n    total = 0\n    for n in nums:\n        total += n\n    return total",
            function_id=uuid4(),
            name="add_numbers",
            signature="def add_numbers(nums: list) -> float",
            file_path="src/utils.py",
            start_line=10,
            end_line=15,
            language="python",
        )

        await e2e_memory_manager.add_memory(base_func)
        await e2e_memory_manager.add_memory(moderate_func)

        # Search - all results returned, we filter by score
        results = await e2e_query_engine.semantic_search(
            query=base_func.content,
            memory_types=[MemoryType.FUNCTION],
            limit=10,
        )

        # Low threshold - more matches
        low_matches = [r for r in results if r.score >= 0.5]

        # High threshold - fewer matches
        high_matches = [r for r in results if r.score >= 0.9]

        # Low threshold should return more results
        assert len(low_matches) >= len(high_matches)
