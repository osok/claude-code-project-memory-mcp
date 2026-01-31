"""Pytest fixtures for the memory service tests."""

import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import Any
from uuid import uuid4

import pytest
from pydantic import SecretStr

from memory_service.config import Settings

# Import mock-src fixtures to make them available to all tests
# These provide comprehensive test fixtures using the mock application
from tests.conftest_mock_src import (
    mock_src_root,
    mock_src_python,
    mock_src_typescript,
    mock_src_go,
    mock_requirements_file,
    mock_design_file,
    expected_python_functions,
    expected_python_classes,
    expected_relationships,
    expected_file_counts,
    mock_codebase,
)
from memory_service.models import (
    BaseMemory,
    CodePatternMemory,
    ComponentMemory,
    DesignMemory,
    FunctionMemory,
    MemoryType,
    RequirementsMemory,
    SessionMemory,
    SyncStatus,
    TestHistoryMemory,
    UserPreferenceMemory,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings with mock values."""
    return Settings(
        qdrant_host="localhost",
        qdrant_port=6333,
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password=SecretStr("testpassword"),
        voyage_api_key=SecretStr("test-api-key"),
        log_level="DEBUG",
        log_format="console",
        metrics_enabled=False,
    )


@pytest.fixture
def sample_embedding() -> list[float]:
    """Create a sample 1024-dimensional embedding."""
    import random

    random.seed(42)
    return [random.random() for _ in range(1024)]


@pytest.fixture
def sample_requirements_memory(sample_embedding: list[float]) -> RequirementsMemory:
    """Create a sample requirements memory."""
    return RequirementsMemory(
        id=uuid4(),
        type=MemoryType.REQUIREMENTS,
        content="The system shall provide semantic search capabilities with sub-200ms latency",
        embedding=sample_embedding,
        requirement_id="REQ-MEM-FN-001",
        title="Semantic Search Latency",
        description="The system shall provide semantic search capabilities with sub-200ms latency",
        priority="High",
        status="Approved",
        source_document="requirements-memory-docs.md",
    )


@pytest.fixture
def sample_design_memory(sample_embedding: list[float]) -> DesignMemory:
    """Create a sample design memory."""
    return DesignMemory(
        id=uuid4(),
        type=MemoryType.DESIGN,
        content="Use Qdrant for vector storage with HNSW indexing",
        embedding=sample_embedding,
        design_type="ADR",
        title="ADR-001: Vector Database Selection",
        decision="Use Qdrant for vector storage",
        rationale="Qdrant provides efficient vector search with filtering capabilities",
        status="Accepted",
        related_requirements=["REQ-MEM-FN-001"],
    )


@pytest.fixture
def sample_code_pattern_memory(sample_embedding: list[float]) -> CodePatternMemory:
    """Create a sample code pattern memory."""
    return CodePatternMemory(
        id=uuid4(),
        type=MemoryType.CODE_PATTERN,
        content="Async context manager pattern for database connections",
        embedding=sample_embedding,
        pattern_name="Async Database Connection",
        pattern_type="Template",
        language="Python",
        code_template="""async with get_connection() as conn:
    result = await conn.execute(query)
    return result""",
        usage_context="Use for all database operations requiring connection management",
    )


@pytest.fixture
def sample_component_memory(sample_embedding: list[float]) -> ComponentMemory:
    """Create a sample component memory."""
    return ComponentMemory(
        id=uuid4(),
        type=MemoryType.COMPONENT,
        content="QdrantAdapter - Storage adapter for Qdrant vector database",
        embedding=sample_embedding,
        component_id="qdrant-adapter",
        component_type="Service",
        name="QdrantAdapter",
        file_path="src/memory_service/storage/qdrant_adapter.py",
        public_interface={
            "exports": [
                {"name": "QdrantAdapter", "type": "class", "signature": "class QdrantAdapter"},
                {"name": "upsert", "type": "function", "signature": "async def upsert(...)"},
            ]
        },
    )


@pytest.fixture
def sample_function_memory(sample_embedding: list[float]) -> FunctionMemory:
    """Create a sample function memory."""
    return FunctionMemory(
        id=uuid4(),
        type=MemoryType.FUNCTION,
        content="def semantic_search(query: str, limit: int = 10) -> list[SearchResult]",
        embedding=sample_embedding,
        function_id=uuid4(),
        name="semantic_search",
        signature="def semantic_search(query: str, limit: int = 10) -> list[SearchResult]",
        file_path="src/memory_service/core/query_engine.py",
        start_line=50,
        end_line=75,
        language="python",
        docstring="Perform semantic search across memories.",
    )


@pytest.fixture
def sample_test_history_memory(sample_embedding: list[float]) -> TestHistoryMemory:
    """Create a sample test history memory."""
    from datetime import datetime, timezone

    return TestHistoryMemory(
        id=uuid4(),
        type=MemoryType.TEST_HISTORY,
        content="test_semantic_search_returns_relevant_results",
        embedding=sample_embedding,
        test_id=uuid4(),
        test_name="test_semantic_search_returns_relevant_results",
        test_file="tests/unit/test_query_engine.py",
        execution_time=datetime.now(timezone.utc),
        status="Passed",
    )


@pytest.fixture
def sample_session_memory(sample_embedding: list[float]) -> SessionMemory:
    """Create a sample session memory."""
    from datetime import datetime, timezone

    return SessionMemory(
        id=uuid4(),
        type=MemoryType.SESSION,
        content="Implemented semantic search functionality with Qdrant integration",
        embedding=sample_embedding,
        session_id=uuid4(),
        start_time=datetime.now(timezone.utc),
        summary="Implemented semantic search functionality",
        key_decisions=["Use HNSW index with ef=200", "Batch embeddings for performance"],
    )


@pytest.fixture
def sample_user_preference_memory(sample_embedding: list[float]) -> UserPreferenceMemory:
    """Create a sample user preference memory."""
    return UserPreferenceMemory(
        id=uuid4(),
        type=MemoryType.USER_PREFERENCE,
        content="Prefer async/await over callbacks for all I/O operations",
        embedding=sample_embedding,
        preference_id=uuid4(),
        category="CodingStyle",
        key="async_pattern",
        value={"pattern": "async/await", "avoid": "callbacks"},
        scope="Language",
    )


@pytest.fixture
def all_sample_memories(
    sample_requirements_memory: RequirementsMemory,
    sample_design_memory: DesignMemory,
    sample_code_pattern_memory: CodePatternMemory,
    sample_component_memory: ComponentMemory,
    sample_function_memory: FunctionMemory,
    sample_test_history_memory: TestHistoryMemory,
    sample_session_memory: SessionMemory,
    sample_user_preference_memory: UserPreferenceMemory,
) -> list[BaseMemory]:
    """Return all sample memories."""
    return [
        sample_requirements_memory,
        sample_design_memory,
        sample_code_pattern_memory,
        sample_component_memory,
        sample_function_memory,
        sample_test_history_memory,
        sample_session_memory,
        sample_user_preference_memory,
    ]
