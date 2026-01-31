"""Integration test fixtures with testcontainers for Qdrant and Neo4j."""

import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import Any
from uuid import uuid4

import pytest
from pydantic import SecretStr

# Testcontainers imports
try:
    from testcontainers.qdrant import QdrantContainer
    from testcontainers.neo4j import Neo4jContainer
    TESTCONTAINERS_AVAILABLE = True
except ImportError:
    # Fallback for systems without testcontainers
    TESTCONTAINERS_AVAILABLE = False
    QdrantContainer = None  # type: ignore
    Neo4jContainer = None  # type: ignore

from memory_service.config import Settings
from memory_service.storage.qdrant_adapter import QdrantAdapter
from memory_service.storage.neo4j_adapter import Neo4jAdapter
from memory_service.embedding.service import EmbeddingService
from memory_service.core.memory_manager import MemoryManager
from memory_service.core.query_engine import QueryEngine
from memory_service.core.workers import IndexerWorker, NormalizerWorker, JobManager
from memory_service.models import (
    MemoryType,
    RequirementsMemory,
    DesignMemory,
    CodePatternMemory,
    ComponentMemory,
    FunctionMemory,
)

# Skip all integration tests if testcontainers is not available
pytestmark = pytest.mark.skipif(
    not TESTCONTAINERS_AVAILABLE,
    reason="testcontainers not available"
)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def qdrant_container() -> Generator[Any, None, None]:
    """Start Qdrant container for integration tests.

    Yields:
        QdrantContainer instance with connection details
    """
    import time
    import httpx

    if not TESTCONTAINERS_AVAILABLE:
        pytest.skip("testcontainers not available")

    container = QdrantContainer(image="qdrant/qdrant:v1.15.0")
    container.start()

    # Wait for Qdrant to be ready
    host = container.get_container_host_ip()
    port = int(container.get_exposed_port(6333))
    url = f"http://{host}:{port}/collections"

    max_retries = 30
    for i in range(max_retries):
        try:
            response = httpx.get(url, timeout=2.0)
            if response.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        raise RuntimeError(f"Qdrant container not ready after {max_retries} seconds")

    yield container

    container.stop()


@pytest.fixture(scope="session")
def neo4j_container() -> Generator[Any, None, None]:
    """Start Neo4j container for integration tests.

    Yields:
        Neo4jContainer instance with connection details
    """
    import time
    from neo4j import GraphDatabase

    if not TESTCONTAINERS_AVAILABLE:
        pytest.skip("testcontainers not available")

    container = Neo4jContainer(
        image="neo4j:5.15.0",
        username="neo4j",
        password="testpassword123",
    )
    container.start()

    # Wait for Neo4j to be ready by trying to connect via bolt protocol
    connection_url = container.get_connection_url()

    max_retries = 60  # Neo4j can take longer to start
    for i in range(max_retries):
        try:
            driver = GraphDatabase.driver(
                connection_url,
                auth=("neo4j", "testpassword123"),
            )
            with driver.session() as session:
                session.run("RETURN 1")
            driver.close()
            break
        except Exception:
            time.sleep(1)
    else:
        raise RuntimeError(f"Neo4j container not ready after {max_retries} seconds")

    yield container

    container.stop()


@pytest.fixture(scope="session")
def integration_settings(
    qdrant_container: Any,
    neo4j_container: Any,
) -> Settings:
    """Create settings from testcontainer instances.

    Args:
        qdrant_container: Running Qdrant container
        neo4j_container: Running Neo4j container

    Returns:
        Settings configured for test containers
    """
    return Settings(
        qdrant_host=qdrant_container.get_container_host_ip(),
        qdrant_port=int(qdrant_container.get_exposed_port(6333)),
        neo4j_uri=neo4j_container.get_connection_url(),
        neo4j_user="neo4j",
        neo4j_password=SecretStr("testpassword123"),
        voyage_api_key=SecretStr("test-api-key"),  # Will use mock
        log_level="DEBUG",
        log_format="console",
        metrics_enabled=False,
    )


@pytest.fixture(scope="function")
async def qdrant_adapter(qdrant_container: Any) -> AsyncGenerator[QdrantAdapter, None]:
    """Create QdrantAdapter connected to test container.

    Yields:
        Initialized QdrantAdapter
    """
    adapter = QdrantAdapter(
        host=qdrant_container.get_container_host_ip(),
        port=int(qdrant_container.get_exposed_port(6333)),
        grpc_port=int(qdrant_container.get_exposed_port(6334)),
        prefer_grpc=False,  # Use HTTP for tests
    )

    # Initialize collections
    await adapter.initialize_collections()

    yield adapter

    # Cleanup: delete all collections
    for memory_type in MemoryType:
        collection = adapter.get_collection_name(memory_type)
        try:
            await adapter.delete_collection(collection)
        except Exception:
            pass


@pytest.fixture(scope="function")
async def neo4j_adapter(neo4j_container: Any) -> AsyncGenerator[Neo4jAdapter, None]:
    """Create Neo4jAdapter connected to test container.

    Yields:
        Initialized Neo4jAdapter
    """
    adapter = Neo4jAdapter(
        uri=neo4j_container.get_connection_url(),
        user="neo4j",
        password="testpassword123",
    )

    # Initialize schema
    await adapter.initialize_schema()

    yield adapter

    # Cleanup: delete all nodes
    async with adapter._driver.session() as session:
        await session.run("MATCH (n) DETACH DELETE n")

    await adapter.close()


class MockEmbeddingService:
    """Mock embedding service for integration tests without API calls."""

    def __init__(self) -> None:
        self._cache: dict[str, list[float]] = {}
        self._call_count = 0

    async def embed(self, content: str) -> tuple[list[float], bool]:
        """Generate deterministic embedding based on content hash."""
        import hashlib

        self._call_count += 1

        if content in self._cache:
            return self._cache[content], False

        # Generate deterministic embedding from content hash
        hash_bytes = hashlib.sha256(content.encode()).digest()
        embedding = self._generate_from_hash(hash_bytes)
        self._cache[content] = embedding
        return embedding, False

    async def embed_for_query(self, query: str) -> list[float]:
        """Generate embedding for a search query."""
        embedding, _ = await self.embed(query)
        return embedding

    async def embed_batch(
        self,
        contents: list[str],
    ) -> list[tuple[list[float], bool]]:
        """Batch embed multiple contents."""
        results = []
        for content in contents:
            emb, is_fallback = await self.embed(content)
            results.append((emb, is_fallback))
        return results

    def _generate_from_hash(self, hash_bytes: bytes) -> list[float]:
        """Generate 1024-dim embedding from hash bytes."""
        import struct

        # Use hash to seed deterministic values
        embedding = []
        for i in range(0, min(len(hash_bytes), 32), 4):
            chunk = hash_bytes[i:i+4]
            val = struct.unpack('f', chunk)[0]
            # Normalize to reasonable range
            normalized = (val % 1.0) if not (val != val) else 0.5  # Handle NaN
            embedding.append(normalized)

        # Extend to 1024 dimensions
        while len(embedding) < 1024:
            idx = len(embedding)
            seed_val = (hash_bytes[idx % 32] + idx) / 256.0
            embedding.append(seed_val)

        # Normalize the vector
        import math
        magnitude = math.sqrt(sum(x * x for x in embedding))
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]

        return embedding[:1024]

    @property
    def call_count(self) -> int:
        return self._call_count


@pytest.fixture
def mock_embedding_service() -> MockEmbeddingService:
    """Create mock embedding service for tests."""
    return MockEmbeddingService()


@pytest.fixture
async def memory_manager(
    qdrant_adapter: QdrantAdapter,
    neo4j_adapter: Neo4jAdapter,
    mock_embedding_service: MockEmbeddingService,
) -> MemoryManager:
    """Create MemoryManager with test adapters.

    Returns:
        Configured MemoryManager
    """
    return MemoryManager(
        qdrant=qdrant_adapter,
        neo4j=neo4j_adapter,
        embedding_service=mock_embedding_service,  # type: ignore
        conflict_threshold=0.95,
    )


@pytest.fixture
async def query_engine(
    qdrant_adapter: QdrantAdapter,
    neo4j_adapter: Neo4jAdapter,
    mock_embedding_service: MockEmbeddingService,
) -> QueryEngine:
    """Create QueryEngine with test adapters.

    Returns:
        Configured QueryEngine
    """
    return QueryEngine(
        qdrant=qdrant_adapter,
        neo4j=neo4j_adapter,
        embedding_service=mock_embedding_service,  # type: ignore
    )


@pytest.fixture
def job_manager() -> JobManager:
    """Create JobManager for tests.

    Returns:
        Configured JobManager
    """
    return JobManager()


@pytest.fixture
async def indexer_worker(
    qdrant_adapter: QdrantAdapter,
    neo4j_adapter: Neo4jAdapter,
    job_manager: JobManager,
) -> IndexerWorker:
    """Create IndexerWorker with test adapters.

    Returns:
        Configured IndexerWorker
    """
    return IndexerWorker(
        qdrant=qdrant_adapter,
        neo4j=neo4j_adapter,
        job_manager=job_manager,
    )


@pytest.fixture
async def normalizer_worker(
    qdrant_adapter: QdrantAdapter,
    neo4j_adapter: Neo4jAdapter,
    job_manager: JobManager,
) -> NormalizerWorker:
    """Create NormalizerWorker with test adapters.

    Returns:
        Configured NormalizerWorker
    """
    return NormalizerWorker(
        qdrant=qdrant_adapter,
        neo4j=neo4j_adapter,
        job_manager=job_manager,
    )


# Sample memory fixtures for integration tests

def generate_test_embedding(seed: int = 42) -> list[float]:
    """Generate deterministic test embedding."""
    import random
    random.seed(seed)
    embedding = [random.random() for _ in range(1024)]
    # Normalize
    import math
    magnitude = math.sqrt(sum(x * x for x in embedding))
    return [x / magnitude for x in embedding]


@pytest.fixture
def sample_requirement() -> RequirementsMemory:
    """Create sample requirements memory for testing."""
    return RequirementsMemory(
        id=uuid4(),
        type=MemoryType.REQUIREMENTS,
        content="The system shall provide semantic search with sub-200ms latency",
        embedding=generate_test_embedding(1),
        requirement_id="REQ-MEM-FN-001",
        title="Semantic Search Latency",
        description="Semantic search shall complete within 200ms",
        priority="High",
        status="Approved",
        source_document="requirements.md",
    )


@pytest.fixture
def sample_design() -> DesignMemory:
    """Create sample design memory for testing."""
    return DesignMemory(
        id=uuid4(),
        type=MemoryType.DESIGN,
        content="Use Qdrant for vector storage with HNSW indexing",
        embedding=generate_test_embedding(2),
        design_type="ADR",
        title="ADR-001: Vector Database Selection",
        decision="Use Qdrant for vector storage",
        rationale="Efficient vector search with filtering",
        status="Accepted",
        related_requirements=["REQ-MEM-FN-001"],
    )


@pytest.fixture
def sample_function() -> FunctionMemory:
    """Create sample function memory for testing."""
    return FunctionMemory(
        id=uuid4(),
        type=MemoryType.FUNCTION,
        content="def semantic_search(query: str, limit: int = 10) -> list[SearchResult]",
        embedding=generate_test_embedding(3),
        function_id=uuid4(),
        name="semantic_search",
        signature="def semantic_search(query: str, limit: int = 10) -> list[SearchResult]",
        file_path="src/query_engine.py",
        start_line=50,
        end_line=75,
        language="python",
        docstring="Perform semantic search across memories.",
    )


@pytest.fixture
def sample_component() -> ComponentMemory:
    """Create sample component memory for testing."""
    return ComponentMemory(
        id=uuid4(),
        type=MemoryType.COMPONENT,
        content="QueryEngine - Core query processing service",
        embedding=generate_test_embedding(4),
        component_id="query-engine",
        component_type="Service",
        name="QueryEngine",
        file_path="src/query_engine.py",
        public_interface={
            "exports": [
                {"name": "QueryEngine", "type": "class"},
                {"name": "semantic_search", "type": "method"},
            ]
        },
    )


@pytest.fixture
def sample_code_pattern() -> CodePatternMemory:
    """Create sample code pattern memory for testing."""
    return CodePatternMemory(
        id=uuid4(),
        type=MemoryType.CODE_PATTERN,
        content="Async context manager for database connections",
        embedding=generate_test_embedding(5),
        pattern_name="Async DB Connection",
        pattern_type="Template",
        language="Python",
        code_template="""async with get_connection() as conn:
    result = await conn.execute(query)
    return result""",
        usage_context="Use for all database operations",
    )
