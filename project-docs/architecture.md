# Project Architecture

This document captures cumulative architectural decisions across all project sequences.

## Active Sequences

| Seq | Name | Architecture Doc |
|-----|------|-----------------|
| 002 | Claude Code Long-Term Memory System | 002-architecture-memory-mcp.md |
| 005 | NPX-Based MCP Server | 005-architecture-npx-mcp.md |
| 006 | Memory Inspector UI | 006-architecture-memory-inspector.md |

## Technology Stack

### Core Technologies

| Technology | Version | Purpose |
|------------|---------|---------|
| TypeScript | 5.0+ | Primary implementation language (MCP server, Inspector) |
| Node.js | 20+ | Runtime for MCP server and Inspector backend |
| Qdrant | Latest | Vector database for embeddings and semantic search |
| Neo4j | 5.x Community | Graph database for relationships and traversals |
| Voyage-Code-3 | Current | Code-optimized embedding model |
| Docker | Latest | Containerization and deployment |

### MCP Server Libraries

| Library | Purpose |
|---------|---------|
| @modelcontextprotocol/sdk | Official MCP SDK for tool registration |
| @qdrant/js-client-rest | Qdrant TypeScript client |
| neo4j-driver | Neo4j TypeScript driver |
| zod | Runtime type validation |
| toml | Configuration file parsing |

### Memory Inspector UI Libraries

| Library | Purpose |
|---------|---------|
| React 18 | Frontend UI framework |
| Vite | Build tool and dev server |
| Express | Backend HTTP server |
| React Query | Server state management |
| Zustand | Client state management |
| Tailwind CSS | Utility-first CSS styling |
| Shadcn/UI | Accessible UI components |
| vis-network | Graph visualization |

## Architectural Patterns

### Memory Hierarchy (Letta/MemGPT Pattern)

Four-tier cognitive memory model:
1. **Working Memory** - Current context window
2. **Episodic Memory** - Session histories and events
3. **Semantic Memory** - Facts and abstractions
4. **Procedural Memory** - Workflows and procedures

### Dual-Store Pattern

- **Qdrant**: Primary store for content, embeddings, metadata
- **Neo4j**: Secondary store for structure and relationships
- **Synchronization**: Ordered writes with compensation

### Query Planning Pattern

Hybrid queries decomposed into:
1. Vector-first: Semantic search followed by graph filtering
2. Graph-first: Relationship traversal followed by similarity ranking
3. Pure vector/graph: Direct single-store execution

## Architecture Decision Records

| ADR | Title | Status |
|-----|-------|--------|
| ADR-001 | MCP Server Transport Mechanism | Superseded by ADR-010 |
| ADR-002 | Memory Storage Partitioning Strategy | Accepted |
| ADR-003 | Embedding Pipeline Architecture | Accepted |
| ADR-004 | Code Parsing Architecture | Accepted |
| ADR-005 | Hybrid Query Engine Design | Accepted |
| ADR-006 | Memory Normalization Process | Accepted |
| ADR-007 | Project Structure and Module Organization | Accepted |
| ADR-008 | Cross-Store Synchronization Strategy | Accepted |
| ADR-009 | Local MCP Architecture | Accepted |
| ADR-010 | TypeScript MCP Server | Accepted |
| ADR-011 | Memory Inspector UI Architecture | Accepted |

## Quality Attribute Targets

### Performance

| Metric | Target | Rationale |
|--------|--------|-----------|
| Semantic search | < 500ms P95 | Interactive query response |
| Graph traversal | < 200ms P95 | 3-hop relationship queries |
| Write latency | < 100ms P95 | Excluding embedding generation |
| Duplicate detection | < 300ms P95 | Real-time before code generation |

### Scalability

| Dimension | Target |
|-----------|--------|
| Memory count | 1,000,000 |
| File count | 100,000 |
| Function index | 500,000 |

### Resource Requirements

| Service | RAM (Recommended) | RAM (Minimum) |
|---------|-------------------|---------------|
| Memory Service | 2GB | 1GB |
| Qdrant | 4GB | 2GB |
| Neo4j | 2GB | 1GB |
| **Total** | **8GB** | **4GB** |

## Security Principles

1. **Localhost Only** - MCP server and HTTP endpoints bind to 127.0.0.1
2. **Secrets in Environment** - No secrets in code or configuration files
3. **Non-Root Containers** - Docker containers run with minimal privileges
4. **Minimal External Access** - Only Voyage AI API requires external network

## Integration Points

### Claude Code

- Protocol: MCP (Model Context Protocol)
- Transport: stdio
- Configuration: .mcp.json or settings.json
- Invocation: `npx claude-memory-mcp --project-id <id>`

### Memory Inspector UI

- Protocol: HTTP/REST
- Backend: Express server on localhost:3001
- Frontend: React SPA on localhost:5173 (dev)
- Reuses: MCP server adapters (QdrantAdapter, Neo4jAdapter, VoyageClient)

### External Services

- Voyage AI: HTTPS API for embeddings

## Cross-Cutting Concerns

### Logging

- Format: Structured JSON (structlog)
- Fields: timestamp, level, component, operation, context
- Levels: DEBUG, INFO, WARNING, ERROR

### Metrics

- Format: Prometheus
- Endpoint: /metrics on HTTP server
- Key metrics: latency histograms, operation counts, cache hit rates

### Error Handling

- Validation errors: Immediate rejection with actionable message
- Transient errors: Retry with exponential backoff
- Dependency errors: Graceful degradation
- Permanent errors: Log and fail with context

## Document References

- Requirements: `requirement-docs/requirements-memory-docs.md`
- MCP Server Requirements: `requirement-docs/REQ-MEM-005-npx-mcp-server.md`
- Inspector UI Requirements: `requirement-docs/REQ-MEM-006-memory-inspector-ui.md`
- Sequence Architectures:
  - `project-docs/002-architecture-memory-mcp.md`
  - `project-docs/005-architecture-npx-mcp.md`
  - `project-docs/006-architecture-memory-inspector.md`
- ADRs: `project-docs/adrs/ADR-*.md`
