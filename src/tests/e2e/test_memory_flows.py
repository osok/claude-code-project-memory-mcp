"""E2E tests for memory persistence flows (E2E-001 to E2E-003).

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
from uuid import uuid4

from memory_service.models import (
    MemoryType,
    RequirementsMemory,
    DesignMemory,
)
from memory_service.core.memory_manager import MemoryManager
from memory_service.core.query_engine import QueryEngine


class TestMemoryPersistenceFlows:
    """E2E tests for memory persistence flows."""

    @pytest.mark.asyncio
    async def test_e2e001_memory_persists_across_operations(
        self,
        e2e_memory_manager: MemoryManager,
        e2e_query_engine: QueryEngine,
    ) -> None:
        """E2E-001: Memory added is retrievable in subsequent operations.

        Simulates: Session 1 adds memory -> Session 2 retrieves it.
        """
        # Session 1: Add memory
        memory = RequirementsMemory(
            id=uuid4(),
            type=MemoryType.REQUIREMENTS,
            content="System shall support user authentication via OAuth2",
            requirement_id="REQ-AUTH-TEST-001",
            title="OAuth2 Authentication",
            description="Support OAuth2 authentication flow",
            priority="Critical",
            status="Approved",
            source_document="requirements.md",
        )

        memory_id, _ = await e2e_memory_manager.add_memory(memory)

        # Session 2: Retrieve memory (simulated by creating new request)
        retrieved = await e2e_memory_manager.get_memory(
            memory_id=memory_id,
            memory_type=MemoryType.REQUIREMENTS,
        )

        assert retrieved is not None
        assert retrieved.id == memory_id
        assert retrieved.content == memory.content
        assert retrieved.requirement_id == "REQ-AUTH-TEST-001"

        # Session 2: Search for memory
        results = await e2e_query_engine.semantic_search(
            query="OAuth2 authentication user login",
            memory_types=[MemoryType.REQUIREMENTS],
            limit=10,
        )

        found_ids = [str(r.id) for r in results]
        assert str(memory_id) in found_ids

    @pytest.mark.asyncio
    async def test_e2e002_full_memory_lifecycle(
        self,
        e2e_memory_manager: MemoryManager,
        e2e_query_engine: QueryEngine,
    ) -> None:
        """E2E-002: Full memory lifecycle via MCP tools - Add -> Search -> Get.

        Tests the complete flow that Claude Code would use.
        """
        # Step 1: Add memory (memory_add tool)
        memory = DesignMemory(
            id=uuid4(),
            type=MemoryType.DESIGN,
            content="Use JWT tokens for stateless authentication with 1-hour expiry",
            design_type="ADR",
            title="ADR-AUTH-001: Token Strategy",
            decision="Use JWT with 1-hour expiry",
            rationale="Stateless tokens reduce server load and enable horizontal scaling",
            status="Accepted",
        )

        memory_id, conflicts = await e2e_memory_manager.add_memory(memory)
        assert memory_id is not None

        # Step 2: Search for memory (memory_search tool)
        search_results = await e2e_query_engine.semantic_search(
            query="JWT authentication token expiry strategy",
            memory_types=[MemoryType.DESIGN],
            limit=10,
        )

        assert len(search_results) > 0
        found = [r for r in search_results if str(r.id) == str(memory_id)]
        assert len(found) == 1
        assert found[0].score > 0.5  # Should have good similarity

        # Step 3: Get memory details (memory_get tool)
        details = await e2e_memory_manager.get_memory(
            memory_id=memory_id,
            memory_type=MemoryType.DESIGN,
        )

        assert details is not None
        assert details.title == "ADR-AUTH-001: Token Strategy"
        assert "JWT" in details.content
        assert details.decision == "Use JWT with 1-hour expiry"

    @pytest.mark.asyncio
    async def test_e2e003_bulk_add_followed_by_search(
        self,
        e2e_memory_manager: MemoryManager,
        e2e_query_engine: QueryEngine,
    ) -> None:
        """E2E-003: Batch import followed by search.

        Tests bulk operations used during project initialization.
        """
        # Bulk add multiple requirements (memory_bulk_add tool)
        requirements = [
            RequirementsMemory(
                id=uuid4(),
                type=MemoryType.REQUIREMENTS,
                content=f"Bulk requirement {i}: System shall {topic}",
                requirement_id=f"REQ-MEM-BULK-{i:03d}",
                title=f"Bulk Requirement {i}",
                description=f"Description for {topic}",
                priority="High" if i < 3 else "Medium",
                status="Approved",
                source_document="bulk-import.md",
            )
            for i, topic in enumerate([
                "support user registration with email verification",
                "enforce password complexity requirements",
                "implement rate limiting on API endpoints",
                "log all authentication attempts",
                "support multi-factor authentication",
            ])
        ]

        added_ids, errors = await e2e_memory_manager.bulk_add_memories(
            memories=requirements,
            check_conflicts=False,
        )

        assert len(added_ids) == 5
        assert len(errors) == 0

        # Search across bulk-added memories (memory_search tool)
        # Search 1: Authentication related
        auth_results = await e2e_query_engine.semantic_search(
            query="authentication security login",
            memory_types=[MemoryType.REQUIREMENTS],
            limit=10,
        )

        assert len(auth_results) >= 2  # Should find MFA and auth logging

        # Search 2: API security
        api_results = await e2e_query_engine.semantic_search(
            query="API rate limiting protection",
            memory_types=[MemoryType.REQUIREMENTS],
            limit=10,
        )

        assert len(api_results) >= 1

        # Verify specific requirements are searchable
        password_results = await e2e_query_engine.semantic_search(
            query="password complexity strength requirements",
            memory_types=[MemoryType.REQUIREMENTS],
            limit=5,
        )

        assert len(password_results) >= 1


class TestMemoryUpdateAndDeleteFlows:
    """E2E tests for memory update and delete operations."""

    @pytest.mark.asyncio
    async def test_update_flow(
        self,
        e2e_memory_manager: MemoryManager,
        e2e_query_engine: QueryEngine,
    ) -> None:
        """Test memory update flow."""
        # Create initial memory
        memory = RequirementsMemory(
            id=uuid4(),
            type=MemoryType.REQUIREMENTS,
            content="Initial requirement content",
            requirement_id="REQ-MEM-UPD-001",
            title="Update Test",
            description="Initial description",
            priority="Medium",
            status="Draft",
            source_document="test.md",
        )

        memory_id, _ = await e2e_memory_manager.add_memory(memory)

        # Update memory (memory_update tool)
        updated = await e2e_memory_manager.update_memory(
            memory_id=memory_id,
            memory_type=MemoryType.REQUIREMENTS,
            updates={
                "content": "Updated requirement content with more details",
                "priority": "High",
                "status": "Approved",
            },
        )

        assert updated is not None
        assert "Updated requirement" in updated.content
        assert updated.priority == "High"
        assert updated.status == "Approved"

        # Verify updated content is searchable
        results = await e2e_query_engine.semantic_search(
            query="Updated requirement details",
            memory_types=[MemoryType.REQUIREMENTS],
            limit=5,
        )

        found = [r for r in results if str(r.id) == str(memory_id)]
        assert len(found) == 1

    @pytest.mark.asyncio
    async def test_delete_flow(
        self,
        e2e_memory_manager: MemoryManager,
        e2e_query_engine: QueryEngine,
    ) -> None:
        """Test memory delete flow."""
        # Create memory
        memory = RequirementsMemory(
            id=uuid4(),
            type=MemoryType.REQUIREMENTS,
            content="Memory to be deleted in E2E test",
            requirement_id="REQ-MEM-DEL-001",
            title="Delete Test",
            description="Will be deleted",
            priority="Low",
            status="Draft",
            source_document="test.md",
        )

        memory_id, _ = await e2e_memory_manager.add_memory(memory)

        # Verify it's searchable
        results_before = await e2e_query_engine.semantic_search(
            query="Memory deleted E2E test",
            memory_types=[MemoryType.REQUIREMENTS],
            limit=10,
        )
        assert any(str(r.id) == str(memory_id) for r in results_before)

        # Delete memory (memory_delete tool)
        deleted = await e2e_memory_manager.delete_memory(
            memory_id=memory_id,
            memory_type=MemoryType.REQUIREMENTS,
            soft_delete=True,
        )

        assert deleted is True

        # Verify it's no longer searchable
        results_after = await e2e_query_engine.semantic_search(
            query="Memory deleted E2E test",
            memory_types=[MemoryType.REQUIREMENTS],
            limit=10,
        )
        assert not any(str(r.id) == str(memory_id) for r in results_after)
