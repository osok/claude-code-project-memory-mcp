/**
 * Browser Page
 *
 * Memory browser with list, filters, and CRUD operations.
 */
import { useState, useCallback } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { Plus, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  MemoryList,
  MemoryDetail,
  MemoryForm,
  MemoryFilters,
  TypeSelector,
  DeleteConfirmation
} from '@/components/browser';
import { DetailPanel } from '@/components/layout/DetailPanel';
import { useMemories, useDeleteMemory, useBulkDeleteMemories, useMemoryStats } from '@/hooks/use-memories';
import { useFilterStore } from '@/stores/filter-store';
import { useSelectionStore } from '@/stores/selection-store';
import { useUIStore } from '@/stores/ui-store';
import { useConfigStore } from '@/stores/config-store';
import type { MemoryType, Memory, PaginationState } from '@/types';

type ViewMode = 'list' | 'detail' | 'create' | 'edit';

export default function BrowserPage() {
  const { type } = useParams<{ type?: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const { pageSize } = useConfigStore();
  const { detailPanelOpen, openDetailPanel, closeDetailPanel, addToast } = useUIStore();
  const { memoryType, setMemoryType, searchText, clearFilters, getFilterParams } = useFilterStore();
  const { selectedMemory, selectMemory, clearSelection } = useSelectionStore();

  // View state
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [editingMemory, setEditingMemory] = useState<Memory | null>(null);
  const [deletingMemories, setDeletingMemories] = useState<Memory[]>([]);

  // Pagination state
  const [pagination, setPagination] = useState<PaginationState>({
    page: 1,
    pageSize,
    sort: 'updated_at',
    order: 'desc'
  });

  // Set memory type from URL
  const currentType = (type as MemoryType | 'all') || memoryType || 'all';

  // Check for id in search params (for direct linking)
  const linkedId = searchParams.get('id');

  // Fetch memories
  const { data, isLoading, refetch } = useMemories({
    type: currentType === 'all' ? undefined : currentType as MemoryType,
    page: pagination.page,
    pageSize: pagination.pageSize,
    sort: pagination.sort,
    order: pagination.order,
    ...getFilterParams()
  });

  // Fetch stats for type counts
  const { data: statsData } = useMemoryStats();

  // Mutations
  const deleteMemory = useDeleteMemory();
  const bulkDelete = useBulkDeleteMemories();

  // Get counts by type
  const typeCounts = statsData?.counts.byType || {};
  const totalCount = statsData?.counts.total || 0;

  // Handle type selection
  const handleTypeSelect = useCallback((t: MemoryType | 'all') => {
    setMemoryType(t);
    setPagination(p => ({ ...p, page: 1 }));
    navigate(t === 'all' ? '/browser' : `/browser/${t}`);
  }, [setMemoryType, navigate]);

  // Handle memory selection
  const handleMemorySelect = useCallback((memory: Memory) => {
    selectMemory(memory.memory_id, memory.type);
    setViewMode('detail');
    openDetailPanel();
  }, [selectMemory, openDetailPanel]);

  // Handle edit
  const handleEdit = useCallback((memory: Memory) => {
    setEditingMemory(memory);
    setViewMode('edit');
    openDetailPanel();
  }, [openDetailPanel]);

  // Handle delete request
  const handleDeleteRequest = useCallback((memories: Memory[]) => {
    setDeletingMemories(memories);
  }, []);

  // Handle delete confirmation
  const handleDeleteConfirm = useCallback(async (hard: boolean) => {
    if (deletingMemories.length === 0) return;

    try {
      if (deletingMemories.length === 1) {
        await deleteMemory.mutateAsync({
          type: deletingMemories[0].type,
          id: deletingMemories[0].memory_id,
          hard
        });
      } else {
        await bulkDelete.mutateAsync({
          ids: deletingMemories.map(m => ({ type: m.type, id: m.memory_id })),
          hard
        });
      }

      addToast({
        title: `Deleted ${deletingMemories.length} ${deletingMemories.length === 1 ? 'memory' : 'memories'}`,
        variant: 'success'
      });

      setDeletingMemories([]);
      clearSelection();
      refetch();
    } catch (error) {
      addToast({
        title: 'Delete failed',
        description: (error as Error).message,
        variant: 'destructive'
      });
    }
  }, [deletingMemories, deleteMemory, bulkDelete, addToast, clearSelection, refetch]);

  // Handle create new
  const handleCreateNew = useCallback(() => {
    setEditingMemory(null);
    setViewMode('create');
    openDetailPanel();
  }, [openDetailPanel]);

  // Handle form success
  const handleFormSuccess = useCallback(() => {
    setViewMode('list');
    closeDetailPanel();
    refetch();
    addToast({
      title: viewMode === 'create' ? 'Memory created' : 'Memory updated',
      variant: 'success'
    });
  }, [closeDetailPanel, refetch, addToast, viewMode]);

  // Handle form cancel
  const handleFormCancel = useCallback(() => {
    setViewMode('list');
    if (!selectedMemory) {
      closeDetailPanel();
    } else {
      setViewMode('detail');
    }
  }, [closeDetailPanel, selectedMemory]);

  // Handle panel close
  const handlePanelClose = useCallback(() => {
    setViewMode('list');
    closeDetailPanel();
    clearSelection();
  }, [closeDetailPanel, clearSelection]);

  // Handle navigation from detail to related memory
  const handleNavigateToMemory = useCallback((memoryType: string, id: string) => {
    navigate(`/browser/${memoryType}?id=${id}`);
  }, [navigate]);

  // Handle pagination change
  const handlePaginationChange = useCallback((changes: Partial<PaginationState>) => {
    setPagination(p => ({ ...p, ...changes }));
  }, []);

  return (
    <div className="flex h-full gap-4">
      {/* Type Selector Sidebar */}
      <aside className="w-48 shrink-0">
        <TypeSelector
          selectedType={currentType}
          counts={typeCounts}
          totalCount={totalCount}
          onSelect={handleTypeSelect}
        />
      </aside>

      {/* Main Content */}
      <div className="flex-1 min-w-0 flex flex-col overflow-hidden">
        {/* Toolbar - fixed at top */}
        <div className="flex items-center gap-4 shrink-0 pb-4">
          <MemoryFilters className="flex-1" />
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Button size="sm" onClick={handleCreateNew}>
            <Plus className="h-4 w-4 mr-2" />
            New Memory
          </Button>
        </div>

        {/* Memory List - scrollable area */}
        <div className="flex-1 overflow-auto">
          <MemoryList
            memories={data?.memories || []}
            isLoading={isLoading}
            pagination={pagination}
            total={data?.total || 0}
            onPaginationChange={handlePaginationChange}
            onSelect={handleMemorySelect}
            onEdit={handleEdit}
            onDelete={handleDeleteRequest}
          />
        </div>
      </div>

      {/* Detail Panel */}
      <DetailPanel
        open={detailPanelOpen}
        onClose={handlePanelClose}
        title={
          viewMode === 'create' ? 'Create Memory' :
          viewMode === 'edit' ? 'Edit Memory' :
          'Memory Details'
        }
      >
        {viewMode === 'detail' && selectedMemory && (
          <MemoryDetail
            type={selectedMemory.type}
            id={selectedMemory.id}
            onEdit={() => {
              const memory = data?.memories.find(m => m.memory_id === selectedMemory.id);
              if (memory) handleEdit(memory);
            }}
            onDelete={() => {
              const memory = data?.memories.find(m => m.memory_id === selectedMemory.id);
              if (memory) handleDeleteRequest([memory]);
            }}
            onNavigate={handleNavigateToMemory}
          />
        )}

        {(viewMode === 'create' || viewMode === 'edit') && (
          <MemoryForm
            mode={viewMode === 'create' ? 'create' : 'edit'}
            type={editingMemory?.type || currentType !== 'all' ? currentType : undefined}
            id={editingMemory?.memory_id}
            onSuccess={handleFormSuccess}
            onCancel={handleFormCancel}
          />
        )}
      </DetailPanel>

      {/* Delete Confirmation Dialog */}
      {deletingMemories.length > 0 && (
        <DeleteConfirmation
          memories={deletingMemories}
          onConfirm={handleDeleteConfirm}
          onCancel={() => setDeletingMemories([])}
          isDeleting={deleteMemory.isPending || bulkDelete.isPending}
        />
      )}
    </div>
  );
}
