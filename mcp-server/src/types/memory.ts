export const MEMORY_TYPES = [
  "requirements",
  "design",
  "code_pattern",
  "component",
  "function",
  "test_history",
  "session",
  "user_preference"
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
