"""FastAPI HTTP server for health checks and metrics."""

from typing import Any

from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from memory_service.storage.qdrant_adapter import QdrantAdapter
from memory_service.storage.neo4j_adapter import Neo4jAdapter
from memory_service.utils.logging import get_logger

logger = get_logger(__name__)


def create_http_server(
    qdrant: QdrantAdapter,
    neo4j: Neo4jAdapter,
) -> FastAPI:
    """Create FastAPI HTTP server for health and metrics.

    Args:
        qdrant: Qdrant adapter
        neo4j: Neo4j adapter

    Returns:
        FastAPI application
    """
    app = FastAPI(
        title="Memory Service",
        description="Health and metrics endpoints for the memory service",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
    )

    @app.get("/health")
    async def health() -> JSONResponse:
        """Liveness check endpoint.

        Returns 200 if the service is running.
        """
        return JSONResponse(
            content={"status": "ok", "service": "memory-service"},
            status_code=200,
        )

    @app.get("/health/ready")
    async def readiness() -> JSONResponse:
        """Readiness check endpoint.

        Verifies connections to Qdrant and Neo4j.
        """
        checks: dict[str, Any] = {
            "qdrant": False,
            "neo4j": False,
        }

        try:
            checks["qdrant"] = await qdrant.health_check()
        except Exception as e:
            logger.error("qdrant_health_failed", error=str(e))

        try:
            checks["neo4j"] = await neo4j.health_check()
        except Exception as e:
            logger.error("neo4j_health_failed", error=str(e))

        all_healthy = all(checks.values())

        return JSONResponse(
            content={
                "status": "ready" if all_healthy else "not_ready",
                "checks": checks,
            },
            status_code=200 if all_healthy else 503,
        )

    @app.get("/metrics")
    async def metrics() -> Response:
        """Prometheus metrics endpoint.

        Returns metrics in Prometheus exposition format.
        """
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )

    @app.get("/status")
    async def status() -> JSONResponse:
        """Detailed system status endpoint."""
        from memory_service.models import MemoryType

        status_data: dict[str, Any] = {
            "service": "memory-service",
            "version": "0.1.0",
            "storage": {
                "qdrant": {"connected": False, "collections": {}},
                "neo4j": {"connected": False, "node_counts": {}},
            },
        }

        # Check Qdrant
        try:
            if await qdrant.health_check():
                status_data["storage"]["qdrant"]["connected"] = True

                # Get collection counts
                for memory_type in MemoryType:
                    collection = qdrant.get_collection_name(memory_type)
                    count = await qdrant.count(collection)
                    status_data["storage"]["qdrant"]["collections"][collection] = count

        except Exception as e:
            status_data["storage"]["qdrant"]["error"] = str(e)

        # Check Neo4j
        try:
            if await neo4j.health_check():
                status_data["storage"]["neo4j"]["connected"] = True

                # Get node counts
                for memory_type in MemoryType:
                    label = neo4j.get_node_label(memory_type)
                    count = await neo4j.count_nodes(label)
                    status_data["storage"]["neo4j"]["node_counts"][label] = count

        except Exception as e:
            status_data["storage"]["neo4j"]["error"] = str(e)

        return JSONResponse(content=status_data)

    return app
