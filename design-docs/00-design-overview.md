# Design Overview: Claude Code Long-Term Memory System

## Document Control

| Field | Value |
|-------|-------|
| Version | 1.1 |
| Status | Draft |
| Sequence | 002, 005 |
| Requirements | requirements-memory-docs.md, REQ-MEM-005-npx-mcp-server.md |
| Architecture | 002-architecture-memory-mcp.md, 005-architecture-npx-mcp.md |

---

## 1. Introduction

### 1.1 Purpose

This document provides the master overview of design documents for the Claude Code Long-Term Memory System. It serves as the entry point for understanding the system design, tracking requirements coverage, and navigating to detailed component designs.

### 1.2 System Summary

The Claude Code Long-Term Memory System is a persistent memory infrastructure that enhances Claude Code's capabilities for complex, multi-session software development projects. It provides:

- **Semantic search** via Qdrant vector database with Voyage-Code-3 embeddings
- **Relationship tracking** via Neo4j graph database
- **Duplicate detection** for preventing code redundancy
- **Design alignment validation** for maintaining architectural consistency
- **Memory normalization** for long-term quality maintenance

### 1.3 Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Language | TypeScript 5.x | MCP server (SEQ 005) |
| Runtime | Node.js 20+ | MCP server execution |
| MCP SDK | @modelcontextprotocol/sdk | Official MCP protocol |
| Vector Database | Qdrant | Embeddings and semantic search |
| Graph Database | Neo4j | Relationships and traversals |
| Embedding Model | Voyage-Code-3 | Code-optimized embeddings (1024 dim) |
| MCP Transport | stdio | Claude Code integration |
| Validation | Zod | Runtime type checking |

---

## 2. Design Document Index

### 2.1 Foundation Layer

| Document | Prefix | Description | Status |
|----------|--------|-------------|--------|
| [Data Architecture](02-data-architecture.md) | 02- | Memory schemas, Qdrant collections, Neo4j graph | Draft |
| [Security Architecture](03-security-architecture.md) | 03- | Authentication, secrets, network isolation | Draft |

### 2.2 Core Layer

| Document | Prefix | Description | Status |
|----------|--------|-------------|--------|
| [Library Design](10-library-design.md) | 10- | Shared models, utilities, common interfaces | Draft |
| [Backend Design](20-backend-design.md) | 20- | Memory service, adapters, embedding service | Draft |

### 2.3 Application Layer

| Document | Prefix | Description | Status |
|----------|--------|-------------|--------|
| [Agent Design](40-agent-design.md) | 40- | Indexer, normalizer background workers | Draft |

### 2.4 Integration Layer

| Document | Prefix | Description | Status |
|----------|--------|-------------|--------|
| [Integration Design](50-integration-design.md) | 50- | MCP API contracts, 27 tools with JSON schemas | Draft |

### 2.5 Infrastructure Layer

| Document | Prefix | Description | Status |
|----------|--------|-------------|--------|
| [Infrastructure Design](60-infrastructure-design.md) | 60- | Docker deployment, volumes, networking | Draft |

---

## 3. Component Architecture

### 3.1 Component Diagram

```
+------------------+
|   Claude Code    |
+--------+---------+
         | stdio (MCP)
         v
+------------------+        +------------------+
|  Memory Service  |        |   HTTP Server    |
|   (MCP Server)   |<------>| /health /metrics |
+--------+---------+        +------------------+
         |
    +----+----+----+
    |    |    |    |
    v    v    v    v
+------+ +------+ +------+ +------+
| Core | |Parse | |Embed | |Store |
+------+ +------+ +------+ +------+
    |              |         |
    |              v         v
    |         +-------+ +-------+
    +-------->| Qdrant| | Neo4j |
              +-------+ +-------+
```

### 3.2 Component Index

| Component | Layer | Design Doc | Primary Responsibility |
|-----------|-------|------------|----------------------|
| MCP Server | API | 20-backend-design.md | Tool routing, request handling |
| HTTP Server | API | 20-backend-design.md | Health checks, metrics |
| Memory Manager | Core | 20-backend-design.md | CRUD operations, lifecycle |
| Query Engine | Core | 20-backend-design.md | Query planning, hybrid execution |
| Indexer | Core | 40-agent-design.md | Codebase scanning, relationship extraction |
| Normalizer | Core | 40-agent-design.md | Deduplication, cleanup |
| Duplicate Detector | Core | 20-backend-design.md | Similarity comparison |
| Qdrant Adapter | Storage | 20-backend-design.md | Vector operations |
| Neo4j Adapter | Storage | 20-backend-design.md | Graph operations |
| Embedding Service | Embedding | 20-backend-design.md | Cache, batching, Voyage API |
| Parser Orchestrator | Parsing | 10-library-design.md | Language detection, extraction |
| Language Extractors | Parsing | 10-library-design.md | AST extraction (7 languages) |

---

## 4. Requirements Traceability Matrix

### 4.1 Functional Requirements

| Requirement ID | Summary | Design Document | Design Section |
|----------------|---------|-----------------|----------------|
| REQ-MEM-FN-001 | Four-tier memory architecture | 02-data-architecture.md | 3.1 |
| REQ-MEM-FN-002 | Working memory token limit (50K) | 50-integration-design.md | 4.3 |
| REQ-MEM-FN-003 | Episodic memory in Qdrant | 02-data-architecture.md | 7.2 |
| REQ-MEM-FN-004 | Semantic memory hybrid storage | 02-data-architecture.md | 7.2, 8.2 |
| REQ-MEM-FN-005 | Procedural memory storage | 02-data-architecture.md | 7.2 |
| REQ-MEM-FN-010 | Requirements memory | 02-data-architecture.md | 5.2.2 |
| REQ-MEM-FN-011 | Design memory | 02-data-architecture.md | 5.2.3 |
| REQ-MEM-FN-012 | Code pattern memory | 02-data-architecture.md | 5.2.4 |
| REQ-MEM-FN-013 | Component registry memory | 02-data-architecture.md | 5.2.5 |
| REQ-MEM-FN-014 | Function index memory | 02-data-architecture.md | 5.2.6 |
| REQ-MEM-FN-015 | Test history memory | 02-data-architecture.md | 5.2.7 |
| REQ-MEM-FN-016 | Session history memory | 02-data-architecture.md | 5.2.8 |
| REQ-MEM-FN-017 | User preferences memory | 02-data-architecture.md | 5.2.9 |
| REQ-MEM-FN-020 | Self-editing memory tools | 50-integration-design.md | 4.2.1 |
| REQ-MEM-FN-021 | Memory extraction | 20-backend-design.md | 8.2 |
| REQ-MEM-FN-022 | Conflict detection | 20-backend-design.md | 8.2 |
| REQ-MEM-FN-023 | Memory consolidation | 40-agent-design.md | 4.2.2 |
| REQ-MEM-FN-024 | Importance scoring | 20-backend-design.md | 8.2 |
| REQ-MEM-FN-030 | Voyage-Code-3 embeddings | 20-backend-design.md | 5.4 |
| REQ-MEM-FN-031 | Similar function search | 50-integration-design.md | 4.2.2 |
| REQ-MEM-FN-032 | Duplicate suggestion | 20-backend-design.md | 5.3 |
| REQ-MEM-FN-033 | Configurable threshold | 60-infrastructure-design.md | 6.2 |
| REQ-MEM-FN-040 | Pattern identification | 20-backend-design.md | 8.2 |
| REQ-MEM-FN-041 | Pattern retrieval tool | 50-integration-design.md | 4.2.4 |
| REQ-MEM-FN-042 | Pattern deviation tracking | 20-backend-design.md | 8.2 |
| REQ-MEM-FN-043 | Relationship tracking | 02-data-architecture.md | 8.3 |
| REQ-MEM-FN-050 | Design context retrieval | 50-integration-design.md | 4.2.4 |
| REQ-MEM-FN-051 | Fix validation tool | 50-integration-design.md | 4.2.4 |
| REQ-MEM-FN-052 | Test failure linking | 02-data-architecture.md | 5.2.7 |
| REQ-MEM-FN-053 | Constraint violation detection | 20-backend-design.md | 8.2 |
| REQ-MEM-FN-060 | File/directory indexing | 50-integration-design.md | 4.2.3 |
| REQ-MEM-FN-061 | Tree-sitter parsing | 10-library-design.md | 5.2 |
| REQ-MEM-FN-062 | Incremental indexing | 40-agent-design.md | 4.2.1 |
| REQ-MEM-FN-063 | Multi-language support | 10-library-design.md | 5.2 |
| REQ-MEM-FN-064 | Relationship extraction | 10-library-design.md | 5.2 |
| REQ-MEM-FN-070 | Memory normalization | 40-agent-design.md | 4.2.2 |
| REQ-MEM-FN-071 | Deduplication (0.95) | 40-agent-design.md | 4.2.2 |
| REQ-MEM-FN-072 | Orphan cleanup | 40-agent-design.md | 4.2.2 |
| REQ-MEM-FN-073 | Embedding refresh | 40-agent-design.md | 4.2.2 |
| REQ-MEM-FN-074 | Rollback capability | 40-agent-design.md | 4.2.2 |
| REQ-MEM-FN-075 | Progress reporting | 50-integration-design.md | 4.2.5 |
| REQ-MEM-FN-080 | Semantic search | 50-integration-design.md | 4.2.2 |
| REQ-MEM-FN-081 | Graph traversal | 50-integration-design.md | 4.2.2 |
| REQ-MEM-FN-082 | Hybrid queries | 20-backend-design.md | 5.2 |
| REQ-MEM-FN-083 | Pagination | 50-integration-design.md | 4.3 |
| REQ-MEM-FN-084 | Relevance ranking | 20-backend-design.md | 5.2 |

### 4.2 Interface Requirements

| Requirement ID | Summary | Design Document | Design Section |
|----------------|---------|-----------------|----------------|
| REQ-MEM-INT-001 | MCP compliance | 50-integration-design.md | 3.1 |
| REQ-MEM-INT-002 | Tool categories | 50-integration-design.md | 4.1 |
| REQ-MEM-INT-003 | JSON schema validation | 50-integration-design.md | 3.3 |
| REQ-MEM-INT-004 | Concurrent invocations | 20-backend-design.md | 10.1 |
| REQ-MEM-INT-010-014 | Memory CRUD tools | 50-integration-design.md | 4.2.1 |
| REQ-MEM-INT-020-024 | Search tools | 50-integration-design.md | 4.2.2 |
| REQ-MEM-INT-030-033 | Index tools | 50-integration-design.md | 4.2.3 |
| REQ-MEM-INT-040-043 | Analysis tools | 50-integration-design.md | 4.2.4 |
| REQ-MEM-INT-050-054 | Maintenance tools | 50-integration-design.md | 4.2.5 |
| REQ-MEM-INT-060-063 | Qdrant interface | 20-backend-design.md | 5.5.1 |
| REQ-MEM-INT-070-074 | Neo4j interface | 20-backend-design.md | 5.5.2 |
| REQ-MEM-INT-080-084 | Voyage interface | 20-backend-design.md | 5.4 |
| REQ-MEM-INT-090-093 | File system interface | 10-library-design.md | 4.4 |

### 4.3 Data Requirements

| Requirement ID | Summary | Design Document | Design Section |
|----------------|---------|-----------------|----------------|
| REQ-MEM-DATA-001 | Base memory schema | 02-data-architecture.md | 5.2.1 |
| REQ-MEM-DATA-002 | UUID format | 02-data-architecture.md | 5.2.1 |
| REQ-MEM-DATA-010-017 | Memory type schemas | 02-data-architecture.md | 5.2.2-5.2.9 |
| REQ-MEM-DATA-020-022 | Graph schema | 02-data-architecture.md | 8.2-8.5 |
| REQ-MEM-DATA-030-032 | Data integrity | 02-data-architecture.md | 11.1-11.3 |
| REQ-MEM-DATA-040-042 | Data retention | 02-data-architecture.md | 13.1-13.3 |

### 4.4 Non-Functional Requirements

| Requirement ID | Summary | Design Document | Design Section |
|----------------|---------|-----------------|----------------|
| REQ-MEM-PERF-001 | Search latency < 500ms | 20-backend-design.md | 10.1 |
| REQ-MEM-PERF-002 | Graph latency < 200ms | 20-backend-design.md | 10.1 |
| REQ-MEM-PERF-003 | Write latency < 100ms | 20-backend-design.md | 10.1 |
| REQ-MEM-PERF-004 | Embedding throughput | 20-backend-design.md | 5.4 |
| REQ-MEM-PERF-005 | Indexing throughput | 40-agent-design.md | 11.1 |
| REQ-MEM-PERF-006 | Duplicate detection < 300ms | 20-backend-design.md | 10.1 |
| REQ-MEM-SEC-001 | Environment variable secrets | 03-security-architecture.md | 10.2 |
| REQ-MEM-SEC-002 | Localhost binding | 03-security-architecture.md | 6.2 |
| REQ-MEM-SEC-003 | Non-root containers | 03-security-architecture.md | 9.2 |
| REQ-MEM-SEC-004 | Database authentication | 03-security-architecture.md | 5.3 |
| REQ-MEM-SEC-005 | External transmission limits | 03-security-architecture.md | 8.1 |
| REQ-MEM-REL-001 | Data persistence | 60-infrastructure-design.md | 5.2 |
| REQ-MEM-REL-002 | Transaction semantics | 02-data-architecture.md | 11.2 |
| REQ-MEM-REL-003 | Graceful degradation | 20-backend-design.md | 11.3 |
| REQ-MEM-REL-004 | Health checks | 20-backend-design.md | 11.4 |
| REQ-MEM-REL-005 | Atomic normalization | 40-agent-design.md | 4.2.2 |
| REQ-MEM-SCAL-001 | 100K source files | 60-infrastructure-design.md | 14.3 |
| REQ-MEM-SCAL-002 | 1M memories | 60-infrastructure-design.md | 14.3 |
| REQ-MEM-SCAL-003 | 500K function index | 60-infrastructure-design.md | 14.3 |
| REQ-MEM-SCAL-004 | Resource limits | 60-infrastructure-design.md | 4.2 |
| REQ-MEM-MAINT-001 | Type hints and docstrings | 10-library-design.md | 13.1 |
| REQ-MEM-MAINT-002 | Structured logging | 60-infrastructure-design.md | 8.2 |
| REQ-MEM-MAINT-003 | Externalized config | 60-infrastructure-design.md | 6.2 |
| REQ-MEM-MAINT-004 | API documentation | 50-integration-design.md | 13.1 |
| REQ-MEM-MAINT-005 | 80% test coverage | 10-library-design.md | 12.1 |
| REQ-MEM-OBS-001 | Prometheus metrics | 60-infrastructure-design.md | 8.3 |
| REQ-MEM-OBS-002 | Tool invocation logging | 60-infrastructure-design.md | 8.2 |
| REQ-MEM-OBS-003 | Memory statistics | 50-integration-design.md | 4.2.5 |
| REQ-MEM-OBS-004 | Error context logging | 60-infrastructure-design.md | 8.2 |
| REQ-MEM-USE-001 | Actionable error messages | 50-integration-design.md | 8.3 |
| REQ-MEM-USE-002 | CLI utility | 50-integration-design.md | 5.1 |
| REQ-MEM-USE-003 | CLAUDE.md integration docs | 50-integration-design.md | 13.1 |

### 4.5 Deployment Requirements

| Requirement ID | Summary | Design Document | Design Section |
|----------------|---------|-----------------|----------------|
| REQ-MEM-DEP-001 | docker-compose.yml | 60-infrastructure-design.md | 4.1 |
| REQ-MEM-DEP-002 | Named volumes | 60-infrastructure-design.md | 5.2 |
| REQ-MEM-DEP-003 | Health checks | 60-infrastructure-design.md | 4.2 |
| REQ-MEM-DEP-004 | .env.example | 60-infrastructure-design.md | 6.2 |
| REQ-MEM-DEP-010 | MCP configuration | 50-integration-design.md | 3.4 |
| REQ-MEM-DEP-011 | CLAUDE.md template | 50-integration-design.md | 13.1 |
| REQ-MEM-DEP-012 | Workflow documentation | 50-integration-design.md | 13.1 |

---

## 5. Architecture Decision Records

| ADR | Title | Decision Summary |
|-----|-------|-----------------|
| ADR-001 | MCP Server Transport | Superseded by ADR-010 |
| ADR-002 | Memory Storage Partitioning | Qdrant for content/embeddings, Neo4j for relationships |
| ADR-003 | Embedding Pipeline | Hybrid: cache-first with async batched generation |
| ADR-004 | Code Parsing | Tree-sitter universal parser with language extractors |
| ADR-005 | Hybrid Query Engine | Query planner with two-phase execution |
| ADR-006 | Normalization Process | Copy-on-write with instant swap |
| ADR-007 | Project Structure | Layered architecture (api/core/storage/parsing/embedding) |
| ADR-008 | Cross-Store Sync | Ordered writes with compensation |
| ADR-009 | Local MCP Architecture | MCP as local process, databases in Docker |
| ADR-010 | TypeScript MCP Server | Replace Python with TypeScript using official SDK |

---

## 6. Design Dependencies

### 6.1 Dependency Graph

```
00-design-overview.md
         |
         v
+--------+--------+
|                 |
v                 v
02-data.md    03-security.md
|                 |
+--------+--------+
         |
         v
   10-library.md
         |
         v
   20-backend.md
         |
    +----+----+
    |         |
    v         v
40-agent.md  50-integration.md
    |         |
    +----+----+
         |
         v
 60-infrastructure.md
```

### 6.2 Design Order

1. **Foundation (Parallel)**
   - 02-data-architecture.md
   - 03-security-architecture.md

2. **Core**
   - 10-library-design.md (depends on 02, 03)
   - 20-backend-design.md (depends on 10)

3. **Application**
   - 40-agent-design.md (depends on 20)

4. **Integration**
   - 50-integration-design.md (depends on 20)

5. **Infrastructure**
   - 60-infrastructure-design.md (depends on all above)

---

## 7. Cross-Cutting Concerns

### 7.1 Logging Strategy

| Level | Usage | Format |
|-------|-------|--------|
| DEBUG | Development diagnostics | JSON |
| INFO | Normal operations | JSON |
| WARNING | Potential issues | JSON |
| ERROR | Failures with context | JSON |

### 7.2 Metrics Strategy

| Category | Metrics | Collection |
|----------|---------|------------|
| Latency | Query/write/embedding time | Histogram |
| Throughput | Operations per second | Counter |
| Cache | Hit/miss rates | Counter |
| Errors | By type and operation | Counter |
| Resources | Memory/CPU usage | Gauge |

### 7.3 Error Handling Strategy

| Error Type | Handling | User Response |
|------------|----------|---------------|
| Validation | Immediate rejection | Detailed error message |
| Transient | Retry with backoff | Timeout message after retries |
| Dependency | Graceful degradation | Partial functionality message |
| Internal | Log and fail | Generic error with request ID |

---

## 8. Document Conventions

### 8.1 Requirement References

Requirements are referenced using the format `REQ-MEM-XXX-NNN` where:
- `MEM` = Memory system namespace
- `XXX` = Category (FN=Functional, INT=Interface, DATA=Data, etc.)
- `NNN` = Sequential number

### 8.2 Design Sections

Each design document follows a consistent structure:
1. Introduction and scope
2. Requirements traceability
3. Architecture overview
4. Component specifications
5. Interface definitions
6. Data design (where applicable)
7. Error handling
8. Performance considerations
9. Security considerations
10. Constraints and assumptions

### 8.3 Diagrams

Diagrams use Mermaid format for:
- Architecture diagrams
- Sequence diagrams
- State diagrams
- Entity-relationship diagrams

---

## 9. Glossary

| Term | Definition |
|------|------------|
| ADR | Architecture Decision Record |
| Embedding | Dense vector representation of text/code for similarity |
| Episodic Memory | Memory of specific events with temporal context |
| HNSW | Hierarchical Navigable Small World (approximate NN algorithm) |
| MCP | Model Context Protocol |
| Procedural Memory | Memory of how to perform tasks |
| Semantic Memory | Memory of facts and abstractions |
| Working Memory | Immediate context in Claude Code's window |

---

## Appendix A: Reference Documents

| Document | Location | Purpose |
|----------|----------|---------|
| Requirements | requirement-docs/requirements-memory-docs.md | Source requirements |
| Architecture | project-docs/002-architecture-memory-mcp.md | System architecture |
| ADR-001 | project-docs/adrs/ADR-001-mcp-server-transport.md | Transport decision |
| ADR-002 | project-docs/adrs/ADR-002-memory-storage-partitioning.md | Storage decision |
| ADR-003 | project-docs/adrs/ADR-003-embedding-pipeline.md | Embedding decision |
| ADR-004 | project-docs/adrs/ADR-004-code-parsing-architecture.md | Parsing decision |
| ADR-005 | project-docs/adrs/ADR-005-hybrid-query-engine.md | Query decision |
| ADR-006 | project-docs/adrs/ADR-006-normalization-process.md | Normalization decision |
| ADR-007 | project-docs/adrs/ADR-007-project-structure.md | Structure decision |
| ADR-008 | project-docs/adrs/ADR-008-cross-store-synchronization.md | Sync decision |
