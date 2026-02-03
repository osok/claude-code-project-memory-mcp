# NPX-Based MCP Server Architecture

| Field | Value |
|-------|-------|
| **Seq** | 005 |
| **Requirements** | REQ-MEM-005-npx-mcp-server.md |
| **ADRs** | ADR-010-typescript-mcp-server.md |

## Technology Choices

| Area | Choice | Rationale |
|------|--------|-----------|
| Language | TypeScript 5.x | Type safety, excellent tooling, Node.js ecosystem |
| MCP SDK | @modelcontextprotocol/sdk | Official reference implementation, proven reliable |
| Vector DB Client | @qdrant/js-client-rest | Official Qdrant JavaScript client |
| Graph DB Driver | neo4j-driver | Official Neo4j JavaScript driver |
| Embedding API | voyageai (npm) | Voyage AI official client |
| Config Format | TOML | Compatibility with existing ~/.config/claude-memory/config.toml |
| Build Tool | tsc + esbuild | Fast compilation, tree-shaking |

## Patterns

### MCP Server Pattern

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

const server = new McpServer({
  name: "memory",
  version: "1.0.0"
});

// Register all 23 tools
server.tool("memory_add", schema, handler);
server.tool("memory_search", schema, handler);
// ... etc

const transport = new StdioServerTransport();
await server.connect(transport);
```

### Tool Registration Pattern

Each tool follows this pattern:

```typescript
interface ToolDefinition<T extends z.ZodType> {
  name: string;
  description: string;
  inputSchema: T;
  handler: (input: z.infer<T>, context: ToolContext) => Promise<ToolResult>;
}
```

### Shared Context Pattern

All tools share a common context object:

```typescript
interface ToolContext {
  projectId: string;
  qdrant: QdrantClient;
  neo4j: Neo4jDriver;
  embedding: VoyageClient;
  config: Config;
}
```

### Error Handling Pattern

```typescript
try {
  // Tool logic
} catch (error) {
  if (error instanceof ValidationError) {
    return { content: [{ type: "text", text: JSON.stringify({ error: error.message }) }] };
  }
  // Log to stderr, not stdout
  console.error(`[ERROR] ${error.message}`);
  throw error;
}
```

## Quality Attributes

| Attribute | Target | Measurement |
|-----------|--------|-------------|
| Startup Time | < 3 seconds | Time from process spawn to tools/list response |
| Tool Response | < 500ms P95 | Time to return tool result (excluding DB latency) |
| Memory Usage | < 200MB | Node.js heap size during normal operation |
| Reliability | 100% tool visibility | All 23 tools callable from Claude Code |

## Security Model

### No Changes from ADR-009

1. **Localhost Only**: Databases bound to 127.0.0.1
2. **Secrets in Config**: API keys in TOML or environment
3. **No Secrets in Logs**: stderr logs sanitized
4. **Project Isolation**: All queries filtered by project_id

### Configuration Security

```
~/.config/claude-memory/config.toml (0600 permissions)
  [voyage]
  api_key = "..."     # Voyage AI API key

  [qdrant]
  url = "http://localhost:6333"

  [neo4j]
  uri = "bolt://localhost:7687"
  user = "neo4j"
  password = "..."    # Neo4j password
```

## Integration Points

### MCP Protocol

- **Transport**: stdio (stdin/stdout)
- **Protocol Version**: MCP 1.0
- **Tools**: 23 registered tools
- **Resources**: None (tools only)
- **Prompts**: None (tools only)

### Qdrant

- **Protocol**: HTTP REST API
- **Port**: 6333 (localhost)
- **Collections**: `{project_id}_{memory_type}` naming
- **Vector Dimensions**: 1024 (voyage-code-3)

### Neo4j

- **Protocol**: Bolt
- **Port**: 7687 (localhost)
- **Authentication**: Basic (user/password)
- **Query Language**: Cypher (read-only for graph_query tool)

### Voyage AI

- **Protocol**: HTTPS
- **Model**: voyage-code-3
- **Batch Size**: 100 texts per request
- **Fallback**: None (API required for code embeddings)

## Error Handling Strategy

### Validation Errors

Return structured error in tool response:
```json
{
  "content": [{"type": "text", "text": "{\"error\": \"Invalid memory_type: xyz\"}"}]
}
```

### Database Connection Errors

Log to stderr and return error:
```json
{
  "content": [{"type": "text", "text": "{\"error\": \"Database connection failed\", \"category\": \"INFRASTRUCTURE\"}"}]
}
```

### Embedding API Errors

Log warning and return partial result or error:
```json
{
  "content": [{"type": "text", "text": "{\"error\": \"Embedding API unavailable\", \"partial_result\": {...}}"}]
}
```

## Constraints

| Constraint | Reason |
|------------|--------|
| TypeScript strict mode | Type safety, catch errors at compile time |
| ES2022+ target | Modern Node.js features |
| No Python dependencies | Clean separation from legacy code |
| stdout reserved for MCP | All logs to stderr only |
| Data schema unchanged | Compatibility with existing memories |

## Module Organization

```
mcp-server/
  package.json          # Package metadata
  tsconfig.json         # TypeScript config (strict: true)
  src/
    index.ts            # Entry point, argument parsing
    server.ts           # MCP server setup, tool registration
    config.ts           # TOML config loading, env overrides
    types/
      index.ts          # Shared TypeScript types
      memory.ts         # Memory-related types
      search.ts         # Search-related types
    tools/
      index.ts          # Tool registry and context
      memory-crud.ts    # memory_add, memory_get, memory_update, memory_delete, memory_bulk_add
      search.ts         # memory_search, code_search, find_duplicates, get_related, graph_query
      indexing.ts       # index_file, index_directory, index_status, reindex
      analysis.ts       # check_consistency, validate_fix, get_design_context, trace_requirements
      maintenance.ts    # memory_statistics, normalize_memory, normalize_status, export_memory, import_memory
    storage/
      qdrant.ts         # Qdrant client wrapper
      neo4j.ts          # Neo4j driver wrapper
    embedding/
      voyage.ts         # Voyage AI embedding client
  bin/
    claude-memory-mcp.js  # npx shebang entry point
  dist/                 # Compiled JavaScript output
```

## Build and Distribution

### package.json

```json
{
  "name": "claude-memory-mcp",
  "version": "1.0.0",
  "bin": {
    "claude-memory-mcp": "./bin/claude-memory-mcp.js"
  },
  "main": "./dist/index.js",
  "type": "module",
  "engines": {
    "node": ">=20.0.0"
  }
}
```

### Build Process

```bash
npm run build       # tsc to compile TypeScript
npm run lint        # ESLint check
npm run test        # Unit tests
npm pack            # Create distributable tarball
```
