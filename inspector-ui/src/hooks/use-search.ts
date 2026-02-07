/**
 * Search Hooks
 *
 * React Query hooks for search operations.
 */
import { useMutation } from '@tanstack/react-query';
import * as api from '@/api/search';
import type { MemoryType } from '@/types';

/**
 * Semantic search
 */
export function useSemanticSearch() {
  return useMutation({
    mutationFn: (params: {
      query: string;
      types?: MemoryType[];
      limit?: number;
      dateRange?: { start?: string; end?: string };
    }) => api.semanticSearch(params)
  });
}

/**
 * Code similarity search
 */
export function useCodeSearch() {
  return useMutation({
    mutationFn: (params: {
      code: string;
      language?: string;
      threshold?: number;
      limit?: number;
    }) => api.codeSearch(params)
  });
}

/**
 * Duplicate detection
 */
export function useDuplicateSearch() {
  return useMutation({
    mutationFn: (params: {
      content: string;
      type: string;
      threshold?: number;
      excludeId?: string;
    }) => api.findDuplicates(params)
  });
}
