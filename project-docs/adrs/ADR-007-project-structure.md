# ADR-007: Project Structure and Module Organization

## Status

Accepted

## Context

The memory system needs a clear, maintainable project structure that:
- Separates concerns appropriately
- Supports testing at all levels
- Enables future extension (new memory types, languages)
- Follows Python packaging best practices
- Supports Docker deployment

Requirements addressed:
- REQ-MEM-MAINT-001: Type hints and docstrings
- REQ-MEM-MAINT-005: 80% unit test coverage
- REQ-MEM-DEP-001: Docker compose configuration

## Options Considered

### Option 1: Flat Structure

```
memory_service/
    main.py
    mcp_server.py
    qdrant_client.py
    neo4j_client.py
    embedding_service.py
    ...
```

- **Pros**: Simple, no import complexity
- **Cons**: Doesn't scale, no clear boundaries

### Option 2: Domain-Driven Modules

```
memory_service/
    domain/
        memories/
        indexing/
        queries/
    infrastructure/
        qdrant/
        neo4j/
        voyage/
    application/
        mcp/
        cli/
```

- **Pros**: Clear domain boundaries, DDD patterns
- **Cons**: Over-engineered for this system size

### Option 3: Layered Architecture

```
memory_service/
    api/           # MCP tools, CLI
    core/          # Business logic
    storage/       # Qdrant, Neo4j adapters
    parsing/       # Code parsing
    embedding/     # Voyage integration
```

- **Pros**: Clear layers, appropriate complexity
- **Cons**: Some cross-cutting concerns

## Decision

**Option 3: Layered Architecture** - Organize by technical layer with clear dependencies.

### Directory Structure

```
claude-code-memory-mcp/
|
+-- src/
|   +-- memory_service/
|   |   +-- __init__.py
|   |   +-- __main__.py           # Entry point
|   |   +-- config.py             # Configuration management
|   |   |
|   |   +-- api/                  # External interfaces
|   |   |   +-- __init__.py
|   |   |   +-- mcp_server.py     # MCP server (stdio)
|   |   |   +-- http_server.py    # Health/metrics HTTP server
|   |   |   +-- cli.py            # CLI commands
|   |   |   +-- tools/            # MCP tool implementations
|   |   |       +-- __init__.py
|   |   |       +-- memory_crud.py
|   |   |       +-- search.py
|   |   |       +-- indexing.py
|   |   |       +-- analysis.py
|   |   |       +-- maintenance.py
|   |   |
|   |   +-- core/                 # Business logic
|   |   |   +-- __init__.py
|   |   |   +-- memory_manager.py # Memory lifecycle
|   |   |   +-- query_engine.py   # Query planning/execution
|   |   |   +-- indexer.py        # Codebase indexing orchestration
|   |   |   +-- normalizer.py     # Normalization process
|   |   |   +-- duplicate_detector.py
|   |   |   +-- pattern_matcher.py
|   |   |   +-- design_validator.py
|   |   |
|   |   +-- models/               # Data models
|   |   |   +-- __init__.py
|   |   |   +-- base.py           # Base memory model
|   |   |   +-- memories.py       # Memory type models
|   |   |   +-- code_elements.py  # Function, Class, etc.
|   |   |   +-- relationships.py  # Relationship types
|   |   |   +-- schemas.py        # Pydantic schemas for validation
|   |   |
|   |   +-- storage/              # Storage adapters
|   |   |   +-- __init__.py
|   |   |   +-- qdrant_adapter.py
|   |   |   +-- neo4j_adapter.py
|   |   |   +-- cache.py          # Embedding cache (SQLite)
|   |   |   +-- sync.py           # Cross-store synchronization
|   |   |
|   |   +-- parsing/              # Code parsing
|   |   |   +-- __init__.py
|   |   |   +-- parser.py         # Tree-sitter orchestration
|   |   |   +-- extractors/       # Language-specific extractors
|   |   |       +-- __init__.py
|   |   |       +-- base.py
|   |   |       +-- python.py
|   |   |       +-- typescript.py
|   |   |       +-- javascript.py
|   |   |       +-- java.py
|   |   |       +-- go.py
|   |   |       +-- rust.py
|   |   |       +-- csharp.py
|   |   |
|   |   +-- embedding/            # Embedding service
|   |   |   +-- __init__.py
|   |   |   +-- service.py        # Main embedding service
|   |   |   +-- voyage_client.py  # Voyage AI client
|   |   |   +-- fallback.py       # Local fallback model
|   |   |   +-- batch_processor.py
|   |   |
|   |   +-- utils/                # Shared utilities
|   |       +-- __init__.py
|   |       +-- logging.py        # Structured logging setup
|   |       +-- metrics.py        # Prometheus metrics
|   |       +-- hashing.py        # Content hashing
|   |       +-- gitignore.py      # Gitignore pattern matching
|   |
|   +-- tests/
|       +-- __init__.py
|       +-- conftest.py           # Pytest fixtures
|       +-- unit/
|       |   +-- test_memory_manager.py
|       |   +-- test_query_engine.py
|       |   +-- test_indexer.py
|       |   +-- test_normalizer.py
|       |   +-- test_parsers/
|       |   +-- test_storage/
|       |   +-- test_embedding/
|       +-- integration/
|       |   +-- test_memory_lifecycle.py
|       |   +-- test_cross_store.py
|       |   +-- test_duplicate_detection.py
|       |   +-- test_normalization.py
|       |   +-- test_mcp_tools.py
|       +-- fixtures/
|           +-- sample_code/      # Sample files for parser tests
|           +-- sample_memories/  # Sample memory data
|
+-- docker/
|   +-- Dockerfile
|   +-- docker-compose.yml
|   +-- docker-compose.dev.yml
|   +-- .env.example
|
+-- scripts/
|   +-- setup.sh                  # Development setup
|   +-- test.sh                   # Run tests
|   +-- lint.sh                   # Run linters
|
+-- docs/
|   +-- api/                      # API documentation
|   +-- deployment/               # Deployment guides
|   +-- claude-integration.md     # CLAUDE.md template
|
+-- pyproject.toml                # Project configuration
+-- README.md
+-- CLAUDE.md                     # Project-specific instructions
```

### Layer Dependencies

```
api/ --> core/ --> models/
          |
          +--> storage/
          |
          +--> parsing/
          |
          +--> embedding/
                  |
                  +--> storage/ (for cache)
```

Rules:
- `api/` can import from `core/` and `models/`
- `core/` can import from `storage/`, `parsing/`, `embedding/`, `models/`
- `storage/`, `parsing/`, `embedding/` can import from `models/` and `utils/`
- `models/` and `utils/` have no internal dependencies

### Key Module Responsibilities

| Module | Responsibility |
|--------|----------------|
| `api/mcp_server.py` | stdio MCP server, tool routing |
| `api/http_server.py` | FastAPI server for health/metrics |
| `api/tools/*` | Individual MCP tool implementations |
| `core/memory_manager.py` | CRUD operations, lifecycle management |
| `core/query_engine.py` | Query planning, hybrid execution |
| `core/indexer.py` | Codebase indexing orchestration |
| `core/normalizer.py` | Normalization job management |
| `storage/qdrant_adapter.py` | Qdrant operations abstraction |
| `storage/neo4j_adapter.py` | Neo4j operations abstraction |
| `parsing/parser.py` | Language detection, tree-sitter invocation |
| `parsing/extractors/*` | Language-specific AST extraction |
| `embedding/service.py` | Embedding pipeline orchestration |

### Configuration Management

Single configuration class with environment variable support:

```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # MCP
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8765

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_api_key: str | None = None

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""

    # Voyage
    voyage_api_key: str = ""
    voyage_model: str = "voyage-code-3"

    # Embedding cache
    embedding_cache_size: int = 10000

    # Duplicate detection
    duplicate_threshold: float = 0.85

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Project
    project_path: str = "/project"

    # Metrics
    metrics_enabled: bool = True
    metrics_port: int = 9090

    class Config:
        env_prefix = ""
        env_file = ".env"
```

### Package Configuration

```toml
# pyproject.toml
[project]
name = "memory-service"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "qdrant-client>=1.7.0",
    "neo4j>=5.0.0",
    "voyageai>=0.2.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "fastapi>=0.100.0",
    "uvicorn>=0.23.0",
    "tree-sitter>=0.20.0",
    "tree-sitter-languages>=1.8.0",
    "httpx>=0.24.0",
    "structlog>=23.0.0",
    "prometheus-client>=0.17.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.0.0",
    "mypy>=1.0.0",
    "ruff>=0.1.0",
]

[project.scripts]
memory-service = "memory_service.__main__:main"
memory-cli = "memory_service.api.cli:main"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.mypy]
python_version = "3.12"
strict = true

[tool.ruff]
target-version = "py312"
select = ["E", "F", "I", "N", "W", "UP"]
```

## Consequences

### Positive
- Clear separation of concerns
- Easy to test each layer independently
- Supports extension (new languages, memory types)
- Standard Python project layout
- Dependencies flow in one direction

### Negative
- Some boilerplate for adapters
- Need to maintain layer boundaries

### Risks
- **Risk**: Circular imports between layers
- **Mitigation**: Strict dependency rules enforced by linter

## Requirements Addressed

- REQ-MEM-MAINT-001 (type hints, docstrings)
- REQ-MEM-MAINT-003 (externalized configuration)
- REQ-MEM-MAINT-005 (test coverage)
- REQ-MEM-DEP-001 (docker-compose)
- REQ-MEM-DEP-004 (.env.example)

## References

- Python packaging: https://packaging.python.org/
- pytest best practices: https://docs.pytest.org/
- Pydantic settings: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
