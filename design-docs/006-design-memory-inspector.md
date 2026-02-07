# Design Document: Memory Inspector UI

## Document Control

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Status | Draft |
| Sequence | 006 |
| Requirements | [REQ-MEM-006-memory-inspector-ui.md](../requirement-docs/REQ-MEM-006-memory-inspector-ui.md) |
| Architecture | [006-architecture-memory-inspector.md](../project-docs/006-architecture-memory-inspector.md) |
| ADR | [ADR-011-memory-inspector-architecture.md](../project-docs/adrs/ADR-011-memory-inspector-architecture.md) |

---

## 1. Introduction

### 1.1 Purpose

This document provides the design overview for the Memory Inspector UI, a development-only web application for inspecting, searching, and managing memories stored in the Claude Code Long-Term Memory System.

### 1.2 Scope

**Included:**
- React frontend with memory browser, search, graph explorer, and maintenance modules
- Express backend API wrapping existing MCP server adapters
- vis-network graph visualization
- CRUD operations on memories

**Excluded:**
- User authentication (dev-only tool)
- Production deployment
- Mobile optimization
- Background workers

### 1.3 Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | React 18 | UI framework |
| | TypeScript | Type safety |
| | Vite | Build tool, dev server |
| | Tailwind CSS | Styling |
| | Shadcn/UI | Component library |
| | React Query | Server state management |
| | Zustand | Client state management |
| | vis-network | Graph visualization |
| | React Router | Client-side routing |
| **Backend** | Node.js 20+ | Runtime |
| | Express | HTTP server |
| | TypeScript | Type safety |
| **Shared** | mcp-server adapters | Database access (QdrantAdapter, Neo4jAdapter) |
| | mcp-server types | Type definitions (Memory, MemoryType) |

---

## 2. Design Documents Index

### 2.1 Related Design Documents

| Document | Description | Status |
|----------|-------------|--------|
| [30-frontend-memory-inspector.md](30-frontend-memory-inspector.md) | Frontend component design, pages, state management | Draft |
| [20-backend-design.md](20-backend-design.md) | Backend design (Seq 006 section for Inspector API) | Updated |

### 2.2 Foundational Documents (Referenced)

| Document | Relevance |
|----------|-----------|
| [02-data-architecture.md](02-data-architecture.md) | Memory schemas, Qdrant collections, Neo4j graph |
| [10-library-design.md](10-library-design.md) | Shared types from mcp-server |

---

## 3. System Architecture

### 3.1 High-Level Architecture

```
+------------------------------------------------------------------+
|                    Memory Inspector UI                            |
|  +------------------------------------------------------------+  |
|  |                   React Frontend (SPA)                      |  |
|  |  +------------+ +------------+ +------------+ +-----------+ |  |
|  |  |  Memory    | |   Search   | |   Graph    | | Mainten-  | |  |
|  |  |  Browser   | |   Module   | |  Explorer  | |   ance    | |  |
|  |  +-----+------+ +-----+------+ +-----+------+ +-----+-----+ |  |
|  |        |              |              |              |        |  |
|  |  +-----v--------------v--------------v--------------v-----+  |  |
|  |  |              React Query + Zustand                      |  |  |
|  |  |           (Server State)    (UI State)                  |  |  |
|  |  +---------------------------+-----------------------------+  |  |
|  +------------------------------|--------------------------------+  |
|                                 | HTTP/REST                         |
|  +------------------------------|--------------------------------+  |
|  |                Express Backend API                            |  |
|  |  +---------------------------+-----------------------------+  |  |
|  |  |                     Route Handlers                       |  |  |
|  |  |   /memories  /search  /graph  /stats  /index  /config    |  |  |
|  |  +--------+---------------+---------------+----------------+  |  |
|  |           |               |               |                   |  |
|  |  +--------v----+  +-------v------+  +-----v------+           |  |
|  |  | QdrantAdapter|  | Neo4jAdapter |  | VoyageClient|          |  |
|  |  | (from mcp)   |  | (from mcp)   |  | (from mcp)  |          |  |
|  |  +--------+----+  +-------+------+  +------+-----+           |  |
|  +-----------|--------------|-----------------|-----------------+  |
+--------------|--------------|-----------------|--------------------+
               |              |                 |
               v              v                 v
       +---------------+ +---------------+ +---------------+
       |    Qdrant     | |    Neo4j      | |   Voyage AI   |
       | (Vectors/Data)| |   (Graph)     | |  (Embeddings) |
       | localhost:6333| | localhost:7687| |    HTTPS      |
       +---------------+ +---------------+ +---------------+
```

### 3.2 Data Flow

1. **User interacts** with React frontend
2. **React Query** manages API calls to Express backend
3. **Express routes** delegate to MCP server adapters
4. **Adapters** query Qdrant/Neo4j databases
5. **Results** flow back through the same path
6. **Zustand** manages UI state (filters, selections, theme)

---

## 4. Requirements Traceability

### 4.1 Functional Requirements Coverage

| Requirement ID | Summary | Design Document | Section |
|----------------|---------|-----------------|---------|
| REQ-006-FN-001 | Memory Type Navigation | 30-frontend | 4.2.1 |
| REQ-006-FN-002 | Memory List View | 30-frontend | 4.2.2 |
| REQ-006-FN-003 | Memory Detail View | 30-frontend | 4.2.3 |
| REQ-006-FN-004 | Memory Filtering | 30-frontend | 4.2.4 |
| REQ-006-FN-005 | Memory Creation | 30-frontend | 4.2.5 |
| REQ-006-FN-006 | Memory Editing | 30-frontend | 4.2.5 |
| REQ-006-FN-007 | Memory Deletion | 30-frontend | 4.2.6 |
| REQ-006-FN-010 | Semantic Search | 30-frontend | 4.3.1 |
| REQ-006-FN-011 | Code Search | 30-frontend | 4.3.2 |
| REQ-006-FN-012 | Duplicate Detection | 30-frontend | 4.3.3 |
| REQ-006-FN-020 | Graph Visualization | 30-frontend | 4.4.1 |
| REQ-006-FN-021 | Relationship Filtering | 30-frontend | 4.4.2 |
| REQ-006-FN-022 | Requirement Tracing | 30-frontend | 4.4.3 |
| REQ-006-FN-023 | Cypher Query Interface | 30-frontend | 4.4.4 |
| REQ-006-FN-030 | System Statistics | 30-frontend | 4.5.1 |
| REQ-006-FN-031 | Normalization Operations | 30-frontend | 4.5.2 |
| REQ-006-FN-032 | Export/Import | 30-frontend | 4.5.3 |
| REQ-006-FN-033 | Indexing Management | 30-frontend | 4.5.4 |
| REQ-006-FN-040 | Project Selection | 30-frontend | 4.6.1 |
| REQ-006-FN-041 | Connection Configuration | 30-frontend | 4.6.2 |

### 4.2 API Requirements Coverage

| Requirement ID | Summary | Design Document | Section |
|----------------|---------|-----------------|---------|
| REQ-006-INT-API-001 | Backend API | 20-backend | Seq 006 |
| REQ-006-DATA-001 | Qdrant Integration | 20-backend | Seq 006 |
| REQ-006-DATA-002 | Neo4j Integration | 20-backend | Seq 006 |
| REQ-006-DATA-003 | Local Configuration | 30-frontend | 5.3 |

### 4.3 Non-Functional Requirements Coverage

| Requirement ID | Summary | Design Document | Section |
|----------------|---------|-----------------|---------|
| REQ-006-NFR-PERF-001 | Response Time | 20-backend | Seq 006 |
| REQ-006-NFR-PERF-002 | Pagination | 30-frontend | 4.2.2 |
| REQ-006-NFR-USE-001 | Keyboard Navigation | 30-frontend | 6.1 |
| REQ-006-NFR-USE-002 | Dark/Light Theme | 30-frontend | 5.1 |
| REQ-006-NFR-COMP-001 | Browser Support | 30-frontend | 7.1 |
| REQ-006-NFR-SEC-001 | No Authentication | 20-backend | Seq 006 |
| REQ-006-NFR-SEC-002 | Read-Only Cypher | 20-backend | Seq 006 |

---

## 5. Directory Structure

```
claude-code-project-memory-mcp/
  mcp-server/                    # Existing MCP server
    src/
      storage/
        qdrant.ts                # QdrantAdapter - reused
        neo4j.ts                 # Neo4jAdapter - reused
      embedding/
        voyage.ts                # VoyageClient - reused
      types/
        memory.ts                # Memory, MemoryType - shared

  inspector-ui/                  # New UI package
    package.json
    tsconfig.json
    vite.config.ts
    tailwind.config.ts

    server/                      # Express backend
      index.ts                   # Entry point, server setup
      routes/
        memories.ts              # /api/memories endpoints
        search.ts                # /api/search endpoints
        graph.ts                 # /api/graph endpoints
        stats.ts                 # /api/stats endpoint
        normalize.ts             # /api/normalize endpoints
        export-import.ts         # /api/export, /api/import
        index-files.ts           # /api/index endpoints
        config.ts                # /api/config endpoints
      middleware/
        error-handler.ts         # Global error handling
        request-logger.ts        # Request logging
      context.ts                 # Server context (adapters)

    src/                         # React frontend
      main.tsx                   # Entry point
      App.tsx                    # Root component, routing
      api/                       # API client layer
      stores/                    # Zustand stores
      hooks/                     # Custom React hooks
      components/                # UI components
      pages/                     # Page components
      lib/                       # Utilities
      types/                     # Frontend-specific types

    public/
      favicon.ico
```

---

## 6. Key Design Decisions

### 6.1 Adapter Reuse (ADR-011 Decision 2)

The Express backend imports and wraps adapters from `mcp-server/src/`:
- `QdrantAdapter` for vector operations
- `Neo4jAdapter` for graph operations
- `VoyageClient` for embedding generation

**Rationale:** Ensures Inspector shows exactly what Claude Code sees through MCP.

### 6.2 State Management (ADR-011 Decision 5)

- **React Query:** Server state (memories, search results, stats)
- **Zustand:** Client state (filters, selections, UI preferences)

**Rationale:** Clear separation of concerns, minimal boilerplate.

### 6.3 Graph Library (ADR-011 Decision 4)

vis-network for graph visualization:
- Force-directed layout
- Built-in clustering for large graphs
- Handles 500+ nodes efficiently

**Rationale:** Mature, battle-tested, good performance for target scale.

---

## 7. Performance Targets

| Operation | Target Latency | Notes |
|-----------|----------------|-------|
| Memory list load | < 500ms | Paginated, server-side |
| Memory detail load | < 200ms | Single record fetch |
| Semantic search | < 2s | Includes embedding time |
| Code search | < 2s | Includes embedding time |
| Graph render (< 500 nodes) | < 1s | vis-network optimized |
| Graph render (500+ nodes) | < 3s | With clustering |

---

## 8. Development Workflow

### 8.1 Start Development

```bash
# Terminal 1: Start databases
cd docker && docker-compose up -d

# Terminal 2: Start Inspector UI (frontend + backend)
cd inspector-ui
npm install
npm run dev
```

### 8.2 Default Ports

| Service | Port | Purpose |
|---------|------|---------|
| Inspector UI (dev) | 5173 | Vite dev server |
| Inspector API | 3001 | Express backend |
| Qdrant | 6333 | Vector database |
| Neo4j Bolt | 7687 | Graph database |

---

## 9. Glossary

| Term | Definition |
|------|------------|
| Inspector | The Memory Inspector UI application |
| Memory | A stored piece of information (requirement, design, code pattern, etc.) |
| Adapter | Database access layer reused from mcp-server |
| vis-network | JavaScript graph visualization library |
| Zustand | Lightweight state management library |
| React Query | Server state management library |

---

## Appendix A: Reference Documents

| Document | Location | Purpose |
|----------|----------|---------|
| Requirements | requirement-docs/REQ-MEM-006-memory-inspector-ui.md | Source requirements |
| Architecture | project-docs/006-architecture-memory-inspector.md | System architecture |
| ADR-011 | project-docs/adrs/ADR-011-memory-inspector-architecture.md | Architecture decisions |
| MCP Server | mcp-server/ | Adapters and types to reuse |
