/**
 * Memory Hooks
 *
 * React Query hooks for memory operations.
 * REQ-007-FN-030 to FN-033: Project switching auto-refresh
 */
import { useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as api from '@/api/memories';
import * as statsApi from '@/api/stats';
import type { Memory, MemoryInput, MemoryType } from '@/types';
import { useUIStore } from '@/stores/ui-store';
import { useSelectionStore } from '@/stores/selection-store';
import { useConfigStore } from '@/stores/config-store';

/**
 * Hook to handle project change events and invalidate caches
 * REQ-007-FN-030, REQ-007-FN-031, REQ-007-FN-032, REQ-007-FN-033
 */
export function useProjectChangeHandler() {
  const queryClient = useQueryClient();
  const { clearSelection } = useSelectionStore();
  const { addToast } = useUIStore();
  const { projectId } = useConfigStore();

  useEffect(() => {
    const handleProjectChange = (event: Event) => {
      const customEvent = event as CustomEvent<{ projectId: string; previousProjectId: string }>;
      const { projectId: newProjectId, previousProjectId } = customEvent.detail;

      // REQ-007-FN-030: Invalidate all cached data
      queryClient.clear();

      // REQ-007-FN-032: Clear current memory selection
      clearSelection();

      // REQ-007-FN-033: Show loading state (handled by React Query)
      // Trigger refetch of key queries
      queryClient.invalidateQueries({ queryKey: ['memories'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
      queryClient.invalidateQueries({ queryKey: ['graph'] });

      addToast({
        title: 'Project changed',
        description: `Switched from "${previousProjectId}" to "${newProjectId}"`,
        variant: 'success',
        duration: 3000
      });
    };

    window.addEventListener('project-changed', handleProjectChange);
    return () => window.removeEventListener('project-changed', handleProjectChange);
  }, [queryClient, clearSelection, addToast]);

  return { projectId };
}

export interface UseMemoriesParams {
  type?: MemoryType | 'all';
  page?: number;
  pageSize?: number;
  sort?: 'created_at' | 'updated_at';
  order?: 'asc' | 'desc';
  search?: string;
  startDate?: string;
  endDate?: string;
}

/**
 * List memories with filters and pagination
 */
export function useMemories(params: UseMemoriesParams = {}) {
  const {
    type = 'all',
    page = 1,
    pageSize = 25,
    sort = 'updated_at',
    order = 'desc',
    search,
    startDate,
    endDate
  } = params;

  return useQuery({
    queryKey: ['memories', type, page, pageSize, sort, order, search, startDate, endDate],
    queryFn: () => api.listMemories({
      type: type !== 'all' ? type : undefined,
      page,
      pageSize,
      sort,
      order,
      search,
      startDate,
      endDate
    })
  });
}

/**
 * Get a single memory by type and ID
 */
export function useMemory(type: string, id: string) {
  return useQuery({
    queryKey: ['memory', type, id],
    queryFn: () => api.getMemory(type, id),
    enabled: !!type && !!id
  });
}

/**
 * Create a new memory
 */
export function useCreateMemory() {
  const queryClient = useQueryClient();
  const { addToast } = useUIStore();

  return useMutation({
    mutationFn: (input: MemoryInput) => api.createMemory(input),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['memories'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
      addToast({
        title: 'Memory created',
        description: `Created ${data.type} memory`,
        variant: 'success'
      });
    },
    onError: (error: Error) => {
      addToast({
        title: 'Failed to create memory',
        description: error.message,
        variant: 'destructive'
      });
    }
  });
}

/**
 * Update an existing memory
 */
export function useUpdateMemory() {
  const queryClient = useQueryClient();
  const { addToast } = useUIStore();

  return useMutation({
    mutationFn: ({ type, id, data }: { type: string; id: string; data: Partial<Omit<MemoryInput, 'type'>> }) =>
      api.updateMemory(type, id, data),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['memory', variables.type, variables.id] });
      queryClient.invalidateQueries({ queryKey: ['memories'] });
      addToast({
        title: 'Memory updated',
        variant: 'success'
      });
    },
    onError: (error: Error) => {
      addToast({
        title: 'Failed to update memory',
        description: error.message,
        variant: 'destructive'
      });
    }
  });
}

/**
 * Delete a memory
 */
export function useDeleteMemory() {
  const queryClient = useQueryClient();
  const { addToast } = useUIStore();

  return useMutation({
    mutationFn: ({ type, id, hard = false }: { type: string; id: string; hard?: boolean }) =>
      api.deleteMemory(type, id, hard),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['memories'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
      addToast({
        title: variables.hard ? 'Memory permanently deleted' : 'Memory deleted',
        variant: 'success'
      });
    },
    onError: (error: Error) => {
      addToast({
        title: 'Failed to delete memory',
        description: error.message,
        variant: 'destructive'
      });
    }
  });
}

/**
 * Bulk delete memories
 */
export function useBulkDeleteMemories() {
  const queryClient = useQueryClient();
  const { addToast } = useUIStore();

  return useMutation({
    mutationFn: ({ ids, hard = false }: { ids: Array<{ type: string; id: string }>; hard?: boolean }) =>
      api.bulkDeleteMemories(ids, hard),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['memories'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
      addToast({
        title: `${data.count} memories deleted`,
        variant: 'success'
      });
    },
    onError: (error: Error) => {
      addToast({
        title: 'Failed to delete memories',
        description: error.message,
        variant: 'destructive'
      });
    }
  });
}

/**
 * Get memory statistics
 */
export function useMemoryStats() {
  return useQuery({
    queryKey: ['stats'],
    queryFn: () => statsApi.getStats(),
    refetchInterval: 60000 // Refresh every minute
  });
}
