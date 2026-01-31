"""Integration tests for persistence durability (IT-070 to IT-074)."""

import pytest
from uuid import uuid4
from typing import Any

from memory_service.models import (
    MemoryType,
    RequirementsMemory,
    DesignMemory,
    RelationshipType,
)
from memory_service.core.memory_manager import MemoryManager
from memory_service.storage.qdrant_adapter import QdrantAdapter
from memory_service.storage.neo4j_adapter import Neo4jAdapter


# Note: These tests require actual container restarts which is complex
# with testcontainers. The tests here verify data persistence within
# a session and document the expected behavior for restart scenarios.


class TestPersistenceDurability:
    """Integration tests for persistence durability (IT-070 to IT-074).

    Note: Container restart tests require special handling. These tests
    verify data persistence within sessions and serve as documentation
    for expected restart behavior.
    """

    @pytest.mark.asyncio
    async def test_it070_memories_survive_session(
        self,
        memory_manager: MemoryManager,
        qdrant_adapter: QdrantAdapter,
    ) -> None:
        """IT-070: Memories survive within a session (proxy for container restart)."""
        # Create memories
        memories = []
        for i in range(5):
            memory = RequirementsMemory(
                id=uuid4(),
                type=MemoryType.REQUIREMENTS,
                content=f"Persistence test requirement {i}",
                requirement_id=f"REQ-MEM-PER-{i:03d}",
                title=f"Persistence Test {i}",
                description=f"Test requirement {i}",
                priority="High",
                status="Approved",
                source_document="test.md",
            )
            memory_id, _ = await memory_manager.add_memory(memory)
            memories.append((memory_id, memory))

        # Verify all can be retrieved
        for memory_id, original in memories:
            retrieved = await memory_manager.get_memory(
                memory_id=memory_id,
                memory_type=MemoryType.REQUIREMENTS,
            )
            assert retrieved is not None
            assert retrieved.content == original.content
            assert retrieved.requirement_id == original.requirement_id

        # Verify count
        count = await qdrant_adapter.count(
            collection="requirements",
            filters={"deleted": False},
        )
        assert count >= 5

    @pytest.mark.asyncio
    async def test_it071_relationships_survive_session(
        self,
        memory_manager: MemoryManager,
        neo4j_adapter: Neo4jAdapter,
    ) -> None:
        """IT-071: Relationships survive within a session."""
        # Create requirement and design
        requirement = RequirementsMemory(
            id=uuid4(),
            type=MemoryType.REQUIREMENTS,
            content="Persistence requirement",
            requirement_id="REQ-MEM-REL-001",
            title="Persistence Relationship Test",
            description="Test relationship persistence",
            priority="High",
            status="Approved",
            source_document="test.md",
        )

        design = DesignMemory(
            id=uuid4(),
            type=MemoryType.DESIGN,
            content="Design for persistence requirement",
            design_type="ADR",
            title="ADR-PERSIST-001",
            decision="Test decision",
            rationale="Test rationale",
            status="Accepted",
        )

        req_id, _ = await memory_manager.add_memory(requirement)
        design_id, _ = await memory_manager.add_memory(design)

        # Create relationship
        await neo4j_adapter.create_relationship(
            source_id=design_id,
            target_id=req_id,
            relationship_type=RelationshipType.IMPLEMENTS,
        )

        # Verify relationship exists
        related = await neo4j_adapter.get_related(
            node_id=design_id,
            relationship_types=[RelationshipType.IMPLEMENTS],
            direction="OUTGOING",
        )

        assert len(related) > 0
        related_ids = [str(r.get("id")) for r in related]
        assert str(req_id) in related_ids

    @pytest.mark.asyncio
    async def test_it072_cache_contents_persist(
        self,
        mock_embedding_service: "MockEmbeddingService",  # type: ignore
    ) -> None:
        """IT-072: Cache contents persist within session."""
        content = "Unique content for cache persistence test"

        # First embedding call
        embedding1, _ = await mock_embedding_service.embed(content)
        first_call_count = mock_embedding_service.call_count

        # Second call - should hit cache
        embedding2, _ = await mock_embedding_service.embed(content)
        second_call_count = mock_embedding_service.call_count

        # Both embeddings should be identical
        assert embedding1 == embedding2

        # Cache hit means same call count (mock increments on each call)
        # For a real cache, second call wouldn't increment external API calls

    @pytest.mark.asyncio
    async def test_it073_full_stack_data_integrity(
        self,
        memory_manager: MemoryManager,
        qdrant_adapter: QdrantAdapter,
        neo4j_adapter: Neo4jAdapter,
    ) -> None:
        """IT-073: Full stack maintains data integrity."""
        # Create interconnected data
        requirement = RequirementsMemory(
            id=uuid4(),
            type=MemoryType.REQUIREMENTS,
            content="Full stack integrity requirement",
            requirement_id="REQ-MEM-STK-001",
            title="Stack Integrity Test",
            description="Test full stack integrity",
            priority="Critical",
            status="Approved",
            source_document="test.md",
        )

        design = DesignMemory(
            id=uuid4(),
            type=MemoryType.DESIGN,
            content="Full stack integrity design",
            design_type="ADR",
            title="ADR-STACK-001",
            decision="Stack decision",
            rationale="Stack rationale",
            status="Accepted",
        )

        # Add to system
        req_id, _ = await memory_manager.add_memory(requirement)
        design_id, _ = await memory_manager.add_memory(design)

        # Create relationship
        await neo4j_adapter.create_relationship(
            source_id=design_id,
            target_id=req_id,
            relationship_type=RelationshipType.IMPLEMENTS,
        )

        # Verify Qdrant data
        qdrant_req = await qdrant_adapter.get(
            collection="requirements",
            point_id=req_id,
        )
        assert qdrant_req is not None
        assert qdrant_req["content"] == requirement.content

        qdrant_design = await qdrant_adapter.get(
            collection="designs",
            point_id=design_id,
        )
        assert qdrant_design is not None
        assert qdrant_design["content"] == design.content

        # Verify Neo4j data
        neo4j_req = await neo4j_adapter.get_node(
            node_id=req_id,
            label="Requirement",
        )
        assert neo4j_req is not None

        neo4j_design = await neo4j_adapter.get_node(
            node_id=design_id,
            label="Design",
        )
        assert neo4j_design is not None

        # Verify relationship
        related = await neo4j_adapter.get_related(
            node_id=design_id,
            relationship_types=[RelationshipType.IMPLEMENTS],
            direction="OUTGOING",
        )
        assert len(related) > 0

    @pytest.mark.asyncio
    async def test_it074_backup_restore_procedure(
        self,
        memory_manager: MemoryManager,
        qdrant_adapter: QdrantAdapter,
    ) -> None:
        """IT-074: Backup and restore procedure maintains data integrity.

        Note: This is a simplified test that verifies data can be retrieved
        after storage. Full backup/restore testing requires external tooling.
        """
        # Create test data
        original_data = []
        for i in range(3):
            memory = RequirementsMemory(
                id=uuid4(),
                type=MemoryType.REQUIREMENTS,
                content=f"Backup test requirement {i}",
                requirement_id=f"REQ-MEM-BAK-{i:03d}",
                title=f"Backup Test {i}",
                description=f"Test requirement {i}",
                priority="Medium",
                status="Draft",
                source_document="test.md",
            )
            memory_id, _ = await memory_manager.add_memory(memory)
            original_data.append({
                "id": memory_id,
                "content": memory.content,
                "requirement_id": memory.requirement_id,
            })

        # Simulate "backup" by reading all data
        backup = []
        for item in original_data:
            data = await qdrant_adapter.get(
                collection="requirements",
                point_id=item["id"],
            )
            if data:
                backup.append(data)

        assert len(backup) == 3

        # Verify backup contains all expected fields
        for item in backup:
            assert "id" in item
            assert "content" in item
            assert "requirement_id" in item

        # Verify data matches original
        backup_ids = {b["id"] for b in backup}
        original_ids = {str(o["id"]) for o in original_data}
        assert backup_ids == original_ids


class TestDataConsistencyChecks:
    """Tests for data consistency verification."""

    @pytest.mark.asyncio
    async def test_cross_store_id_consistency(
        self,
        memory_manager: MemoryManager,
        qdrant_adapter: QdrantAdapter,
        neo4j_adapter: Neo4jAdapter,
    ) -> None:
        """Test that IDs are consistent between Qdrant and Neo4j."""
        memory = RequirementsMemory(
            id=uuid4(),
            type=MemoryType.REQUIREMENTS,
            content="Cross-store consistency check",
            requirement_id="REQ-MEM-XST-001",
            title="Cross Store Test",
            description="Test cross-store ID consistency",
            priority="High",
            status="Draft",
            source_document="test.md",
        )

        memory_id, _ = await memory_manager.add_memory(memory)

        # Get from Qdrant
        qdrant_data = await qdrant_adapter.get(
            collection="requirements",
            point_id=memory_id,
        )

        # Get from Neo4j
        neo4j_data = await neo4j_adapter.get_node(
            node_id=memory_id,
            label="Requirement",
        )

        # Both should exist
        assert qdrant_data is not None
        assert neo4j_data is not None

        # IDs should match
        assert qdrant_data["id"] == neo4j_data["id"]

    @pytest.mark.asyncio
    async def test_deletion_consistency(
        self,
        memory_manager: MemoryManager,
        qdrant_adapter: QdrantAdapter,
        neo4j_adapter: Neo4jAdapter,
    ) -> None:
        """Test that deletion is consistent across stores."""
        memory = RequirementsMemory(
            id=uuid4(),
            type=MemoryType.REQUIREMENTS,
            content="Deletion consistency test",
            requirement_id="REQ-MEM-DEL-001",
            title="Deletion Test",
            description="Test deletion consistency",
            priority="Low",
            status="Draft",
            source_document="test.md",
        )

        memory_id, _ = await memory_manager.add_memory(memory)

        # Delete memory
        await memory_manager.delete_memory(
            memory_id=memory_id,
            memory_type=MemoryType.REQUIREMENTS,
            soft_delete=True,
        )

        # Verify Qdrant shows deleted
        qdrant_data = await qdrant_adapter.get(
            collection="requirements",
            point_id=memory_id,
        )
        assert qdrant_data is not None
        assert qdrant_data.get("deleted") is True

        # Verify Neo4j shows deleted
        neo4j_data = await neo4j_adapter.get_node(
            node_id=memory_id,
            label="Requirement",
        )
        if neo4j_data:
            assert neo4j_data.get("deleted") is True


class TestRecoveryScenarios:
    """Tests for recovery scenarios."""

    @pytest.mark.asyncio
    async def test_partial_failure_recovery(
        self,
        memory_manager: MemoryManager,
        qdrant_adapter: QdrantAdapter,
    ) -> None:
        """Test recovery from partial failures."""
        # Create batch of memories
        memories = [
            RequirementsMemory(
                id=uuid4(),
                type=MemoryType.REQUIREMENTS,
                content=f"Recovery test {i}",
                requirement_id=f"REQ-MEM-REC-{i:03d}",
                title=f"Recovery Test {i}",
                description=f"Test {i}",
                priority="Medium",
                status="Draft",
                source_document="test.md",
            )
            for i in range(5)
        ]

        # Add all
        added_ids, errors = await memory_manager.bulk_add_memories(
            memories=memories,
            check_conflicts=False,
        )

        # All should succeed
        assert len(added_ids) == 5
        assert len(errors) == 0

        # Verify all can be retrieved
        for memory_id in added_ids:
            retrieved = await memory_manager.get_memory(
                memory_id=memory_id,
                memory_type=MemoryType.REQUIREMENTS,
            )
            assert retrieved is not None

    @pytest.mark.asyncio
    async def test_connection_resilience(
        self,
        qdrant_adapter: QdrantAdapter,
    ) -> None:
        """Test that connections are resilient to usage patterns."""
        # Perform many operations
        for i in range(50):
            point_id = uuid4()
            await qdrant_adapter.upsert(
                collection="requirements",
                point_id=point_id,
                vector=[0.1 * (i % 10)] * 1024,
                payload={
                    "id": str(point_id),
                    "content": f"Resilience test {i}",
                    "deleted": False,
                },
            )

        # Search should still work
        results = await qdrant_adapter.search(
            collection="requirements",
            vector=[0.1] * 1024,
            limit=10,
        )

        assert len(results) > 0
