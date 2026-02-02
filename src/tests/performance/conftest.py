"""Performance test fixtures with testcontainers for Qdrant and Neo4j.

Following testing strategy:
- Use real Qdrant and Neo4j containers (testcontainers)
- Use deterministic embedding service for reproducibility
- Use mock-src/ application for realistic test data
- No mocking of code parsing or storage operations
"""

import asyncio
import hashlib
import math
import random
import time
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from pydantic import SecretStr

try:
    from testcontainers.qdrant import QdrantContainer
    from testcontainers.neo4j import Neo4jContainer
    TESTCONTAINERS_AVAILABLE = True
except ImportError:
    TESTCONTAINERS_AVAILABLE = False
    QdrantContainer = None  # type: ignore
    Neo4jContainer = None  # type: ignore

from memory_service.config import Settings
from memory_service.storage.qdrant_adapter import QdrantAdapter, COLLECTIONS
from memory_service.storage.neo4j_adapter import Neo4jAdapter, NODE_LABELS
from memory_service.core.memory_manager import MemoryManager
from memory_service.core.query_engine import QueryEngine
from memory_service.core.workers import IndexerWorker
from memory_service.models import (
    MemoryType,
    RequirementsMemory,
    DesignMemory,
    FunctionMemory,
    ComponentMemory,
)

pytestmark = pytest.mark.skipif(
    not TESTCONTAINERS_AVAILABLE,
    reason="testcontainers not available"
)


class PerformanceTimer:
    """Context manager for timing operations."""

    def __init__(self) -> None:
        self.start_time: float = 0
        self.end_time: float = 0
        self.duration_ms: float = 0

    def __enter__(self) -> "PerformanceTimer":
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args: Any) -> None:
        self.end_time = time.perf_counter()
        self.duration_ms = (self.end_time - self.start_time) * 1000


class PerformanceMetrics:
    """Collect and calculate performance metrics."""

    def __init__(self) -> None:
        self.measurements: list[float] = []

    def add(self, duration_ms: float) -> None:
        """Add a measurement."""
        self.measurements.append(duration_ms)

    def p50(self) -> float:
        """Get 50th percentile."""
        if not self.measurements:
            return 0.0
        sorted_m = sorted(self.measurements)
        idx = len(sorted_m) // 2
        return sorted_m[idx]

    def p95(self) -> float:
        """Get 95th percentile."""
        if not self.measurements:
            return 0.0
        sorted_m = sorted(self.measurements)
        idx = int(len(sorted_m) * 0.95)
        return sorted_m[min(idx, len(sorted_m) - 1)]

    def p99(self) -> float:
        """Get 99th percentile."""
        if not self.measurements:
            return 0.0
        sorted_m = sorted(self.measurements)
        idx = int(len(sorted_m) * 0.99)
        return sorted_m[min(idx, len(sorted_m) - 1)]

    def mean(self) -> float:
        """Get mean."""
        if not self.measurements:
            return 0.0
        return sum(self.measurements) / len(self.measurements)

    def count(self) -> int:
        """Get count of measurements."""
        return len(self.measurements)


@pytest.fixture
def perf_timer() -> PerformanceTimer:
    """Create a performance timer."""
    return PerformanceTimer()


@pytest.fixture
def perf_metrics() -> PerformanceMetrics:
    """Create a performance metrics collector."""
    return PerformanceMetrics()


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def qdrant_container() -> Generator[Any, None, None]:
    """Start Qdrant container for performance tests."""
    if not TESTCONTAINERS_AVAILABLE:
        pytest.skip("testcontainers not available")

    # Use latest Qdrant that's compatible with client version 1.16.x
    container = QdrantContainer(image="qdrant/qdrant:v1.16.0")
    container.start()

    # Wait for Qdrant to be ready with health check
    import requests
    host = container.get_container_host_ip()
    port = container.get_exposed_port(6333)
    url = f"http://{host}:{port}/healthz"

    max_retries = 30
    for i in range(max_retries):
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(0.5)
    else:
        container.stop()
        pytest.fail("Qdrant container failed to become ready")

    yield container
    container.stop()


@pytest.fixture(scope="session")
def neo4j_container() -> Generator[Any, None, None]:
    """Start Neo4j container for performance tests."""
    if not TESTCONTAINERS_AVAILABLE:
        pytest.skip("testcontainers not available")

    container = Neo4jContainer(
        image="neo4j:5.15.0",
        username="neo4j",
        password="testpassword123",
    )
    container.start()

    # Wait for Neo4j to be ready
    from neo4j import GraphDatabase

    uri = container.get_connection_url()
    max_retries = 30
    for i in range(max_retries):
        try:
            driver = GraphDatabase.driver(uri, auth=("neo4j", "testpassword123"))
            with driver.session() as session:
                session.run("RETURN 1")
            driver.close()
            break
        except Exception:
            pass
        time.sleep(0.5)
    else:
        container.stop()
        pytest.fail("Neo4j container failed to become ready")

    yield container
    container.stop()


@pytest.fixture(scope="session")
def perf_settings(
    qdrant_container: Any,
    neo4j_container: Any,
) -> Settings:
    """Create settings for performance tests."""
    return Settings(
        qdrant_host=qdrant_container.get_container_host_ip(),
        qdrant_port=int(qdrant_container.get_exposed_port(6333)),
        neo4j_uri=neo4j_container.get_connection_url(),
        neo4j_user="neo4j",
        neo4j_password=SecretStr("testpassword123"),
        voyage_api_key=SecretStr("test-api-key"),
        log_level="WARNING",
        log_format="console",
        metrics_enabled=False,
    )


class DeterministicEmbeddingService:
    """Deterministic embedding service for reproducible performance tests.

    This is NOT a mock - it provides real, consistent embeddings using
    a hash-based algorithm. This is allowed per testing strategy as it
    replaces external API calls (VoyageAI) while maintaining determinism.
    """

    def __init__(self, dimension: int = 1024) -> None:
        self._dimension = dimension
        self._cache: dict[str, list[float]] = {}

    async def embed(self, content: str) -> tuple[list[float], bool]:
        """Generate deterministic embedding for content."""
        if content in self._cache:
            return self._cache[content], True  # Cache hit

        embedding = self._generate_embedding(content)
        self._cache[content] = embedding
        return embedding, False  # Cache miss

    async def embed_for_query(self, query: str) -> list[float]:
        """Generate embedding for search query."""
        embedding, _ = await self.embed(query)
        return embedding

    async def embed_batch(
        self,
        contents: list[str],
    ) -> list[tuple[list[float], bool]]:
        """Batch embed multiple contents."""
        return [await self.embed(c) for c in contents]

    def _generate_embedding(self, content: str) -> list[float]:
        """Generate deterministic embedding using content hash."""
        # Use SHA-256 for better distribution
        hash_bytes = hashlib.sha256(content.encode()).digest()

        # Use hash to seed random generator for reproducibility
        seed = int.from_bytes(hash_bytes[:8], 'big')
        rng = random.Random(seed)

        # Generate embedding
        embedding = [rng.gauss(0, 1) for _ in range(self._dimension)]

        # Normalize to unit vector (like real embeddings)
        magnitude = math.sqrt(sum(x * x for x in embedding))
        return [x / magnitude for x in embedding]


@pytest.fixture
def embedding_service() -> DeterministicEmbeddingService:
    """Create deterministic embedding service for tests."""
    return DeterministicEmbeddingService()


@pytest.fixture(scope="function")
async def qdrant_adapter(qdrant_container: Any) -> AsyncGenerator[QdrantAdapter, None]:
    """Create QdrantAdapter for performance tests."""
    adapter = QdrantAdapter(
        host=qdrant_container.get_container_host_ip(),
        port=int(qdrant_container.get_exposed_port(6333)),
        grpc_port=int(qdrant_container.get_exposed_port(6334)),
        prefer_grpc=False,
    )
    await adapter.initialize_collections()
    yield adapter

    # Cleanup - delete all points from collections
    loop = asyncio.get_running_loop()
    for memory_type in MemoryType:
        collection = COLLECTIONS.get(memory_type)
        if collection:
            try:
                # Delete all points by scrolling and deleting
                await loop.run_in_executor(
                    None,
                    lambda c=collection: adapter._client.delete(
                        collection_name=c,
                        points_selector={"filter": {}},
                    ),
                )
            except Exception:
                pass


@pytest.fixture(scope="function")
async def neo4j_adapter(neo4j_container: Any) -> AsyncGenerator[Neo4jAdapter, None]:
    """Create Neo4jAdapter for performance tests."""
    adapter = Neo4jAdapter(
        uri=neo4j_container.get_connection_url(),
        user="neo4j",
        password="testpassword123",
    )
    await adapter.initialize_schema()
    yield adapter

    # Cleanup - delete all nodes
    async with adapter._driver.session() as session:
        await session.run("MATCH (n) DETACH DELETE n")
    await adapter.close()


@pytest.fixture
async def memory_manager(
    qdrant_adapter: QdrantAdapter,
    neo4j_adapter: Neo4jAdapter,
    embedding_service: DeterministicEmbeddingService,
) -> MemoryManager:
    """Create MemoryManager for performance tests."""
    return MemoryManager(
        qdrant=qdrant_adapter,
        neo4j=neo4j_adapter,
        embedding_service=embedding_service,  # type: ignore
    )


@pytest.fixture
async def query_engine(
    qdrant_adapter: QdrantAdapter,
    neo4j_adapter: Neo4jAdapter,
    embedding_service: DeterministicEmbeddingService,
) -> QueryEngine:
    """Create QueryEngine for performance tests."""
    return QueryEngine(
        qdrant=qdrant_adapter,
        neo4j=neo4j_adapter,
        embedding_service=embedding_service,  # type: ignore
    )


# Mock-src fixtures for realistic test data
@pytest.fixture(scope="session")
def mock_src_root() -> Path:
    """Path to mock-src directory."""
    # Navigate from tests/performance/ to project root
    project_root = Path(__file__).parent.parent.parent.parent
    mock_src = project_root / "mock-src"
    if not mock_src.exists():
        pytest.skip("mock-src directory not found")
    return mock_src


@pytest.fixture(scope="session")
def mock_src_python(mock_src_root: Path) -> Path:
    """Path to Python mock application."""
    python_path = mock_src_root / "python" / "tasktracker"
    if not python_path.exists():
        pytest.skip("mock-src/python/tasktracker not found")
    return python_path


def generate_test_embedding(seed: int) -> list[float]:
    """Generate deterministic test embedding."""
    rng = random.Random(seed)
    embedding = [rng.gauss(0, 1) for _ in range(1024)]
    magnitude = math.sqrt(sum(x * x for x in embedding))
    return [x / magnitude for x in embedding]


def create_test_function_memory(index: int) -> FunctionMemory:
    """Create a test function memory."""
    return FunctionMemory(
        id=uuid4(),
        type=MemoryType.FUNCTION,
        content=f"def process_data_{index}(input: str, options: dict) -> Result: Process data with options",
        embedding=generate_test_embedding(index),
        function_id=uuid4(),
        name=f"process_data_{index}",
        signature=f"def process_data_{index}(input: str, options: dict) -> Result",
        file_path=f"src/module_{index // 100}/processor_{index}.py",
        start_line=10 + (index % 100) * 20,
        end_line=30 + (index % 100) * 20,
        language="python",
        docstring=f"Process data with various options. Index: {index}",
    )


def create_test_requirement_memory(index: int) -> RequirementsMemory:
    """Create a test requirements memory."""
    return RequirementsMemory(
        id=uuid4(),
        type=MemoryType.REQUIREMENTS,
        content=f"The system shall support feature {index} with high performance",
        embedding=generate_test_embedding(index + 100000),
        requirement_id=f"REQ-MEM-FN-{index:05d}",
        title=f"Feature Requirement {index}",
        description=f"Detailed description for requirement {index}",
        priority="High" if index % 3 == 0 else "Medium",
        status="Approved",
        source_document="requirements.md",
    )


def create_test_component_memory(index: int) -> ComponentMemory:
    """Create a test component memory."""
    return ComponentMemory(
        id=uuid4(),
        type=MemoryType.COMPONENT,
        content=f"Component{index} - Service for handling operation type {index % 10}",
        embedding=generate_test_embedding(index + 200000),
        component_id=f"component-{index}",
        component_type="Service",
        name=f"Component{index}",
        file_path=f"src/components/component_{index}.py",
        public_interface={
            "exports": [
                {"name": f"Component{index}", "type": "class"},
                {"name": f"process_{index}", "type": "function"},
            ]
        },
    )
