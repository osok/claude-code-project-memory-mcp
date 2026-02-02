"""E2E test fixtures with testcontainers and full stack setup.

================================================================================
                        TESTING STRATEGY - MANDATORY
================================================================================

**Test against real code, not mocks.**

1. USE mock-src/ - A comprehensive mock application for testing code parsing,
   indexing, and relationship detection. Located at: mock-src/

2. DON'T mock infrastructure being tested - Mock external APIs (embeddings),
   but NOT the parsing/indexing being validated.

3. KNOWN expected results - Test against defined expected outputs in
   conftest_mock_src.py (EXPECTED_PYTHON_FUNCTIONS, EXPECTED_PYTHON_CLASSES,
   EXPECTED_RELATIONSHIPS).

4. USE fixtures from conftest_mock_src.py:
   - mock_src_python: Path to Python mock app
   - mock_codebase: Alias for E2E tests
   - expected_python_functions: Known function extraction results
   - expected_python_classes: Known class extraction results
   - expected_relationships: Known relationship extraction results

See: project-docs/testing-strategy.md and CLAUDE.md for full documentation.
================================================================================
"""

import asyncio
import tempfile
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from pydantic import SecretStr

# Import mock-src fixtures - these provide the test codebase
from tests.conftest_mock_src import (
    mock_src_root,
    mock_src_python,
    mock_src_typescript,
    mock_src_go,
    mock_codebase,
    mock_requirements_file,
    mock_design_file,
    expected_python_functions,
    expected_python_classes,
    expected_relationships,
    expected_file_counts,
)

# Testcontainers imports
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
from memory_service.embedding.service import EmbeddingService
from memory_service.core.memory_manager import MemoryManager
from memory_service.core.query_engine import QueryEngine
from memory_service.core.workers import IndexerWorker, NormalizerWorker, JobManager
from memory_service.storage.sync import SyncManager
from memory_service.models import MemoryType

# Skip all E2E tests if testcontainers is not available
pytestmark = pytest.mark.skipif(
    not TESTCONTAINERS_AVAILABLE,
    reason="testcontainers not available"
)


@pytest.fixture(scope="module")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests.

    Uses module scope to match the adapter fixture scopes and avoid
    'Future attached to a different loop' errors.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture(scope="module")
def qdrant_container() -> Generator[Any, None, None]:
    """Start Qdrant container for E2E tests."""
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


@pytest.fixture(scope="module")
def neo4j_container() -> Generator[Any, None, None]:
    """Start Neo4j container for E2E tests."""
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


class MockEmbeddingServiceE2E:
    """Mock embedding service for E2E tests."""

    def __init__(self) -> None:
        self._cache: dict[str, list[float]] = {}

    async def embed(self, content: str) -> tuple[list[float], bool]:
        """Generate deterministic embedding."""
        import hashlib

        if content in self._cache:
            return self._cache[content], False

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
        """Batch embed."""
        return [await self.embed(c) for c in contents]

    def _generate_from_hash(self, hash_bytes: bytes) -> list[float]:
        """Generate 1024-dim embedding from hash."""
        import math

        embedding = []
        for i in range(1024):
            seed_val = (hash_bytes[i % 32] + i) / 256.0
            embedding.append(seed_val)

        magnitude = math.sqrt(sum(x * x for x in embedding))
        return [x / magnitude for x in embedding]


@pytest.fixture(scope="module")
def mock_embedding_service() -> MockEmbeddingServiceE2E:
    """Create mock embedding service."""
    return MockEmbeddingServiceE2E()


@pytest_asyncio.fixture(scope="module")
async def e2e_qdrant_adapter(qdrant_container: Any) -> AsyncGenerator[QdrantAdapter, None]:
    """Create QdrantAdapter for E2E tests."""
    adapter = QdrantAdapter(
        host=qdrant_container.get_container_host_ip(),
        port=int(qdrant_container.get_exposed_port(6333)),
        grpc_port=int(qdrant_container.get_exposed_port(6334)),
        prefer_grpc=False,
    )
    await adapter.initialize_collections()
    yield adapter


@pytest_asyncio.fixture(scope="module")
async def e2e_neo4j_adapter(neo4j_container: Any) -> AsyncGenerator[Neo4jAdapter, None]:
    """Create Neo4jAdapter for E2E tests."""
    adapter = Neo4jAdapter(
        uri=neo4j_container.get_connection_url(),
        user="neo4j",
        password="testpassword123",
    )
    await adapter.initialize_schema()
    yield adapter
    await adapter.close()


@pytest.fixture(scope="module")
def e2e_memory_manager(
    e2e_qdrant_adapter: QdrantAdapter,
    e2e_neo4j_adapter: Neo4jAdapter,
    mock_embedding_service: MockEmbeddingServiceE2E,
) -> MemoryManager:
    """Create MemoryManager for E2E tests."""
    return MemoryManager(
        qdrant=e2e_qdrant_adapter,
        neo4j=e2e_neo4j_adapter,
        embedding_service=mock_embedding_service,  # type: ignore
        conflict_threshold=0.95,
    )


@pytest.fixture(scope="module")
def e2e_query_engine(
    e2e_qdrant_adapter: QdrantAdapter,
    e2e_neo4j_adapter: Neo4jAdapter,
    mock_embedding_service: MockEmbeddingServiceE2E,
) -> QueryEngine:
    """Create QueryEngine for E2E tests."""
    return QueryEngine(
        qdrant=e2e_qdrant_adapter,
        neo4j=e2e_neo4j_adapter,
        embedding_service=mock_embedding_service,  # type: ignore
    )


@pytest.fixture(scope="module")
def e2e_job_manager() -> JobManager:
    """Create JobManager for E2E tests."""
    return JobManager()


@pytest.fixture(scope="module")
def e2e_indexer_worker(
    e2e_qdrant_adapter: QdrantAdapter,
    e2e_neo4j_adapter: Neo4jAdapter,
    mock_embedding_service: MockEmbeddingServiceE2E,
    e2e_job_manager: JobManager,
) -> IndexerWorker:
    """Create IndexerWorker for E2E tests."""
    return IndexerWorker(
        qdrant=e2e_qdrant_adapter,
        neo4j=e2e_neo4j_adapter,
        job_manager=e2e_job_manager,
        embedding_service=mock_embedding_service,
    )


@pytest.fixture(scope="module")
def e2e_normalizer_worker(
    e2e_qdrant_adapter: QdrantAdapter,
    e2e_neo4j_adapter: Neo4jAdapter,
    e2e_job_manager: JobManager,
) -> NormalizerWorker:
    """Create NormalizerWorker for E2E tests."""
    return NormalizerWorker(
        qdrant=e2e_qdrant_adapter,
        neo4j=e2e_neo4j_adapter,
        job_manager=e2e_job_manager,
    )


@pytest.fixture
def temp_codebase() -> Generator[Path, None, None]:
    """Create a temporary codebase for E2E testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Create Python project structure
        src = root / "src"
        src.mkdir()

        # Main module
        (src / "main.py").write_text('''"""Main application module."""

from utils import format_string
from models import User


def main():
    """Application entry point."""
    user = User(name="Test", email="test@example.com")
    print(format_string(user.name))


if __name__ == "__main__":
    main()
''')

        # Utils module
        (src / "utils.py").write_text('''"""Utility functions."""


def format_string(text: str) -> str:
    """Format a string by stripping and lowercasing."""
    return text.strip().lower()


def validate_email(email: str) -> bool:
    """Validate email format."""
    return "@" in email and "." in email
''')

        # Models module
        (src / "models.py").write_text('''"""Data models."""

from dataclasses import dataclass


@dataclass
class User:
    """User model."""
    name: str
    email: str

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {"name": self.name, "email": self.email}


@dataclass
class Admin(User):
    """Admin user extending User."""
    role: str = "admin"
''')

        # Tests directory
        tests = root / "tests"
        tests.mkdir()

        (tests / "test_utils.py").write_text('''"""Tests for utils module."""

from utils import format_string, validate_email


def test_format_string():
    """Test format_string function."""
    assert format_string("  Hello  ") == "hello"


def test_validate_email():
    """Test validate_email function."""
    assert validate_email("test@example.com")
    assert not validate_email("invalid")
''')

        # .gitignore
        (root / ".gitignore").write_text('''__pycache__/
*.pyc
.env
.venv/
''')

        yield root
