/**
 * Memory API
 *
 * API functions for memory CRUD operations.
 */
import { get, post, put, del } from './client';
import type { Memory, MemoryListResponse, MemoryInput, FilterState, PaginationState } from '@/types';

export interface ListMemoriesParams extends PaginationState {
  type?: string;
  types?: string;
  search?: string;
  startDate?: string;
  endDate?: string;
  deleted?: boolean;
}

export async function listMemories(params: ListMemoriesParams): Promise<MemoryListResponse> {
  return get<MemoryListResponse>('/api/memories', params as Record<string, string | number | boolean | undefined>);
}

export async function getMemory(type: string, id: string): Promise<Memory> {
  return get<Memory>(`/api/memories/${type}/${id}`);
}

export async function createMemory(input: MemoryInput): Promise<Memory> {
  return post<Memory>('/api/memories', input);
}

export async function updateMemory(
  type: string,
  id: string,
  data: Partial<Omit<MemoryInput, 'type'>>
): Promise<Memory> {
  return put<Memory>(`/api/memories/${type}/${id}`, data);
}

export async function deleteMemory(
  type: string,
  id: string,
  hard: boolean = false
): Promise<{ success: boolean; id: string; hard: boolean }> {
  return del<{ success: boolean; id: string; hard: boolean }>(
    `/api/memories/${type}/${id}`,
    { hard: hard ? 'true' : 'false' }
  );
}

export async function bulkDeleteMemories(
  ids: Array<{ type: string; id: string }>,
  hard: boolean = false
): Promise<{ success: boolean; deleted: string[]; count: number; hard: boolean }> {
  return post('/api/memories/bulk-delete', { ids, hard });
}
