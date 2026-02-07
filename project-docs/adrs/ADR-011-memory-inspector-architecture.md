# ADR-011: Memory Inspector UI Architecture

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Deciders** | User |
| **Requirements** | REQ-MEM-006-FN-001 through REQ-MEM-006-FN-041 |
| **Related ADRs** | ADR-010 (TypeScript MCP Server) |

## Context

The Memory Inspector UI is a development-only web application for inspecting, searching, and managing memories stored in the Claude Code Long-Term Memory System. It needs to:

1. Browse all 8 memory types with CRUD operations
2. Perform semantic search and code search
3. Visualize memory relationships as an interactive graph
4. Provide maintenance operations (stats, normalize, export/import, indexing)

Key constraints:
- Development-only tool (no authentication needed)
- Must connect to existing Qdrant and Neo4j databases
- Must reuse existing data models and embedding logic
- Single-user, localhost operation

This ADR documents six key architectural decisions for the Memory Inspector UI.

---

## Decision 1: Monorepo Structure

### Context

The Memory Inspector needs access to type definitions and potentially adapter code from the existing MCP server. We need to decide whether to keep it in the same repository or create a separate package.

### Options Considered

#### Option 1A: Same Repository (inspector-ui/)

- **Pros**:
  - Shared TypeScript types (`Memory`, `MemoryType`, etc.)
  - Coordinated releases and versioning
  - Single repository to manage
  - Easier refactoring across boundaries
- **Cons**:
  - Larger repository
  - Different build tools (Vite vs tsc)
  - Mixed concerns in one repo

#### Option 1B: Separate NPM Package

- **Pros**:
  - Independent release lifecycle
  - Cleaner separation of concerns
  - Smaller focused repositories
- **Cons**:
  - Type duplication or complex publishing
  - Harder to coordinate breaking changes
  - More overhead for a dev-only tool

### Decision

**Option 1A: Same Repository** - Add `inspector-ui/` folder alongside `mcp-server/`.

### Rationale

The Memory Inspector is a tightly coupled companion tool to the MCP server. Sharing types ensures consistency and reduces maintenance burden. The different build tools (Vite for UI, tsc for server) work fine in a monorepo structure.

---

## Decision 2: Backend Architecture

### Context

The UI needs a backend to serve the API endpoints. The existing MCP server has well-tested adapters for Qdrant and Neo4j. We need to decide how to structure the backend.

### Options Considered

#### Option 2A: Reuse MCP Adapters

- **Pros**:
  - No code duplication
  - Guaranteed consistency with MCP behavior
  - Leverage existing tests and validation
  - Single source of truth for database logic
- **Cons**:
  - Coupling between packages
  - May need to export more from mcp-server
  - Backend and MCP server must stay compatible

#### Option 2B: Dedicated Backend with Own Adapters

- **Pros**:
  - Complete independence
  - Can optimize specifically for REST patterns
  - No coupling to MCP server internals
- **Cons**:
  - Duplicate adapter logic
  - Risk of behavior drift
  - Double maintenance burden

#### Option 2C: Direct Browser-to-Database

- **Pros**:
  - Simplest architecture (no backend)
  - Fewer moving parts
- **Cons**:
  - Security risk exposing DB ports to browser
  - No embedding generation capability
  - CORS complications
  - Cannot leverage existing Node.js adapter code

### Decision

**Option 2A: Reuse MCP Adapters** - Create an Express server in `inspector-ui/server/` that imports and wraps `QdrantAdapter`, `Neo4jAdapter`, and `VoyageClient` from `mcp-server/src/`.

### Rationale

The adapters are well-designed and battle-tested. An Express layer provides the REST API while delegating to proven code. This ensures the Inspector shows exactly what Claude Code sees through MCP.

---

## Decision 3: Frontend Framework

### Context

The frontend needs to provide a responsive, interactive UI for memory browsing, search, and graph visualization. Requirements recommend React.

### Options Considered

#### Option 3A: React 18 + Vite

- **Pros**:
  - Fast development experience (HMR, quick builds)
  - Industry standard with rich ecosystem
  - Excellent TypeScript support
  - Lightweight for dev-only tool
  - Large community and resources
- **Cons**:
  - Need to add routing manually
  - No SSR (not needed for this use case)

#### Option 3B: Next.js

- **Pros**:
  - Full-stack framework with API routes
  - SSR/SSG capabilities
  - File-based routing
- **Cons**:
  - Overkill for localhost dev tool
  - Heavier than needed
  - SSR unnecessary for single-user local app

#### Option 3C: Vue 3 + Vite

- **Pros**:
  - Simpler learning curve
  - Good Vite integration
- **Cons**:
  - Smaller ecosystem for visualization libraries
  - Team familiarity with React (existing codebase is TypeScript)

### Decision

**Option 3A: React 18 + Vite + TypeScript**

### Rationale

Vite provides excellent DX with fast HMR. React 18 offers the concurrency features and ecosystem needed for a responsive UI. TypeScript ensures type safety and enables sharing types with the backend.

---

## Decision 4: Graph Visualization Library

### Context

The Graph Explorer module (REQ-006-FN-020 through REQ-006-FN-023) requires interactive visualization of memory relationships. Requirements specify handling up to 500 nodes with sub-second rendering.

### Options Considered

#### Option 4A: vis-network

- **Pros**:
  - Mature, battle-tested library
  - Built-in clustering for large graphs
  - Stable, well-documented API
  - Good performance up to 1000+ nodes
  - Rich interaction events (click, hover, drag)
  - Hierarchical and force-directed layouts
- **Cons**:
  - Non-React native (imperative API)
  - Requires wrapper component
  - Canvas-based (not SVG)

#### Option 4B: react-force-graph

- **Pros**:
  - React-friendly API
  - 2D and 3D rendering options
  - Good performance with WebGL (3D mode)
- **Cons**:
  - Less built-in features than vis-network
  - Fewer layout algorithms
  - 3D mode overkill for this use case

#### Option 4C: Cytoscape.js

- **Pros**:
  - Academic-grade graph algorithms
  - Compound nodes support
  - Extensive layout options
- **Cons**:
  - Steeper learning curve
  - Larger bundle size
  - More complex than needed

#### Option 4D: @react-sigma (Sigma.js)

- **Pros**:
  - WebGL rendering
  - Handles very large graphs (10k+ nodes)
- **Cons**:
  - Less intuitive API
  - Overkill for 500 node target

### Decision

**Option 4A: vis-network**

### Rationale

vis-network is proven stable and handles the target scale (500 nodes) easily. Built-in clustering helps when viewing large memory sets. The imperative API is manageable with a React wrapper component. Its force-directed layout works well for relationship graphs.

---

## Decision 5: State Management

### Context

The UI needs to manage server state (memories, search results, stats) and client state (filters, selected items, UI preferences).

### Options Considered

#### Option 5A: React Query + Zustand

- **Pros**:
  - React Query: Perfect for server state (caching, refetching, loading states)
  - Zustand: Minimal boilerplate for UI state
  - Clear separation of concerns
  - Both are lightweight
- **Cons**:
  - Two libraries to learn
  - Some overlap in capabilities

#### Option 5B: React Query Alone

- **Pros**:
  - Simpler (one library)
  - May be sufficient for most state
- **Cons**:
  - Global UI state needs React Context or prop drilling
  - Awkward for non-server state (filters, selections)

#### Option 5C: Redux Toolkit + RTK Query

- **Pros**:
  - Unified state management
  - Powerful debugging tools
- **Cons**:
  - More boilerplate
  - Overkill for dev-only tool
  - Heavier than needed

### Decision

**Option 5A: React Query + Zustand**

### Rationale

React Query excels at server state (memories are fetched, cached, invalidated). Zustand provides a simple store for UI state (current filters, selected memory, sidebar state) without Redux boilerplate. Together they cover all state management needs with minimal overhead.

---

## Decision 6: UI Component Library

### Context

The UI needs consistent, accessible components for forms, tables, dialogs, and navigation. Requirements mention Shadcn/UI as a recommendation.

### Options Considered

#### Option 6A: Shadcn/UI + Tailwind CSS

- **Pros**:
  - Copy-paste components (full control over code)
  - Built on Radix UI (accessible primitives)
  - Modern, clean design
  - Tailwind for rapid styling
  - Easy to customize
- **Cons**:
  - More initial setup
  - Need to add components individually

#### Option 6B: Chakra UI

- **Pros**:
  - All-in-one component library
  - Built-in dark mode
  - Great developer experience
- **Cons**:
  - Larger bundle size
  - Less customizable
  - Runtime CSS-in-JS overhead

#### Option 6C: Ant Design

- **Pros**:
  - Rich table and form components
  - Enterprise-ready
- **Cons**:
  - Large bundle size
  - Opinionated styling hard to override
  - Chinese-first documentation

### Decision

**Option 6A: Shadcn/UI + Tailwind CSS**

### Rationale

Shadcn/UI provides accessible, customizable components without framework lock-in. Tailwind CSS enables rapid UI development. The copy-paste model means we only include components we use, keeping the bundle small. Perfect for a dev-only tool where we want control.

---

## Consequences

### Positive

1. **Code Reuse**: Sharing adapters ensures Inspector shows exactly what MCP sees
2. **Type Safety**: Shared TypeScript types prevent drift between UI and backend
3. **Fast Development**: Vite + React Query + Tailwind enable rapid iteration
4. **Proven Libraries**: vis-network and React Query are battle-tested
5. **Right-Sized**: No overkill frameworks for a dev-only tool
6. **Maintainability**: Single repo simplifies coordination

### Negative

1. **Monorepo Complexity**: Build configuration for two packages
2. **vis-network Wrapper**: Need to bridge imperative API to React
3. **Two State Libraries**: React Query + Zustand requires understanding both
4. **Coupling**: Backend depends on mcp-server internals

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| MCP server breaking changes affect Inspector | Medium | Medium | Semantic versioning, shared test suite |
| vis-network integration issues | Low | Medium | Wrapper component isolates complexity |
| Bundle size grows | Low | Low | Tree-shaking, lazy loading, only import needed Shadcn components |

---

## Implementation Notes

### Package Structure

```
claude-code-project-memory-mcp/
  mcp-server/           # Existing MCP server
    src/
      storage/          # Adapters to reuse
      types/            # Types to share
  inspector-ui/         # New UI package
    server/             # Express backend
    src/                # React frontend
    package.json
```

### Type Sharing

Export types from `mcp-server/src/types/` and import in Inspector:

```typescript
// inspector-ui/server/routes.ts
import { Memory, MemoryType } from "../../mcp-server/src/types/memory.js";
```

### vis-network React Wrapper

```typescript
// inspector-ui/src/components/GraphCanvas.tsx
import { useEffect, useRef } from "react";
import { Network } from "vis-network";

export function GraphCanvas({ nodes, edges, onNodeClick }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const networkRef = useRef<Network | null>(null);

  useEffect(() => {
    if (containerRef.current) {
      networkRef.current = new Network(containerRef.current, { nodes, edges }, options);
      networkRef.current.on("click", onNodeClick);
    }
    return () => networkRef.current?.destroy();
  }, [nodes, edges]);

  return <div ref={containerRef} className="h-full w-full" />;
}
```

---

## References

- [REQ-MEM-006 Requirements](../../requirement-docs/REQ-MEM-006-memory-inspector-ui.md)
- [ADR-010 TypeScript MCP Server](./ADR-010-typescript-mcp-server.md)
- [vis-network Documentation](https://visjs.github.io/vis-network/docs/network/)
- [React Query Documentation](https://tanstack.com/query/latest)
- [Shadcn/UI Documentation](https://ui.shadcn.com/)
- [Zustand Documentation](https://github.com/pmndrs/zustand)
