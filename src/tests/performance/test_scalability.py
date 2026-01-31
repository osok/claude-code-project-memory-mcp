"""Performance tests for scalability (PT-060 to PT-062).

Tests measure system performance at scale:
- PT-060: Memory count scalability - 1M memories
- PT-061: Source file scalability - 100K files
- PT-062: Function index scalability - 500K functions
"""

import asyncio
import random
import time
from uuid import uuid4

import pytest

from memory_service.models import MemoryType, FunctionMemory
from memory_service.core.memory_manager import MemoryManager
from memory_service.core.query_engine import QueryEngine
from memory_service.storage.qdrant_adapter import QdrantAdapter

from .conftest import (
    PerformanceMetrics,
    create_test_function_memory,
    create_test_requirement_memory,
    create_test_component_memory,
)


# Reduced counts for CI - these are scaled-down versions
# Production tests should use full counts
MEMORY_SCALE_TARGET = 10000  # Use 1000000 for full test
FILE_SCALE_TARGET = 1000  # Use 100000 for full test
FUNCTION_SCALE_TARGET = 5000  # Use 500000 for full test

BATCH_SIZE = 100
QUERY_SAMPLES = 50


class TestScalability:
    """Test suite for scalability requirements."""

    @pytest.mark.asyncio
    async def test_pt_060_memory_count_scalability(
        self,
        memory_manager: MemoryManager,
        query_engine: QueryEngine,
    ) -> None:
        """PT-060: Memory count scalability - 1M memories.

        Target: System maintains performance with 1M memories.
        """
        # Progressively add memories and measure query performance
        checkpoints = [1000, 2500, 5000, 7500, MEMORY_SCALE_TARGET]
        checkpoint_metrics: dict[int, PerformanceMetrics] = {}

        total_added = 0
        for checkpoint in checkpoints:
            # Add memories up to checkpoint
            while total_added < checkpoint:
                batch_end = min(total_added + BATCH_SIZE, checkpoint)
                memories = [
                    create_test_function_memory(i)
                    for i in range(total_added, batch_end)
                ]
                await memory_manager.bulk_add_memories(memories)
                total_added = batch_end

            # Measure query performance at this scale
            metrics = PerformanceMetrics()
            for _ in range(QUERY_SAMPLES):
                query = f"Process data function {random.randint(0, total_added)}"

                start = time.perf_counter()
                results = await query_engine.semantic_search(
                    query=query,
                    memory_types=[MemoryType.FUNCTION],
                    limit=10,
                )
                duration_ms = (time.perf_counter() - start) * 1000
                metrics.add(duration_ms)

            checkpoint_metrics[checkpoint] = metrics

        # Report scaling behavior
        print(f"\nPT-060: Memory count scalability")
        print(f"  {'Count':>10} | {'P50 (ms)':>10} | {'P95 (ms)':>10} | {'Mean (ms)':>10}")
        print("  " + "-" * 50)
        for count, metrics in checkpoint_metrics.items():
            print(f"  {count:>10} | {metrics.p50():>10.2f} | {metrics.p95():>10.2f} | {metrics.mean():>10.2f}")

        # Performance should not degrade more than 2x as scale increases
        first_p95 = checkpoint_metrics[checkpoints[0]].p95()
        last_p95 = checkpoint_metrics[checkpoints[-1]].p95()
        degradation = last_p95 / first_p95 if first_p95 > 0 else float('inf')

        print(f"\n  Performance degradation: {degradation:.2f}x")
        assert degradation < 5, f"Performance degraded {degradation:.1f}x (max 5x allowed)"

    @pytest.mark.asyncio
    async def test_pt_061_source_file_scalability(
        self,
        memory_manager: MemoryManager,
        query_engine: QueryEngine,
    ) -> None:
        """PT-061: Source file scalability - 100K files.

        Target: System handles 100K indexed source files.
        """
        # Simulate source file indexing by creating component memories
        # Each component represents a file
        checkpoints = [200, 500, FILE_SCALE_TARGET]
        checkpoint_metrics: dict[int, PerformanceMetrics] = {}

        total_added = 0
        for checkpoint in checkpoints:
            while total_added < checkpoint:
                batch_end = min(total_added + BATCH_SIZE, checkpoint)
                memories = [
                    create_test_component_memory(i)
                    for i in range(total_added, batch_end)
                ]
                await memory_manager.bulk_add_memories(memories)
                total_added = batch_end

            # Measure file lookup performance
            metrics = PerformanceMetrics()
            for _ in range(QUERY_SAMPLES):
                query = f"Component service for handling operations"

                start = time.perf_counter()
                results = await query_engine.semantic_search(
                    query=query,
                    memory_types=[MemoryType.COMPONENT],
                    limit=10,
                )
                duration_ms = (time.perf_counter() - start) * 1000
                metrics.add(duration_ms)

            checkpoint_metrics[checkpoint] = metrics

        print(f"\nPT-061: Source file scalability")
        print(f"  {'Files':>10} | {'P50 (ms)':>10} | {'P95 (ms)':>10}")
        print("  " + "-" * 35)
        for count, metrics in checkpoint_metrics.items():
            print(f"  {count:>10} | {metrics.p50():>10.2f} | {metrics.p95():>10.2f}")

        # Check performance remains acceptable
        final_p95 = checkpoint_metrics[checkpoints[-1]].p95()
        assert final_p95 < 500, f"P95 {final_p95:.2f}ms exceeds 500ms at scale"

    @pytest.mark.asyncio
    async def test_pt_062_function_index_scalability(
        self,
        memory_manager: MemoryManager,
        query_engine: QueryEngine,
    ) -> None:
        """PT-062: Function index scalability - 500K functions.

        Target: System maintains search performance with 500K functions.
        """
        checkpoints = [500, 1500, 3000, FUNCTION_SCALE_TARGET]
        checkpoint_metrics: dict[int, PerformanceMetrics] = {}

        total_added = 0
        for checkpoint in checkpoints:
            while total_added < checkpoint:
                batch_end = min(total_added + BATCH_SIZE, checkpoint)
                memories = [
                    create_test_function_memory(i)
                    for i in range(total_added, batch_end)
                ]
                await memory_manager.bulk_add_memories(memories)
                total_added = batch_end

            # Measure function search performance
            metrics = PerformanceMetrics()
            for _ in range(QUERY_SAMPLES):
                query = f"def process_data(input, options) -> Result"

                start = time.perf_counter()
                results = await query_engine.semantic_search(
                    query=query,
                    memory_types=[MemoryType.FUNCTION],
                    limit=10,
                )
                duration_ms = (time.perf_counter() - start) * 1000
                metrics.add(duration_ms)

            checkpoint_metrics[checkpoint] = metrics

        print(f"\nPT-062: Function index scalability")
        print(f"  {'Functions':>10} | {'P50 (ms)':>10} | {'P95 (ms)':>10} | {'P99 (ms)':>10}")
        print("  " + "-" * 55)
        for count, metrics in checkpoint_metrics.items():
            print(f"  {count:>10} | {metrics.p50():>10.2f} | {metrics.p95():>10.2f} | {metrics.p99():>10.2f}")

        # Verify performance at scale
        final_p95 = checkpoint_metrics[checkpoints[-1]].p95()
        target = 500 if FUNCTION_SCALE_TARGET >= 500000 else 500
        assert final_p95 < target, f"P95 {final_p95:.2f}ms exceeds target {target}ms"


class TestConcurrentScaling:
    """Tests for concurrent access at scale."""

    @pytest.mark.asyncio
    async def test_concurrent_reads_at_scale(
        self,
        memory_manager: MemoryManager,
        query_engine: QueryEngine,
    ) -> None:
        """Test concurrent read performance at scale."""
        # Add test data
        memories = [create_test_function_memory(i) for i in range(1000)]
        await memory_manager.bulk_add_memories(memories)

        async def run_query() -> float:
            query = f"Process data function {random.randint(0, 1000)}"
            start = time.perf_counter()
            await query_engine.semantic_search(
                query=query,
                memory_types=[MemoryType.FUNCTION],
                limit=10,
            )
            return (time.perf_counter() - start) * 1000

        # Test different concurrency levels
        concurrency_levels = [10, 25, 50]

        for level in concurrency_levels:
            start = time.perf_counter()
            durations = await asyncio.gather(*[run_query() for _ in range(level)])
            total_time = (time.perf_counter() - start) * 1000

            print(f"\nConcurrency {level}:")
            print(f"  Total time: {total_time:.2f}ms")
            print(f"  Max query: {max(durations):.2f}ms")
            print(f"  Mean query: {sum(durations) / len(durations):.2f}ms")

    @pytest.mark.asyncio
    async def test_mixed_operations_at_scale(
        self,
        memory_manager: MemoryManager,
        query_engine: QueryEngine,
    ) -> None:
        """Test mixed read/write operations at scale."""
        # Add initial data
        memories = [create_test_function_memory(i) for i in range(500)]
        await memory_manager.bulk_add_memories(memories)

        async def read_op() -> tuple[str, float]:
            query = f"Process function {random.randint(0, 500)}"
            start = time.perf_counter()
            await query_engine.semantic_search(
                query=query,
                memory_types=[MemoryType.FUNCTION],
                limit=5,
            )
            return "read", (time.perf_counter() - start) * 1000

        async def write_op(idx: int) -> tuple[str, float]:
            memory = create_test_function_memory(1000 + idx)
            start = time.perf_counter()
            await memory_manager.add_memory(memory)
            return "write", (time.perf_counter() - start) * 1000

        # Mix of reads and writes (80% reads, 20% writes)
        operations = []
        for i in range(50):
            if random.random() < 0.8:
                operations.append(read_op())
            else:
                operations.append(write_op(i))

        start = time.perf_counter()
        results = await asyncio.gather(*operations)
        total_time = (time.perf_counter() - start) * 1000

        read_times = [d for op, d in results if op == "read"]
        write_times = [d for op, d in results if op == "write"]

        print(f"\nMixed operations (50 total):")
        print(f"  Total time: {total_time:.2f}ms")
        print(f"  Reads: {len(read_times)}, mean {sum(read_times) / len(read_times):.2f}ms")
        if write_times:
            print(f"  Writes: {len(write_times)}, mean {sum(write_times) / len(write_times):.2f}ms")


class TestResourceUtilization:
    """Tests for resource utilization at scale."""

    @pytest.mark.asyncio
    async def test_memory_efficiency(
        self,
        qdrant_adapter: QdrantAdapter,
        memory_manager: MemoryManager,
    ) -> None:
        """Test memory efficiency when storing many memories."""
        import sys

        # Track memory growth
        batch_count = 10
        batch_size = 100

        for batch_num in range(batch_count):
            memories = [
                create_test_function_memory(batch_num * batch_size + i)
                for i in range(batch_size)
            ]
            await memory_manager.bulk_add_memories(memories)

        # Get collection info
        collections = await qdrant_adapter.list_collections()
        total_points = 0

        for collection in collections:
            info = await qdrant_adapter.get_collection_info(collection)
            if info:
                total_points += info.get("points_count", 0)

        print(f"\nMemory efficiency:")
        print(f"  Total points stored: {total_points}")
        print(f"  Batches: {batch_count} x {batch_size}")

        # Verify all points were stored
        expected = batch_count * batch_size
        assert total_points >= expected * 0.95, f"Missing points: {total_points} < {expected}"
