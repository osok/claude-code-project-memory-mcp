# Claude Code Long-Term Memory System

A persistent memory infrastructure for Claude Code enabling context persistence, duplicate detection, design alignment verification, and consistency enforcement across multi-session software development projects.

## Features

- **Semantic Search**: Find relevant context using natural language queries
- **Duplicate Detection**: Identify similar code patterns before implementation
- **Design Alignment**: Validate changes against project requirements and ADRs
- **Requirements Traceability**: Track implementation status of requirements
- **Code Indexing**: Parse and index codebases for semantic search
- **Session Continuity**: Persist context across development sessions

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Voyage AI API key ([Get one here](https://www.voyageai.com/))

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd claude-code-memory-service
   ```

2. Configure environment:
   ```bash
   cp docker/.env.example docker/.env
   # Edit docker/.env with your VOYAGE_API_KEY and NEO4J_PASSWORD
   ```

3. Start services:
   ```bash
   cd docker
   docker-compose up -d
   ```

4. Verify installation:
   ```bash
   curl http://localhost:9090/health
   ```

### Claude Code Integration

Add to your `~/.claude/mcp.json`:

```json
{
  "mcpServers": {
    "memory": {
      "command": "docker",
      "args": [
        "exec", "-i", "memory-service",
        "python", "-m", "memory_service", "mcp"
      ]
    }
  }
}
```

## Documentation

| Document | Description |
|----------|-------------|
| [API Reference](user-docs/api-reference.md) | Complete tool documentation |
| [Deployment Guide](user-docs/deployment-guide.md) | Docker setup and configuration |
| [Integration Template](user-docs/integration-template.md) | CLAUDE.md integration examples |
| [CLAUDE.md](CLAUDE.md) | Development workflow |

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Claude Code                         │
│                 (MCP Client)                         │
└────────────────────┬────────────────────────────────┘
                     │ stdio
┌────────────────────▼────────────────────────────────┐
│              Memory Service                          │
│  ┌──────────────────────────────────────────────┐   │
│  │            MCP Server                         │   │
│  │  23 Tools: CRUD, Search, Index, Analysis     │   │
│  └──────────────────────────────────────────────┘   │
│  ┌────────────────┐  ┌────────────────────────┐     │
│  │ Query Engine   │  │ Memory Manager         │     │
│  │ - Semantic     │  │ - CRUD Operations      │     │
│  │ - Hybrid       │  │ - Conflict Detection   │     │
│  │ - Graph        │  │ - Importance Scoring   │     │
│  └────────────────┘  └────────────────────────┘     │
│  ┌────────────────┐  ┌────────────────────────┐     │
│  │ Indexer        │  │ Normalizer             │     │
│  │ - Code Parsing │  │ - Deduplication        │     │
│  │ - Relationship │  │ - Orphan Cleanup       │     │
│  └────────────────┘  └────────────────────────┘     │
└───────────┬─────────────────────────┬───────────────┘
            │                         │
    ┌───────▼──────┐         ┌───────▼──────┐
    │    Qdrant    │         │    Neo4j     │
    │   (Vectors)  │         │   (Graph)    │
    └──────────────┘         └──────────────┘
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

## MCP Tools

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

- **Python 3.12** - Runtime
- **Qdrant** - Vector database for semantic search
- **Neo4j** - Graph database for relationships
- **Voyage-Code-3** - Code embedding model
- **Tree-sitter** - Multi-language code parsing
- **FastAPI** - HTTP server
- **MCP Protocol** - Claude Code integration

## Development

See [CLAUDE.md](CLAUDE.md) for the complete development workflow.

### Running Tests

```bash
# Unit tests
pytest src/tests/unit/ -v --cov=memory_service

# Integration tests (requires Docker)
pytest src/tests/integration/ -v

# Performance tests
pytest src/tests/performance/ -v

# Security tests
pytest src/tests/security/ -v
```

### Project Structure

```
├── src/
│   ├── memory_service/
│   │   ├── api/          # MCP server, HTTP server, CLI
│   │   ├── core/         # Memory manager, query engine, workers
│   │   ├── embedding/    # Voyage client, embedding service
│   │   ├── models/       # Pydantic models
│   │   ├── parsing/      # Code parsing extractors
│   │   ├── storage/      # Qdrant and Neo4j adapters
│   │   └── utils/        # Logging, metrics, utilities
│   └── tests/
├── docker/               # Docker configuration
├── project-docs/         # Architecture and design docs
├── user-docs/            # User documentation
└── CLAUDE.md             # Development workflow
```

## License

[License details to be added]
