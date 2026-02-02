"""Entry point for the memory service."""

import asyncio
import signal
import sys
from typing import NoReturn

from memory_service.config import get_settings
from memory_service.utils.logging import get_logger, setup_logging


async def run_mcp_only() -> None:
    """Run only the MCP server (for stdio integration with Claude Code)."""
    from memory_service.api.mcp_server import MCPServer
    from memory_service.storage.qdrant_adapter import QdrantAdapter
    from memory_service.storage.neo4j_adapter import Neo4jAdapter
    from memory_service.embedding.service import EmbeddingService

    settings = get_settings()

    # Initialize storage adapters with project_id for data isolation
    qdrant = QdrantAdapter(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
        api_key=settings.qdrant_api_key,
        project_id=settings.project_id,
    )
    neo4j = Neo4jAdapter(
        uri=settings.neo4j_uri,
        user=settings.neo4j_user,
        password=settings.neo4j_password,
        project_id=settings.project_id,
    )
    embedding_service = EmbeddingService(
        api_key=settings.voyage_api_key,
        model=settings.voyage_model,
    )

    # Initialize collections/schema
    await qdrant.initialize_collections()
    await neo4j.initialize_schema()

    # Create and run MCP server only
    mcp_server = MCPServer(
        qdrant=qdrant,
        neo4j=neo4j,
        embedding_service=embedding_service,
    )

    try:
        await mcp_server.run()
    finally:
        await qdrant.close()
        await neo4j.close()


async def run_services() -> None:
    """Run all services (MCP server, HTTP server, background workers)."""
    from memory_service.api.http_server import create_http_server
    from memory_service.api.mcp_server import MCPServer
    from memory_service.core.workers import SyncWorker
    from memory_service.storage.qdrant_adapter import QdrantAdapter
    from memory_service.storage.neo4j_adapter import Neo4jAdapter
    from memory_service.embedding.service import EmbeddingService

    settings = get_settings()
    logger = get_logger(__name__)

    logger.info("starting_memory_service", version="0.1.0", project_id=settings.project_id)

    # Initialize storage adapters with project_id for data isolation
    qdrant = QdrantAdapter(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
        api_key=settings.qdrant_api_key,
        project_id=settings.project_id,
    )
    neo4j = Neo4jAdapter(
        uri=settings.neo4j_uri,
        user=settings.neo4j_user,
        password=settings.neo4j_password,
        project_id=settings.project_id,
    )
    embedding_service = EmbeddingService(
        api_key=settings.voyage_api_key,
        model=settings.voyage_model,
    )

    # Initialize collections/schema
    await qdrant.initialize_collections()
    await neo4j.initialize_schema()

    # Create MCP server
    mcp_server = MCPServer(
        qdrant=qdrant,
        neo4j=neo4j,
        embedding_service=embedding_service,
    )

    # Create HTTP server
    http_app = create_http_server(qdrant=qdrant, neo4j=neo4j)

    # Create sync worker
    sync_worker = SyncWorker(qdrant=qdrant, neo4j=neo4j)

    # Setup graceful shutdown
    shutdown_event = asyncio.Event()

    def handle_signal(sig: signal.Signals) -> None:
        logger.info("shutdown_signal_received", signal=sig.name)
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, handle_signal, sig)

    # Run all services
    import uvicorn

    http_config = uvicorn.Config(
        http_app,
        host=settings.metrics_host,
        port=settings.metrics_port,
        log_level="warning",
    )
    http_server = uvicorn.Server(http_config)

    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(mcp_server.run())
            tg.create_task(http_server.serve())
            tg.create_task(sync_worker.run(shutdown_event))
            tg.create_task(shutdown_event.wait())
    except* Exception as eg:
        for exc in eg.exceptions:
            logger.error("service_error", error=str(exc))
    finally:
        logger.info("shutting_down_services")
        await qdrant.close()
        await neo4j.close()
        logger.info("memory_service_stopped")


def main() -> NoReturn:
    """Main entry point."""
    # Check for "mcp" argument to run MCP-only mode
    if len(sys.argv) > 1 and sys.argv[1] == "mcp":
        # Use stderr for logging in MCP mode to keep stdout clean for JSON-RPC
        setup_logging(use_stderr=True)
        try:
            asyncio.run(run_mcp_only())
        except KeyboardInterrupt:
            pass
        sys.exit(0)

    # Default: run all services with stdout logging
    setup_logging()
    try:
        asyncio.run(run_services())
    except KeyboardInterrupt:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
