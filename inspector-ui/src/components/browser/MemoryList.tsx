/**
 * Memory List Component
 *
 * Paginated table of memories with selection, sorting, and resizable columns.
 * REQ-007-FN-040 to REQ-007-FN-046
 */
import { useState, useMemo, useRef, useCallback } from 'react';
import { ChevronUp, ChevronDown, ChevronLeft, ChevronRight, MoreHorizontal, Trash2, Eye, Edit } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { SkeletonMemoryList } from '@/components/common/LoadingStates';
import { useSelectionStore } from '@/stores/selection-store';
import { cn, truncate, formatRelativeTime } from '@/lib/utils';
import type { Memory, MemoryType, PaginationState } from '@/types';

// Column width definitions (session storage key)
const COLUMN_WIDTHS_KEY = 'inspector-column-widths';

interface ColumnWidths {
  id: number;
  type: number;
  component: number;
  language: number;
  content: number;
  created: number;
  updated: number;
}

const DEFAULT_WIDTHS: ColumnWidths = {
  id: 100,
  type: 100,
  component: 120,
  language: 100,
  content: 250,
  created: 120,
  updated: 120
};

function loadColumnWidths(): ColumnWidths {
  try {
    const stored = sessionStorage.getItem(COLUMN_WIDTHS_KEY);
    if (stored) {
      return { ...DEFAULT_WIDTHS, ...JSON.parse(stored) };
    }
  } catch {
    // Ignore errors
  }
  return DEFAULT_WIDTHS;
}

function saveColumnWidths(widths: ColumnWidths) {
  try {
    sessionStorage.setItem(COLUMN_WIDTHS_KEY, JSON.stringify(widths));
  } catch {
    // Ignore errors
  }
}

interface MemoryListProps {
  memories: Memory[];
  isLoading?: boolean;
  pagination: PaginationState;
  total: number;
  onPaginationChange: (pagination: Partial<PaginationState>) => void;
  onSelect: (memory: Memory) => void;
  onEdit?: (memory: Memory) => void;
  onDelete?: (memories: Memory[]) => void;
  className?: string;
}

export function MemoryList({
  memories,
  isLoading = false,
  pagination,
  total,
  onPaginationChange,
  onSelect,
  onEdit,
  onDelete,
  className
}: MemoryListProps) {
  const {
    selectedIds,
    toggleSelection,
    selectAll,
    clearSelection,
    isSelected
  } = useSelectionStore();

  const [hoveredRowId, setHoveredRowId] = useState<string | null>(null);
  const [columnWidths, setColumnWidths] = useState<ColumnWidths>(loadColumnWidths);
  const [resizingColumn, setResizingColumn] = useState<keyof ColumnWidths | null>(null);
  const resizeStartX = useRef<number>(0);
  const resizeStartWidth = useRef<number>(0);

  // Calculate pagination info
  const totalPages = Math.ceil(total / pagination.pageSize);
  const startItem = (pagination.page - 1) * pagination.pageSize + 1;
  const endItem = Math.min(pagination.page * pagination.pageSize, total);

  // Check if all visible items are selected
  const allSelected = memories.length > 0 && memories.every(m => isSelected(m.memory_id));
  const someSelected = memories.some(m => isSelected(m.memory_id));

  const handleSelectAll = () => {
    if (allSelected) {
      clearSelection();
    } else {
      selectAll(memories.map(m => m.memory_id));
    }
  };

  const handleSort = (field: 'created_at' | 'updated_at') => {
    if (pagination.sort === field) {
      onPaginationChange({
        order: pagination.order === 'asc' ? 'desc' : 'asc'
      });
    } else {
      onPaginationChange({ sort: field, order: 'desc' });
    }
  };

  const SortIcon = ({ field }: { field: 'created_at' | 'updated_at' }) => {
    if (pagination.sort !== field) return null;
    return pagination.order === 'asc' ? (
      <ChevronUp className="h-3 w-3" />
    ) : (
      <ChevronDown className="h-3 w-3" />
    );
  };

  // Get selected memories for bulk operations
  const selectedMemories = useMemo(() => {
    return memories.filter(m => isSelected(m.memory_id));
  }, [memories, isSelected, selectedIds]);

  // Column resizing handlers
  const handleResizeStart = useCallback((column: keyof ColumnWidths, e: React.MouseEvent) => {
    e.preventDefault();
    setResizingColumn(column);
    resizeStartX.current = e.clientX;
    resizeStartWidth.current = columnWidths[column];

    const handleMouseMove = (e: MouseEvent) => {
      const delta = e.clientX - resizeStartX.current;
      const newWidth = Math.max(60, resizeStartWidth.current + delta);
      setColumnWidths(prev => {
        const updated = { ...prev, [column]: newWidth };
        saveColumnWidths(updated);
        return updated;
      });
    };

    const handleMouseUp = () => {
      setResizingColumn(null);
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  }, [columnWidths]);

  // Column resize handle component
  const ResizeHandle = ({ column }: { column: keyof ColumnWidths }) => (
    <div
      className={cn(
        'absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/50 transition-colors',
        resizingColumn === column && 'bg-primary/50'
      )}
      onMouseDown={(e) => handleResizeStart(column, e)}
    />
  );

  if (isLoading) {
    return <SkeletonMemoryList rows={pagination.pageSize} />;
  }

  if (memories.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <p>No memories found</p>
        <p className="text-sm mt-1">Try adjusting your filters</p>
      </div>
    );
  }

  return (
    <div className={cn('space-y-4', className)}>
      {/* Bulk action bar */}
      {someSelected && (
        <div className="flex items-center gap-4 p-2 bg-muted rounded-md">
          <span className="text-sm font-medium">
            {selectedIds.size} selected
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => clearSelection()}
          >
            Clear
          </Button>
          <div className="flex-1" />
          {onDelete && (
            <Button
              variant="destructive"
              size="sm"
              onClick={() => onDelete(selectedMemories)}
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Delete Selected
            </Button>
          )}
        </div>
      )}

      {/* Table */}
      <div className="rounded-md border overflow-hidden overflow-x-auto">
        <table className="w-full text-sm table-fixed" style={{ minWidth: '900px' }}>
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="w-10 p-3">
                <input
                  type="checkbox"
                  checked={allSelected}
                  ref={el => {
                    if (el) el.indeterminate = someSelected && !allSelected;
                  }}
                  onChange={handleSelectAll}
                  className="rounded"
                />
              </th>
              <th className="p-3 text-left font-medium relative" style={{ width: columnWidths.id }}>
                ID
                <ResizeHandle column="id" />
              </th>
              <th className="p-3 text-left font-medium relative" style={{ width: columnWidths.type }}>
                Type
                <ResizeHandle column="type" />
              </th>
              <th className="p-3 text-left font-medium relative" style={{ width: columnWidths.component }}>
                Component
                <ResizeHandle column="component" />
              </th>
              <th className="p-3 text-left font-medium relative" style={{ width: columnWidths.language }}>
                Language
                <ResizeHandle column="language" />
              </th>
              <th className="p-3 text-left font-medium relative" style={{ width: columnWidths.content }}>
                Content
                <ResizeHandle column="content" />
              </th>
              <th
                className="p-3 text-left font-medium cursor-pointer select-none relative"
                style={{ width: columnWidths.created }}
                onClick={() => handleSort('created_at')}
              >
                <div className="flex items-center gap-1">
                  Created
                  <SortIcon field="created_at" />
                </div>
                <ResizeHandle column="created" />
              </th>
              <th
                className="p-3 text-left font-medium cursor-pointer select-none relative"
                style={{ width: columnWidths.updated }}
                onClick={() => handleSort('updated_at')}
              >
                <div className="flex items-center gap-1">
                  Updated
                  <SortIcon field="updated_at" />
                </div>
                <ResizeHandle column="updated" />
              </th>
              <th className="w-10 p-3"></th>
            </tr>
          </thead>
          <tbody>
            {memories.map((memory) => (
              <tr
                key={memory.memory_id}
                className={cn(
                  'border-b last:border-0 cursor-pointer transition-colors',
                  isSelected(memory.memory_id) && 'bg-primary/5',
                  hoveredRowId === memory.memory_id && 'bg-muted/50'
                )}
                onClick={() => onSelect(memory)}
                onMouseEnter={() => setHoveredRowId(memory.memory_id)}
                onMouseLeave={() => setHoveredRowId(null)}
              >
                <td className="p-3" onClick={(e) => e.stopPropagation()}>
                  <input
                    type="checkbox"
                    checked={isSelected(memory.memory_id)}
                    onChange={() => toggleSelection(memory.memory_id)}
                    className="rounded"
                  />
                </td>
                <td className="p-3" style={{ width: columnWidths.id }}>
                  <code className="text-xs font-mono text-muted-foreground">
                    {memory.memory_id.slice(0, 8)}...
                  </code>
                </td>
                <td className="p-3" style={{ width: columnWidths.type }}>
                  <Badge variant={memory.type as MemoryType}>
                    {memory.type}
                  </Badge>
                </td>
                <td className="p-3" style={{ width: columnWidths.component }}>
                  <span className="text-xs text-muted-foreground truncate block">
                    {(memory.metadata?.component_name as string) || (memory.metadata?.component as string) || '-'}
                  </span>
                </td>
                <td className="p-3" style={{ width: columnWidths.language }}>
                  <span className="text-xs text-muted-foreground truncate block">
                    {(memory.metadata?.language as string) || '-'}
                  </span>
                </td>
                <td className="p-3" style={{ width: columnWidths.content }}>
                  <span className="truncate block">
                    {truncate(memory.content, 60)}
                  </span>
                </td>
                <td className="p-3 text-muted-foreground whitespace-nowrap" style={{ width: columnWidths.created }}>
                  {formatRelativeTime(memory.created_at)}
                </td>
                <td className="p-3 text-muted-foreground whitespace-nowrap" style={{ width: columnWidths.updated }}>
                  {formatRelativeTime(memory.updated_at)}
                </td>
                <td className="p-3" onClick={(e) => e.stopPropagation()}>
                  <RowActions
                    memory={memory}
                    onView={() => onSelect(memory)}
                    onEdit={onEdit ? () => onEdit(memory) : undefined}
                    onDelete={onDelete ? () => onDelete([memory]) : undefined}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination - REQ-007-FN-044 to FN-046 */}
      <div className="flex items-center justify-between bg-muted/30 p-3 rounded-md border">
        <div className="text-sm text-muted-foreground">
          Showing {total === 0 ? 0 : startItem}-{endItem} of {total} memories
        </div>

        <div className="flex items-center gap-3">
          {/* Page size selector - REQ-007-FN-046 */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">Per page:</span>
            <select
              value={pagination.pageSize}
              onChange={(e) => onPaginationChange({ pageSize: Number(e.target.value), page: 1 })}
              className="h-8 rounded-md border border-input bg-background px-2 text-sm"
            >
              <option value={10}>10</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>

          <div className="w-px h-6 bg-border" />

          {/* Page navigation - REQ-007-FN-044, FN-045 */}
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="icon"
              className="h-8 w-8"
              onClick={() => onPaginationChange({ page: 1 })}
              disabled={pagination.page <= 1}
              title="First page"
            >
              <ChevronLeft className="h-4 w-4" />
              <ChevronLeft className="h-4 w-4 -ml-3" />
            </Button>
            <Button
              variant="outline"
              size="icon"
              className="h-8 w-8"
              onClick={() => onPaginationChange({ page: pagination.page - 1 })}
              disabled={pagination.page <= 1}
              title="Previous page"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>

            {/* Page numbers */}
            <div className="flex items-center gap-1 px-2">
              {(() => {
                const pages = [];
                const maxVisible = 5;
                let start = Math.max(1, pagination.page - Math.floor(maxVisible / 2));
                const end = Math.min(totalPages, start + maxVisible - 1);
                start = Math.max(1, end - maxVisible + 1);

                for (let i = start; i <= end; i++) {
                  pages.push(
                    <Button
                      key={i}
                      variant={i === pagination.page ? 'default' : 'ghost'}
                      size="sm"
                      className="h-8 w-8 p-0"
                      onClick={() => onPaginationChange({ page: i })}
                    >
                      {i}
                    </Button>
                  );
                }
                return pages;
              })()}
            </div>

            <Button
              variant="outline"
              size="icon"
              className="h-8 w-8"
              onClick={() => onPaginationChange({ page: pagination.page + 1 })}
              disabled={pagination.page >= totalPages}
              title="Next page"
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="icon"
              className="h-8 w-8"
              onClick={() => onPaginationChange({ page: totalPages })}
              disabled={pagination.page >= totalPages}
              title="Last page"
            >
              <ChevronRight className="h-4 w-4" />
              <ChevronRight className="h-4 w-4 -ml-3" />
            </Button>
          </div>

          {/* Page X of Y indicator */}
          <span className="text-sm text-muted-foreground whitespace-nowrap">
            Page {pagination.page} of {totalPages || 1}
          </span>
        </div>
      </div>
    </div>
  );
}

interface RowActionsProps {
  memory: Memory;
  onView: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
}

function RowActions({ memory, onView, onEdit, onDelete }: RowActionsProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <Button
        variant="ghost"
        size="icon"
        className="h-8 w-8"
        onClick={() => setOpen(!open)}
      >
        <MoreHorizontal className="h-4 w-4" />
      </Button>

      {open && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setOpen(false)}
          />
          <div className="absolute right-0 top-full mt-1 w-36 bg-popover border rounded-md shadow-lg z-20">
            <button
              className="flex items-center gap-2 w-full px-3 py-2 text-sm hover:bg-muted"
              onClick={() => {
                onView();
                setOpen(false);
              }}
            >
              <Eye className="h-4 w-4" />
              View
            </button>
            {onEdit && (
              <button
                className="flex items-center gap-2 w-full px-3 py-2 text-sm hover:bg-muted"
                onClick={() => {
                  onEdit();
                  setOpen(false);
                }}
              >
                <Edit className="h-4 w-4" />
                Edit
              </button>
            )}
            {onDelete && (
              <button
                className="flex items-center gap-2 w-full px-3 py-2 text-sm text-destructive hover:bg-destructive/10"
                onClick={() => {
                  onDelete();
                  setOpen(false);
                }}
              >
                <Trash2 className="h-4 w-4" />
                Delete
              </button>
            )}
          </div>
        </>
      )}
    </div>
  );
}

export default MemoryList;
