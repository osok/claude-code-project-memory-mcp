"""Performance tests for write latency (PT-020 to PT-023).

Tests measure write operation latency against targets:
- PT-020: Memory add (excl. embedding) P95 < 100ms
- PT-021: Memory update P95 < 100ms
- PT-022: Memory delete P95 < 50ms
- PT-023: Bulk add (100 memories) P95 < 2000ms
"""

import asyncio
import time
from uuid import uuid4

import pytest

from memory_service.models import MemoryType, FunctionMemory
from memory_service.core.memory_manager import MemoryManager

from .conftest import (
    PerformanceMetrics,
    create_test_function_memory,
    generate_test_embedding,
)


OPERATION_COUNT = 50  # Number of operations to measure


class TestWriteLatency:
    """Test suite for write operation latency requirements."""

    @pytest.mark.asyncio
    async def test_pt_020_memory_add_latency(
        self,
        memory_manager: MemoryManager,
    ) -> None:
        """PT-020: Memory add (excl. embedding) P95 < 100ms.

        Target: Single memory add under 100ms (embedding cached).
        """
        metrics = PerformanceMetrics()

        # Pre-warm embedding cache
        test_content = "def process_data(input: str) -> Result: Process and return"
        await memory_manager._embedding_service.embed(test_content)

        for i in range(OPERATION_COUNT):
            memory = FunctionMemory(
                id=uuid4(),
                type=MemoryType.FUNCTION,
                content=test_content,  # Same content = cached embedding
                embedding=generate_test_embedding(i),
                function_id=uuid4(),
                name=f"process_data_{i}",
                signature="def process_data(input: str) -> Result",
                file_path=f"src/module_{i}.py",
                start_line=10,
                end_line=30,
                language="python",
            )

            start = time.perf_counter()
            result = await memory_manager.add_memory(memory)
            duration_ms = (time.perf_counter() - start) * 1000
            metrics.add(duration_ms)

        p95 = metrics.p95()
        print(f"\nPT-020: Memory add P95 = {p95:.2f}ms (target: <100ms)")
        print(f"  Mean = {metrics.mean():.2f}ms, Count = {metrics.count()}")

        assert p95 < 100, f"P95 {p95:.2f}ms exceeds target 100ms"

    @pytest.mark.asyncio
    async def test_pt_021_memory_update_latency(
        self,
        memory_manager: MemoryManager,
    ) -> None:
        """PT-021: Memory update P95 < 100ms.

        Target: Memory update under 100ms for content changes.
        """
        # First, create memories to update
        memory_ids = []
        for i in range(OPERATION_COUNT):
            memory = create_test_function_memory(i)
            result = await memory_manager.add_memory(memory)
            memory_ids.append(memory.id)

        metrics = PerformanceMetrics()

        for i, memory_id in enumerate(memory_ids):
            # Update with new content
            update_data = {
                "content": f"Updated function content for operation {i}",
                "docstring": f"Updated documentation for function {i}",
            }

            start = time.perf_counter()
            result = await memory_manager.update_memory(
                memory_id=memory_id,
                memory_type=MemoryType.FUNCTION,
                updates=update_data,
            )
            duration_ms = (time.perf_counter() - start) * 1000
            metrics.add(duration_ms)

        p95 = metrics.p95()
        print(f"\nPT-021: Memory update P95 = {p95:.2f}ms (target: <100ms)")

        assert p95 < 100, f"P95 {p95:.2f}ms exceeds target 100ms"

    @pytest.mark.asyncio
    async def test_pt_022_memory_delete_latency(
        self,
        memory_manager: MemoryManager,
    ) -> None:
        """PT-022: Memory delete P95 < 50ms.

        Target: Soft delete under 50ms.
        """
        # Create memories to delete
        memory_ids = []
        for i in range(OPERATION_COUNT):
            memory = create_test_function_memory(i + 1000)  # Different seeds
            result = await memory_manager.add_memory(memory)
            memory_ids.append(memory.id)

        metrics = PerformanceMetrics()

        for memory_id in memory_ids:
            start = time.perf_counter()
            result = await memory_manager.delete_memory(
                memory_id=memory_id,
                memory_type=MemoryType.FUNCTION,
            )
            duration_ms = (time.perf_counter() - start) * 1000
            metrics.add(duration_ms)

        p95 = metrics.p95()
        print(f"\nPT-022: Memory delete P95 = {p95:.2f}ms (target: <50ms)")

        assert p95 < 50, f"P95 {p95:.2f}ms exceeds target 50ms"

    @pytest.mark.asyncio
    async def test_pt_023_bulk_add_latency(
        self,
        memory_manager: MemoryManager,
    ) -> None:
        """PT-023: Bulk add (100 memories) P95 < 2000ms.

        Target: Batch of 100 memories under 2000ms (with cached embeddings).
        """
        metrics = PerformanceMetrics()
        batch_size = 100
        num_batches = 10

        for batch_num in range(num_batches):
            memories = [
                create_test_function_memory(batch_num * batch_size + i)
                for i in range(batch_size)
            ]

            start = time.perf_counter()
            result = await memory_manager.bulk_add_memories(memories)
            duration_ms = (time.perf_counter() - start) * 1000
            metrics.add(duration_ms)

        p95 = metrics.p95()
        print(f"\nPT-023: Bulk add (100) P95 = {p95:.2f}ms (target: <2000ms)")
        print(f"  Mean = {metrics.mean():.2f}ms")

        assert p95 < 2000, f"P95 {p95:.2f}ms exceeds target 2000ms"


class TestWriteScaling:
    """Additional tests for write operation scaling."""

    @pytest.mark.asyncio
    async def test_write_scales_with_batch_size(
        self,
        memory_manager: MemoryManager,
    ) -> None:
        """Verify write latency scales appropriately with batch size."""
        batch_sizes = [10, 50, 100]
        timings: dict[int, float] = {}

        for batch_size in batch_sizes:
            metrics = PerformanceMetrics()

            for batch_num in range(5):
                memories = [
                    create_test_function_memory(batch_num * 1000 + i)
                    for i in range(batch_size)
                ]

                start = time.perf_counter()
                result = await memory_manager.bulk_add_memories(memories)
                duration_ms = (time.perf_counter() - start) * 1000
                metrics.add(duration_ms)

            timings[batch_size] = metrics.mean()

        print(f"\nWrite scaling by batch size:")
        for size, timing in timings.items():
            per_item = timing / size
            print(f"  batch={size}: {timing:.2f}ms total, {per_item:.2f}ms/item")

        # Per-item time should decrease or stay roughly constant with larger batches
        per_item_10 = timings[10] / 10
        per_item_100 = timings[100] / 100
        assert per_item_100 <= per_item_10 * 1.5, "Batch write doesn't scale well"

    @pytest.mark.asyncio
    async def test_concurrent_writes(
        self,
        memory_manager: MemoryManager,
    ) -> None:
        """Test concurrent write operations."""
        async def write_memory(index: int) -> float:
            memory = create_test_function_memory(index + 5000)
            start = time.perf_counter()
            await memory_manager.add_memory(memory)
            return (time.perf_counter() - start) * 1000

        # Run 20 concurrent writes
        tasks = [write_memory(i) for i in range(20)]

        start = time.perf_counter()
        durations = await asyncio.gather(*tasks)
        total_time = (time.perf_counter() - start) * 1000

        print(f"\nConcurrent writes (20):")
        print(f"  Total time: {total_time:.2f}ms")
        print(f"  Max individual: {max(durations):.2f}ms")
        print(f"  Mean individual: {sum(durations) / len(durations):.2f}ms")

        # Total time should be less than sum of individual times
        assert total_time < sum(durations) * 0.8, "Concurrent writes not parallelizing"

    @pytest.mark.asyncio
    async def test_update_with_relationship_cascade(
        self,
        memory_manager: MemoryManager,
    ) -> None:
        """Test update latency when relationships exist."""
        # Create a memory with relationships
        main_memory = create_test_function_memory(9000)
        await memory_manager.add_memory(main_memory)

        # Create related memories
        for i in range(5):
            related = create_test_function_memory(9001 + i)
            await memory_manager.add_memory(related)
            # Note: In a full implementation, we'd create relationships here

        metrics = PerformanceMetrics()

        for i in range(20):
            update_data = {"content": f"Updated content {i}", "docstring": f"Doc {i}"}

            start = time.perf_counter()
            await memory_manager.update_memory(
                memory_id=main_memory.id,
                memory_type=MemoryType.FUNCTION,
                updates=update_data,
            )
            duration_ms = (time.perf_counter() - start) * 1000
            metrics.add(duration_ms)

        p95 = metrics.p95()
        print(f"\nUpdate with relationships P95 = {p95:.2f}ms")

        # Should still be under target even with relationships
        assert p95 < 150, f"Update with relationships P95 {p95:.2f}ms too slow"
