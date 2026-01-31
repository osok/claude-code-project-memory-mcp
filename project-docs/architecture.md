# Project Architecture

This document captures cumulative architectural decisions across all project sequences.

## Active Sequences

| Seq | Name | Architecture Doc |
|-----|------|-----------------|
| 002 | Claude Code Long-Term Memory System | 002-architecture-memory-mcp.md |

## Technology Stack

### Core Technologies

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.12+ | Primary implementation language |
| Qdrant | Latest | Vector database for embeddings and semantic search |
| Neo4j | 5.x Community | Graph database for relationships and traversals |
| Voyage-Code-3 | Current | Code-optimized embedding model |
| Tree-sitter | 0.20+ | Universal code parsing |
| Docker | Latest | Containerization and deployment |

### Frameworks and Libraries

| Library | Purpose |
|---------|---------|
| FastAPI | HTTP server for health/metrics endpoints |
| pydantic | Data validation and settings management |
| structlog | Structured JSON logging |
| prometheus-client | Metrics exposure |
| qdrant-client | Qdrant Python client |
| neo4j | Neo4j Python driver |
| voyageai | Voyage AI client |
| tree-sitter-languages | Pre-built language grammars |

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
| ADR-001 | MCP Server Transport Mechanism | Accepted |
| ADR-002 | Memory Storage Partitioning Strategy | Accepted |
| ADR-003 | Embedding Pipeline Architecture | Accepted |
| ADR-004 | Code Parsing Architecture | Accepted |
| ADR-005 | Hybrid Query Engine Design | Accepted |
| ADR-006 | Memory Normalization Process | Accepted |
| ADR-007 | Project Structure and Module Organization | Accepted |
| ADR-008 | Cross-Store Synchronization Strategy | Accepted |

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

### External Services

- Voyage AI: HTTPS API for embeddings
- Fallback: Local sentence-transformers model

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
- Sequence Architecture: `project-docs/002-architecture-memory-mcp.md`
- ADRs: `project-docs/adrs/ADR-*.md`
