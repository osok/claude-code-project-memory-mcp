"""Unit tests for HTTP server endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from memory_service.api.http_server import create_http_server
from memory_service.models import MemoryType


class TestHealthEndpoint:
    """Unit tests for /health endpoint."""

    @pytest.fixture
    def mock_qdrant(self) -> AsyncMock:
        """Create mock Qdrant adapter."""
        mock = AsyncMock()
        mock.health_check.return_value = True
        return mock

    @pytest.fixture
    def mock_neo4j(self) -> AsyncMock:
        """Create mock Neo4j adapter."""
        mock = AsyncMock()
        mock.health_check.return_value = True
        return mock

    @pytest.fixture
    def client(self, mock_qdrant: AsyncMock, mock_neo4j: AsyncMock) -> TestClient:
        """Create test client."""
        app = create_http_server(mock_qdrant, mock_neo4j)
        return TestClient(app)

    def test_health_returns_ok(self, client: TestClient) -> None:
        """Test health endpoint returns ok status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "memory-service"


class TestReadinessEndpoint:
    """Unit tests for /health/ready endpoint."""

    @pytest.fixture
    def mock_qdrant(self) -> AsyncMock:
        """Create mock Qdrant adapter."""
        mock = AsyncMock()
        mock.health_check.return_value = True
        return mock

    @pytest.fixture
    def mock_neo4j(self) -> AsyncMock:
        """Create mock Neo4j adapter."""
        mock = AsyncMock()
        mock.health_check.return_value = True
        return mock

    @pytest.fixture
    def client(self, mock_qdrant: AsyncMock, mock_neo4j: AsyncMock) -> TestClient:
        """Create test client."""
        app = create_http_server(mock_qdrant, mock_neo4j)
        return TestClient(app)

    def test_readiness_all_healthy(
        self,
        mock_qdrant: AsyncMock,
        mock_neo4j: AsyncMock,
    ) -> None:
        """Test readiness when all services are healthy."""
        app = create_http_server(mock_qdrant, mock_neo4j)
        client = TestClient(app)

        response = client.get("/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["checks"]["qdrant"] is True
        assert data["checks"]["neo4j"] is True

    def test_readiness_qdrant_unhealthy(
        self,
        mock_qdrant: AsyncMock,
        mock_neo4j: AsyncMock,
    ) -> None:
        """Test readiness when Qdrant is unhealthy."""
        mock_qdrant.health_check.return_value = False
        app = create_http_server(mock_qdrant, mock_neo4j)
        client = TestClient(app)

        response = client.get("/health/ready")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["qdrant"] is False

    def test_readiness_neo4j_unhealthy(
        self,
        mock_qdrant: AsyncMock,
        mock_neo4j: AsyncMock,
    ) -> None:
        """Test readiness when Neo4j is unhealthy."""
        mock_neo4j.health_check.return_value = False
        app = create_http_server(mock_qdrant, mock_neo4j)
        client = TestClient(app)

        response = client.get("/health/ready")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["neo4j"] is False

    def test_readiness_qdrant_exception(
        self,
        mock_qdrant: AsyncMock,
        mock_neo4j: AsyncMock,
    ) -> None:
        """Test readiness when Qdrant raises exception."""
        mock_qdrant.health_check.side_effect = Exception("Connection failed")
        app = create_http_server(mock_qdrant, mock_neo4j)
        client = TestClient(app)

        response = client.get("/health/ready")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["qdrant"] is False

    def test_readiness_neo4j_exception(
        self,
        mock_qdrant: AsyncMock,
        mock_neo4j: AsyncMock,
    ) -> None:
        """Test readiness when Neo4j raises exception."""
        mock_neo4j.health_check.side_effect = Exception("Connection failed")
        app = create_http_server(mock_qdrant, mock_neo4j)
        client = TestClient(app)

        response = client.get("/health/ready")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["neo4j"] is False


class TestMetricsEndpoint:
    """Unit tests for /metrics endpoint."""

    @pytest.fixture
    def mock_qdrant(self) -> AsyncMock:
        """Create mock Qdrant adapter."""
        return AsyncMock()

    @pytest.fixture
    def mock_neo4j(self) -> AsyncMock:
        """Create mock Neo4j adapter."""
        return AsyncMock()

    @pytest.fixture
    def client(self, mock_qdrant: AsyncMock, mock_neo4j: AsyncMock) -> TestClient:
        """Create test client."""
        app = create_http_server(mock_qdrant, mock_neo4j)
        return TestClient(app)

    def test_metrics_returns_prometheus_format(self, client: TestClient) -> None:
        """Test metrics endpoint returns Prometheus format."""
        response = client.get("/metrics")

        assert response.status_code == 200
        # Prometheus format should have text/plain content type
        assert "text/plain" in response.headers["content-type"] or "text" in response.headers["content-type"]


class TestStatusEndpoint:
    """Unit tests for /status endpoint."""

    @pytest.fixture
    def mock_qdrant(self) -> MagicMock:
        """Create mock Qdrant adapter."""
        mock = MagicMock()
        # Sync methods use regular returns
        mock.get_collection_name = lambda mt: f"memories_{mt.value}"
        # Async methods use AsyncMock
        mock.health_check = AsyncMock(return_value=True)
        mock.count = AsyncMock(return_value=10)
        return mock

    @pytest.fixture
    def mock_neo4j(self) -> MagicMock:
        """Create mock Neo4j adapter."""
        mock = MagicMock()
        # Sync methods use regular returns
        mock.get_node_label = lambda mt: mt.value.title()
        # Async methods use AsyncMock
        mock.health_check = AsyncMock(return_value=True)
        mock.count_nodes = AsyncMock(return_value=5)
        return mock

    @pytest.fixture
    def client(self, mock_qdrant: AsyncMock, mock_neo4j: AsyncMock) -> TestClient:
        """Create test client."""
        app = create_http_server(mock_qdrant, mock_neo4j)
        return TestClient(app)

    def test_status_all_healthy(
        self,
        mock_qdrant: AsyncMock,
        mock_neo4j: AsyncMock,
    ) -> None:
        """Test status when all services are healthy."""
        app = create_http_server(mock_qdrant, mock_neo4j)
        client = TestClient(app)

        response = client.get("/status")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "memory-service"
        assert data["version"] == "0.1.0"
        assert data["storage"]["qdrant"]["connected"] is True
        assert data["storage"]["neo4j"]["connected"] is True

    def test_status_qdrant_disconnected(
        self,
        mock_qdrant: AsyncMock,
        mock_neo4j: AsyncMock,
    ) -> None:
        """Test status when Qdrant is disconnected."""
        mock_qdrant.health_check.return_value = False
        app = create_http_server(mock_qdrant, mock_neo4j)
        client = TestClient(app)

        response = client.get("/status")

        assert response.status_code == 200
        data = response.json()
        assert data["storage"]["qdrant"]["connected"] is False

    def test_status_neo4j_disconnected(
        self,
        mock_qdrant: AsyncMock,
        mock_neo4j: AsyncMock,
    ) -> None:
        """Test status when Neo4j is disconnected."""
        mock_neo4j.health_check.return_value = False
        app = create_http_server(mock_qdrant, mock_neo4j)
        client = TestClient(app)

        response = client.get("/status")

        assert response.status_code == 200
        data = response.json()
        assert data["storage"]["neo4j"]["connected"] is False

    def test_status_qdrant_error(
        self,
        mock_qdrant: AsyncMock,
        mock_neo4j: AsyncMock,
    ) -> None:
        """Test status when Qdrant raises error."""
        mock_qdrant.health_check.side_effect = Exception("Connection error")
        app = create_http_server(mock_qdrant, mock_neo4j)
        client = TestClient(app)

        response = client.get("/status")

        assert response.status_code == 200
        data = response.json()
        assert "error" in data["storage"]["qdrant"]

    def test_status_neo4j_error(
        self,
        mock_qdrant: AsyncMock,
        mock_neo4j: AsyncMock,
    ) -> None:
        """Test status when Neo4j raises error."""
        mock_neo4j.health_check.side_effect = Exception("Connection error")
        app = create_http_server(mock_qdrant, mock_neo4j)
        client = TestClient(app)

        response = client.get("/status")

        assert response.status_code == 200
        data = response.json()
        assert "error" in data["storage"]["neo4j"]


class TestHttpServerCreation:
    """Unit tests for HTTP server creation."""

    def test_create_server_returns_fastapi(self) -> None:
        """Test that create_http_server returns FastAPI app."""
        from fastapi import FastAPI

        mock_qdrant = AsyncMock()
        mock_neo4j = AsyncMock()

        app = create_http_server(mock_qdrant, mock_neo4j)

        assert isinstance(app, FastAPI)

    def test_create_server_disables_docs(self) -> None:
        """Test that docs are disabled."""
        mock_qdrant = AsyncMock()
        mock_neo4j = AsyncMock()

        app = create_http_server(mock_qdrant, mock_neo4j)

        assert app.docs_url is None
        assert app.redoc_url is None

    def test_create_server_has_title(self) -> None:
        """Test that app has correct title."""
        mock_qdrant = AsyncMock()
        mock_neo4j = AsyncMock()

        app = create_http_server(mock_qdrant, mock_neo4j)

        assert app.title == "Memory Service"
