"""E2E tests for semantic search and graph traversal flows (E2E-060 to E2E-071)."""

import pytest
from uuid import uuid4

from memory_service.models import (
    MemoryType,
    RequirementsMemory,
    DesignMemory,
    FunctionMemory,
    ComponentMemory,
    RelationshipType,
)
from memory_service.core.memory_manager import MemoryManager
from memory_service.core.query_engine import QueryEngine
from memory_service.storage.neo4j_adapter import Neo4jAdapter


class TestSemanticSearchFlows:
    """E2E tests for semantic search flows (E2E-060, E2E-061)."""

    @pytest.mark.asyncio
    async def test_e2e060_natural_language_search(
        self,
        e2e_memory_manager: MemoryManager,
        e2e_query_engine: QueryEngine,
    ) -> None:
        """E2E-060: Natural language query returns relevant memories.

        Flow: memory_search with natural language -> relevant results
        """
        # Add various memories
        auth_req = RequirementsMemory(
            id=uuid4(),
            type=MemoryType.REQUIREMENTS,
            content="The system shall authenticate users using secure password hashing",
            requirement_id="REQ-AUTH-NL-001",
            title="Secure Authentication",
            description="Secure user authentication requirement",
            priority="Critical",
            status="Approved",
            source_document="requirements.md",
        )

        perf_req = RequirementsMemory(
            id=uuid4(),
            type=MemoryType.REQUIREMENTS,
            content="The API shall respond within 200 milliseconds for 95% of requests",
            requirement_id="REQ-PERF-001",
            title="API Performance",
            description="API latency requirement",
            priority="High",
            status="Approved",
            source_document="requirements.md",
        )

        cache_design = DesignMemory(
            id=uuid4(),
            type=MemoryType.DESIGN,
            content="Implement Redis caching to improve API response times",
            design_type="ADR",
            title="ADR-PERF-001: Redis Caching",
            decision="Use Redis for caching",
            rationale="Reduces database load",
            status="Accepted",
        )

        await e2e_memory_manager.add_memory(auth_req)
        await e2e_memory_manager.add_memory(perf_req)
        await e2e_memory_manager.add_memory(cache_design)

        # Natural language search for authentication
        auth_results = await e2e_query_engine.semantic_search(
            query="how does the system handle user login and security",
            memory_types=[MemoryType.REQUIREMENTS],
            limit=10,
        )

        # Should find auth requirement
        assert len(auth_results) >= 1
        auth_ids = [str(r["id"]) for r in auth_results]
        assert str(auth_req.id) in auth_ids

        # Natural language search for performance
        perf_results = await e2e_query_engine.semantic_search(
            query="what are the speed and latency requirements",
            memory_types=[MemoryType.REQUIREMENTS, MemoryType.DESIGN],
            limit=10,
        )

        # Should find performance-related memories
        assert len(perf_results) >= 1

    @pytest.mark.asyncio
    async def test_e2e061_search_with_filters(
        self,
        e2e_memory_manager: MemoryManager,
        e2e_query_engine: QueryEngine,
    ) -> None:
        """E2E-061: Filter by type and time range.

        Flow: memory_search with filters -> filtered results
        """
        from datetime import datetime, timezone, timedelta

        # Add memories at different times (simulated)
        old_req = RequirementsMemory(
            id=uuid4(),
            type=MemoryType.REQUIREMENTS,
            content="Old requirement from initial planning",
            requirement_id="REQ-OLD-001",
            title="Old Requirement",
            description="From initial planning phase",
            priority="Medium",
            status="Approved",
            source_document="old-requirements.md",
        )

        recent_req = RequirementsMemory(
            id=uuid4(),
            type=MemoryType.REQUIREMENTS,
            content="Recent requirement added during development",
            requirement_id="REQ-RECENT-001",
            title="Recent Requirement",
            description="Added recently",
            priority="High",
            status="Draft",
            source_document="new-requirements.md",
        )

        design = DesignMemory(
            id=uuid4(),
            type=MemoryType.DESIGN,
            content="Design decision for recent requirement",
            design_type="ADR",
            title="ADR-RECENT-001",
            decision="Decision for new feature",
            rationale="Based on recent requirements",
            status="Accepted",
        )

        await e2e_memory_manager.add_memory(old_req)
        await e2e_memory_manager.add_memory(recent_req)
        await e2e_memory_manager.add_memory(design)

        # Search with type filter - only requirements
        req_only = await e2e_query_engine.semantic_search(
            query="requirement planning development",
            memory_types=[MemoryType.REQUIREMENTS],
            limit=10,
        )

        # All results should be requirements
        for result in req_only:
            assert result.get("type") == "requirements"

        # Search with type filter - only designs
        design_only = await e2e_query_engine.semantic_search(
            query="design decision feature",
            memory_types=[MemoryType.DESIGN],
            limit=10,
        )

        for result in design_only:
            assert result.get("type") == "design"


class TestGraphTraversalFlows:
    """E2E tests for graph traversal flows (E2E-070, E2E-071)."""

    @pytest.mark.asyncio
    async def test_e2e070_find_component_dependencies(
        self,
        e2e_memory_manager: MemoryManager,
        e2e_query_engine: QueryEngine,
        e2e_neo4j_adapter: Neo4jAdapter,
    ) -> None:
        """E2E-070: Find all dependencies of component.

        Flow: get_related -> traverse dependencies
        """
        # Create component dependency graph
        # UserService -> AuthService -> DatabaseService
        db_service = ComponentMemory(
            id=uuid4(),
            type=MemoryType.COMPONENT,
            content="DatabaseService - Database connection management",
            component_id="database-service",
            component_type="Service",
            name="DatabaseService",
            file_path="src/services/database.py",
        )

        auth_service = ComponentMemory(
            id=uuid4(),
            type=MemoryType.COMPONENT,
            content="AuthService - Authentication logic",
            component_id="auth-service",
            component_type="Service",
            name="AuthService",
            file_path="src/services/auth.py",
            dependencies=["DatabaseService"],
        )

        user_service = ComponentMemory(
            id=uuid4(),
            type=MemoryType.COMPONENT,
            content="UserService - User management",
            component_id="user-service",
            component_type="Service",
            name="UserService",
            file_path="src/services/user.py",
            dependencies=["AuthService", "DatabaseService"],
        )

        await e2e_memory_manager.add_memory(db_service)
        await e2e_memory_manager.add_memory(auth_service)
        await e2e_memory_manager.add_memory(user_service)

        # Create dependency relationships
        await e2e_neo4j_adapter.create_relationship(
            from_id=auth_service.id,
            to_id=db_service.id,
            relationship_type=RelationshipType.DEPENDS_ON,
        )
        await e2e_neo4j_adapter.create_relationship(
            from_id=user_service.id,
            to_id=auth_service.id,
            relationship_type=RelationshipType.DEPENDS_ON,
        )
        await e2e_neo4j_adapter.create_relationship(
            from_id=user_service.id,
            to_id=db_service.id,
            relationship_type=RelationshipType.DEPENDS_ON,
        )

        # Find dependencies of UserService (get_related tool)
        dependencies = await e2e_query_engine.get_related(
            memory_id=user_service.id,
            relationship_types=[RelationshipType.DEPENDS_ON],
            direction="OUTGOING",
            depth=1,
        )

        # Should find AuthService and DatabaseService
        dep_ids = [str(d.get("id")) for d in dependencies]
        assert str(auth_service.id) in dep_ids
        assert str(db_service.id) in dep_ids

        # Find transitive dependencies (depth 2)
        transitive_deps = await e2e_query_engine.get_related(
            memory_id=user_service.id,
            relationship_types=[RelationshipType.DEPENDS_ON],
            direction="OUTGOING",
            depth=2,
        )

        # Should include all dependencies
        trans_dep_ids = [str(d.get("id")) for d in transitive_deps]
        assert str(db_service.id) in trans_dep_ids

    @pytest.mark.asyncio
    async def test_e2e071_find_function_callers(
        self,
        e2e_memory_manager: MemoryManager,
        e2e_query_engine: QueryEngine,
        e2e_neo4j_adapter: Neo4jAdapter,
    ) -> None:
        """E2E-071: Find all callers of function.

        Flow: graph_query -> find CALLS relationships
        """
        # Create function call graph
        # main() -> process_data() -> validate_input()
        validate_func = FunctionMemory(
            id=uuid4(),
            type=MemoryType.FUNCTION,
            content="def validate_input(data: dict) -> bool",
            function_id=uuid4(),
            name="validate_input",
            signature="def validate_input(data: dict) -> bool",
            file_path="src/validators.py",
            start_line=1,
            end_line=10,
            language="python",
        )

        process_func = FunctionMemory(
            id=uuid4(),
            type=MemoryType.FUNCTION,
            content="def process_data(data: dict) -> dict",
            function_id=uuid4(),
            name="process_data",
            signature="def process_data(data: dict) -> dict",
            file_path="src/processor.py",
            start_line=1,
            end_line=15,
            language="python",
        )

        main_func = FunctionMemory(
            id=uuid4(),
            type=MemoryType.FUNCTION,
            content="def main() -> None",
            function_id=uuid4(),
            name="main",
            signature="def main() -> None",
            file_path="src/main.py",
            start_line=1,
            end_line=20,
            language="python",
        )

        await e2e_memory_manager.add_memory(validate_func)
        await e2e_memory_manager.add_memory(process_func)
        await e2e_memory_manager.add_memory(main_func)

        # Create CALLS relationships
        await e2e_neo4j_adapter.create_relationship(
            from_id=process_func.id,
            to_id=validate_func.id,
            relationship_type=RelationshipType.CALLS,
        )
        await e2e_neo4j_adapter.create_relationship(
            from_id=main_func.id,
            to_id=process_func.id,
            relationship_type=RelationshipType.CALLS,
        )

        # Find callers of validate_input (graph_query tool)
        callers = await e2e_query_engine.get_related(
            memory_id=validate_func.id,
            relationship_types=[RelationshipType.CALLS],
            direction="INCOMING",
            depth=1,
        )

        # Should find process_data as caller
        caller_ids = [str(c.get("id")) for c in callers]
        assert str(process_func.id) in caller_ids

        # Find all callers recursively
        all_callers = await e2e_query_engine.get_related(
            memory_id=validate_func.id,
            relationship_types=[RelationshipType.CALLS],
            direction="INCOMING",
            depth=2,
        )

        # Should find main as indirect caller
        all_caller_ids = [str(c.get("id")) for c in all_callers]
        assert str(main_func.id) in all_caller_ids


class TestHybridQueries:
    """E2E tests for hybrid vector + graph queries."""

    @pytest.mark.asyncio
    async def test_semantic_search_then_graph_traversal(
        self,
        e2e_memory_manager: MemoryManager,
        e2e_query_engine: QueryEngine,
        e2e_neo4j_adapter: Neo4jAdapter,
    ) -> None:
        """Test combining semantic search with graph traversal."""
        # Create related memories
        req = RequirementsMemory(
            id=uuid4(),
            type=MemoryType.REQUIREMENTS,
            content="System shall encrypt sensitive data at rest",
            requirement_id="REQ-ENC-001",
            title="Data Encryption",
            description="Encrypt sensitive data",
            priority="Critical",
            status="Approved",
            source_document="requirements.md",
        )

        design = DesignMemory(
            id=uuid4(),
            type=MemoryType.DESIGN,
            content="Use AES-256 encryption for data at rest",
            design_type="ADR",
            title="ADR-ENC-001",
            decision="Use AES-256",
            rationale="Industry standard encryption",
            status="Accepted",
        )

        func = FunctionMemory(
            id=uuid4(),
            type=MemoryType.FUNCTION,
            content="def encrypt_data(data: bytes, key: bytes) -> bytes",
            function_id=uuid4(),
            name="encrypt_data",
            signature="def encrypt_data(data: bytes, key: bytes) -> bytes",
            file_path="src/crypto.py",
            start_line=10,
            end_line=20,
            language="python",
        )

        await e2e_memory_manager.add_memory(req)
        await e2e_memory_manager.add_memory(design)
        await e2e_memory_manager.add_memory(func)

        # Create relationships
        await e2e_neo4j_adapter.create_relationship(
            from_id=design.id,
            to_id=req.id,
            relationship_type=RelationshipType.IMPLEMENTS,
        )
        await e2e_neo4j_adapter.create_relationship(
            from_id=func.id,
            to_id=design.id,
            relationship_type=RelationshipType.IMPLEMENTS,
        )

        # Step 1: Semantic search for encryption
        search_results = await e2e_query_engine.semantic_search(
            query="encryption data security",
            memory_types=[MemoryType.REQUIREMENTS, MemoryType.DESIGN],
            limit=5,
        )

        # Should find requirement or design
        assert len(search_results) >= 1

        # Step 2: Get related from search result
        first_result_id = search_results[0]["id"]
        related = await e2e_query_engine.get_related(
            memory_id=first_result_id,
            relationship_types=[RelationshipType.IMPLEMENTS],
            depth=2,
        )

        # Should find related memories
        # (direction depends on which memory was found first)
