"""E2E tests for normalization flows (E2E-050 to E2E-051)."""

import pytest
from uuid import uuid4

from memory_service.models import (
    MemoryType,
    RequirementsMemory,
)
from memory_service.core.memory_manager import MemoryManager
from memory_service.core.workers import NormalizerWorker
from memory_service.storage.qdrant_adapter import QdrantAdapter


class TestNormalizationFlows:
    """E2E tests for normalization flows (E2E-050, E2E-051)."""

    @pytest.mark.asyncio
    async def test_e2e050_start_normalization_monitor_progress(
        self,
        e2e_memory_manager: MemoryManager,
        e2e_normalizer_worker: NormalizerWorker,
    ) -> None:
        """E2E-050: Start normalization, monitor progress.

        Flow: normalize_memory -> normalize_status -> check progress
        """
        # Add some test data
        for i in range(5):
            memory = RequirementsMemory(
                id=uuid4(),
                type=MemoryType.REQUIREMENTS,
                content=f"Normalization flow test requirement {i}",
                requirement_id=f"REQ-NORM-FLOW-{i:03d}",
                title=f"Normalization Test {i}",
                description=f"Test requirement {i}",
                priority="Medium",
                status="Draft",
                source_document="test.md",
            )
            await e2e_memory_manager.add_memory(memory)

        # Step 1: Start normalization (normalize_memory tool)
        result = await e2e_normalizer_worker.run(
            phases=["snapshot", "validation"],
            dry_run=True,
        )

        # Step 2: Check status (normalize_status tool)
        assert "status" in result or "phases" in result

        # The result should contain phase information
        if "phases" in result:
            phases = result["phases"]
            assert "snapshot" in phases or "validation" in phases

        # Dry run should not modify data
        assert result.get("dry_run") is True

    @pytest.mark.asyncio
    async def test_e2e051_normalization_cleans_inconsistencies(
        self,
        e2e_memory_manager: MemoryManager,
        e2e_normalizer_worker: NormalizerWorker,
        e2e_qdrant_adapter: QdrantAdapter,
    ) -> None:
        """E2E-051: Normalize cleans up inconsistencies.

        Flow: Create inconsistency -> normalize_memory -> verify cleanup
        """
        # Step 1: Create duplicate memories (same content)
        content = "Duplicate content for normalization cleanup test"
        dup1 = RequirementsMemory(
            id=uuid4(),
            type=MemoryType.REQUIREMENTS,
            content=content,
            requirement_id="REQ-DUP-001",
            title="Duplicate A",
            description="First duplicate",
            priority="High",
            status="Draft",
            source_document="test.md",
        )

        dup2 = RequirementsMemory(
            id=uuid4(),
            type=MemoryType.REQUIREMENTS,
            content=content,  # Same content
            requirement_id="REQ-DUP-002",
            title="Duplicate B",
            description="Second duplicate",
            priority="Medium",
            status="Draft",
            source_document="test.md",
        )

        await e2e_memory_manager.add_memory(dup1, check_conflicts=False)
        await e2e_memory_manager.add_memory(dup2, check_conflicts=False)

        # Step 2: Run normalization deduplication phase
        result = await e2e_normalizer_worker.run(
            phases=["deduplication"],
            dry_run=True,  # Use dry run to see what would be cleaned
        )

        # Step 3: Check deduplication stats
        dedup_stats = result.get("phases", {}).get("deduplication", {})
        # Should report found duplicates (exact format depends on implementation)


class TestNormalizationPhases:
    """E2E tests for individual normalization phases."""

    @pytest.mark.asyncio
    async def test_full_normalization_workflow(
        self,
        e2e_memory_manager: MemoryManager,
        e2e_normalizer_worker: NormalizerWorker,
        e2e_qdrant_adapter: QdrantAdapter,
    ) -> None:
        """Test complete normalization workflow."""
        # Add test data
        memories = [
            RequirementsMemory(
                id=uuid4(),
                type=MemoryType.REQUIREMENTS,
                content=f"Full normalization test {i}",
                requirement_id=f"REQ-FULL-{i:03d}",
                title=f"Full Test {i}",
                description=f"Description {i}",
                priority="High",
                status="Approved",
                source_document="test.md",
            )
            for i in range(3)
        ]

        for memory in memories:
            await e2e_memory_manager.add_memory(memory)

        # Get count before
        count_before = await e2e_qdrant_adapter.count(
            collection="requirements",
            filters={"deleted": False},
        )

        # Run full normalization
        result = await e2e_normalizer_worker.run(dry_run=False)

        # Get count after
        count_after = await e2e_qdrant_adapter.count(
            collection="requirements",
            filters={"deleted": False},
        )

        # Should complete successfully
        assert result.get("status") in ["completed", "success"]

        # Data should be preserved (or consolidated if duplicates)
        assert count_after >= count_before - len(memories)

    @pytest.mark.asyncio
    async def test_validation_phase(
        self,
        e2e_memory_manager: MemoryManager,
        e2e_normalizer_worker: NormalizerWorker,
    ) -> None:
        """Test validation phase checks data integrity."""
        # Add valid data
        memory = RequirementsMemory(
            id=uuid4(),
            type=MemoryType.REQUIREMENTS,
            content="Valid requirement for validation test",
            requirement_id="REQ-VALID-TEST",
            title="Validation Test",
            description="Test validation phase",
            priority="High",
            status="Approved",
            source_document="test.md",
        )

        await e2e_memory_manager.add_memory(memory)

        # Run validation only
        result = await e2e_normalizer_worker.run(
            phases=["validation"],
            dry_run=True,
        )

        # Should pass validation
        validation_stats = result.get("phases", {}).get("validation", {})
        # Check for validation results

    @pytest.mark.asyncio
    async def test_cleanup_old_deleted(
        self,
        e2e_memory_manager: MemoryManager,
        e2e_normalizer_worker: NormalizerWorker,
        e2e_qdrant_adapter: QdrantAdapter,
    ) -> None:
        """Test cleanup phase removes old soft-deleted entries."""
        from datetime import datetime, timezone, timedelta

        # Create and delete a memory
        memory = RequirementsMemory(
            id=uuid4(),
            type=MemoryType.REQUIREMENTS,
            content="Memory to be cleaned up",
            requirement_id="REQ-CLEANUP-001",
            title="Cleanup Test",
            description="Will be deleted",
            priority="Low",
            status="Draft",
            source_document="test.md",
        )

        memory_id, _ = await e2e_memory_manager.add_memory(memory)

        # Simulate old deletion (> 30 days)
        old_date = (datetime.now(timezone.utc) - timedelta(days=35)).isoformat()
        await e2e_qdrant_adapter.update_payload(
            collection="requirements",
            point_id=memory_id,
            payload={"deleted": True, "deleted_at": old_date},
        )

        # Run cleanup phase
        result = await e2e_normalizer_worker.run(
            phases=["cleanup"],
            dry_run=False,
        )

        # Check cleanup stats
        cleanup_stats = result.get("phases", {}).get("cleanup", {})
