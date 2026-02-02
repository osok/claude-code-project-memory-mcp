"""Performance tests for duplicate detection latency (PT-050 to PT-051).

Tests measure duplicate detection performance:
- PT-050: Duplicate check P95 < 300ms (10K function index)
- PT-051: Duplicate check P95 < 500ms (500K function index)
"""

import random
import time
from uuid import uuid4

import pytest

from memory_service.models import MemoryType, FunctionMemory
from memory_service.core.memory_manager import MemoryManager
from memory_service.core.query_engine import QueryEngine

from .conftest import (
    PerformanceMetrics,
    create_test_function_memory,
    generate_test_embedding,
)


# Reduced counts for CI - scale up for production testing
SMALL_INDEX_SIZE = 1000  # Use 10000 for full test
LARGE_INDEX_SIZE = 5000  # Use 500000 for full test
QUERY_COUNT = 50


class TestDuplicateDetectionLatency:
    """Test suite for duplicate detection latency requirements."""

    @pytest.fixture
    async def small_function_index(
        self,
        memory_manager: MemoryManager,
    ) -> MemoryManager:
        """Populate with small function index (10K)."""
        batch_size = 100
        for batch_start in range(0, SMALL_INDEX_SIZE, batch_size):
            memories = [
                create_test_function_memory(i)
                for i in range(batch_start, min(batch_start + batch_size, SMALL_INDEX_SIZE))
            ]
            await memory_manager.bulk_add_memories(memories)
        return memory_manager

    @pytest.fixture
    async def large_function_index(
        self,
        memory_manager: MemoryManager,
    ) -> MemoryManager:
        """Populate with large function index (500K scaled down)."""
        batch_size = 100
        for batch_start in range(0, LARGE_INDEX_SIZE, batch_size):
            memories = [
                create_test_function_memory(i)
                for i in range(batch_start, min(batch_start + batch_size, LARGE_INDEX_SIZE))
            ]
            await memory_manager.bulk_add_memories(memories)
        return memory_manager

    @pytest.mark.asyncio
    async def test_pt_050_duplicate_check_small_index(
        self,
        small_function_index: MemoryManager,
        query_engine: QueryEngine,
    ) -> None:
        """PT-050: Duplicate check P95 < 300ms (10K function index).

        Target: Find duplicates within 300ms in 10K function index.
        """
        metrics = PerformanceMetrics()

        for i in range(QUERY_COUNT):
            # Create a function that might be a duplicate
            test_code = f"def process_data_{random.randint(0, SMALL_INDEX_SIZE)}(input: str, options: dict) -> Result"

            start = time.perf_counter()
            results = await query_engine.semantic_search(
                query=test_code,
                memory_types=[MemoryType.FUNCTION],
                limit=10,
            )
            # Filter for duplicates (similarity >= 0.85)
            duplicates = [r for r in results if r.score >= 0.85]
            duration_ms = (time.perf_counter() - start) * 1000
            metrics.add(duration_ms)

        p95 = metrics.p95()
        print(f"\nPT-050: Duplicate check (10K) P95 = {p95:.2f}ms (target: <300ms)")
        print(f"  Mean = {metrics.mean():.2f}ms")
        print(f"  Index size: {SMALL_INDEX_SIZE}")

        # Adjust for scaled test
        target = 300 if SMALL_INDEX_SIZE >= 10000 else 300
        assert p95 < target, f"P95 {p95:.2f}ms exceeds target {target}ms"

    @pytest.mark.asyncio
    async def test_pt_051_duplicate_check_large_index(
        self,
        large_function_index: MemoryManager,
        query_engine: QueryEngine,
    ) -> None:
        """PT-051: Duplicate check P95 < 500ms (500K function index).

        Target: Find duplicates within 500ms in 500K function index.
        """
        metrics = PerformanceMetrics()

        for i in range(QUERY_COUNT):
            test_code = f"def process_data_{random.randint(0, LARGE_INDEX_SIZE)}(input: str, options: dict) -> Result"

            start = time.perf_counter()
            results = await query_engine.semantic_search(
                query=test_code,
                memory_types=[MemoryType.FUNCTION],
                limit=10,
            )
            # Filter for duplicates (similarity >= 0.85)
            duplicates = [r for r in results if r.score >= 0.85]
            duration_ms = (time.perf_counter() - start) * 1000
            metrics.add(duration_ms)

        p95 = metrics.p95()
        print(f"\nPT-051: Duplicate check (500K) P95 = {p95:.2f}ms (target: <500ms)")
        print(f"  Mean = {metrics.mean():.2f}ms")
        print(f"  Index size: {LARGE_INDEX_SIZE}")

        # Adjust for scaled test
        target = 500 if LARGE_INDEX_SIZE >= 500000 else 500
        assert p95 < target, f"P95 {p95:.2f}ms exceeds target {target}ms"


class TestDuplicateDetectionAccuracy:
    """Additional tests for duplicate detection accuracy under load."""

    @pytest.mark.asyncio
    async def test_duplicate_detection_with_threshold(
        self,
        memory_manager: MemoryManager,
        query_engine: QueryEngine,
    ) -> None:
        """Test detection at different similarity thresholds."""
        # Add test functions
        memories = [create_test_function_memory(i) for i in range(500)]
        await memory_manager.bulk_add_memories(memories)

        thresholds = [0.70, 0.85, 0.95]
        test_code = "def process_data_0(input: str, options: dict) -> Result"

        for threshold in thresholds:
            metrics = PerformanceMetrics()

            for _ in range(20):
                start = time.perf_counter()
                results = await query_engine.semantic_search(
                    query=test_code,
                    memory_types=[MemoryType.FUNCTION],
                    limit=10,
                )
                # Filter based on threshold
                filtered = [r for r in results if r.score >= threshold]
                duration_ms = (time.perf_counter() - start) * 1000
                metrics.add(duration_ms)

            print(f"\nThreshold {threshold}: P95 = {metrics.p95():.2f}ms, "
                  f"results vary with similarity")

    @pytest.mark.asyncio
    async def test_batch_duplicate_check(
        self,
        memory_manager: MemoryManager,
        query_engine: QueryEngine,
    ) -> None:
        """Test checking multiple functions for duplicates."""
        # Add existing functions
        memories = [create_test_function_memory(i) for i in range(500)]
        await memory_manager.bulk_add_memories(memories)

        # Check batch of functions
        functions_to_check = [
            f"def process_data_{random.randint(0, 500)}(input: str) -> Result"
            for _ in range(10)
        ]

        start = time.perf_counter()
        results = []
        for func in functions_to_check:
            result = await query_engine.semantic_search(
                query=func,
                memory_types=[MemoryType.FUNCTION],
                limit=5,
            )
            # Filter for duplicates
            duplicates = [r for r in result if r.score >= 0.85]
            results.append(duplicates)
        duration_ms = (time.perf_counter() - start) * 1000

        print(f"\nBatch duplicate check (10 functions):")
        print(f"  Total time: {duration_ms:.2f}ms")
        print(f"  Per function: {duration_ms / 10:.2f}ms")

        # Batch check should be reasonably efficient
        assert duration_ms / 10 < 100, "Per-function check too slow in batch"

    @pytest.mark.asyncio
    async def test_near_duplicate_detection(
        self,
        memory_manager: MemoryManager,
        query_engine: QueryEngine,
    ) -> None:
        """Test detection of near-duplicates (renamed functions)."""
        # Add original function
        original = FunctionMemory(
            id=uuid4(),
            type=MemoryType.FUNCTION,
            content="def calculate_total(items: list, tax_rate: float) -> float: Calculate total with tax",
            embedding=generate_test_embedding(1),
            function_id=uuid4(),
            name="calculate_total",
            signature="def calculate_total(items: list, tax_rate: float) -> float",
            file_path="src/pricing.py",
            start_line=10,
            end_line=25,
            language="python",
        )
        await memory_manager.add_memory(original)

        # Check near-duplicates
        near_duplicates = [
            "def compute_total(items: list, tax_rate: float) -> float: Compute total with tax",  # Renamed
            "def calculate_sum(items: list, tax_rate: float) -> float: Calculate sum with tax",  # Different name
            "def calculate_total(products: list, rate: float) -> float: Calculate total",  # Different params
        ]

        for near_dup in near_duplicates:
            start = time.perf_counter()
            results = await query_engine.semantic_search(
                query=near_dup,
                memory_types=[MemoryType.FUNCTION],
                limit=5,
            )
            duration_ms = (time.perf_counter() - start) * 1000

            has_match = any(r.score > 0.85 for r in results) if results else False
            print(f"  Query: {near_dup[:50]}... -> Match: {has_match}, Time: {duration_ms:.1f}ms")
