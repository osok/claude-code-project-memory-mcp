"""Performance test fixtures with testcontainers for Qdrant and Neo4j."""

import asyncio
import random
import time
from collections.abc import AsyncGenerator, Generator
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
from memory_service.storage.qdrant_adapter import QdrantAdapter
from memory_service.storage.neo4j_adapter import Neo4jAdapter
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

    container = QdrantContainer(image="qdrant/qdrant:v1.7.0")
    container.start()
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
        log_level="WARNING",  # Reduce noise
        log_format="console",
        metrics_enabled=False,
    )


class MockEmbeddingService:
    """Fast mock embedding service for performance tests."""

    def __init__(self) -> None:
        self._cache: dict[str, list[float]] = {}

    async def embed(self, content: str) -> tuple[list[float], bool]:
        """Generate fast deterministic embedding."""
        if content in self._cache:
            return self._cache[content], False

        # Fast hash-based embedding
        embedding = self._fast_embed(content)
        self._cache[content] = embedding
        return embedding, False

    async def embed_batch(
        self,
        contents: list[str],
    ) -> list[tuple[list[float], bool]]:
        """Batch embed multiple contents."""
        return [await self.embed(c) for c in contents]

    def _fast_embed(self, content: str) -> list[float]:
        """Generate fast 1024-dim embedding."""
        import hashlib
        hash_bytes = hashlib.md5(content.encode()).digest()
        random.seed(int.from_bytes(hash_bytes[:4], 'big'))
        embedding = [random.random() for _ in range(1024)]
        # Normalize
        import math
        mag = math.sqrt(sum(x * x for x in embedding))
        return [x / mag for x in embedding]


@pytest.fixture
def mock_embedding_service() -> MockEmbeddingService:
    """Create fast mock embedding service."""
    return MockEmbeddingService()


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

    # Cleanup
    for memory_type in MemoryType:
        collection = adapter.get_collection_name(memory_type)
        try:
            await adapter.delete_collection(collection)
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

    # Cleanup
    async with adapter._driver.session() as session:
        await session.run("MATCH (n) DETACH DELETE n")
    await adapter.close()


@pytest.fixture
async def memory_manager(
    qdrant_adapter: QdrantAdapter,
    neo4j_adapter: Neo4jAdapter,
    mock_embedding_service: MockEmbeddingService,
) -> MemoryManager:
    """Create MemoryManager for performance tests."""
    return MemoryManager(
        qdrant=qdrant_adapter,
        neo4j=neo4j_adapter,
        embedding_service=mock_embedding_service,  # type: ignore
    )


@pytest.fixture
async def query_engine(
    qdrant_adapter: QdrantAdapter,
    neo4j_adapter: Neo4jAdapter,
    mock_embedding_service: MockEmbeddingService,
) -> QueryEngine:
    """Create QueryEngine for performance tests."""
    return QueryEngine(
        qdrant=qdrant_adapter,
        neo4j=neo4j_adapter,
        embedding_service=mock_embedding_service,  # type: ignore
    )


def generate_test_embedding(seed: int) -> list[float]:
    """Generate deterministic test embedding."""
    random.seed(seed)
    embedding = [random.random() for _ in range(1024)]
    import math
    mag = math.sqrt(sum(x * x for x in embedding))
    return [x / mag for x in embedding]


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
