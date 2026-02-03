export * from "./memory.js";

export interface Point {
  id: string;
  vector: number[];
  payload: Record<string, unknown>;
}

export interface SearchParams {
  collections: string[];
  vector: number[];
  limit: number;
  filter?: {
    must?: Array<{
      key: string;
      match: { value: unknown };
    }>;
  };
}

export interface SearchResult {
  id: string;
  score: number;
  payload: Record<string, unknown>;
}
