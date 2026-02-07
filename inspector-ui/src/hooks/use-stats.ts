/**
 * Stats Hooks
 *
 * React Query hooks for statistics and maintenance operations.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as api from '@/api/stats';
import { useUIStore } from '@/stores/ui-store';

/**
 * Get system statistics
 */
export function useStats() {
  return useQuery({
    queryKey: ['stats'],
    queryFn: api.getStats,
    refetchInterval: 60000 // Auto-refresh every minute
  });
}

/**
 * Start normalization job
 */
export function useNormalize() {
  const { addToast } = useUIStore();

  return useMutation({
    mutationFn: api.startNormalize,
    onSuccess: (data) => {
      addToast({
        title: 'Normalization started',
        description: `Job ID: ${data.jobId}`,
        variant: 'success'
      });
    },
    onError: (error: Error) => {
      addToast({
        title: 'Failed to start normalization',
        description: error.message,
        variant: 'destructive'
      });
    }
  });
}

/**
 * Get normalization job status
 */
export function useNormalizeStatus(jobId: string | null) {
  return useQuery({
    queryKey: ['normalize', jobId],
    queryFn: () => api.getNormalizeStatus(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const data = query.state.data;
      // Poll while job is running
      if (data?.status === 'pending' || data?.status === 'running') {
        return 2000;
      }
      return false;
    }
  });
}

/**
 * Export memories
 */
export function useExport() {
  const { addToast } = useUIStore();

  return useMutation({
    mutationFn: api.exportMemories,
    onSuccess: (data) => {
      // Trigger download
      const blob = new Blob([data], { type: 'application/x-ndjson' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `memories-${new Date().toISOString().split('T')[0]}.jsonl`;
      a.click();
      URL.revokeObjectURL(url);

      addToast({
        title: 'Export complete',
        variant: 'success'
      });
    },
    onError: (error: Error) => {
      addToast({
        title: 'Export failed',
        description: error.message,
        variant: 'destructive'
      });
    }
  });
}

/**
 * Import memories
 */
export function useImport() {
  const queryClient = useQueryClient();
  const { addToast } = useUIStore();

  return useMutation({
    mutationFn: api.importMemories,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['memories'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
      addToast({
        title: 'Import complete',
        description: `Imported ${data.results.imported}, skipped ${data.results.skipped}`,
        variant: 'success'
      });
    },
    onError: (error: Error) => {
      addToast({
        title: 'Import failed',
        description: error.message,
        variant: 'destructive'
      });
    }
  });
}

/**
 * Index a file
 */
export function useIndexFile() {
  const queryClient = useQueryClient();
  const { addToast } = useUIStore();

  return useMutation({
    mutationFn: api.indexFile,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['memories'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
      addToast({
        title: 'File indexed',
        description: `Indexed as ${data.type}: ${data.path}`,
        variant: 'success'
      });
    },
    onError: (error: Error) => {
      addToast({
        title: 'Indexing failed',
        description: error.message,
        variant: 'destructive'
      });
    }
  });
}

/**
 * Index a directory
 */
export function useIndexDirectory() {
  const { addToast } = useUIStore();

  return useMutation({
    mutationFn: api.indexDirectory,
    onSuccess: (data) => {
      addToast({
        title: 'Directory indexing started',
        description: `Job ID: ${data.jobId}`,
        variant: 'success'
      });
    },
    onError: (error: Error) => {
      addToast({
        title: 'Failed to start indexing',
        description: error.message,
        variant: 'destructive'
      });
    }
  });
}

/**
 * Get index job status
 */
export function useIndexStatus(jobId: string | null) {
  return useQuery({
    queryKey: ['index', jobId],
    queryFn: () => api.getIndexStatus(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.status === 'pending' || data?.status === 'running') {
        return 2000;
      }
      return false;
    }
  });
}

/**
 * Test database connections
 */
export function useTestConnections() {
  return useMutation({
    mutationFn: api.testConnections
  });
}

/**
 * Clean test results (REQ-007-FN-062)
 */
export function useCleanTestResults() {
  const queryClient = useQueryClient();
  const { addToast } = useUIStore();

  return useMutation({
    mutationFn: api.cleanTestResults,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['memories'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
      addToast({
        title: data.status === 'dry_run' ? 'Test cleanup preview' : 'Test results cleaned',
        description: `${data.cleaned_count} test results ${data.status === 'dry_run' ? 'would be' : ''} cleaned`,
        variant: 'success'
      });
    },
    onError: (error: Error) => {
      addToast({
        title: 'Failed to clean test results',
        description: error.message,
        variant: 'destructive'
      });
    }
  });
}

/**
 * Get available projects
 */
export function useProjects() {
  return useQuery({
    queryKey: ['projects'],
    queryFn: api.getProjects,
    staleTime: 5 * 60 * 1000 // Cache for 5 minutes
  });
}
