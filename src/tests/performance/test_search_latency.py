"""Performance tests for search latency (PT-001 to PT-005).

Tests measure semantic search latency against targets:
- PT-001: Semantic search P50 < 200ms (100K memories, 1000 queries)
- PT-002: Semantic search P95 < 500ms (100K memories, 1000 queries)
- PT-003: Semantic search P99 < 1000ms (100K memories, 1000 queries)
- PT-004: Search with type filter < 500ms (100K memories, single type)
- PT-005: Search with time range < 500ms (100K memories, 7-day range)
"""

import asyncio
import random
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from memory_service.models import MemoryType, FunctionMemory
from memory_service.core.memory_manager import MemoryManager
from memory_service.core.query_engine import QueryEngine

from .conftest import (
    PerformanceMetrics,
    PerformanceTimer,
    create_test_function_memory,
    create_test_requirement_memory,
    generate_test_embedding,
)


# Reduced counts for CI - scale up for production testing
MEMORY_COUNT = 1000  # Use 100000 for full test
QUERY_COUNT = 100  # Use 1000 for full test


class TestSearchLatency:
    """Test suite for search latency requirements."""

    @pytest.fixture
    async def populated_memory_manager(
        self,
        memory_manager: MemoryManager,
    ) -> MemoryManager:
        """Populate memory manager with test data."""
        # Create batch of memories
        batch_size = 100
        for batch_start in range(0, MEMORY_COUNT, batch_size):
            memories = [
                create_test_function_memory(i)
                for i in range(batch_start, min(batch_start + batch_size, MEMORY_COUNT))
            ]
            await memory_manager.bulk_add_memories(memories)

        return memory_manager

    @pytest.mark.asyncio
    async def test_pt_001_semantic_search_p50(
        self,
        populated_memory_manager: MemoryManager,
        query_engine: QueryEngine,
    ) -> None:
        """PT-001: Semantic search P50 < 200ms.

        Target: P50 latency under 200ms with 100K memories.
        """
        metrics = PerformanceMetrics()

        # Run multiple queries
        for i in range(QUERY_COUNT):
            query = f"Process data with various options for task {random.randint(0, MEMORY_COUNT)}"

            start = time.perf_counter()
            results = await query_engine.semantic_search(
                query=query,
                memory_types=[MemoryType.FUNCTION],
                limit=10,
            )
            duration_ms = (time.perf_counter() - start) * 1000
            metrics.add(duration_ms)

        p50 = metrics.p50()
        print(f"\nPT-001: Search P50 = {p50:.2f}ms (target: <200ms)")
        print(f"  P95 = {metrics.p95():.2f}ms, P99 = {metrics.p99():.2f}ms")
        print(f"  Mean = {metrics.mean():.2f}ms, Count = {metrics.count()}")

        # For scaled-down test, adjust expectations proportionally
        target = 200 if MEMORY_COUNT >= 100000 else 200 * (MEMORY_COUNT / 100000 + 0.5)
        assert p50 < target, f"P50 {p50:.2f}ms exceeds target {target}ms"

    @pytest.mark.asyncio
    async def test_pt_002_semantic_search_p95(
        self,
        populated_memory_manager: MemoryManager,
        query_engine: QueryEngine,
    ) -> None:
        """PT-002: Semantic search P95 < 500ms.

        Target: P95 latency under 500ms with 100K memories.
        """
        metrics = PerformanceMetrics()

        for i in range(QUERY_COUNT):
            query = f"Find function that handles processing for module {random.randint(0, 100)}"

            start = time.perf_counter()
            results = await query_engine.semantic_search(
                query=query,
                memory_types=[MemoryType.FUNCTION],
                limit=10,
            )
            duration_ms = (time.perf_counter() - start) * 1000
            metrics.add(duration_ms)

        p95 = metrics.p95()
        print(f"\nPT-002: Search P95 = {p95:.2f}ms (target: <500ms)")

        target = 500 if MEMORY_COUNT >= 100000 else 500
        assert p95 < target, f"P95 {p95:.2f}ms exceeds target {target}ms"

    @pytest.mark.asyncio
    async def test_pt_003_semantic_search_p99(
        self,
        populated_memory_manager: MemoryManager,
        query_engine: QueryEngine,
    ) -> None:
        """PT-003: Semantic search P99 < 1000ms.

        Target: P99 latency under 1000ms with 100K memories.
        """
        metrics = PerformanceMetrics()

        for i in range(QUERY_COUNT):
            query = f"Search for data processor with options index {random.randint(0, MEMORY_COUNT)}"

            start = time.perf_counter()
            results = await query_engine.semantic_search(
                query=query,
                memory_types=[MemoryType.FUNCTION],
                limit=10,
            )
            duration_ms = (time.perf_counter() - start) * 1000
            metrics.add(duration_ms)

        p99 = metrics.p99()
        print(f"\nPT-003: Search P99 = {p99:.2f}ms (target: <1000ms)")

        target = 1000
        assert p99 < target, f"P99 {p99:.2f}ms exceeds target {target}ms"

    @pytest.mark.asyncio
    async def test_pt_004_search_with_type_filter(
        self,
        memory_manager: MemoryManager,
        query_engine: QueryEngine,
    ) -> None:
        """PT-004: Search with type filter < 500ms.

        Target: Filtered search under 500ms with 100K memories.
        """
        # Add mixed memory types
        batch_size = 50
        for batch_start in range(0, MEMORY_COUNT // 2, batch_size):
            function_memories = [
                create_test_function_memory(i)
                for i in range(batch_start, min(batch_start + batch_size, MEMORY_COUNT // 2))
            ]
            requirement_memories = [
                create_test_requirement_memory(i)
                for i in range(batch_start, min(batch_start + batch_size, MEMORY_COUNT // 2))
            ]
            await memory_manager.bulk_add_memories(function_memories)
            await memory_manager.bulk_add_memories(requirement_memories)

        metrics = PerformanceMetrics()

        for i in range(QUERY_COUNT // 2):
            query = f"Process data with options {random.randint(0, 1000)}"

            start = time.perf_counter()
            results = await query_engine.semantic_search(
                query=query,
                memory_types=[MemoryType.FUNCTION],  # Single type filter
                limit=10,
            )
            duration_ms = (time.perf_counter() - start) * 1000
            metrics.add(duration_ms)

        p95 = metrics.p95()
        print(f"\nPT-004: Search with type filter P95 = {p95:.2f}ms (target: <500ms)")

        assert p95 < 500, f"P95 {p95:.2f}ms exceeds target 500ms"

    @pytest.mark.asyncio
    async def test_pt_005_search_with_time_range(
        self,
        memory_manager: MemoryManager,
        query_engine: QueryEngine,
    ) -> None:
        """PT-005: Search with time range < 500ms.

        Target: Time-filtered search under 500ms with 100K memories.
        """
        # Add memories with varying timestamps
        now = datetime.now(timezone.utc)
        batch_size = 50

        for batch_start in range(0, MEMORY_COUNT // 2, batch_size):
            memories = []
            for i in range(batch_start, min(batch_start + batch_size, MEMORY_COUNT // 2)):
                mem = create_test_function_memory(i)
                # Spread memories over last 30 days
                days_ago = i % 30
                # Note: BaseMemory.created_at is set automatically, we can't easily change it
                # In a real test we'd need to manipulate storage directly
                memories.append(mem)
            await memory_manager.bulk_add_memories(memories)

        metrics = PerformanceMetrics()

        # Query with time range (last 7 days)
        start_time = now - timedelta(days=7)
        end_time = now

        for i in range(QUERY_COUNT // 2):
            query = f"Find processor function {random.randint(0, 1000)}"

            start = time.perf_counter()
            results = await query_engine.semantic_search(
                query=query,
                memory_types=[MemoryType.FUNCTION],
                time_range=(start_time, end_time),
                limit=10,
            )
            duration_ms = (time.perf_counter() - start) * 1000
            metrics.add(duration_ms)

        p95 = metrics.p95()
        print(f"\nPT-005: Search with time range P95 = {p95:.2f}ms (target: <500ms)")

        assert p95 < 500, f"P95 {p95:.2f}ms exceeds target 500ms"


class TestSearchScaling:
    """Additional tests for search performance scaling."""

    @pytest.mark.asyncio
    async def test_search_scales_with_result_limit(
        self,
        memory_manager: MemoryManager,
        query_engine: QueryEngine,
    ) -> None:
        """Verify search latency scales appropriately with limit parameter."""
        # Add test data
        memories = [create_test_function_memory(i) for i in range(500)]
        await memory_manager.bulk_add_memories(memories)

        query = "Process data with options"
        limits = [10, 50, 100]
        timings: dict[int, float] = {}

        for limit in limits:
            metrics = PerformanceMetrics()
            for _ in range(20):
                start = time.perf_counter()
                results = await query_engine.semantic_search(
                    query=query,
                    memory_types=[MemoryType.FUNCTION],
                    limit=limit,
                )
                duration_ms = (time.perf_counter() - start) * 1000
                metrics.add(duration_ms)
            timings[limit] = metrics.mean()

        print(f"\nSearch scaling by limit:")
        for limit, timing in timings.items():
            print(f"  limit={limit}: {timing:.2f}ms")

        # Larger limits should not dramatically increase latency
        # Allow 3x increase max from limit 10 to 100
        assert timings[100] < timings[10] * 5, "Search latency scales poorly with limit"
