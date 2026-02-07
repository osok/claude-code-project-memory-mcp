/**
 * Frontend Type Definitions
 *
 * Types for the Memory Inspector UI.
 */

// Memory types from mcp-server (must match mcp-server/src/types/memory.ts)
export const MEMORY_TYPES = [
  // Documentation & Decisions
  'requirements',      // Requirements docs, user stories, acceptance criteria
  'design',            // Design docs, component designs, UI/UX specs
  'architecture',      // ADRs, architecture decisions, system design

  // Code Structure
  'component',         // Components, modules, services
  'function',          // Functions, methods, class definitions
  'code_pattern',      // Code patterns, snippets, implementations

  // Testing
  'test_result',       // Test execution results (pass/fail, coverage, duration)
  'test_history',      // Historical test trends, flaky tests, regressions

  // Runtime
  'session',           // Session state, phase completions
  'user_preference'    // User preferences and customizations
] as const;

export type MemoryType = typeof MEMORY_TYPES[number];

// Memory interface
export interface Memory {
  memory_id: string;
  type: MemoryType;
  content: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  deleted: boolean;
  project_id: string;
}

// API Response types
export interface MemoryListResponse {
  memories: Memory[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

export interface SearchResult {
  memory: Memory;
  score: number;
  highlights?: string[];
}

export interface CodeSearchResult extends SearchResult {
  filePath?: string;
  functionName?: string;
  language?: string;
}

export interface SearchResponse {
  results: SearchResult[];
  count: number;
  duration: number;
}

export interface CodeSearchResponse {
  results: CodeSearchResult[];
  count: number;
  duration: number;
  threshold: number;
}

export interface DuplicateResult {
  memory: Memory;
  score: number;
  similarity: string;
}

export interface DuplicateResponse {
  duplicates: DuplicateResult[];
  count: number;
  duration: number;
  threshold: number;
}

// Graph types
export interface GraphNode {
  id: string;
  label: string;
  type: MemoryType | string;
  metadata: Record<string, unknown>;
  distance?: number;
}

export interface GraphEdge {
  id: string;
  from: string;
  to: string;
  label: string;
  type: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface RequirementTrace {
  requirement: {
    id: string;
    requirementId: string;
    content: string;
    metadata: Record<string, unknown>;
  };
  implementations: Array<{
    id: string;
    type: string;
    label: string;
    metadata: Record<string, unknown>;
  }>;
  tests: Array<{
    id: string;
    type: string;
    label: string;
    metadata: Record<string, unknown>;
  }>;
  coverage: {
    implementedCount: number;
    testedCount: number;
    hasImplementation: boolean;
    hasCoverage: boolean;
  };
}

// Stats types
export interface StatsResponse {
  projectId: string;
  counts: {
    total: number;
    byType: Record<MemoryType, number>;
  };
  connections: {
    qdrant: {
      status: 'connected' | 'disconnected' | 'error';
      url: string;
    };
    neo4j: {
      status: 'connected' | 'disconnected' | 'error';
      uri: string;
      nodeCount: number;
      relationshipCount: number;
    };
  };
  storage: {
    estimatedMB: number;
  };
  timestamp: string;
}

// Job status types
export interface JobStatus {
  id: string;
  status: 'pending' | 'running' | 'complete' | 'failed';
  startedAt: string;
  completedAt?: string;
  error?: string;
}

export interface NormalizeJobStatus extends JobStatus {
  phases: string[];
  dryRun: boolean;
  results: Array<{
    phase: string;
    count: number;
    details: string[];
  }>;
}

export interface IndexJobStatus extends JobStatus {
  type: 'file' | 'directory' | 'reindex';
  path: string;
  filesProcessed: number;
  filesTotal: number;
  errors: string[];
}

// Filter types
export interface FilterState {
  types: MemoryType[];
  dateRange: {
    start?: string;
    end?: string;
  };
  searchText: string;
  metadata: Record<string, string>;
}

// Pagination types
export interface PaginationState {
  page: number;
  pageSize: number;
  sort: 'created_at' | 'updated_at';
  order: 'asc' | 'desc';
}

// Config types
export interface ConfigResponse {
  projectId: string;
  connections: {
    qdrant: { url: string };
    neo4j: { uri: string; user: string; hasPassword: boolean };
    voyage: { hasApiKey: boolean };
  };
  ui: {
    defaultPageSize: number;
    maxPageSize: number;
    theme: string;
  };
}

// Memory input for create/update
export interface MemoryInput {
  type: MemoryType;
  content: string;
  metadata?: Record<string, unknown>;
  relationships?: Array<{
    targetId: string;
    type: string;
  }>;
}
