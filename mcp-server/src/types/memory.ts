export const MEMORY_TYPES = [
  // Documentation & Decisions
  "requirements",      // Requirements docs, user stories, acceptance criteria
  "design",            // Design docs, component designs, UI/UX specs
  "architecture",      // ADRs, architecture decisions, system design

  // Code Structure
  "component",         // Components, modules, services
  "function",          // Functions, methods, class definitions
  "code_pattern",      // Code patterns, snippets, implementations

  // Testing
  "test_result",       // Test execution results (pass/fail, coverage, duration)
  "test_history",      // Historical test trends, flaky tests, regressions

  // Runtime
  "session",           // Session state, phase completions
  "user_preference"    // User preferences and customizations
] as const;

export type MemoryType = typeof MEMORY_TYPES[number];

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

export interface Relationship {
  type: string;
  target_id: string;
}

export interface MemoryInput {
  memory_type: MemoryType;
  content: string;
  metadata?: Record<string, unknown>;
  relationships?: Relationship[];
}

export interface BulkMemoryInput {
  memories: MemoryInput[];
}

export interface SearchInput {
  query: string;
  memory_types?: MemoryType[];
  limit?: number;
  time_range?: {
    start?: string;
    end?: string;
  };
}

export interface CodeSearchInput {
  code_snippet: string;
  language?: string;
  limit?: number;
}

export interface GraphQueryInput {
  cypher: string;
  params?: Record<string, unknown>;
}

export interface IndexFileInput {
  file_path: string;
  language?: string;
}

export interface IndexDirectoryInput {
  directory_path: string;
  patterns?: string[];
  exclude_patterns?: string[];
}

export interface ExportInput {
  output_path: string;
  memory_types?: MemoryType[];
}

export interface ImportInput {
  input_path: string;
}

export interface NormalizeInput {
  phases?: string[];
}
