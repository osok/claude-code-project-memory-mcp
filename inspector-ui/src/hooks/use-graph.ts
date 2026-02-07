/**
 * Graph Hooks
 *
 * React Query hooks for graph operations.
 */
import { useQuery, useMutation } from '@tanstack/react-query';
import * as api from '@/api/graph';

export interface GraphFilters {
  types?: string[];
  relationshipTypes?: string[];
  limit?: number;
}

/**
 * Get graph overview
 */
export function useGraphOverview(filters?: GraphFilters) {
  return useQuery({
    queryKey: ['graph', 'overview', filters],
    queryFn: () => api.getGraphOverview({
      types: filters?.types?.join(','),
      relationshipTypes: filters?.relationshipTypes?.join(','),
      limit: filters?.limit
    })
  });
}

/**
 * Get related nodes for a specific memory
 */
export function useRelatedNodes(nodeId: string, depth: number = 2) {
  return useQuery({
    queryKey: ['graph', 'related', nodeId, depth],
    queryFn: () => api.getRelatedNodes(nodeId, { depth }),
    enabled: !!nodeId
  });
}

/**
 * Trace a requirement through implementations and tests
 */
export function useRequirementTrace(reqId: string) {
  return useQuery({
    queryKey: ['graph', 'trace', reqId],
    queryFn: () => api.traceRequirement(reqId),
    enabled: !!reqId
  });
}

/**
 * Execute custom Cypher query
 */
export function useCypherQuery() {
  return useMutation({
    mutationFn: (params: { cypher: string; params?: Record<string, unknown> }) =>
      api.executeCypher(params)
  });
}
