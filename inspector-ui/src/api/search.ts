/**
 * Search API
 *
 * API functions for search operations.
 */
import { post } from './client';
import type { SearchResponse, CodeSearchResponse, DuplicateResponse, MemoryType } from '@/types';

export interface SemanticSearchParams {
  query: string;
  types?: MemoryType[];
  limit?: number;
  dateRange?: {
    start?: string;
    end?: string;
  };
}

export interface CodeSearchParams {
  code: string;
  language?: string;
  threshold?: number;
  limit?: number;
}

export interface DuplicateSearchParams {
  content: string;
  type: string;
  threshold?: number;
  excludeId?: string;
}

export async function semanticSearch(params: SemanticSearchParams): Promise<SearchResponse> {
  return post<SearchResponse>('/api/search', params);
}

export async function codeSearch(params: CodeSearchParams): Promise<CodeSearchResponse> {
  return post<CodeSearchResponse>('/api/search/code', params);
}

export async function findDuplicates(params: DuplicateSearchParams): Promise<DuplicateResponse> {
  return post<DuplicateResponse>('/api/search/duplicates', params);
}
