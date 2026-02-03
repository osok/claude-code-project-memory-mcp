# ADR-010: TypeScript MCP Server (Replacing Python)

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Deciders** | User |
| **Requirements** | REQ-MEM-005-FN-001 through REQ-MEM-005-FN-010 |
| **Supersedes** | ADR-001 (transport mechanism), ADR-009 (partially - process model unchanged) |

## Context

The Python MCP server implemented in SEQ 003 has persistent stdio transport issues that prevent Claude Code from accessing the tools:

1. **Symptom**: Tools are returned via JSON-RPC but Claude cannot call them
2. **Root Cause**: Custom stdio transport implementation has subtle issues with Python's asyncio and subprocess communication
3. **Fix Attempts Failed**:
   - Stdout/stderr routing adjustments
   - Asyncio pipe refactoring
   - Buffer management changes

The Python MCP SDK's stdio transport implementation appears to have fundamental issues that are difficult to debug and fix.

## Decision

**We will replace the Python MCP server with a TypeScript implementation using the official `@modelcontextprotocol/sdk` npm package.**

### Architecture

```
Developer Machine
+--------------------------------------------------+
|                                                  |
|  +-------------------------------------------+   |
|  |          Project Directory                |   |
|  |  .mcp.json (points to npx or node)        |   |
|  +-------------------------------------------+   |
|                       |                          |
|                       | stdio                    |
|                       v                          |
|  +-------------------------------------------+   |
|  |     MCP Server (TypeScript/Node.js)       |   |
|  |     npx claude-memory-mcp --project-id X  |   |
|  +-------------------------------------------+   |
|                       |                          |
|          +------------+------------+             |
|          v                         v             |
|  +---------------+       +------------------+    |
|  |    Docker     |       |      Docker      |    |
|  |    Qdrant     |       |      Neo4j       |    |
|  |  (unchanged)  |       |   (unchanged)    |    |
|  +---------------+       +------------------+    |
+--------------------------------------------------+
```

### Key Design Choices

1. **Official MCP SDK**: Use `@modelcontextprotocol/sdk` for reliable stdio transport
2. **npx Invocation**: No global installation required, version pinning via package name
3. **Same Tool Set**: All 23 tools with identical input/output schemas
4. **Same Databases**: Connect to existing Qdrant and Neo4j instances
5. **Same Data Model**: Full compatibility with existing memories
6. **TOML Config**: Continue using `~/.config/claude-memory/config.toml`

## Rationale

### Why TypeScript/Official SDK

| Aspect | Python MCP SDK | TypeScript MCP SDK |
|--------|----------------|-------------------|
| Maturity | Custom implementation | Official reference |
| stdio Transport | Broken/unreliable | Battle-tested |
| Debugging | Difficult | Standard Node.js tools |
| Async Model | Python asyncio complexity | Node.js event loop |
| Community Support | Limited | Primary SDK |

### Why Not Fix Python

1. **Time Investment**: Multiple fix attempts already failed
2. **Unclear Root Cause**: Debugging async stdio issues is notoriously difficult
3. **Opportunity Cost**: Better to use proven working solution
4. **Risk**: Continued investment may not yield results

### Why npx vs Global Install

1. **Version Management**: Each project can pin to specific version
2. **No Global Pollution**: No npm global package management issues
3. **Easy Updates**: Just change version in .mcp.json
4. **Development Mode**: Can point to local build during development

## Alternatives Considered

### 1. Continue Fixing Python Implementation
- **Rejected**: Multiple attempts failed, diminishing returns
- **Risk**: May never work reliably

### 2. HTTP Transport Instead of stdio
- **Rejected**: Adds complexity (port management, CORS, auth)
- **Issue**: MCP specification prefers stdio for desktop tools

### 3. Go Implementation
- **Rejected**: No official MCP SDK for Go
- **Issue**: Would require custom protocol implementation

## Consequences

### Positive

1. **Reliable Tools**: Official SDK has proven stdio transport
2. **Community Alignment**: Using primary MCP SDK
3. **Faster Development**: TypeScript tooling is excellent
4. **Clean Slate**: No legacy Python code to maintain

### Negative

1. **Code Rewrite**: All tool implementations must be rewritten
2. **Two Languages**: New TypeScript codebase alongside Python (until cleanup)
3. **Learning Curve**: Different implementation patterns
4. **Dependency Shift**: Node.js/npm instead of Python/pip

### Migration Impact

1. **User Impact**: Update .mcp.json to use npx command
2. **Data Migration**: None - same databases, same schemas
3. **Cleanup**: Delete Python src/memory_service/ after TypeScript works

## Implementation Notes

### Project Structure

```
mcp-server/
  package.json        # Package metadata, dependencies
  tsconfig.json       # TypeScript configuration
  src/
    index.ts          # Entry point, CLI argument handling
    server.ts         # MCP server setup with all tools
    config.ts         # TOML config loading
    tools/            # Tool implementations by category
    storage/          # Qdrant and Neo4j clients
    embedding/        # Voyage AI client
    types/            # TypeScript type definitions
  bin/
    claude-memory-mcp.js  # npx entry point
```

### MCP Configuration

**Local Development:**
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

**Published Package:**
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

### Data Compatibility Requirements

| Store | Naming Convention | Must Match |
|-------|------------------|------------|
| Qdrant Collections | `{project_id}_{memory_type}` | Exact |
| Neo4j Labels | `Memory`, `Function`, `Component`, etc. | Exact |
| Neo4j Properties | `project_id`, `memory_id`, etc. | Exact |
| Embeddings | voyage-code-3, 1024 dimensions | Exact |

## Compliance

- **REQ-MEM-005-FN-001**: Use @modelcontextprotocol/sdk - SATISFIED
- **REQ-MEM-005-FN-002**: npx invocation - SATISFIED
- **REQ-MEM-005-FN-003**: All 23 tools - SATISFIED (by design)
- **REQ-MEM-005-FN-009**: Tools visible and callable from Claude Code - TARGET
- **REQ-MEM-005-NFR-003**: No Python dependencies - SATISFIED
