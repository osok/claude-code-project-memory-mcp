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
|  |  .mcp.json (project config)               |   |
|  +-------------------------------------------+   |
|                       |                          |
|                       | stdio                    |
|                       v                          |
|  +-------------------------------------------+   |
|  |     MCP Server (local Node.js process)    |   |
|  |  node mcp-server/bin/claude-memory-mcp.js  |   |
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

- Node.js 20+
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

**2. Create global configuration:**

```bash
mkdir -p ~/.config/claude-memory

cat > ~/.config/claude-memory/config.toml << 'EOF'
[voyage]
api_key = "your-voyage-api-key"

[qdrant]
url = "http://localhost:6333"

[neo4j]
uri = "bolt://localhost:7687"
user = "neo4j"
password = "your-neo4j-password"
EOF
```

### Claude Code Integration

From your project directory, run:

```bash
claude mcp add memory -- node /path/to/claude-code-project-memory-mcp/mcp-server/bin/claude-memory-mcp.js --project-id my-project
```

Replace `/path/to/` with the actual absolute path to this repository. Use a unique `--project-id` for each project (lowercase, hyphens, underscores only).

> **Warning:** Do not use `npx claude-memory-mcp`. There is a different, unrelated package with that name on npm.

After adding, restart Claude Code. The 23 memory tools are automatically discovered via MCP -- no changes needed to your project's `CLAUDE.md`.

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
[voyage]
api_key = "your-voyage-api-key"

[qdrant]
url = "http://localhost:6333"

[neo4j]
uri = "bolt://localhost:7687"
user = "neo4j"
password = "your-password"
```

### Configuration Precedence

1. Environment variables (highest priority)
2. Global config file
3. Built-in defaults

### Environment Variables

| Variable | Description |
|----------|-------------|
| `CLAUDE_MEMORY_QDRANT_URL` | Qdrant URL |
| `CLAUDE_MEMORY_NEO4J_URI` | Neo4j connection URI |
| `CLAUDE_MEMORY_NEO4J_USER` | Neo4j user |
| `CLAUDE_MEMORY_NEO4J_PASSWORD` | Neo4j password |
| `CLAUDE_MEMORY_VOYAGE_API_KEY` | Voyage AI API key |

## Project Isolation

Each project's data is isolated via `--project-id`. Multiple projects share the same Qdrant/Neo4j databases without data mixing.

**How it works:**
- Qdrant collections are prefixed: `myproject_functions`, `myproject_designs`, etc.
- Neo4j nodes include `project_id` property with automatic filtering
- Project ID is set once at server startup via `--project-id`

**For multiple projects:**

Create separate `.mcp.json` files in each project with different `--project-id` values. Each project automatically uses its isolated memory space.

## CLI Usage

```bash
# Start MCP server (requires --project-id)
node /path/to/claude-code-project-memory-mcp/mcp-server/bin/claude-memory-mcp.js --project-id my-project

# Show help
node /path/to/claude-code-project-memory-mcp/mcp-server/bin/claude-memory-mcp.js --help
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
- `memory_delete` - Soft delete memories
- `memory_bulk_add` - Batch create memories

### Search (5 tools)
- `memory_search` - Semantic search across memories
- `code_search` - Find similar code patterns
- `graph_query` - Execute Cypher queries
- `find_duplicates` - Detect duplicate content
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

- **TypeScript/Node.js 20+** - Runtime
- **@modelcontextprotocol/sdk** - Official MCP SDK
- **Qdrant** - Vector database for semantic search
- **Neo4j** - Graph database for relationships
- **Voyage-Code-3** - Code embedding model (1024 dimensions)
- **MCP Protocol** - Claude Code integration

## Project Structure

```
├── mcp-server/           # TypeScript MCP server
│   ├── src/
│   │   ├── index.ts      # CLI entry point
│   │   ├── server.ts     # MCP server setup
│   │   ├── context.ts    # Shared tool context
│   │   ├── config.ts     # TOML config loading
│   │   ├── tools/        # 23 tool implementations
│   │   ├── storage/      # Qdrant and Neo4j adapters
│   │   ├── embedding/    # Voyage AI client
│   │   └── utils/        # Logging utilities
│   ├── package.json
│   └── tsconfig.json
├── docker/               # Database docker-compose
├── project-docs/         # Architecture and design docs
├── user-docs/            # User documentation
└── CLAUDE.md             # Development workflow
```

## Development

### Building

```bash
cd mcp-server
npm install
npm run build
```

### Running locally

```bash
cd mcp-server
node dist/index.js --project-id test-project
```

### Running tests

```bash
cd mcp-server
npm test
```

## Migrating from Python MCP

If you were using the earlier Python-based MCP server:

1. Update your `.mcp.json` to use npx instead of the Python command
2. Your existing data in Docker volumes will be preserved
3. No changes needed to database infrastructure

## License

MIT License
