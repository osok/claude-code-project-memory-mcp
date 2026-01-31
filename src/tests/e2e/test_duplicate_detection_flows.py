"""E2E tests for duplicate detection flows (E2E-010 to E2E-011)."""

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
    """E2E tests for duplicate detection flows."""

    @pytest.mark.asyncio
    async def test_e2e010_index_then_find_duplicates(
        self,
        e2e_memory_manager: MemoryManager,
        e2e_query_engine: QueryEngine,
        e2e_indexer_worker: IndexerWorker,
        temp_codebase: Path,
    ) -> None:
        """E2E-010: Index codebase, detect existing similar function.

        Flow: index_directory -> find_duplicates
        """
        # Step 1: Index the codebase
        result = await e2e_indexer_worker.index_directory(str(temp_codebase))

        # Step 2: Add a function that's similar to one in the codebase
        # The codebase has: def format_string(text: str) -> str
        similar_function = FunctionMemory(
            id=uuid4(),
            type=MemoryType.FUNCTION,
            content="""def clean_text(input_str: str) -> str:
    '''Clean a string by stripping and lowercasing.'''
    return input_str.strip().lower()""",
            function_id=uuid4(),
            name="clean_text",
            signature="def clean_text(input_str: str) -> str",
            file_path="src/new_utils.py",
            start_line=1,
            end_line=4,
            language="python",
            docstring="Clean a string by stripping and lowercasing.",
        )

        # Add the similar function
        await e2e_memory_manager.add_memory(similar_function)

        # Step 3: Find duplicates (find_duplicates tool)
        duplicates = await e2e_query_engine.semantic_search(
            query=similar_function.content,
            memory_types=[MemoryType.FUNCTION],
            limit=10,
            min_similarity=0.7,
        )

        # Should find both the original and similar function
        assert len(duplicates) >= 1

        # At least one should be a high-similarity match
        high_matches = [d for d in duplicates if d["score"] > 0.7]
        assert len(high_matches) >= 1

    @pytest.mark.asyncio
    async def test_e2e011_check_code_before_implementation(
        self,
        e2e_memory_manager: MemoryManager,
        e2e_query_engine: QueryEngine,
    ) -> None:
        """E2E-011: Check new code before implementation.

        Flow: Developer writes code -> find_duplicates -> see existing similar code
        """
        # Step 1: Add existing function to memory
        existing_function = FunctionMemory(
            id=uuid4(),
            type=MemoryType.FUNCTION,
            content="""def validate_email_address(email: str) -> bool:
    '''Validate that email has correct format.'''
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))""",
            function_id=uuid4(),
            name="validate_email_address",
            signature="def validate_email_address(email: str) -> bool",
            file_path="src/validators.py",
            start_line=10,
            end_line=15,
            language="python",
            docstring="Validate that email has correct format.",
        )

        await e2e_memory_manager.add_memory(existing_function)

        # Step 2: Developer wants to implement similar function
        new_code = """def check_email_format(email_string: str) -> bool:
    '''Check if email format is valid.'''
    import re
    regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'
    return bool(re.match(regex, email_string))"""

        # Step 3: Check for duplicates before implementing
        duplicates = await e2e_query_engine.semantic_search(
            query=new_code,
            memory_types=[MemoryType.FUNCTION],
            limit=5,
            min_similarity=0.7,
        )

        # Should find the existing similar function
        assert len(duplicates) >= 1
        found_ids = [str(d["id"]) for d in duplicates]
        assert str(existing_function.id) in found_ids

        # The match should provide useful info
        match = duplicates[0]
        assert "score" in match
        assert match["score"] > 0.7
        # Should include file path info
        assert "file_path" in match.get("payload", match)

    @pytest.mark.asyncio
    async def test_duplicate_detection_with_language_filter(
        self,
        e2e_memory_manager: MemoryManager,
        e2e_query_engine: QueryEngine,
    ) -> None:
        """Test duplicate detection with language filtering."""
        # Add Python function
        python_func = FunctionMemory(
            id=uuid4(),
            type=MemoryType.FUNCTION,
            content="def process_data(data: list) -> list:\n    return [x * 2 for x in data]",
            function_id=uuid4(),
            name="process_data",
            signature="def process_data(data: list) -> list",
            file_path="src/processor.py",
            start_line=1,
            end_line=2,
            language="python",
        )

        # Add TypeScript function with similar logic
        ts_func = FunctionMemory(
            id=uuid4(),
            type=MemoryType.FUNCTION,
            content="function processData(data: number[]): number[] {\n    return data.map(x => x * 2);\n}",
            function_id=uuid4(),
            name="processData",
            signature="function processData(data: number[]): number[]",
            file_path="src/processor.ts",
            start_line=1,
            end_line=3,
            language="typescript",
        )

        await e2e_memory_manager.add_memory(python_func)
        await e2e_memory_manager.add_memory(ts_func)

        # Search for similar functions
        results = await e2e_query_engine.semantic_search(
            query="function that doubles array elements",
            memory_types=[MemoryType.FUNCTION],
            limit=10,
        )

        # Should find both
        assert len(results) >= 2
        languages = [r.get("payload", r).get("language") for r in results]
        # At least one Python and one TypeScript
        assert any(l == "python" for l in languages if l)
        assert any(l == "typescript" for l in languages if l)


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

        # Low threshold should find more matches
        low_results = await e2e_query_engine.semantic_search(
            query=base_func.content,
            memory_types=[MemoryType.FUNCTION],
            limit=10,
            min_similarity=0.5,
        )

        # High threshold should find fewer matches
        high_results = await e2e_query_engine.semantic_search(
            query=base_func.content,
            memory_types=[MemoryType.FUNCTION],
            limit=10,
            min_similarity=0.9,
        )

        # Low threshold should return more results
        assert len(low_results) >= len(high_results)
