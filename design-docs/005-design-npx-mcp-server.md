# Design Document: NPX-Based MCP Server

## Document Control

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Status | Draft |
| Sequence | 005 |
| Requirements | REQ-MEM-005-npx-mcp-server.md |
| Architecture | 005-architecture-npx-mcp.md |
| ADR | ADR-010-typescript-mcp-server.md |

---

## 1. Introduction

### 1.1 Purpose

This document describes the design for the TypeScript MCP server that replaces the Python implementation. The new server uses the official `@modelcontextprotocol/sdk` for reliable stdio transport.

### 1.2 Scope

**Included:**
- TypeScript MCP server structure
- Tool implementations matching existing schemas
- Storage adapter clients (Qdrant, Neo4j)
- Embedding client (Voyage AI)
- Configuration loading (TOML)
- npx packaging and invocation

**Excluded:**
- Changes to Qdrant/Neo4j data schemas (see 02-data-architecture.md)
- Changes to tool input/output schemas (see 50-integration-design.md)
- Database deployment (see 60-infrastructure-design.md)

### 1.3 Requirements Traceability

| Requirement ID | Requirement Summary | Design Section |
|----------------|---------------------|----------------|
| REQ-MEM-005-FN-001 | Use @modelcontextprotocol/sdk | 3.1 |
| REQ-MEM-005-FN-002 | npx invocation | 6.2 |
| REQ-MEM-005-FN-003 | All 23 tools | 4.1-4.5 |
| REQ-MEM-005-FN-004 | Connect to Qdrant | 5.1 |
| REQ-MEM-005-FN-005 | Connect to Neo4j | 5.2 |
| REQ-MEM-005-FN-006 | Voyage AI embeddings | 5.3 |
| REQ-MEM-005-FN-007 | Project isolation | 5.4 |
| REQ-MEM-005-FN-008 | CLI --project-id | 3.2 |
| REQ-MEM-005-FN-009 | Tools visible/callable | 3.1 |
| REQ-MEM-005-FN-010 | TOML config | 3.3 |
| REQ-MEM-005-NFR-001 | Start < 3 seconds | 7.1 |
| REQ-MEM-005-NFR-002 | TypeScript strict | 6.1 |
| REQ-MEM-005-NFR-003 | No Python deps | 6.1 |
| REQ-MEM-005-NFR-004 | Log to stderr | 7.2 |
| REQ-MEM-005-NFR-005 | TOML compatible | 3.3 |

---

## 2. Design Context

### 2.1 Problem Statement

The Python MCP server has persistent stdio transport issues:
- Tools are registered and visible in `/mcp` status
- JSON-RPC protocol works (tools/list returns 23 tools)
- But tools are NOT callable from Claude Code
- Root cause: asyncio and subprocess stdio pipe handling

### 2.2 Solution Overview

Replace the Python implementation with TypeScript using the official MCP SDK, which has proven reliable stdio transport.

### 2.3 Design Constraints

| Constraint | Source | Impact |
|------------|--------|--------|
| Same tool schemas | Data compatibility | No changes to input/output |
| Same database schemas | Data compatibility | Qdrant/Neo4j unchanged |
| Same embedding model | Data compatibility | voyage-code-3, 1024 dim |
| Same config path | User compatibility | ~/.config/claude-memory/ |
| stdout reserved | MCP protocol | All logs to stderr |

---

## 3. MCP Server Design

### 3.1 Server Structure

```typescript
// src/server.ts
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { registerTools } from "./tools/index.js";
import { createContext } from "./context.js";

export async function createServer(projectId: string): Promise<McpServer> {
  const server = new McpServer({
    name: "memory",
    version: "1.0.0"
  });

  const context = await createContext(projectId);
  registerTools(server, context);

  return server;
}

export async function startServer(projectId: string): Promise<void> {
  const server = await createServer(projectId);
  const transport = new StdioServerTransport();
  await server.connect(transport);
}
```

### 3.2 CLI Entry Point

```typescript
// src/index.ts
#!/usr/bin/env node
import { parseArgs } from "node:util";
import { startServer } from "./server.js";

const { values } = parseArgs({
  options: {
    "project-id": { type: "string", short: "p" },
    help: { type: "boolean", short: "h" }
  }
});

if (values.help) {
  console.error("Usage: claude-memory-mcp --project-id <id>");
  process.exit(0);
}

if (!values["project-id"]) {
  console.error("Error: --project-id is required");
  process.exit(1);
}

// Validate project-id format
const projectIdPattern = /^[a-z][a-z0-9_-]{0,62}$/;
if (!projectIdPattern.test(values["project-id"])) {
  console.error("Error: project-id must match pattern: [a-z][a-z0-9_-]{0,62}");
  process.exit(1);
}

startServer(values["project-id"]).catch((error) => {
  console.error(`Fatal error: ${error.message}`);
  process.exit(1);
});
```

### 3.3 Configuration Loading

Config path: `~/.config/claude-memory/config.toml`

```typescript
// src/config.ts
import { readFileSync, existsSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import TOML from "toml";

interface Config {
  voyage: {
    api_key: string;
  };
  qdrant: {
    url: string;
  };
  neo4j: {
    uri: string;
    user: string;
    password: string;
  };
}

export function loadConfig(): Config {
  const configPath = join(homedir(), ".config", "claude-memory", "config.toml");

  // Environment variables override config file
  const config: Config = {
    voyage: {
      api_key: process.env.CLAUDE_MEMORY_VOYAGE_API_KEY || ""
    },
    qdrant: {
      url: process.env.CLAUDE_MEMORY_QDRANT_URL || "http://localhost:6333"
    },
    neo4j: {
      uri: process.env.CLAUDE_MEMORY_NEO4J_URI || "bolt://localhost:7687",
      user: process.env.CLAUDE_MEMORY_NEO4J_USER || "neo4j",
      password: process.env.CLAUDE_MEMORY_NEO4J_PASSWORD || ""
    }
  };

  // Load from TOML if exists
  if (existsSync(configPath)) {
    try {
      const tomlContent = readFileSync(configPath, "utf-8");
      const fileConfig = TOML.parse(tomlContent);

      // Merge with precedence: env > file > defaults
      if (fileConfig.voyage?.api_key && !process.env.CLAUDE_MEMORY_VOYAGE_API_KEY) {
        config.voyage.api_key = fileConfig.voyage.api_key;
      }
      // ... similar for other fields
    } catch (error) {
      console.error(`Warning: Failed to parse config.toml: ${error}`);
    }
  }

  return config;
}
```

---

## 4. Tool Implementations

All 23 tools are implemented with identical schemas to the Python version.
See 50-integration-design.md for complete JSON schemas.

### 4.1 Memory CRUD Tools (5)

```typescript
// src/tools/memory-crud.ts
import { z } from "zod";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { ToolContext } from "./context.js";

const MemoryType = z.enum([
  "requirements", "design", "code_pattern", "component",
  "function", "test_history", "session", "user_preference"
]);

// memory_add
const memoryAddSchema = z.object({
  memory_type: MemoryType,
  content: z.string().min(1).max(100000),
  metadata: z.record(z.unknown()).optional(),
  relationships: z.array(z.object({
    type: z.string(),
    target_id: z.string().uuid()
  })).optional()
});

export function registerMemoryCrudTools(server: McpServer, ctx: ToolContext) {
  server.tool(
    "memory_add",
    "Create a new memory",
    memoryAddSchema,
    async (input) => {
      const embedding = await ctx.voyage.embed(input.content);
      const memoryId = crypto.randomUUID();

      await ctx.qdrant.upsert(ctx.collectionName(input.memory_type), {
        id: memoryId,
        vector: embedding,
        payload: {
          type: input.memory_type,
          content: input.content,
          metadata: input.metadata || {},
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          deleted: false,
          project_id: ctx.projectId
        }
      });

      // Create Neo4j node if applicable
      if (needsGraphNode(input.memory_type)) {
        await ctx.neo4j.createNode(input.memory_type, memoryId, input.metadata);
      }

      return {
        content: [{
          type: "text",
          text: JSON.stringify({ memory_id: memoryId, status: "created" })
        }]
      };
    }
  );

  // memory_get
  server.tool("memory_get", "Retrieve memory by ID", ...);

  // memory_update
  server.tool("memory_update", "Update existing memory", ...);

  // memory_delete
  server.tool("memory_delete", "Delete memory (soft delete)", ...);

  // memory_bulk_add
  server.tool("memory_bulk_add", "Batch add memories", ...);
}
```

### 4.2 Search Tools (5)

```typescript
// src/tools/search.ts
export function registerSearchTools(server: McpServer, ctx: ToolContext) {
  // memory_search - Semantic search across memories
  server.tool("memory_search", "Semantic search across memories",
    z.object({
      query: z.string(),
      memory_types: z.array(MemoryType).optional(),
      limit: z.number().min(1).max(100).default(10),
      time_range: z.object({
        start: z.string().datetime().optional(),
        end: z.string().datetime().optional()
      }).optional()
    }),
    async (input) => {
      const embedding = await ctx.voyage.embed(input.query);

      const results = await ctx.qdrant.search({
        collections: input.memory_types?.map(t => ctx.collectionName(t))
                    || ctx.allCollections(),
        vector: embedding,
        limit: input.limit,
        filter: {
          must: [
            { key: "project_id", match: { value: ctx.projectId } },
            { key: "deleted", match: { value: false } }
          ]
        }
      });

      return { content: [{ type: "text", text: JSON.stringify(results) }] };
    }
  );

  // code_search - Find similar code patterns
  server.tool("code_search", ...);

  // find_duplicates - Check for duplicate code
  server.tool("find_duplicates", ...);

  // get_related - Get graph-related entities
  server.tool("get_related", ...);

  // graph_query - Execute read-only Cypher
  server.tool("graph_query", ...);
}
```

### 4.3 Indexing Tools (4)

```typescript
// src/tools/indexing.ts
export function registerIndexingTools(server: McpServer, ctx: ToolContext) {
  // index_file - Index single source file
  server.tool("index_file", ...);

  // index_directory - Index directory recursively
  server.tool("index_directory", ...);

  // index_status - Get indexing job status
  server.tool("index_status", ...);

  // reindex - Trigger reindexing
  server.tool("reindex", ...);
}
```

### 4.4 Analysis Tools (4)

```typescript
// src/tools/analysis.ts
export function registerAnalysisTools(server: McpServer, ctx: ToolContext) {
  // check_consistency - Verify code follows patterns
  server.tool("check_consistency", ...);

  // validate_fix - Validate fix against design
  server.tool("validate_fix", ...);

  // get_design_context - Get ADRs/patterns for component
  server.tool("get_design_context", ...);

  // trace_requirements - Trace requirement to implementations
  server.tool("trace_requirements", ...);
}
```

### 4.5 Maintenance Tools (5)

```typescript
// src/tools/maintenance.ts
export function registerMaintenanceTools(server: McpServer, ctx: ToolContext) {
  // memory_statistics - Get system health/counts
  server.tool("memory_statistics", ...);

  // normalize_memory - Run normalization phases
  server.tool("normalize_memory", ...);

  // normalize_status - Get normalization job status
  server.tool("normalize_status", ...);

  // export_memory - Export to JSONL
  server.tool("export_memory", ...);

  // import_memory - Import from JSONL
  server.tool("import_memory", ...);
}
```

---

## 5. Storage Adapters

### 5.1 Qdrant Client

```typescript
// src/storage/qdrant.ts
import { QdrantClient } from "@qdrant/js-client-rest";

export class QdrantAdapter {
  private client: QdrantClient;
  private projectId: string;

  constructor(url: string, projectId: string) {
    this.client = new QdrantClient({ url });
    this.projectId = projectId;
  }

  collectionName(memoryType: string): string {
    return `${this.projectId}_${memoryType}`;
  }

  async ensureCollection(memoryType: string): Promise<void> {
    const name = this.collectionName(memoryType);
    const exists = await this.client.collectionExists(name);

    if (!exists) {
      await this.client.createCollection(name, {
        vectors: {
          size: 1024,  // voyage-code-3 dimensions
          distance: "Cosine"
        }
      });
    }
  }

  async upsert(collection: string, point: Point): Promise<void> {
    await this.client.upsert(collection, {
      points: [point]
    });
  }

  async search(params: SearchParams): Promise<SearchResult[]> {
    // Multi-collection search with project_id filter
  }

  async get(collection: string, id: string): Promise<Point | null> {
    // Get by ID with project_id validation
  }

  async delete(collection: string, id: string): Promise<void> {
    // Soft delete (set deleted: true)
  }
}
```

### 5.2 Neo4j Client

```typescript
// src/storage/neo4j.ts
import neo4j, { Driver, Session } from "neo4j-driver";

export class Neo4jAdapter {
  private driver: Driver;
  private projectId: string;

  constructor(uri: string, user: string, password: string, projectId: string) {
    this.driver = neo4j.driver(uri, neo4j.auth.basic(user, password));
    this.projectId = projectId;
  }

  async createNode(type: string, memoryId: string, properties: Record<string, unknown>): Promise<void> {
    const session = this.driver.session();
    try {
      await session.run(
        `CREATE (n:${type} {memory_id: $memoryId, project_id: $projectId, ...props})`,
        { memoryId, projectId: this.projectId, props: properties }
      );
    } finally {
      await session.close();
    }
  }

  async query(cypher: string, params: Record<string, unknown>): Promise<any[]> {
    // Execute read-only query with project_id filter injected
    if (!cypher.toLowerCase().startsWith("match")) {
      throw new Error("Only MATCH queries allowed");
    }

    const session = this.driver.session({ defaultAccessMode: neo4j.session.READ });
    try {
      // Inject project_id filter
      const result = await session.run(cypher, { ...params, projectId: this.projectId });
      return result.records.map(r => r.toObject());
    } finally {
      await session.close();
    }
  }

  async getRelated(entityId: string, relationshipTypes: string[], depth: number): Promise<any[]> {
    // Graph traversal with project_id filter
  }

  async close(): Promise<void> {
    await this.driver.close();
  }
}
```

### 5.3 Voyage AI Client

```typescript
// src/embedding/voyage.ts
export class VoyageClient {
  private apiKey: string;
  private baseUrl = "https://api.voyageai.com/v1";

  constructor(apiKey: string) {
    this.apiKey = apiKey;
  }

  async embed(text: string): Promise<number[]> {
    const response = await fetch(`${this.baseUrl}/embeddings`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${this.apiKey}`
      },
      body: JSON.stringify({
        model: "voyage-code-3",
        input: text
      })
    });

    if (!response.ok) {
      throw new Error(`Voyage API error: ${response.status}`);
    }

    const data = await response.json();
    return data.data[0].embedding;  // 1024 dimensions
  }

  async embedBatch(texts: string[]): Promise<number[][]> {
    // Batch embedding for efficiency (max 100 per request)
  }
}
```

### 5.4 Project Isolation

All storage operations include project_id:

| Store | Isolation Method |
|-------|------------------|
| Qdrant | Collection naming: `{projectId}_{memoryType}` |
| Neo4j | Property filter: `WHERE n.project_id = $projectId` |

---

## 6. Package Structure

### 6.1 TypeScript Configuration

```json
// tsconfig.json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "outDir": "./dist",
    "rootDir": "./src",
    "declaration": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

### 6.2 Package Configuration

```json
// package.json
{
  "name": "claude-memory-mcp",
  "version": "1.0.0",
  "description": "MCP server for Claude Code long-term memory",
  "type": "module",
  "bin": {
    "claude-memory-mcp": "./bin/claude-memory-mcp.js"
  },
  "main": "./dist/index.js",
  "types": "./dist/index.d.ts",
  "engines": {
    "node": ">=20.0.0"
  },
  "scripts": {
    "build": "tsc",
    "lint": "eslint src/",
    "test": "vitest",
    "prepublishOnly": "npm run build"
  },
  "dependencies": {
    "@modelcontextprotocol/sdk": "^1.0.0",
    "@qdrant/js-client-rest": "^1.9.0",
    "neo4j-driver": "^5.0.0",
    "toml": "^3.0.0",
    "zod": "^3.22.0"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "typescript": "^5.0.0",
    "vitest": "^1.0.0",
    "eslint": "^8.0.0"
  }
}
```

### 6.3 npx Entry Point

```javascript
#!/usr/bin/env node
// bin/claude-memory-mcp.js
import "../dist/index.js";
```

---

## 7. Operational Design

### 7.1 Startup Performance

Target: < 3 seconds to ready state

| Phase | Budget |
|-------|--------|
| Node.js startup | 500ms |
| Module loading | 500ms |
| Config loading | 100ms |
| DB connections | 1500ms |
| Tool registration | 100ms |
| **Total** | **2700ms** |

### 7.2 Logging

All logs to stderr (stdout reserved for MCP):

```typescript
// src/utils/logger.ts
export function log(level: string, message: string, data?: unknown): void {
  const entry = {
    timestamp: new Date().toISOString(),
    level,
    message,
    ...data
  };
  console.error(JSON.stringify(entry));
}

export const logger = {
  debug: (msg: string, data?: unknown) => log("DEBUG", msg, data),
  info: (msg: string, data?: unknown) => log("INFO", msg, data),
  warn: (msg: string, data?: unknown) => log("WARN", msg, data),
  error: (msg: string, data?: unknown) => log("ERROR", msg, data)
};
```

### 7.3 Error Handling

```typescript
// Tool error response format
function toolError(code: string, message: string, suggestion?: string) {
  return {
    content: [{
      type: "text",
      text: JSON.stringify({
        error: {
          code,
          message,
          suggestion
        }
      })
    }]
  };
}

// Usage in tool
try {
  // ... tool logic
} catch (error) {
  if (error instanceof ValidationError) {
    return toolError("VALIDATION_ERROR", error.message, "Check input format");
  }
  logger.error("Tool error", { error: error.message });
  return toolError("INTERNAL_ERROR", "An unexpected error occurred");
}
```

---

## 8. Data Compatibility

### 8.1 Qdrant Compatibility

| Aspect | Python Implementation | TypeScript Implementation |
|--------|----------------------|---------------------------|
| Collection naming | `{project_id}_{memory_type}` | Same |
| Vector dimensions | 1024 | Same |
| Distance metric | Cosine | Same |
| Payload schema | See 02-data-architecture.md | Same |

### 8.2 Neo4j Compatibility

| Aspect | Python Implementation | TypeScript Implementation |
|--------|----------------------|---------------------------|
| Node labels | Memory, Function, Component, etc. | Same |
| Relationship types | CALLS, IMPORTS, etc. | Same |
| Properties | memory_id, project_id, etc. | Same |
| Indexes | See 02-data-architecture.md | Same |

### 8.3 Verification

After implementation, verify compatibility by:
1. Reading memories created by Python server
2. Writing memories readable by Python server (if running)
3. Running graph queries returning same results

---

## 9. Testing Strategy

### 9.1 Unit Tests

| Component | Test File | Focus |
|-----------|-----------|-------|
| Config loading | config.test.ts | TOML parsing, env override |
| Qdrant adapter | qdrant.test.ts | Collection operations |
| Neo4j adapter | neo4j.test.ts | Node/relationship operations |
| Voyage client | voyage.test.ts | Embedding API |
| Each tool | tools/*.test.ts | Input validation, output format |

### 9.2 Integration Tests

| Test | Purpose |
|------|---------|
| MCP protocol | Tools/list, tools/call via stdio |
| Data roundtrip | Create -> Read -> Update -> Delete |
| Cross-store | Qdrant + Neo4j consistency |
| Project isolation | Different project_ids isolated |

### 9.3 E2E Tests

| Test | Purpose |
|------|---------|
| Claude Code integration | Tools visible in /mcp |
| Tool invocation | Can call each tool |
| Data compatibility | Read Python-created data |

---

## 10. Migration Plan

### 10.1 Steps

1. **Build TypeScript MCP server** - Complete implementation
2. **Verify all 23 tools** - Test each tool works
3. **Verify data compatibility** - Read existing memories
4. **Update documentation** - user-docs/quick-reference.md
5. **Delete Python code** - Remove src/memory_service/
6. **Update project structure** - Remove pyproject.toml, etc.

### 10.2 Rollback

If TypeScript implementation fails:
- Python code remains until verification complete
- Both can coexist (different .mcp.json configs)
- No data migration needed (same schemas)

---

## Appendix A: File Structure

```
mcp-server/
  package.json
  tsconfig.json
  bin/
    claude-memory-mcp.js       # npx entry point (shebang)
  src/
    index.ts                   # CLI entry, argument parsing
    server.ts                  # MCP server setup
    context.ts                 # Shared tool context
    config.ts                  # TOML config loading
    types/
      index.ts                 # Common types
      memory.ts                # Memory-related types
    tools/
      index.ts                 # Tool registry
      memory-crud.ts           # 5 CRUD tools
      search.ts                # 5 search tools
      indexing.ts              # 4 indexing tools
      analysis.ts              # 4 analysis tools
      maintenance.ts           # 5 maintenance tools
    storage/
      qdrant.ts                # Qdrant client adapter
      neo4j.ts                 # Neo4j driver adapter
    embedding/
      voyage.ts                # Voyage AI client
    utils/
      logger.ts                # stderr logging
      validation.ts            # Input validation helpers
  dist/                        # Compiled output
```

---

## Appendix B: References

| Document | Purpose |
|----------|---------|
| 02-data-architecture.md | Data schemas (Qdrant, Neo4j) |
| 50-integration-design.md | Tool JSON schemas |
| ADR-010-typescript-mcp-server.md | Architecture decision |
| user-docs/quick-reference.md | Tool usage documentation |
