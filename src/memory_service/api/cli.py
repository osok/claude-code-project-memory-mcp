"""Command-line interface for memory service administration."""

import asyncio
import json
import sys
from typing import Any

import click

from memory_service.config import get_settings
from memory_service.utils.logging import setup_logging


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
def cli(verbose: bool) -> None:
    """Memory Service CLI - Administration and debugging tools."""
    if verbose:
        import logging

        logging.getLogger().setLevel(logging.DEBUG)


@cli.command()
def health() -> None:
    """Check service health."""

    async def _check_health() -> dict[str, Any]:
        from memory_service.storage.qdrant_adapter import QdrantAdapter
        from memory_service.storage.neo4j_adapter import Neo4jAdapter

        settings = get_settings()

        result = {
            "qdrant": {"status": "unknown"},
            "neo4j": {"status": "unknown"},
        }

        try:
            qdrant = QdrantAdapter(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
                api_key=settings.qdrant_api_key,
                project_id=settings.project_id,
            )
            result["qdrant"]["status"] = "healthy" if await qdrant.health_check() else "unhealthy"
            await qdrant.close()
        except Exception as e:
            result["qdrant"]["status"] = "error"
            result["qdrant"]["error"] = str(e)

        try:
            neo4j = Neo4jAdapter(
                uri=settings.neo4j_uri,
                user=settings.neo4j_user,
                password=settings.neo4j_password,
                project_id=settings.project_id,
            )
            result["neo4j"]["status"] = "healthy" if await neo4j.health_check() else "unhealthy"
            await neo4j.close()
        except Exception as e:
            result["neo4j"]["status"] = "error"
            result["neo4j"]["error"] = str(e)

        return result

    setup_logging()
    result = asyncio.run(_check_health())
    click.echo(json.dumps(result, indent=2))

    # Exit with error if any service is unhealthy
    if any(v.get("status") != "healthy" for v in result.values()):
        sys.exit(1)


@cli.command()
def stats() -> None:
    """Show memory statistics."""

    async def _get_stats() -> dict[str, Any]:
        from memory_service.storage.qdrant_adapter import QdrantAdapter
        from memory_service.models import MemoryType

        settings = get_settings()

        qdrant = QdrantAdapter(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            api_key=settings.qdrant_api_key,
            project_id=settings.project_id,
        )

        stats: dict[str, Any] = {
            "project_id": settings.project_id,
            "memory_counts": {},
            "total": 0,
        }

        for memory_type in MemoryType:
            collection = qdrant.get_collection_name(memory_type)
            try:
                count = await qdrant.count(collection, filters={"deleted": False})
                stats["memory_counts"][memory_type.value] = count
                stats["total"] += count
            except Exception:
                stats["memory_counts"][memory_type.value] = "error"

        await qdrant.close()
        return stats

    setup_logging()
    result = asyncio.run(_get_stats())
    click.echo(json.dumps(result, indent=2))


@cli.command()
@click.argument("directory", type=click.Path(exists=True))
@click.option("--extensions", "-e", multiple=True, help="File extensions to include")
@click.option("--exclude", "-x", multiple=True, help="Patterns to exclude")
@click.option("--force", "-f", is_flag=True, help="Force re-index even if files unchanged")
@click.option("--dry-run", is_flag=True, help="Show what would be indexed without indexing")
def index(directory: str, extensions: tuple[str, ...], exclude: tuple[str, ...], force: bool, dry_run: bool) -> None:
    """Index a directory of source code.

    Parses source files, extracts functions and classes, and stores them
    in Qdrant and Neo4j for semantic search and relationship tracking.
    """

    async def _index() -> dict[str, Any]:
        from pathlib import Path

        from memory_service.storage.qdrant_adapter import QdrantAdapter
        from memory_service.storage.neo4j_adapter import Neo4jAdapter
        from memory_service.embedding.service import EmbeddingService
        from memory_service.core.workers import IndexerWorker, JobManager
        from memory_service.utils.gitignore import GitignoreFilter

        settings = get_settings()
        ext_list = list(extensions) if extensions else None
        exclude_list = list(exclude) if exclude else None

        if dry_run:
            gitignore = GitignoreFilter(Path(directory))
            files = list(gitignore.iter_files(extensions=ext_list))
            return {
                "mode": "dry_run",
                "directory": directory,
                "file_count": len(files),
                "files": [str(f) for f in files[:50]],
                "truncated": len(files) > 50,
            }

        # Initialize storage adapters with project_id
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

        # Create indexer worker (the proper way to index with storage)
        job_manager = JobManager()
        indexer = IndexerWorker(
            qdrant=qdrant,
            neo4j=neo4j,
            job_manager=job_manager,
            embedding_service=embedding_service,
        )

        # Run the actual indexing (parse + store)
        result = await indexer.index_directory(
            directory=directory,
            extensions=ext_list,
            exclude_patterns=exclude_list,
            force=force,
        )

        await qdrant.close()
        await neo4j.close()

        return result

    setup_logging()
    result = asyncio.run(_index())
    click.echo(json.dumps(result, indent=2, default=str))


@cli.command()
@click.option("--phases", "-p", multiple=True, help="Specific phases to run")
@click.option("--dry-run", is_flag=True, help="Report changes without applying")
def normalize(phases: tuple[str, ...], dry_run: bool) -> None:
    """Start a normalization job.

    Phases: snapshot, deduplication, orphan_detection, embedding_refresh,
            cleanup, validation, swap
    """

    async def _normalize() -> dict[str, Any]:
        from memory_service.storage.qdrant_adapter import QdrantAdapter
        from memory_service.storage.neo4j_adapter import Neo4jAdapter
        from memory_service.core.workers import NormalizerWorker, JobManager

        settings = get_settings()

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
        job_manager = JobManager()

        normalizer = NormalizerWorker(
            qdrant=qdrant,
            neo4j=neo4j,
            job_manager=job_manager,
        )

        phase_list = list(phases) if phases else None

        result = await normalizer.normalize(
            phases=phase_list,
            dry_run=dry_run,
        )

        await qdrant.close()
        await neo4j.close()

        return result

    setup_logging()
    result = asyncio.run(_normalize())
    click.echo(json.dumps(result, indent=2, default=str))

    if result.get("status") != "success":
        sys.exit(1)


@cli.command()
@click.argument("output", type=click.Path())
@click.option("--memory-types", "-t", multiple=True, help="Memory types to export")
def backup(output: str, memory_types: tuple[str, ...]) -> None:
    """Backup memory data to JSONL file."""

    async def _backup() -> dict[str, Any]:
        from memory_service.storage.qdrant_adapter import QdrantAdapter
        from memory_service.models import MemoryType

        settings = get_settings()

        qdrant = QdrantAdapter(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            api_key=settings.qdrant_api_key,
        )

        # Determine types to export
        if memory_types:
            types = [MemoryType(t) for t in memory_types]
        else:
            types = list(MemoryType)

        exported = 0

        with open(output, "w") as f:
            for mem_type in types:
                collection = qdrant.get_collection_name(mem_type)
                offset = None

                while True:
                    points, next_offset = await qdrant.scroll(
                        collection=collection,
                        filters={"deleted": False},
                        limit=100,
                        offset=offset,
                        with_vectors=True,
                    )

                    for point in points:
                        record = {
                            "id": point["id"],
                            "type": mem_type.value,
                            "vector": point.get("vector"),
                            **point.get("payload", {}),
                        }
                        f.write(json.dumps(record, default=str) + "\n")
                        exported += 1

                    if not next_offset:
                        break
                    offset = next_offset

        await qdrant.close()

        return {
            "status": "completed",
            "output_path": output,
            "exported_count": exported,
        }

    setup_logging()
    result = asyncio.run(_backup())
    click.echo(json.dumps(result, indent=2))


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--skip-existing", is_flag=True, help="Skip memories that already exist")
def restore(input_file: str, skip_existing: bool) -> None:
    """Restore memory data from JSONL backup."""

    async def _restore() -> dict[str, Any]:
        from memory_service.storage.qdrant_adapter import QdrantAdapter
        from memory_service.models import MemoryType

        settings = get_settings()

        qdrant = QdrantAdapter(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            api_key=settings.qdrant_api_key,
        )

        imported = 0
        skipped = 0
        errors = 0

        with open(input_file) as f:
            for line in f:
                if not line.strip():
                    continue

                try:
                    record = json.loads(line)
                    mem_type = MemoryType(record.pop("type"))
                    collection = qdrant.get_collection_name(mem_type)
                    point_id = record.pop("id")
                    vector = record.pop("vector", None)

                    if not vector:
                        errors += 1
                        continue

                    if skip_existing:
                        existing = await qdrant.get(collection, point_id)
                        if existing:
                            skipped += 1
                            continue

                    await qdrant.upsert(
                        collection=collection,
                        point_id=point_id,
                        vector=vector,
                        payload=record,
                    )
                    imported += 1

                except Exception as e:
                    errors += 1
                    click.echo(f"Error: {e}", err=True)

        await qdrant.close()

        return {
            "status": "completed",
            "input_path": input_file,
            "imported_count": imported,
            "skipped_count": skipped,
            "error_count": errors,
        }

    setup_logging()
    result = asyncio.run(_restore())
    click.echo(json.dumps(result, indent=2))

    if result.get("error_count", 0) > 0:
        sys.exit(1)


@cli.command()
def init_schema() -> None:
    """Initialize database schemas and collections."""

    async def _init() -> dict[str, Any]:
        from memory_service.storage.qdrant_adapter import QdrantAdapter
        from memory_service.storage.neo4j_adapter import Neo4jAdapter

        settings = get_settings()

        result = {"qdrant": "pending", "neo4j": "pending"}

        try:
            qdrant = QdrantAdapter(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
                api_key=settings.qdrant_api_key,
                project_id=settings.project_id,
            )
            await qdrant.initialize_collections()
            result["qdrant"] = "initialized"
            await qdrant.close()
        except Exception as e:
            result["qdrant"] = f"error: {e}"

        try:
            neo4j = Neo4jAdapter(
                uri=settings.neo4j_uri,
                user=settings.neo4j_user,
                password=settings.neo4j_password,
                project_id=settings.project_id,
            )
            await neo4j.initialize_schema()
            result["neo4j"] = "initialized"
            await neo4j.close()
        except Exception as e:
            result["neo4j"] = f"error: {e}"

        return result

    setup_logging()
    result = asyncio.run(_init())
    click.echo(json.dumps(result, indent=2))


def main() -> None:
    """CLI entry point."""
    cli()


if __name__ == "__main__":
    main()
