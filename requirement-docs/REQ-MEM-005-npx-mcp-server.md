# REQ-MEM-005: NPX-Based MCP Server

## 1. Overview

### 1.1 Purpose

Replace the problematic Python MCP server with a TypeScript/Node.js implementation using the official `@modelcontextprotocol/sdk`. The Python implementation has persistent stdio transport issues that prevent Claude Code from accessing the tools.

### 1.2 Problem Statement

The Python MCP server:
- Returns 23 tools via JSON-RPC protocol
- Shows "connected" in Claude Code `/mcp`
- Tools are NOT accessible to Claude
- Multiple fix attempts have failed (stdout/stderr routing, asyncio pipe issues)
- Custom stdio transport implementation is unreliable

### 1.3 Solution

Build a new MCP server using:
- TypeScript with `@modelcontextprotocol/sdk` (official SDK)
- npx for easy invocation
- Same backend databases (Qdrant, Neo4j)
- Same 23 tools with identical functionality

### 1.4 Scope

| In Scope | Out of Scope |
|----------|--------------|
| New TypeScript MCP server | Changes to Qdrant/Neo4j schemas |
| All 23 existing tools | New tool functionality |
| npx-based invocation | Python code maintenance |
| Connection to existing databases | Database migration |
| Project isolation via --project-id | Multi-tenant changes |

## 2. Requirements

### 2.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| REQ-MEM-005-FN-001 | Server SHALL use `@modelcontextprotocol/sdk` | P0 |
| REQ-MEM-005-FN-002 | Server SHALL be invocable via `npx` | P0 |
| REQ-MEM-005-FN-003 | Server SHALL expose all 23 tools from Python implementation | P0 |
| REQ-MEM-005-FN-004 | Server SHALL connect to Qdrant for vector storage | P0 |
| REQ-MEM-005-FN-005 | Server SHALL connect to Neo4j for graph storage | P0 |
| REQ-MEM-005-FN-006 | Server SHALL support Voyage AI embeddings | P0 |
| REQ-MEM-005-FN-007 | Server SHALL isolate data by project_id | P0 |
| REQ-MEM-005-FN-008 | Server SHALL accept --project-id CLI argument | P0 |
| REQ-MEM-005-FN-009 | Tools SHALL be visible and callable from Claude Code | P0 |
| REQ-MEM-005-FN-010 | Server SHALL read config from ~/.config/claude-memory/config.toml | P1 |

### 2.2 Tool Requirements

All 23 tools must be implemented with identical input/output schemas:

#### Memory CRUD (5 tools)
| Tool | Description |
|------|-------------|
| memory_add | Create a new memory |
| memory_get | Retrieve memory by ID |
| memory_update | Update existing memory |
| memory_delete | Delete memory (soft delete default) |
| memory_bulk_add | Batch add memories |

#### Search (5 tools)
| Tool | Description |
|------|-------------|
| memory_search | Semantic search across memories |
| code_search | Find similar code patterns |
| find_duplicates | Check for duplicate code |
| get_related | Get graph-related entities |
| graph_query | Execute read-only Cypher |

#### Indexing (4 tools)
| Tool | Description |
|------|-------------|
| index_file | Index single source file |
| index_directory | Index directory recursively |
| index_status | Get indexing job status |
| reindex | Trigger reindexing |

#### Analysis (4 tools)
| Tool | Description |
|------|-------------|
| check_consistency | Verify code follows patterns |
| validate_fix | Validate fix against design |
| get_design_context | Get ADRs/patterns for component |
| trace_requirements | Trace requirement to implementations |

#### Maintenance (5 tools)
| Tool | Description |
|------|-------------|
| memory_statistics | Get system health/counts |
| normalize_memory | Run normalization phases |
| normalize_status | Get normalization job status |
| export_memory | Export to JSONL |
| import_memory | Import from JSONL |

### 2.3 Non-Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| REQ-MEM-005-NFR-001 | Server SHALL start in < 3 seconds | P1 |
| REQ-MEM-005-NFR-002 | Server SHALL use TypeScript with strict mode | P1 |
| REQ-MEM-005-NFR-003 | Server SHALL have no Python dependencies | P0 |
| REQ-MEM-005-NFR-004 | Server SHALL log to stderr only | P0 |
| REQ-MEM-005-NFR-005 | Configuration SHALL be compatible with existing TOML | P1 |

## 3. Technical Design

### 3.1 Project Structure

```
mcp-server/
├── package.json
├── tsconfig.json
├── src/
│   ├── index.ts              # Entry point
│   ├── server.ts             # MCP server setup
│   ├── config.ts             # Configuration loading
│   ├── tools/
│   │   ├── index.ts          # Tool registry
│   │   ├── memory-crud.ts    # Memory CRUD tools
│   │   ├── search.ts         # Search tools
│   │   ├── indexing.ts       # Indexing tools
│   │   ├── analysis.ts       # Analysis tools
│   │   └── maintenance.ts    # Maintenance tools
│   ├── storage/
│   │   ├── qdrant.ts         # Qdrant client
│   │   └── neo4j.ts          # Neo4j client
│   ├── embedding/
│   │   └── voyage.ts         # Voyage AI client
│   └── types/
│       └── index.ts          # TypeScript types
└── bin/
    └── claude-memory-mcp.js  # npx entry point
```

### 3.2 Dependencies

```json
{
  "dependencies": {
    "@modelcontextprotocol/sdk": "^1.0.0",
    "@qdrant/js-client-rest": "^1.9.0",
    "neo4j-driver": "^5.0.0",
    "toml": "^3.0.0",
    "voyageai": "^0.1.0"
  },
  "devDependencies": {
    "typescript": "^5.0.0",
    "@types/node": "^20.0.0"
  }
}
```

### 3.3 MCP Configuration

New `.mcp.json` format:
```json
{
  "mcpServers": {
    "memory": {
      "command": "npx",
      "args": ["-y", "claude-memory-mcp", "--project-id", "my-project"]
    }
  }
}
```

Or for local development:
```json
{
  "mcpServers": {
    "memory": {
      "command": "node",
      "args": ["./mcp-server/dist/index.js", "--project-id", "my-project"]
    }
  }
}
```

### 3.4 Data Compatibility

The TypeScript server must:
- Use same Qdrant collection naming: `{project_id}_{memory_type}`
- Use same Neo4j node labels and relationship types
- Use same embedding model (voyage-code-3)
- Produce identical vector dimensions (1024)

## 4. Success Criteria

| Criteria | Measurement |
|----------|-------------|
| Tools visible | All 23 tools appear in Claude's available tools |
| Tools callable | Can call any tool from Claude Code |
| Data compatible | Can read memories created by Python server |
| Project isolation | Different project_ids see different data |
| Startup time | Server starts in < 3 seconds |

## 5. Migration Plan

1. Build and test TypeScript MCP server
2. Verify all 23 tools work from Claude Code
3. Verify data compatibility with existing memories
4. Update user-docs/quick-reference.md with new setup
5. Delete Python source code (src/memory_service/)
6. Update project documentation

## 6. References

- [MCP TypeScript SDK](https://github.com/modelcontextprotocol/typescript-sdk)
- [MCP Specification](https://modelcontextprotocol.io/docs)
- [Qdrant JS Client](https://github.com/qdrant/qdrant-js)
- [Neo4j JavaScript Driver](https://github.com/neo4j/neo4j-javascript-driver)
- [Voyage AI](https://docs.voyageai.com/)
