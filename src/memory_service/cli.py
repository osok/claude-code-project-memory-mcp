"""CLI entry point for claude-memory-mcp.

This module provides the main command-line interface for the MCP server,
including commands for initialization, database connectivity checks, and
running the server with project isolation.

Usage:
    claude-memory-mcp --project-id my-project    # Start MCP server
    claude-memory-mcp init-config                # Create config file
    claude-memory-mcp check-db                   # Verify database connectivity
    claude-memory-mcp --version                  # Show version
    claude-memory-mcp --help                     # Show help

Requirements:
    REQ-MEM-002-FN-003: CLI entry point claude-memory-mcp
    REQ-MEM-002-FN-012: --project-id CLI argument
    REQ-MEM-002-FN-024: init-config command
    REQ-MEM-002-FN-043: check-db command
    REQ-MEM-002-INT-CLI-001: All subcommands functional
"""

import asyncio
import contextlib
import os
import re
import sys
from pathlib import Path
from typing import Any

import click

# Version
__version__ = "0.2.0"

# Project ID validation pattern (REQ-MEM-002-DATA-010)
PROJECT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")


def validate_project_id(project_id: str) -> bool:
    """Validate project_id format.

    Args:
        project_id: Project identifier to validate

    Returns:
        True if valid, False otherwise

    Pattern: ^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$
    - Must start with alphanumeric
    - Can contain alphanumeric, underscore, hyphen
    - 1-64 characters total
    """
    return bool(PROJECT_ID_PATTERN.match(project_id))


def get_config_path() -> Path:
    """Get the global config file path (XDG compliant).

    Returns:
        Path to config file:
        - Linux/macOS: ~/.config/claude-memory/config.toml
        - Windows: %APPDATA%/claude-memory/config.toml
    """
    if os.name == "nt":  # Windows
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:  # Linux/macOS
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "claude-memory" / "config.toml"


def get_default_config() -> dict[str, Any]:
    """Get default configuration for init-config.

    Returns:
        Default configuration dictionary
    """
    return {
        "qdrant": {
            "host": "localhost",
            "port": 6333,
        },
        "neo4j": {
            "uri": "bolt://localhost:7687",
            "user": "neo4j",
            "password": "changeme",
        },
        "voyage": {
            "api_key": "your-voyage-api-key",
            "model": "voyage-code-3",
        },
        "server": {
            "log_level": "INFO",
        },
        "cache": {
            "path": "~/.cache/claude-memory/embeddings.db",
            "size": 10000,
            "ttl_days": 30,
        },
        "search": {
            "default_limit": 10,
            "max_limit": 100,
            "duplicate_threshold": 0.85,
        },
        "normalization": {
            "batch_size": 1000,
            "soft_delete_retention_days": 30,
        },
    }


def load_toml_config(path: Path | None = None) -> dict[str, Any]:
    """Load configuration from TOML file.

    Args:
        path: Path to config file (uses default if None)

    Returns:
        Configuration dictionary (empty if file doesn't exist)
    """
    try:
        import tomli
    except ImportError:
        # Python 3.11+ has tomllib in stdlib
        import tomllib as tomli

    config_path = path or get_config_path()
    if config_path.exists():
        with open(config_path, "rb") as f:
            return tomli.load(f)
    return {}


def flatten_config(toml_config: dict[str, Any]) -> dict[str, Any]:
    """Flatten nested TOML config to flat dictionary for Settings.

    Args:
        toml_config: Nested TOML configuration

    Returns:
        Flattened configuration dictionary
    """
    overrides = {}

    if "qdrant" in toml_config:
        if "host" in toml_config["qdrant"]:
            overrides["qdrant_host"] = toml_config["qdrant"]["host"]
        if "port" in toml_config["qdrant"]:
            overrides["qdrant_port"] = toml_config["qdrant"]["port"]
        if "api_key" in toml_config["qdrant"]:
            overrides["qdrant_api_key"] = toml_config["qdrant"]["api_key"]

    if "neo4j" in toml_config:
        if "uri" in toml_config["neo4j"]:
            overrides["neo4j_uri"] = toml_config["neo4j"]["uri"]
        if "user" in toml_config["neo4j"]:
            overrides["neo4j_user"] = toml_config["neo4j"]["user"]
        if "password" in toml_config["neo4j"]:
            overrides["neo4j_password"] = toml_config["neo4j"]["password"]

    if "voyage" in toml_config:
        if "api_key" in toml_config["voyage"]:
            overrides["voyage_api_key"] = toml_config["voyage"]["api_key"]
        if "model" in toml_config["voyage"]:
            overrides["voyage_model"] = toml_config["voyage"]["model"]

    if "server" in toml_config and "log_level" in toml_config["server"]:
        overrides["log_level"] = toml_config["server"]["log_level"]

    if "cache" in toml_config:
        if "path" in toml_config["cache"]:
            overrides["embedding_cache_path"] = toml_config["cache"]["path"]
        if "size" in toml_config["cache"]:
            overrides["embedding_cache_size"] = toml_config["cache"]["size"]
        if "ttl_days" in toml_config["cache"]:
            overrides["embedding_cache_ttl_days"] = toml_config["cache"]["ttl_days"]

    if "search" in toml_config:
        if "default_limit" in toml_config["search"]:
            overrides["search_default_limit"] = toml_config["search"]["default_limit"]
        if "max_limit" in toml_config["search"]:
            overrides["search_max_limit"] = toml_config["search"]["max_limit"]
        if "duplicate_threshold" in toml_config["search"]:
            overrides["duplicate_threshold"] = toml_config["search"]["duplicate_threshold"]

    if "normalization" in toml_config:
        if "batch_size" in toml_config["normalization"]:
            overrides["normalization_batch_size"] = toml_config["normalization"]["batch_size"]
        if "soft_delete_retention_days" in toml_config["normalization"]:
            overrides["soft_delete_retention_days"] = toml_config["normalization"]["soft_delete_retention_days"]

    return overrides


class ErrorCategory:
    """Error categories for clear error messages (REQ-MEM-002-NFR-USE-002)."""

    CONFIGURATION = "configuration"
    DATABASE = "database"
    API_KEY = "api_key"
    VALIDATION = "validation"
    INTERNAL = "internal"


def format_error(category: str, message: str, remediation: str) -> str:
    """Format error with category and remediation.

    Args:
        category: Error category
        message: Error message
        remediation: Suggested fix

    Returns:
        Formatted error string
    """
    return f"""
Error [{category.upper()}]: {message}

Remediation: {remediation}
"""


@click.group(invoke_without_command=True)
@click.option(
    "--project-id",
    type=str,
    help="Project identifier (required for server mode)",
)
@click.option(
    "--config",
    type=click.Path(exists=False),
    help="Override global config file path",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    help="Override log level",
)
@click.version_option(version=__version__, prog_name="claude-memory-mcp")
@click.pass_context
def main(
    ctx: click.Context,
    project_id: str | None,
    config: str | None,
    log_level: str | None,
) -> None:
    """Claude Code Long-Term Memory MCP Server.

    Start the server with: claude-memory-mcp --project-id my-project

    The MCP server provides persistent memory for Claude Code, enabling
    context persistence, semantic search, duplicate detection, and
    design alignment verification across development sessions.

    Configuration is loaded from (in priority order):
    1. CLI arguments
    2. Environment variables (CLAUDE_MEMORY_*)
    3. Global config file (~/.config/claude-memory/config.toml)
    4. Built-in defaults
    """
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config
    ctx.obj["log_level"] = log_level

    # If no subcommand, run server
    if ctx.invoked_subcommand is None:
        if not project_id:
            click.echo(
                format_error(
                    ErrorCategory.VALIDATION,
                    "--project-id is required to start the server",
                    "Usage: claude-memory-mcp --project-id <project-name>",
                ),
                err=True,
            )
            sys.exit(1)

        # Validate project_id format (REQ-MEM-002-DATA-010)
        if not validate_project_id(project_id):
            click.echo(
                format_error(
                    ErrorCategory.VALIDATION,
                    f"Invalid project_id '{project_id}'",
                    "Project ID must match: ^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$\n"
                    "  - Start with alphanumeric character\n"
                    "  - Use only letters, numbers, hyphens, underscores\n"
                    "  - Maximum 64 characters",
                ),
                err=True,
            )
            sys.exit(1)

        ctx.obj["project_id"] = project_id
        asyncio.run(run_server(ctx.obj))


@main.command()
@click.pass_context
def init_config(ctx: click.Context) -> None:
    """Create global configuration file with defaults.

    Creates the configuration file at ~/.config/claude-memory/config.toml
    (or %APPDATA%/claude-memory/config.toml on Windows).

    The file is created with restrictive permissions (600) to protect
    sensitive data like API keys.
    """
    try:
        import tomli_w
    except ImportError:
        click.echo("Error: tomli-w package required. Install with: pip install tomli-w", err=True)
        sys.exit(1)

    config_path = Path(ctx.obj.get("config_path") or get_config_path())

    if config_path.exists():
        click.echo(f"Config file already exists: {config_path}")
        if not click.confirm("Overwrite?"):
            sys.exit(0)

    # Create directory if needed
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Write default config
    default_config = get_default_config()
    with open(config_path, "wb") as f:
        tomli_w.dump(default_config, f)

    # Set permissions to 600 (owner read/write only) - REQ-MEM-002-NFR-SEC-002
    # Use contextlib.suppress for Windows compatibility (chmod may not be supported)
    with contextlib.suppress(OSError):
        config_path.chmod(0o600)

    click.echo(f"Created config file: {config_path}")
    click.echo()
    click.echo("Next steps:")
    click.echo("  1. Edit the config file to add your Voyage API key")
    click.echo("  2. Update the Neo4j password if changed from default")
    click.echo("  3. Start databases: cd docker && docker-compose up -d")
    click.echo("  4. Verify connectivity: claude-memory-mcp check-db")


@main.command()
@click.pass_context
def check_db(ctx: click.Context) -> None:
    """Verify database connectivity.

    Checks connection to:
    - Qdrant vector database
    - Neo4j graph database
    - Voyage AI API (if configured)

    Returns exit code 0 if all checks pass, 1 otherwise.
    """
    asyncio.run(check_database_connectivity(ctx.obj))


async def run_server(options: dict[str, Any]) -> None:
    """Run the MCP server.

    Args:
        options: CLI options including project_id, config_path, log_level
    """
    from memory_service.config import Settings
    from memory_service.utils.logging import get_logger, setup_logging

    # Load configuration with precedence: CLI > env > file > defaults
    config_path = options.get("config_path")
    toml_config = load_toml_config(Path(config_path) if config_path else None)
    overrides = flatten_config(toml_config)

    # Create settings (env vars will override via pydantic-settings)
    settings = Settings(**overrides)

    # Apply CLI overrides
    if options.get("log_level"):
        settings.log_level = options["log_level"]

    project_id = options["project_id"]

    # Setup logging to stderr (keep stdout clean for MCP stdio)
    setup_logging(use_stderr=True)
    logger = get_logger(__name__)

    logger.info("starting_mcp_server", project_id=project_id, version=__version__)

    # Import after config is loaded
    from memory_service.api.mcp_server import MCPServer
    from memory_service.embedding.service import EmbeddingService
    from memory_service.storage.neo4j_adapter import Neo4jAdapter
    from memory_service.storage.qdrant_adapter import QdrantAdapter

    # Initialize Qdrant with fail-fast (REQ-MEM-002-NFR-USE-003)
    try:
        qdrant = QdrantAdapter(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            api_key=settings.qdrant_api_key,
            project_id=project_id,
        )
        await qdrant.initialize_collections()
        logger.info("qdrant_connected", host=settings.qdrant_host, port=settings.qdrant_port)
    except Exception as e:
        logger.error("qdrant_connection_failed", error=str(e))
        click.echo(
            format_error(
                ErrorCategory.DATABASE,
                f"Cannot connect to Qdrant at {settings.qdrant_host}:{settings.qdrant_port}",
                "Make sure databases are running:\n"
                "  cd docker && docker-compose up -d\n\n"
                f"Details: {e}",
            ),
            err=True,
        )
        sys.exit(1)

    # Initialize Neo4j with fail-fast (REQ-MEM-002-NFR-USE-003)
    try:
        neo4j = Neo4jAdapter(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password,
            project_id=project_id,
        )
        await neo4j.initialize_schema()
        logger.info("neo4j_connected", uri=settings.neo4j_uri)
    except Exception as e:
        logger.error("neo4j_connection_failed", error=str(e))
        click.echo(
            format_error(
                ErrorCategory.DATABASE,
                f"Cannot connect to Neo4j at {settings.neo4j_uri}",
                "Make sure databases are running:\n"
                "  cd docker && docker-compose up -d\n\n"
                "If authentication failed, check neo4j.password in config.\n\n"
                f"Details: {e}",
            ),
            err=True,
        )
        await qdrant.close()
        sys.exit(1)

    # Initialize embedding service
    embedding_service = EmbeddingService(
        api_key=settings.voyage_api_key,
        model=settings.voyage_model,
    )

    # Warn if Voyage API key not configured
    if not settings.voyage_api_key or not settings.voyage_api_key.get_secret_value():
        logger.warning("voyage_api_key_not_configured")
        click.echo(
            "Warning: Voyage API key not configured. Embedding operations will fail.",
            err=True,
        )
        click.echo(
            "Add voyage.api_key to ~/.config/claude-memory/config.toml",
            err=True,
        )

    # Create and run MCP server
    mcp_server = MCPServer(
        qdrant=qdrant,
        neo4j=neo4j,
        embedding_service=embedding_service,
    )

    try:
        await mcp_server.run()
    except KeyboardInterrupt:
        logger.info("mcp_server_interrupted")
    finally:
        await qdrant.close()
        await neo4j.close()
        logger.info("mcp_server_stopped")


async def check_database_connectivity(options: dict[str, Any]) -> None:
    """Check database connectivity.

    Args:
        options: CLI options including config_path
    """
    from memory_service.config import Settings

    config_path = options.get("config_path")
    toml_config = load_toml_config(Path(config_path) if config_path else None)
    overrides = flatten_config(toml_config)
    settings = Settings(**overrides)

    click.echo("Checking database connectivity...")
    click.echo()

    all_ok = True

    # Check Qdrant
    click.echo(f"Qdrant ({settings.qdrant_host}:{settings.qdrant_port})... ", nl=False)
    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        collections = client.get_collections()
        click.echo(click.style("OK", fg="green") + f" ({len(collections.collections)} collections)")
    except Exception as e:
        click.echo(click.style("FAILED", fg="red"))
        click.echo(f"  Error: {e}")
        all_ok = False

    # Check Neo4j
    click.echo(f"Neo4j ({settings.neo4j_uri})... ", nl=False)
    try:
        from neo4j import GraphDatabase

        password = settings.neo4j_password.get_secret_value() if settings.neo4j_password else ""
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, password),
        )
        with driver.session() as session:
            result = session.run("RETURN 1 as n")
            result.single()
        driver.close()
        click.echo(click.style("OK", fg="green"))
    except Exception as e:
        click.echo(click.style("FAILED", fg="red"))
        click.echo(f"  Error: {e}")
        all_ok = False

    # Check Voyage API (optional)
    voyage_key = settings.voyage_api_key.get_secret_value() if settings.voyage_api_key else ""
    if voyage_key and voyage_key != "your-voyage-api-key":
        click.echo("Voyage API... ", nl=False)
        try:
            import voyageai

            client = voyageai.Client(api_key=voyage_key)
            # Just verify we can create the client - don't make API call
            click.echo(click.style("OK", fg="green") + " (key configured)")
        except Exception as e:
            click.echo(click.style("FAILED", fg="red"))
            click.echo(f"  Error: {e}")
            all_ok = False
    else:
        click.echo("Voyage API... ", nl=False)
        click.echo(click.style("NOT CONFIGURED", fg="yellow"))
        click.echo("  Add voyage.api_key to config.toml for embedding support")

    click.echo()
    if all_ok:
        click.echo(click.style("All checks passed!", fg="green"))
        sys.exit(0)
    else:
        click.echo(click.style("Some checks failed. See above for details.", fg="red"))
        sys.exit(1)


if __name__ == "__main__":
    main()
