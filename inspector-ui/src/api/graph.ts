/**
 * Graph API
 *
 * API functions for graph operations.
 */
import { get, post } from './client';
import type { GraphData, RequirementTrace } from '@/types';

export interface GraphOverviewParams {
  types?: string;
  limit?: number;
  relationshipTypes?: string;
}

export interface RelatedNodesParams {
  depth?: number;
  types?: string;
  relationshipTypes?: string;
}

export interface CypherQueryParams {
  cypher: string;
  params?: Record<string, unknown>;
}

export interface CypherQueryResponse {
  columns: string[];
  rows: Record<string, unknown>[];
  rowCount: number;
  duration: number;
  graph: GraphData;
}

export async function getGraphOverview(params?: GraphOverviewParams): Promise<GraphData> {
  return get<GraphData>('/api/graph/overview', params as Record<string, string | number | undefined>);
}

export async function getRelatedNodes(
  id: string,
  params?: RelatedNodesParams
): Promise<{ sourceId: string } & GraphData> {
  return get<{ sourceId: string } & GraphData>(
    `/api/graph/related/${id}`,
    params as Record<string, string | number | undefined>
  );
}

export async function traceRequirement(reqId: string): Promise<RequirementTrace> {
  return get<RequirementTrace>(`/api/graph/trace/${encodeURIComponent(reqId)}`);
}

export async function executeCypher(params: CypherQueryParams): Promise<CypherQueryResponse> {
  return post<CypherQueryResponse>('/api/graph/query', params);
}
