# Memory Inspector UI - Requirements Specification

| Field | Value |
|-------|-------|
| **Document ID** | REQ-MEM-006 |
| **Version** | 1.0.0 |
| **Status** | Draft |
| **Classification** | Internal |
| **Compliance** | ISO/IEC/IEEE 29148:2018 |

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Stakeholder Requirements](#2-stakeholder-requirements)
3. [System Requirements](#3-system-requirements)
4. [Interface Requirements](#4-interface-requirements)
5. [Data Requirements](#5-data-requirements)
6. [Non-Functional Requirements](#6-non-functional-requirements)
7. [Verification Requirements](#7-verification-requirements)
8. [Deployment Requirements](#8-deployment-requirements)
9. [Document Control](#9-document-control)

---

## 1. Introduction

### 1.1 Purpose

This document specifies the requirements for the Memory Inspector UI, a standalone development tool for inspecting, searching, and managing memories stored in the Claude Code Long-Term Memory System.

### 1.2 Scope

The Memory Inspector UI is a **development-only** web application that provides:

- **Memory Browser** - View and search all memory types
- **Graph Explorer** - Visualize relationships between memories
- **Code Search** - Find similar code patterns
- **Maintenance Dashboard** - System health, statistics, and operations
- **CRUD Operations** - Create, read, update, delete memories

**Out of Scope:**
- User authentication (dev-only tool)
- Multi-user support
- Production deployment
- Mobile device optimization

### 1.3 Definitions

| Term | Definition |
|------|------------|
| Memory | A stored piece of information (requirement, design, code pattern, etc.) |
| MCP | Model Context Protocol - the interface for Claude Code tools |
| Qdrant | Vector database storing memory embeddings |
| Neo4j | Graph database storing memory relationships |
| Project ID | Unique identifier isolating memory data per project |

### 1.4 References

| Reference | Description |
|-----------|-------------|
| [Quick Reference](../user-docs/quick-reference.md) | Memory service tool documentation |
| [MCP Server Design](../design-docs/005-design-npx-mcp-server.md) | TypeScript MCP server design |

### 1.5 Constraints

| Constraint | Description |
|------------|-------------|
| **C-001** | No authentication required - runs locally for development only |
| **C-002** | Must connect to existing Qdrant and Neo4j databases |
| **C-003** | Must support project ID isolation |
| **C-004** | Single-user operation only |

---

## 2. Stakeholder Requirements

### 2.1 Stakeholder Identification

#### STK-006-001: Developer

**Role:** Software Developer using Claude Code
**Responsibilities:**
- Building applications with Claude Code assistance
- Managing project memory across sessions
- Debugging memory-related issues
- Maintaining memory data quality

**Goals:**
- Quick visibility into stored memories
- Easy search for existing patterns
- Understanding memory relationships
- Maintaining clean memory state

### 2.2 Stakeholder Needs

#### STK-006-010: Memory Visibility

**Priority:** Must Have
**Stakeholder:** STK-006-001

Developers need to see what memories exist for their project, including content, metadata, and relationships.

**Success Criteria:**
1. Browse all memory types in a unified interface
2. View full memory content and metadata
3. See relationships to other memories
4. Filter and sort by any field

#### STK-006-011: Pattern Discovery

**Priority:** Must Have
**Stakeholder:** STK-006-001

Developers need to find existing code patterns and designs to ensure consistency across the codebase.

**Success Criteria:**
1. Semantic search across all memories
2. Code-specific search with language filtering
3. Similarity detection for new code
4. Quick access to related patterns

#### STK-006-012: Memory Maintenance

**Priority:** Should Have
**Stakeholder:** STK-006-001

Developers need to maintain memory quality by identifying duplicates, orphans, and outdated entries.

**Success Criteria:**
1. View system health metrics
2. Identify and remove duplicates
3. Find orphaned memories
4. Export/import for backup

#### STK-006-013: Relationship Understanding

**Priority:** Should Have
**Stakeholder:** STK-006-001

Developers need to understand how memories relate to each other (requirements to code, designs to implementations).

**Success Criteria:**
1. Visual graph of memory relationships
2. Trace requirements to implementations
3. See what follows a pattern
4. Navigate between related memories

---

## 3. System Requirements

### 3.1 System Context

The Memory Inspector UI operates as a standalone web application connecting directly to the memory databases.

```
┌─────────────────────────────────────────────────────────────┐
│                    Memory Inspector UI                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Web Application (SPA)                    │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────────┐   │   │
│  │  │ Memory  │ │  Code   │ │  Graph  │ │ Mainten-  │   │   │
│  │  │ Browser │ │ Search  │ │ Explorer│ │   ance    │   │   │
│  │  └────┬────┘ └────┬────┘ └────┬────┘ └─────┬─────┘   │   │
│  │       └───────────┴───────────┴────────────┘         │   │
│  │                        │                              │   │
│  │  ┌─────────────────────┴──────────────────────────┐  │   │
│  │  │              Backend API (Express)              │  │   │
│  │  └─────────────────────┬──────────────────────────┘  │   │
│  └────────────────────────┼─────────────────────────────┘   │
│                           │                                  │
└───────────────────────────┼──────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│    Qdrant     │   │    Neo4j      │   │    Voyage     │
│ (Vectors/Data)│   │   (Graph)     │   │ (Embeddings)  │
│ localhost:6333│   │ localhost:7687│   │    API        │
└───────────────┘   └───────────────┘   └───────────────┘
```

### 3.2 Functional Requirements

#### 3.2.1 Memory Browser Module

##### REQ-006-FN-001: Memory Type Navigation

| Attribute | Value |
|-----------|-------|
| **Priority** | Must Have |
| **Component** | Memory Browser |
| **Traces To** | STK-006-010 |

The system shall provide navigation between all 8 memory types.

**Acceptance Criteria:**
1. Sidebar displays all memory types with counts
2. Clicking a type shows memories of that type
3. "All Memories" option shows unified view
4. Counts update after CRUD operations

##### REQ-006-FN-002: Memory List View

| Attribute | Value |
|-----------|-------|
| **Priority** | Must Have |
| **Component** | Memory Browser |
| **Traces To** | STK-006-010 |

The system shall display memories in a paginated list with key information.

**Acceptance Criteria:**
1. Table view with columns: ID (truncated), Type, Title/Summary, Created, Updated
2. Pagination with configurable page size (10, 25, 50, 100)
3. Sort by any column (ascending/descending)
4. Click row to open detail view
5. Checkbox selection for bulk operations

##### REQ-006-FN-003: Memory Detail View

| Attribute | Value |
|-----------|-------|
| **Priority** | Must Have |
| **Component** | Memory Browser |
| **Traces To** | STK-006-010 |

The system shall display full memory details in a detail panel.

**Acceptance Criteria:**
1. Full content displayed with syntax highlighting for code
2. All metadata fields shown in key-value format
3. Relationships section showing linked memories
4. Edit and Delete buttons
5. Copy ID to clipboard button
6. Navigate to related memories via links

##### REQ-006-FN-004: Memory Filtering

| Attribute | Value |
|-----------|-------|
| **Priority** | Must Have |
| **Component** | Memory Browser |
| **Traces To** | STK-006-010 |

The system shall support filtering memories by various criteria.

**Acceptance Criteria:**
1. Filter by memory type (multi-select)
2. Filter by date range (created/updated)
3. Filter by metadata field values
4. Text search within content
5. Active filters shown as chips with remove option
6. Clear all filters button

##### REQ-006-FN-005: Memory Creation

| Attribute | Value |
|-----------|-------|
| **Priority** | Must Have |
| **Component** | Memory Browser |
| **Traces To** | STK-006-010 |

The system shall allow creating new memories.

**Acceptance Criteria:**
1. "New Memory" button opens creation form
2. Memory type dropdown (required)
3. Content field with syntax highlighting
4. Dynamic metadata fields based on type
5. Optional relationship linking
6. Validation before submission
7. Success/error notification

##### REQ-006-FN-006: Memory Editing

| Attribute | Value |
|-----------|-------|
| **Priority** | Must Have |
| **Component** | Memory Browser |
| **Traces To** | STK-006-010 |

The system shall allow editing existing memories.

**Acceptance Criteria:**
1. Edit button in detail view
2. Form pre-populated with current values
3. Content editable with syntax highlighting
4. Metadata fields editable
5. Relationships can be added/removed
6. Save and Cancel buttons
7. Confirmation dialog for unsaved changes

##### REQ-006-FN-007: Memory Deletion

| Attribute | Value |
|-----------|-------|
| **Priority** | Must Have |
| **Component** | Memory Browser |
| **Traces To** | STK-006-010 |

The system shall allow deleting memories.

**Acceptance Criteria:**
1. Delete button in detail view
2. Bulk delete for selected memories
3. Confirmation dialog with memory preview
4. Soft delete by default
5. Option for hard delete with warning
6. Success notification with undo option (soft delete only)

#### 3.2.2 Search Module

##### REQ-006-FN-010: Semantic Search

| Attribute | Value |
|-----------|-------|
| **Priority** | Must Have |
| **Component** | Search |
| **Traces To** | STK-006-011 |

The system shall support semantic search across all memories.

**Acceptance Criteria:**
1. Search bar prominently displayed
2. Natural language query input
3. Optional memory type filter
4. Optional date range filter
5. Results ranked by relevance score
6. Result count displayed
7. Click result to navigate to detail view

##### REQ-006-FN-011: Code Search

| Attribute | Value |
|-----------|-------|
| **Priority** | Must Have |
| **Component** | Search |
| **Traces To** | STK-006-011 |

The system shall support code-specific search.

**Acceptance Criteria:**
1. Code search tab/mode
2. Code input area with syntax highlighting
3. Language filter dropdown
4. Similarity threshold slider (0.70-0.95)
5. Results show matching code with similarity score
6. Diff view highlighting similarities

##### REQ-006-FN-012: Duplicate Detection

| Attribute | Value |
|-----------|-------|
| **Priority** | Should Have |
| **Component** | Search |
| **Traces To** | STK-006-011 |

The system shall identify potential duplicate memories.

**Acceptance Criteria:**
1. "Find Duplicates" button/mode
2. Input content to check
3. Select memory type
4. Configurable similarity threshold
5. Results show potential duplicates with scores
6. Quick action to view or delete duplicates

#### 3.2.3 Graph Explorer Module

##### REQ-006-FN-020: Graph Visualization

| Attribute | Value |
|-----------|-------|
| **Priority** | Should Have |
| **Component** | Graph Explorer |
| **Traces To** | STK-006-013 |

The system shall visualize memory relationships as an interactive graph.

**Acceptance Criteria:**
1. Force-directed graph layout
2. Nodes represent memories (colored by type)
3. Edges represent relationships (labeled by type)
4. Click node to show details panel
5. Zoom and pan controls
6. Node search/highlight

##### REQ-006-FN-021: Relationship Filtering

| Attribute | Value |
|-----------|-------|
| **Priority** | Should Have |
| **Component** | Graph Explorer |
| **Traces To** | STK-006-013 |

The system shall support filtering the graph by relationship types.

**Acceptance Criteria:**
1. Relationship type checkboxes (SATISFIES, IMPLEMENTS, CALLS, etc.)
2. Memory type filter
3. Depth control (1-5 levels)
4. Show/hide orphan nodes toggle
5. Filter updates graph in real-time

##### REQ-006-FN-022: Requirement Tracing

| Attribute | Value |
|-----------|-------|
| **Priority** | Should Have |
| **Component** | Graph Explorer |
| **Traces To** | STK-006-013 |

The system shall trace requirements to their implementations.

**Acceptance Criteria:**
1. Select requirement from dropdown or search
2. Show implementing components
3. Show verifying tests
4. Coverage indicator (implemented/tested)
5. Highlight trace path in graph

##### REQ-006-FN-023: Cypher Query Interface

| Attribute | Value |
|-----------|-------|
| **Priority** | Could Have |
| **Component** | Graph Explorer |
| **Traces To** | STK-006-013 |

The system shall allow custom Cypher queries (read-only).

**Acceptance Criteria:**
1. Cypher query editor with syntax highlighting
2. Query history dropdown
3. Execute button with loading indicator
4. Results displayed in table and graph views
5. Read-only validation (reject writes)
6. Error messages for invalid queries

#### 3.2.4 Maintenance Module

##### REQ-006-FN-030: System Statistics

| Attribute | Value |
|-----------|-------|
| **Priority** | Must Have |
| **Component** | Maintenance |
| **Traces To** | STK-006-012 |

The system shall display memory system statistics.

**Acceptance Criteria:**
1. Memory counts by type (table and chart)
2. Total storage used
3. Qdrant collection status
4. Neo4j node/relationship counts
5. Last indexed timestamp
6. Refresh button with timestamp

##### REQ-006-FN-031: Normalization Operations

| Attribute | Value |
|-----------|-------|
| **Priority** | Should Have |
| **Component** | Maintenance |
| **Traces To** | STK-006-012 |

The system shall support memory normalization operations.

**Acceptance Criteria:**
1. Phase selection checkboxes (dedup, orphan_detection, cleanup, etc.)
2. Dry run toggle
3. Run button with confirmation
4. Progress indicator during operation
5. Results summary on completion
6. Job history with status

##### REQ-006-FN-032: Export/Import

| Attribute | Value |
|-----------|-------|
| **Priority** | Should Have |
| **Component** | Maintenance |
| **Traces To** | STK-006-012 |

The system shall support exporting and importing memories.

**Acceptance Criteria:**
1. Export: select memory types, specify filename
2. Export format: JSONL
3. Download button for export file
4. Import: file upload or path input
5. Conflict resolution dropdown (skip, overwrite, error)
6. Import preview showing count and types
7. Progress indicator during import

##### REQ-006-FN-033: Indexing Management

| Attribute | Value |
|-----------|-------|
| **Priority** | Should Have |
| **Component** | Maintenance |
| **Traces To** | STK-006-012 |

The system shall manage codebase indexing.

**Acceptance Criteria:**
1. Index single file: path input, language detection
2. Index directory: path, extensions filter, exclude patterns
3. Reindex: directory path, scope (full/changed)
4. Index job status display
5. Cancel running index job
6. Last indexed files list

#### 3.2.5 Configuration Module

##### REQ-006-FN-040: Project Selection

| Attribute | Value |
|-----------|-------|
| **Priority** | Must Have |
| **Component** | Configuration |
| **Traces To** | C-003 |

The system shall allow selecting the active project.

**Acceptance Criteria:**
1. Project ID input field
2. Recently used projects dropdown
3. Apply button to switch projects
4. Current project displayed in header
5. Warning when switching with unsaved changes

##### REQ-006-FN-041: Connection Configuration

| Attribute | Value |
|-----------|-------|
| **Priority** | Must Have |
| **Component** | Configuration |
| **Traces To** | C-002 |

The system shall allow configuring database connections.

**Acceptance Criteria:**
1. Qdrant URL input (default: localhost:6333)
2. Neo4j URI input (default: bolt://localhost:7687)
3. Neo4j credentials inputs
4. Voyage API key input (masked)
5. Test connection buttons
6. Save configuration locally

---

## 4. Interface Requirements

### 4.1 User Interfaces

#### REQ-006-INT-UI-001: Main Layout

| Attribute | Value |
|-----------|-------|
| **Priority** | Must Have |
| **Component** | All |

The application shall use a consistent layout structure.

**Interface Elements:**
- **Header:** Logo, project selector, settings button
- **Sidebar:** Navigation for modules (Browser, Search, Graph, Maintenance)
- **Main Content:** Module-specific content area
- **Detail Panel:** Slide-out panel for memory details (right side)
- **Footer:** Status bar with connection indicators

#### REQ-006-INT-UI-002: Memory Browser Interface

| Attribute | Value |
|-----------|-------|
| **Priority** | Must Have |
| **Component** | Memory Browser |

**Interface Elements:**
- Left sidebar: Memory type list with counts
- Toolbar: Search, Filter, Sort, New Memory, Bulk Actions
- Main area: Memory list table
- Right panel: Selected memory detail (collapsible)

#### REQ-006-INT-UI-003: Search Interface

| Attribute | Value |
|-----------|-------|
| **Priority** | Must Have |
| **Component** | Search |

**Interface Elements:**
- Search bar: Large, prominent, with search button
- Tabs: Semantic Search, Code Search, Duplicate Detection
- Filters panel: Type, date range, advanced options
- Results area: List with relevance scores
- Preview panel: Quick view of selected result

#### REQ-006-INT-UI-004: Graph Explorer Interface

| Attribute | Value |
|-----------|-------|
| **Priority** | Should Have |
| **Component** | Graph Explorer |

**Interface Elements:**
- Graph canvas: Interactive visualization area
- Controls: Zoom, pan, reset, layout options
- Filter panel: Relationship types, memory types, depth
- Details panel: Selected node information
- Legend: Node/edge type colors

#### REQ-006-INT-UI-005: Maintenance Interface

| Attribute | Value |
|-----------|-------|
| **Priority** | Should Have |
| **Component** | Maintenance |

**Interface Elements:**
- Statistics cards: Counts, storage, health
- Operations panel: Normalize, Export, Import tabs
- Job history table: Recent operations with status
- Index management section: File/directory indexing

### 4.2 API Interfaces

#### REQ-006-INT-API-001: Backend API

| Attribute | Value |
|-----------|-------|
| **Priority** | Must Have |
| **Component** | Backend |

REST API for frontend operations.

**Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| **Memories** | | |
| GET | `/api/memories` | List memories (paginated, filtered) |
| GET | `/api/memories/:type/:id` | Get memory by type and ID |
| POST | `/api/memories` | Create memory |
| PUT | `/api/memories/:type/:id` | Update memory |
| DELETE | `/api/memories/:type/:id` | Delete memory |
| **Search** | | |
| POST | `/api/search` | Semantic search |
| POST | `/api/search/code` | Code similarity search |
| POST | `/api/search/duplicates` | Find duplicates |
| **Graph** | | |
| GET | `/api/graph/related/:id` | Get related entities |
| POST | `/api/graph/query` | Execute Cypher query |
| GET | `/api/graph/trace/:reqId` | Trace requirement |
| **Maintenance** | | |
| GET | `/api/stats` | Get statistics |
| POST | `/api/normalize` | Run normalization |
| GET | `/api/normalize/:jobId` | Get job status |
| POST | `/api/export` | Export memories |
| POST | `/api/import` | Import memories |
| **Indexing** | | |
| POST | `/api/index/file` | Index single file |
| POST | `/api/index/directory` | Index directory |
| POST | `/api/reindex` | Reindex |
| GET | `/api/index/status/:jobId` | Index job status |
| **Configuration** | | |
| GET | `/api/config` | Get configuration |
| PUT | `/api/config` | Update configuration |
| POST | `/api/config/test` | Test connections |

---

## 5. Data Requirements

### 5.1 Data Sources

#### REQ-006-DATA-001: Qdrant Integration

| Attribute | Value |
|-----------|-------|
| **Priority** | Must Have |
| **Component** | Backend |

The system shall connect to Qdrant for memory data and embeddings.

**Requirements:**
1. Read points from project-specific collections
2. Support filtering by metadata
3. Support vector similarity search
4. Handle pagination for large result sets

#### REQ-006-DATA-002: Neo4j Integration

| Attribute | Value |
|-----------|-------|
| **Priority** | Must Have |
| **Component** | Backend |

The system shall connect to Neo4j for relationship data.

**Requirements:**
1. Read nodes and relationships
2. Execute read-only Cypher queries
3. Support graph traversal queries
4. Filter by project ID

#### REQ-006-DATA-003: Local Configuration Storage

| Attribute | Value |
|-----------|-------|
| **Priority** | Must Have |
| **Component** | Frontend |

The system shall persist configuration locally.

**Stored Data:**
- Database connection settings
- Recent project IDs
- UI preferences (page size, column visibility)
- Search history

**Storage:** Browser localStorage or file-based config

---

## 6. Non-Functional Requirements

### 6.1 Performance Requirements

#### REQ-006-NFR-PERF-001: Response Time

| Attribute | Value |
|-----------|-------|
| **Priority** | Should Have |
| **Component** | All |

The system shall respond within acceptable latency.

| Operation | Target |
|-----------|--------|
| Memory list load | < 500ms |
| Memory detail load | < 200ms |
| Semantic search | < 2s |
| Code search | < 2s |
| Graph render (< 500 nodes) | < 1s |

#### REQ-006-NFR-PERF-002: Memory List Pagination

| Attribute | Value |
|-----------|-------|
| **Priority** | Must Have |
| **Component** | Memory Browser |

The system shall handle large memory sets efficiently.

**Requirements:**
1. Server-side pagination
2. Virtual scrolling for large pages
3. Maximum 100 items per page
4. Total count without full scan

### 6.2 Usability Requirements

#### REQ-006-NFR-USE-001: Keyboard Navigation

| Attribute | Value |
|-----------|-------|
| **Priority** | Should Have |
| **Component** | All |

The system shall support keyboard navigation.

**Requirements:**
1. Tab navigation between elements
2. Enter to activate buttons/links
3. Escape to close dialogs/panels
4. Arrow keys for list navigation
5. Keyboard shortcuts for common actions (Ctrl+S save, Ctrl+F search)

#### REQ-006-NFR-USE-002: Dark/Light Theme

| Attribute | Value |
|-----------|-------|
| **Priority** | Could Have |
| **Component** | All |

The system shall support dark and light themes.

**Requirements:**
1. System preference detection
2. Manual toggle in settings
3. Persist preference

### 6.3 Compatibility Requirements

#### REQ-006-NFR-COMP-001: Browser Support

| Attribute | Value |
|-----------|-------|
| **Priority** | Must Have |
| **Component** | Frontend |

The system shall support modern browsers.

| Browser | Minimum Version |
|---------|-----------------|
| Chrome | 90+ |
| Firefox | 88+ |
| Safari | 14+ |
| Edge | 90+ |

### 6.4 Security Requirements

#### REQ-006-NFR-SEC-001: No Authentication

| Attribute | Value |
|-----------|-------|
| **Priority** | Must Have |
| **Component** | All |
| **Traces To** | C-001 |

The system shall operate without authentication.

**Requirements:**
1. No login required
2. No session management
3. Runs on localhost only
4. Warning banner if accessed from non-localhost

#### REQ-006-NFR-SEC-002: Read-Only Cypher

| Attribute | Value |
|-----------|-------|
| **Priority** | Must Have |
| **Component** | Graph Explorer |

Custom Cypher queries shall be validated as read-only.

**Requirements:**
1. Block CREATE, MERGE, DELETE, SET, REMOVE operations
2. Validate query before execution
3. Timeout long-running queries (30s default)

---

## 7. Verification Requirements

### 7.1 Testing Requirements

#### REQ-006-VER-001: Unit Test Coverage

| Attribute | Value |
|-----------|-------|
| **Priority** | Should Have |
| **Component** | All |

| Component | Coverage Target |
|-----------|-----------------|
| Backend API | 70% |
| Frontend Components | 60% |

#### REQ-006-VER-002: Integration Testing

| Attribute | Value |
|-----------|-------|
| **Priority** | Should Have |
| **Component** | Backend |

**Requirements:**
1. API endpoint tests against real databases (Docker)
2. Search functionality validation
3. CRUD operations verification
4. Error handling tests

#### REQ-006-VER-003: E2E Testing

| Attribute | Value |
|-----------|-------|
| **Priority** | Could Have |
| **Component** | Frontend |

**Requirements:**
1. Critical user flows tested
2. Browser automation (Playwright/Cypress)
3. Visual regression for key pages

---

## 8. Deployment Requirements

### 8.1 Environment Requirements

#### REQ-006-DEP-001: Development Deployment

| Attribute | Value |
|-----------|-------|
| **Priority** | Must Have |
| **Environment** | Development |

The system shall run as a local development tool.

**Requirements:**
1. Single command startup (npm run dev or similar)
2. Hot reload for development
3. No external dependencies beyond databases
4. Default to localhost:3000 (configurable)

#### REQ-006-DEP-002: Database Prerequisites

| Attribute | Value |
|-----------|-------|
| **Priority** | Must Have |
| **Environment** | All |

The system requires running database instances.

**Prerequisites:**
1. Qdrant running on localhost:6333
2. Neo4j running on localhost:7687
3. Valid Voyage API key for embeddings
4. Docker Compose available for quick setup

### 8.2 Technology Stack

#### REQ-006-DEP-010: Frontend Technology

| Attribute | Value |
|-----------|-------|
| **Priority** | Must Have |
| **Component** | Frontend |

**Recommended Stack:**
- Framework: React 18+ with TypeScript
- Build: Vite
- UI Components: Shadcn/UI or Radix UI
- Styling: Tailwind CSS
- State: React Query + Zustand
- Graph: vis-network or react-force-graph

#### REQ-006-DEP-011: Backend Technology

| Attribute | Value |
|-----------|-------|
| **Priority** | Must Have |
| **Component** | Backend |

**Recommended Stack:**
- Runtime: Node.js 18+
- Framework: Express or Fastify
- Language: TypeScript
- Database clients: @qdrant/js-client-rest, neo4j-driver
- Embeddings: Voyage AI SDK

---

## 9. Document Control

### 9.1 Revision History

| Version | Author | Changes |
|---------|--------|---------|
| 1.0.0 | Claude | Initial requirements document |

### 9.2 Requirement Summary

| Category | Must Have | Should Have | Could Have | Total |
|----------|-----------|-------------|------------|-------|
| Functional | 13 | 9 | 1 | 23 |
| Interface | 5 | 2 | 0 | 7 |
| Data | 3 | 0 | 0 | 3 |
| Non-Functional | 4 | 3 | 1 | 8 |
| Verification | 0 | 2 | 1 | 3 |
| Deployment | 2 | 0 | 0 | 2 |
| **Total** | **27** | **16** | **3** | **46** |

### 9.3 Traceability Matrix

| Requirement | Stakeholder Need | Constraint |
|-------------|------------------|------------|
| REQ-006-FN-001 to FN-007 | STK-006-010 | - |
| REQ-006-FN-010 to FN-012 | STK-006-011 | - |
| REQ-006-FN-020 to FN-023 | STK-006-013 | - |
| REQ-006-FN-030 to FN-033 | STK-006-012 | - |
| REQ-006-FN-040 | - | C-003 |
| REQ-006-FN-041 | - | C-002 |
| REQ-006-NFR-SEC-001 | - | C-001, C-004 |
