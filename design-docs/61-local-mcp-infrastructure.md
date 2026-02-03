# Local MCP Infrastructure Design

| Field | Value |
|-------|-------|
| **Document ID** | 61-local-mcp-infrastructure |
| **Status** | Draft |
| **Requirements** | REQ-MEM-002-* |
| **ADR** | ADR-009-local-mcp-architecture |

---

## 1. Overview

This design document specifies the infrastructure changes required to transition the MCP server from running inside Docker to running as a native local process. Databases (Qdrant, Neo4j) remain as shared Docker infrastructure.

### 1.1 Scope

**In Scope:**
- Package structure and naming
- CLI interface design
- Global configuration file format and loading
- Docker infrastructure simplification
- Startup validation and error handling

**Out of Scope:**
- MCP tool functionality (unchanged)
- Database schema (unchanged)
- Core memory operations (unchanged)

---

## 2. Package Structure

### 2.1 Package Naming

Current: `memory-service`
New: `claude-memory-mcp`

```
claude-memory-mcp/
  src/
    claude_memory_mcp/         # Renamed from memory_service
      __init__.py
      __main__.py
      config.py               # Enhanced with TOML support
      cli.py                  # New CLI module
      api/
        mcp_server.py         # Modified (no set_project)
        tools/
          ...                 # Unchanged
      core/
        ...                   # Unchanged
      storage/
        ...                   # Unchanged
      embedding/
        ...                   # Unchanged
      models/
        ...                   # Unchanged
      utils/
        ...                   # Unchanged
  pyproject.toml              # Updated
  docker/
    docker-compose.yml        # Database-only
  README.md
```

### 2.2 pyproject.toml Changes

```toml
[project]
name = "claude-memory-mcp"
version = "0.2.0"
description = "Claude Code Long-Term Memory MCP Server"
requires-python = ">=3.11"
dependencies = [
    "qdrant-client>=1.7.0",
    "neo4j>=5.0.0",
    "voyageai>=0.2.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "tree-sitter>=0.21.0,<0.22.0",
    "tree-sitter-languages>=1.8.0",
    "httpx>=0.24.0",
    "structlog>=23.0.0",
    "click>=8.0.0",
    "pathspec>=0.11.0",
    "aiosqlite>=0.19.0",
    "tomli>=2.0.0",
    "tomli-w>=1.0.0",
]

[project.scripts]
claude-memory-mcp = "claude_memory_mcp.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/claude_memory_mcp"]
```

**Key Changes:**
- Package name: `claude-memory-mcp`
- Python requirement: `>=3.11` (was `>=3.12`)
- Removed: `fastapi`, `uvicorn`, `prometheus-client` (no HTTP server)
- Added: `tomli`, `tomli-w` (TOML config support)
- Entry point: `claude-memory-mcp` command

---

## 3. CLI Interface Design

### 3.1 Command Structure

```
claude-memory-mcp [OPTIONS] [COMMAND]

Commands:
  (default)     Start the MCP server (requires --project-id)
  init-config   Create global configuration file
  check-db      Verify database connectivity
  --version     Show version and exit
  --help        Show help and exit

Options:
  --project-id TEXT   Project identifier (required for server mode)
  --config PATH       Override global config file path
  --log-level LEVEL   Override log level (DEBUG|INFO|WARNING|ERROR)
```

### 3.2 CLI Implementation

```python
# cli.py
import sys
import asyncio
from pathlib import Path
from typing import Optional

import click
import tomli
import tomli_w

from claude_memory_mcp.config import (
    get_config_path,
    load_config,
    validate_project_id,
    DEFAULT_CONFIG,
)


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
@click.version_option(version="0.2.0", prog_name="claude-memory-mcp")
@click.pass_context
def main(
    ctx: click.Context,
    project_id: Optional[str],
    config: Optional[str],
    log_level: Optional[str],
) -> None:
    """Claude Code Long-Term Memory MCP Server.

    Start the server with: claude-memory-mcp --project-id my-project
    """
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config
    ctx.obj["log_level"] = log_level

    # If no subcommand, run server
    if ctx.invoked_subcommand is None:
        if not project_id:
            click.echo("Error: --project-id is required to start the server", err=True)
            click.echo("Usage: claude-memory-mcp --project-id <project-name>", err=True)
            sys.exit(1)

        # Validate project_id format
        if not validate_project_id(project_id):
            click.echo(
                f"Error: Invalid project_id '{project_id}'. "
                "Must match: ^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$",
                err=True,
            )
            sys.exit(1)

        ctx.obj["project_id"] = project_id
        asyncio.run(run_server(ctx.obj))


@main.command()
@click.pass_context
def init_config(ctx: click.Context) -> None:
    """Create global configuration file with defaults."""
    config_path = Path(ctx.obj.get("config_path") or get_config_path())

    if config_path.exists():
        click.echo(f"Config file already exists: {config_path}")
        if not click.confirm("Overwrite?"):
            sys.exit(0)

    # Create directory if needed
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Write default config
    with open(config_path, "wb") as f:
        tomli_w.dump(DEFAULT_CONFIG, f)

    # Set permissions to 600 (owner read/write only)
    config_path.chmod(0o600)

    click.echo(f"Created config file: {config_path}")
    click.echo("Edit this file to add your Voyage API key and Neo4j password.")


@main.command()
@click.pass_context
def check_db(ctx: click.Context) -> None:
    """Verify database connectivity."""
    asyncio.run(check_database_connectivity(ctx.obj))


async def run_server(options: dict) -> None:
    """Run the MCP server."""
    from claude_memory_mcp.config import load_config
    from claude_memory_mcp.utils.logging import setup_logging, get_logger

    # Load configuration
    config_path = options.get("config_path")
    config = load_config(config_path)

    # Apply CLI overrides
    if options.get("log_level"):
        config.log_level = options["log_level"]

    project_id = options["project_id"]

    # Setup logging to stderr (keep stdout clean for MCP)
    setup_logging(use_stderr=True, level=config.log_level)
    logger = get_logger(__name__)

    logger.info("starting_mcp_server", project_id=project_id, version="0.2.0")

    # Import after config is loaded
    from claude_memory_mcp.storage.qdrant_adapter import QdrantAdapter
    from claude_memory_mcp.storage.neo4j_adapter import Neo4jAdapter
    from claude_memory_mcp.embedding.service import EmbeddingService
    from claude_memory_mcp.api.mcp_server import MCPServer

    # Initialize adapters with project_id
    try:
        qdrant = QdrantAdapter(
            host=config.qdrant_host,
            port=config.qdrant_port,
            api_key=config.qdrant_api_key,
            project_id=project_id,
        )
        await qdrant.initialize_collections()
    except Exception as e:
        logger.error("qdrant_connection_failed", error=str(e))
        click.echo(f"Error: Cannot connect to Qdrant at {config.qdrant_host}:{config.qdrant_port}", err=True)
        click.echo("Make sure databases are running: docker-compose up -d", err=True)
        sys.exit(1)

    try:
        neo4j = Neo4jAdapter(
            uri=config.neo4j_uri,
            user=config.neo4j_user,
            password=config.neo4j_password,
            project_id=project_id,
        )
        await neo4j.initialize_schema()
    except Exception as e:
        logger.error("neo4j_connection_failed", error=str(e))
        click.echo(f"Error: Cannot connect to Neo4j at {config.neo4j_uri}", err=True)
        click.echo("Make sure databases are running: docker-compose up -d", err=True)
        await qdrant.close()
        sys.exit(1)

    embedding_service = EmbeddingService(
        api_key=config.voyage_api_key,
        model=config.voyage_model,
    )

    # Create and run MCP server
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


async def check_database_connectivity(options: dict) -> None:
    """Check database connectivity."""
    from claude_memory_mcp.config import load_config

    config_path = options.get("config_path")
    config = load_config(config_path)

    click.echo("Checking database connectivity...")
    click.echo()

    # Check Qdrant
    click.echo(f"Qdrant ({config.qdrant_host}:{config.qdrant_port})... ", nl=False)
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(host=config.qdrant_host, port=config.qdrant_port)
        client.get_collections()
        click.echo(click.style("OK", fg="green"))
    except Exception as e:
        click.echo(click.style(f"FAILED: {e}", fg="red"))

    # Check Neo4j
    click.echo(f"Neo4j ({config.neo4j_uri})... ", nl=False)
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            config.neo4j_uri,
            auth=(config.neo4j_user, config.neo4j_password.get_secret_value()),
        )
        with driver.session() as session:
            session.run("RETURN 1")
        driver.close()
        click.echo(click.style("OK", fg="green"))
    except Exception as e:
        click.echo(click.style(f"FAILED: {e}", fg="red"))

    # Check Voyage API (optional)
    if config.voyage_api_key and config.voyage_api_key.get_secret_value():
        click.echo("Voyage API... ", nl=False)
        try:
            import voyageai
            client = voyageai.Client(api_key=config.voyage_api_key.get_secret_value())
            # Simple test - just check we can create client
            click.echo(click.style("OK (key configured)", fg="green"))
        except Exception as e:
            click.echo(click.style(f"FAILED: {e}", fg="red"))
    else:
        click.echo("Voyage API... ", nl=False)
        click.echo(click.style("NOT CONFIGURED", fg="yellow"))


if __name__ == "__main__":
    main()
```

---

## 4. Configuration System

### 4.1 Global Config File

**Location (XDG Base Directory):**
- Linux/macOS: `~/.config/claude-memory/config.toml`
- Windows: `%APPDATA%\claude-memory\config.toml`

**Format (TOML):**

```toml
# Claude Memory MCP Configuration
# Created by: claude-memory-mcp init-config

[qdrant]
host = "localhost"
port = 6333
# api_key = "optional-if-auth-enabled"

[neo4j]
uri = "bolt://localhost:7687"
user = "neo4j"
password = "changeme"

[voyage]
api_key = "your-voyage-api-key"
model = "voyage-code-3"

[server]
log_level = "INFO"

[cache]
path = "~/.cache/claude-memory/embeddings.db"
size = 10000
ttl_days = 30

[search]
default_limit = 10
max_limit = 100
duplicate_threshold = 0.85

[normalization]
batch_size = 1000
soft_delete_retention_days = 30
```

### 4.2 Configuration Precedence

```
CLI Arguments (highest priority)
        |
        v
Environment Variables (CLAUDE_MEMORY_*)
        |
        v
Global Config File (~/.config/claude-memory/config.toml)
        |
        v
Built-in Defaults (lowest priority)
```

### 4.3 Environment Variable Mapping

| Config Key | Environment Variable |
|------------|---------------------|
| qdrant.host | CLAUDE_MEMORY_QDRANT_HOST |
| qdrant.port | CLAUDE_MEMORY_QDRANT_PORT |
| qdrant.api_key | CLAUDE_MEMORY_QDRANT_API_KEY |
| neo4j.uri | CLAUDE_MEMORY_NEO4J_URI |
| neo4j.user | CLAUDE_MEMORY_NEO4J_USER |
| neo4j.password | CLAUDE_MEMORY_NEO4J_PASSWORD |
| voyage.api_key | CLAUDE_MEMORY_VOYAGE_API_KEY |
| voyage.model | CLAUDE_MEMORY_VOYAGE_MODEL |
| server.log_level | CLAUDE_MEMORY_LOG_LEVEL |

### 4.4 Config Module Implementation

```python
# config.py
import os
import re
from pathlib import Path
from functools import lru_cache
from typing import Any, Optional

import tomli
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


# Project ID validation pattern
PROJECT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")


def validate_project_id(project_id: str) -> bool:
    """Validate project_id format."""
    return bool(PROJECT_ID_PATTERN.match(project_id))


def get_config_path() -> Path:
    """Get the global config file path (XDG compliant)."""
    if os.name == "nt":  # Windows
        base = Path(os.environ.get("APPDATA", "~"))
    else:  # Linux/macOS
        base = Path(os.environ.get("XDG_CONFIG_HOME", "~/.config"))
    return base.expanduser() / "claude-memory" / "config.toml"


def load_toml_config(path: Optional[Path] = None) -> dict[str, Any]:
    """Load configuration from TOML file."""
    config_path = path or get_config_path()
    if config_path.exists():
        with open(config_path, "rb") as f:
            return tomli.load(f)
    return {}


# Default configuration for init-config
DEFAULT_CONFIG = {
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


class Settings(BaseSettings):
    """Application settings with multi-source loading."""

    model_config = SettingsConfigDict(
        env_prefix="CLAUDE_MEMORY_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Qdrant Configuration
    qdrant_host: str = Field(default="localhost")
    qdrant_port: int = Field(default=6333)
    qdrant_api_key: SecretStr | None = Field(default=None)

    # Neo4j Configuration
    neo4j_uri: str = Field(default="bolt://localhost:7687")
    neo4j_user: str = Field(default="neo4j")
    neo4j_password: SecretStr = Field(default=SecretStr(""))

    # Voyage AI Configuration
    voyage_api_key: SecretStr = Field(default=SecretStr(""))
    voyage_model: str = Field(default="voyage-code-3")

    # Logging
    log_level: str = Field(default="INFO")

    # Cache
    embedding_cache_path: str = Field(default="~/.cache/claude-memory/embeddings.db")
    embedding_cache_size: int = Field(default=10000)
    embedding_cache_ttl_days: int = Field(default=30)

    # Search
    search_default_limit: int = Field(default=10)
    search_max_limit: int = Field(default=100)
    duplicate_threshold: float = Field(default=0.85)

    # Normalization
    normalization_batch_size: int = Field(default=1000)
    soft_delete_retention_days: int = Field(default=30)


def load_config(config_path: Optional[str] = None) -> Settings:
    """Load configuration with precedence: CLI > env > file > defaults."""
    # Load TOML config
    path = Path(config_path) if config_path else None
    toml_config = load_toml_config(path)

    # Flatten nested TOML to environment-like keys
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

    if "server" in toml_config:
        if "log_level" in toml_config["server"]:
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

    # Create settings with overrides from TOML (env vars take precedence via pydantic-settings)
    return Settings(**overrides)
```

---

## 5. Docker Infrastructure Changes

### 5.1 Simplified docker-compose.yml

```yaml
# docker/docker-compose.yml
# Database infrastructure for Claude Memory MCP
# The MCP server runs locally, not in Docker

version: '3.8'

services:
  qdrant:
    image: qdrant/qdrant:v1.15.0
    container_name: claude-memory-qdrant
    restart: unless-stopped
    ports:
      - "127.0.0.1:6333:6333"
      - "127.0.0.1:6334:6334"
    environment:
      - QDRANT__SERVICE__GRPC_PORT=6334
      - QDRANT__LOG_LEVEL=${QDRANT_LOG_LEVEL:-INFO}
    ulimits:
      nofile:
        soft: 65536
        hard: 65536
    volumes:
      - claude-memory-qdrant-data:/qdrant/storage

  neo4j:
    image: neo4j:5.15-community
    container_name: claude-memory-neo4j
    restart: unless-stopped
    ports:
      - "127.0.0.1:7474:7474"
      - "127.0.0.1:7687:7687"
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD:-changeme}
      - NEO4J_PLUGINS=["apoc"]
      - NEO4J_dbms_security_procedures_unrestricted=apoc.*
      - NEO4J_dbms_memory_heap_initial__size=512m
      - NEO4J_dbms_memory_heap_max__size=1G
      - NEO4J_dbms_memory_pagecache_size=512m
    volumes:
      - claude-memory-neo4j-data:/data
      - claude-memory-neo4j-logs:/logs
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:7474"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

volumes:
  claude-memory-qdrant-data:
    name: claude-memory-qdrant-data
  claude-memory-neo4j-data:
    name: claude-memory-neo4j-data
  claude-memory-neo4j-logs:
    name: claude-memory-neo4j-logs
```

### 5.2 Key Changes from Original

| Aspect | Before | After |
|--------|--------|-------|
| Services | memory-service + qdrant + neo4j | qdrant + neo4j only |
| Ports | 0.0.0.0 binding | 127.0.0.1 binding (localhost only) |
| Volume names | qdrant-data, neo4j-data | claude-memory-* prefix |
| Networks | memory-network | None (simplified) |
| .env needs | VOYAGE_API_KEY, PROJECT_PATH | NEO4J_PASSWORD only |

### 5.3 docker/.env.example

```env
# Claude Memory Database Configuration
# Copy to .env and edit

# Neo4j password (required)
NEO4J_PASSWORD=changeme

# Optional: Qdrant log level
QDRANT_LOG_LEVEL=INFO
```

---

## 6. MCP Server Changes

### 6.1 Remove set_project Tool

The `set_project` and `get_project` tools will be removed from `mcp_server.py`. Project isolation is enforced at startup via `--project-id`.

**Removed code:**

```python
# Remove these tool registrations
self._register_tool("set_project", ...)
self._register_tool("get_project", ...)

# Remove these handlers
async def _handle_set_project(self, args: dict[str, Any]) -> dict[str, Any]:
    ...

async def _handle_get_project(self, args: dict[str, Any]) -> dict[str, Any]:
    ...
```

**Add project info to initialize response:**

```python
def _handle_initialize(self, msg_id: Any, params: dict[str, Any]) -> dict[str, Any]:
    return self._success_response(
        msg_id,
        {
            "protocolVersion": "2024-11-05",
            "serverInfo": {
                "name": "claude-memory-mcp",
                "version": "0.2.0",
                "project_id": self._current_project_id,  # Add this
            },
            "capabilities": {
                "tools": {"listChanged": False},
            },
        },
    )
```

### 6.2 Startup Validation

The server performs these checks at startup:

1. **Config file exists** (or warn if using defaults)
2. **Qdrant connectivity** (fail-fast with clear error)
3. **Neo4j connectivity** (fail-fast with clear error)
4. **Voyage API key** (warn if missing, may fail on first embed call)

---

## 7. Error Messages

### 7.1 Error Categories

```python
class ErrorCategory(str, Enum):
    CONFIGURATION = "configuration"
    DATABASE = "database"
    API_KEY = "api_key"
    VALIDATION = "validation"
    INTERNAL = "internal"


def format_error(category: ErrorCategory, message: str, remediation: str) -> str:
    """Format error with category and remediation."""
    return f"""
Error [{category.value.upper()}]: {message}

Remediation: {remediation}
"""
```

### 7.2 Common Error Messages

| Condition | Error Message | Remediation |
|-----------|---------------|-------------|
| No config file | Configuration file not found | Run: claude-memory-mcp init-config |
| Qdrant unreachable | Cannot connect to Qdrant at localhost:6333 | Run: docker-compose up -d |
| Neo4j unreachable | Cannot connect to Neo4j at bolt://localhost:7687 | Run: docker-compose up -d |
| Neo4j auth failed | Neo4j authentication failed | Check password in config.toml |
| Missing Voyage key | Voyage API key not configured | Add voyage.api_key to config.toml |
| Invalid project_id | Invalid project_id format | Must match: ^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$ |
| Missing --project-id | --project-id is required | claude-memory-mcp --project-id your-project |

---

## 8. mcp.json Integration

### 8.1 Per-Project Configuration

```json
{
  "mcpServers": {
    "memory": {
      "command": "claude-memory-mcp",
      "args": ["--project-id", "my-project"]
    }
  }
}
```

### 8.2 Using Project Virtual Environment

```json
{
  "mcpServers": {
    "memory": {
      "command": ".venv/bin/claude-memory-mcp",
      "args": ["--project-id", "my-project"]
    }
  }
}
```

### 8.3 With Log Level Override

```json
{
  "mcpServers": {
    "memory": {
      "command": "claude-memory-mcp",
      "args": ["--project-id", "my-project", "--log-level", "DEBUG"]
    }
  }
}
```

---

## 9. Requirements Compliance

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| REQ-MEM-002-FN-001 | Compliant | Package named claude-memory-mcp |
| REQ-MEM-002-FN-003 | Compliant | CLI entry point claude-memory-mcp |
| REQ-MEM-002-FN-010 | Compliant | Local process, not Docker |
| REQ-MEM-002-FN-011 | Compliant | stdio transport only |
| REQ-MEM-002-FN-012 | Compliant | --project-id CLI argument |
| REQ-MEM-002-FN-020 | Compliant | TOML config at ~/.config/claude-memory/ |
| REQ-MEM-002-FN-024 | Compliant | init-config command |
| REQ-MEM-002-FN-034 | Compliant | set_project removed |
| REQ-MEM-002-FN-042 | Compliant | Ports bound to 127.0.0.1 |
| REQ-MEM-002-FN-043 | Compliant | check-db command |
| REQ-MEM-002-CON-001 | Compliant | MCP not in Docker |
| REQ-MEM-002-DATA-002 | Compliant | CLI > env > file > defaults |
| REQ-MEM-002-NFR-USE-002 | Compliant | Error messages with remediation |
| REQ-MEM-002-NFR-USE-003 | Compliant | Fail-fast on DB unavailable |
| REQ-MEM-002-NFR-SEC-002 | Compliant | Config file chmod 600 |

---

*Document Version: 1.0*
*Last Updated: 2026-02-02*
