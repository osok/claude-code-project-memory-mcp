/**
 * Stats and Maintenance API
 *
 * API functions for statistics, normalization, export/import, and indexing.
 */
import { get, post, del } from './client';
import type { StatsResponse, NormalizeJobStatus, IndexJobStatus, ConfigResponse, Memory } from '@/types';

// Stats
export async function getStats(): Promise<StatsResponse> {
  return get<StatsResponse>('/api/stats');
}

// Normalization
export interface NormalizeParams {
  phases?: ('dedup' | 'orphan_detection' | 'cleanup' | 'embedding_refresh')[];
  dryRun?: boolean;
}

export async function startNormalize(params?: NormalizeParams): Promise<{ jobId: string; status: string }> {
  return post('/api/normalize', params || {});
}

export async function getNormalizeStatus(jobId: string): Promise<NormalizeJobStatus> {
  return get<NormalizeJobStatus>(`/api/normalize/${jobId}`);
}

// Export/Import
export interface ExportParams {
  types?: string[];
  includeDeleted?: boolean;
}

export async function exportMemories(params?: ExportParams): Promise<string> {
  return post<string>('/api/export', params || {});
}

export interface ImportParams {
  memories: Array<{
    type: string;
    content: string;
    metadata?: Record<string, unknown>;
    memory_id?: string;
    created_at?: string;
  }>;
  conflictResolution?: 'skip' | 'overwrite' | 'error';
}

export interface ImportResult {
  success: boolean;
  results: {
    imported: number;
    skipped: number;
    errors: string[];
  };
}

export async function importMemories(params: ImportParams): Promise<ImportResult> {
  return post<ImportResult>('/api/import/import', params);
}

// Indexing
export interface IndexFileParams {
  path: string;
  language?: string;
}

export interface IndexFileResult {
  success: boolean;
  memoryId: string;
  type: string;
  language: string;
  path: string;
  size: number;
}

export async function indexFile(params: IndexFileParams): Promise<IndexFileResult> {
  return post<IndexFileResult>('/api/index/file', params);
}

export interface IndexDirectoryParams {
  path: string;
  patterns?: string[];
  excludePatterns?: string[];
}

export async function indexDirectory(params: IndexDirectoryParams): Promise<{ jobId: string; status: string }> {
  return post('/api/index/directory', params);
}

export interface ReindexParams {
  path: string;
  scope?: 'full' | 'changed';
}

export async function reindex(params: ReindexParams): Promise<{ jobId: string; status: string }> {
  return post('/api/index/reindex', params);
}

export async function getIndexStatus(jobId: string): Promise<IndexJobStatus> {
  return get<IndexJobStatus>(`/api/index/status/${jobId}`);
}

export async function cancelIndex(jobId: string): Promise<{ success: boolean; jobId: string }> {
  return del<{ success: boolean; jobId: string }>(`/api/index/cancel/${jobId}`);
}

// Test Result Cleanup (REQ-007-FN-062)
export interface TestResultCleanupParams {
  suiteName?: string;
  suiteId?: string;
  olderThanDays?: number;
  keepCount?: number;
  dryRun?: boolean;
}

export interface TestResultCleanupResult {
  status: 'complete' | 'dry_run';
  cleaned_count: number;
  details: string[];
  params: {
    suite_name?: string;
    suite_id?: string;
    older_than_days: number;
    keep_count: number;
  };
}

export async function cleanTestResults(params: TestResultCleanupParams): Promise<TestResultCleanupResult> {
  return post<TestResultCleanupResult>('/api/normalize/test-results', params);
}

// Config
export async function getConfig(): Promise<ConfigResponse> {
  return get<ConfigResponse>('/api/config');
}

// Projects
export interface ProjectsResponse {
  projects: string[];
  total: number;
}

export async function getProjects(): Promise<ProjectsResponse> {
  return get<ProjectsResponse>('/api/config/projects');
}

export async function testConnections(): Promise<{
  success: boolean;
  connections: {
    qdrant: { status: 'ok' | 'error'; message?: string };
    neo4j: { status: 'ok' | 'error'; message?: string };
    voyage: { status: 'ok' | 'error'; message?: string };
  };
}> {
  return post('/api/config/test');
}
