# Claude Code Long-Term Memory MCP Server

A *development-time* memory service for Claude Code - **not** runtime memory for your application. This MCP server helps Claude maintain context across coding sessions by storing project decisions, code patterns, and requirements. It's tooling that helps Claude build your application better.

Enables context persistence, duplicate detection, design alignment verification, and consistency enforcement across multi-session software development projects.

## Architecture

The MCP server runs **locally** on your machine (not in Docker), while databases run as shared Docker infrastructure:

```
Developer Machine
+--------------------------------------------------+
|                                                  |
|  +-------------------------------------------+   |
|  |          Project Directory                |   |
|  |  .claude/mcp.json (project config)        |   |
|  |  .venv/ (includes claude-memory-mcp)      |   |
|  +-------------------------------------------+   |
|                       |                          |
|                       | stdio                    |
|                       v                          |
|  +-------------------------------------------+   |
|  |       MCP Server (local Python process)   |   |
|  |       claude-memory-mcp --project-id X    |   |
|  +-------------------------------------------+   |
|                       |                          |
|          +------------+------------+             |
|          v                         v             |
|  +---------------+       +------------------+    |
|  |    Docker     |       |      Docker      |    |
|  |    Qdrant     |       |      Neo4j       |    |
|  |  (shared)     |       |    (shared)      |    |
|  +---------------+       +------------------+    |
+--------------------------------------------------+
```

## Features

- **Project Isolation**: Each project has isolated data via `--project-id` namespacing
- **Semantic Search**: Find relevant context using natural language queries
- **Duplicate Detection**: Identify similar code patterns before implementation
- **Design Alignment**: Validate changes against project requirements and ADRs
- **Requirements Traceability**: Track implementation status of requirements
- **Code Indexing**: Parse and index codebases for semantic search
- **Session Continuity**: Persist context across development sessions

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Voyage AI API key ([Get one here](https://www.voyageai.com/))

### Installation

**1. Start the database infrastructure (one-time setup):**

```bash
git clone <repository-url>
cd claude-code-memory-service/docker

# Configure Neo4j password
cp .env.example .env
# Edit .env and set NEO4J_PASSWORD

# Start databases
docker-compose up -d
```

**2. Install the MCP server:**

```bash
pip install claude-memory-mcp
# or add to your project's requirements.txt / pyproject.toml
```

**3. Initialize global configuration:**

```bash
claude-memory-mcp init-config
# Edit ~/.config/claude-memory/config.toml with:
#   - Your Voyage AI API key
#   - Neo4j password (must match .env)
```

**4. Verify connectivity:**

```bash
claude-memory-mcp check-db
```

### Claude Code Integration

**1. Create `.claude/mcp.json` in your project:**

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

If using a project virtual environment:

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

**2. Add to your project's `CLAUDE.md`:**

```markdown
## Memory Service

Uses persistent memory for context across sessions. See [Quick Reference](user-docs/quick-reference.md).

**Workflow:**
- Session start: `memory_search` for context
- Before coding: `code_search`, `find_duplicates`, `get_design_context`
- After coding: `memory_add` for decisions and session summary

**Key tools:** `memory_search`, `code_search`, `find_duplicates`, `get_design_context`, `memory_add`
```

## Documentation

| Document | Description |
|----------|-------------|
| [Quick Reference](user-docs/quick-reference.md) | Concise tool usage guide |
| [API Reference](user-docs/api-reference.md) | Complete tool documentation |
| [Deployment Guide](user-docs/deployment-guide.md) | Docker setup and configuration |
| [Integration Template](user-docs/integration-template.md) | Full CLAUDE.md integration examples |

## Configuration

### Global Configuration

Located at `~/.config/claude-memory/config.toml`:

```toml
[qdrant]
host = "localhost"
port = 6333

[neo4j]
uri = "bolt://localhost:7687"
user = "neo4j"
password = "your-password"

[voyage]
api_key = "your-voyage-api-key"
model = "voyage-code-3"

[server]
log_level = "INFO"
```

Create with: `claude-memory-mcp init-config`

### Configuration Precedence

1. CLI arguments (highest priority)
2. Environment variables (`CLAUDE_MEMORY_*` prefix)
3. Global config file
4. Built-in defaults

### Environment Variables

| Variable | Description |
|----------|-------------|
| `CLAUDE_MEMORY_QDRANT_HOST` | Qdrant hostname |
| `CLAUDE_MEMORY_QDRANT_PORT` | Qdrant port |
| `CLAUDE_MEMORY_NEO4J_URI` | Neo4j connection URI |
| `CLAUDE_MEMORY_NEO4J_PASSWORD` | Neo4j password |
| `CLAUDE_MEMORY_VOYAGE_API_KEY` | Voyage AI API key |
| `CLAUDE_MEMORY_LOG_LEVEL` | Log level |

## Project Isolation

Each project's data is isolated via `--project-id`. Multiple projects share the same Qdrant/Neo4j databases without data mixing.

**How it works:**
- Qdrant collections are prefixed: `myproject_functions`, `myproject_designs`, etc.
- Neo4j nodes include `project_id` property with automatic filtering
- Project ID is set once at server startup via `--project-id`

**For multiple projects:**

Create separate `mcp.json` files in each project with different `--project-id` values. Each project automatically uses its isolated memory space.

## CLI Commands

```bash
# Start MCP server (requires --project-id)
claude-memory-mcp --project-id my-project

# Create global config file
claude-memory-mcp init-config

# Check database connectivity
claude-memory-mcp check-db

# Show version
claude-memory-mcp --version

# Show help
claude-memory-mcp --help
```

## Memory Types

| Type | Purpose |
|------|---------|
| `requirements` | Project requirements and specifications |
| `design` | ADRs and architectural decisions |
| `code_pattern` | Reusable code patterns and templates |
| `component` | System components and modules |
| `function` | Indexed functions and methods |
| `test_history` | Test execution history |
| `session` | Development session summaries |
| `user_preference` | User preferences and settings |

## MCP Tools (23 tools)

### Memory CRUD (5 tools)
- `memory_add` - Create new memories
- `memory_get` - Retrieve memories
- `memory_update` - Update existing memories
- `memory_delete` - Soft/hard delete memories
- `memory_bulk_add` - Batch create memories

### Search (5 tools)
- `memory_search` - Semantic search across memories
- `code_search` - Find similar code patterns
- `graph_query` - Execute Cypher queries
- `find_duplicates` - Detect duplicate functions
- `get_related` - Get related entities

### Indexing (4 tools)
- `index_file` - Index single file
- `index_directory` - Index directory recursively
- `index_status` - Check indexing status
- `reindex` - Re-index codebase

### Analysis (4 tools)
- `check_consistency` - Verify pattern compliance
- `validate_fix` - Validate fix against design
- `get_design_context` - Get design context
- `trace_requirements` - Trace requirement implementation

### Maintenance (5 tools)
- `normalize_memory` - Run normalization
- `normalize_status` - Check normalization status
- `memory_statistics` - Get system statistics
- `export_memory` - Export to JSONL
- `import_memory` - Import from JSONL

## Technology Stack

- **Python 3.11+** - Runtime
- **Qdrant** - Vector database for semantic search
- **Neo4j** - Graph database for relationships
- **Voyage-Code-3** - Code embedding model
- **Tree-sitter** - Multi-language code parsing
- **MCP Protocol** - Claude Code integration

## Development

### Running Tests

```bash
# Unit tests
pytest src/tests/unit/ -v --cov=memory_service

# Integration tests (requires Docker)
pytest src/tests/integration/ -v

# Security tests
pytest src/tests/security/ -v
```

### Project Structure

```
├── src/
│   ├── memory_service/
│   │   ├── api/          # MCP server, CLI
│   │   ├── core/         # Memory manager, query engine, workers
│   │   ├── embedding/    # Voyage client, embedding service
│   │   ├── models/       # Pydantic models
│   │   ├── parsing/      # Code parsing extractors
│   │   ├── storage/      # Qdrant and Neo4j adapters
│   │   └── utils/        # Logging, metrics, utilities
│   └── tests/
├── docker/               # Database docker-compose
├── project-docs/         # Architecture and design docs
├── user-docs/            # User documentation
└── CLAUDE.md             # Development workflow
```

## Migrating from Docker-based MCP

If you were using an earlier version where the MCP server ran inside Docker:

1. Stop the old containers: `docker-compose down`
2. Install the new package: `pip install claude-memory-mcp`
3. Create global config: `claude-memory-mcp init-config`
4. Update your `mcp.json` to use the local command instead of `docker exec`
5. Start databases with new docker-compose: `docker-compose up -d`

Your existing data in Docker volumes will be preserved.

## License

MIT License
