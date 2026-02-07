/**
 * Selection Store
 *
 * Zustand store for selection state.
 */
import { create } from 'zustand';
import type { MemoryType } from '@/types';

interface SelectedMemory {
  id: string;
  type: string;
}

interface SelectionState {
  // Single selection (for detail panel)
  selectedMemory: SelectedMemory | null;

  // Multi-selection (for bulk operations)
  selectedIds: Set<string>;

  // Actions
  selectMemory: (id: string, type: string) => void;
  clearSelection: () => void;

  toggleSelection: (id: string) => void;
  toggleBulkSelect: (id: string, type: MemoryType) => void;
  addToBulkSelect: (id: string, type: MemoryType) => void;
  removeFromBulkSelect: (id: string) => void;
  selectAll: (items: string[] | Array<{ id: string; type: MemoryType }>) => void;
  clearBulkSelection: () => void;

  // Computed
  isSelected: (id: string) => boolean;
  getSelectedCount: () => number;
  getSelectedItems: () => Array<{ id: string; type: MemoryType }>;
}

// Store selection with type info
const selectionMap = new Map<string, MemoryType>();

export const useSelectionStore = create<SelectionState>((set, get) => ({
  selectedMemory: null,
  selectedIds: new Set(),

  selectMemory: (id, type) => set({
    selectedMemory: { id, type }
  }),

  clearSelection: () => set({
    selectedMemory: null
  }),

  toggleSelection: (id) => set(state => {
    const newSet = new Set(state.selectedIds);
    if (newSet.has(id)) {
      newSet.delete(id);
      selectionMap.delete(id);
    } else {
      newSet.add(id);
    }
    return { selectedIds: newSet };
  }),

  toggleBulkSelect: (id, type) => set(state => {
    const newSet = new Set(state.selectedIds);
    if (newSet.has(id)) {
      newSet.delete(id);
      selectionMap.delete(id);
    } else {
      newSet.add(id);
      selectionMap.set(id, type);
    }
    return { selectedIds: newSet };
  }),

  addToBulkSelect: (id, type) => set(state => {
    const newSet = new Set(state.selectedIds);
    newSet.add(id);
    selectionMap.set(id, type);
    return { selectedIds: newSet };
  }),

  removeFromBulkSelect: (id) => set(state => {
    const newSet = new Set(state.selectedIds);
    newSet.delete(id);
    selectionMap.delete(id);
    return { selectedIds: newSet };
  }),

  selectAll: (items) => set(() => {
    const newSet = new Set<string>();
    selectionMap.clear();
    if (Array.isArray(items) && items.length > 0) {
      if (typeof items[0] === 'string') {
        // Array of IDs
        (items as string[]).forEach(id => {
          newSet.add(id);
        });
      } else {
        // Array of objects with id and type
        (items as Array<{ id: string; type: MemoryType }>).forEach(({ id, type }) => {
          newSet.add(id);
          selectionMap.set(id, type);
        });
      }
    }
    return { selectedIds: newSet };
  }),

  clearBulkSelection: () => {
    selectionMap.clear();
    set({ selectedIds: new Set() });
  },

  isSelected: (id) => get().selectedIds.has(id),

  getSelectedCount: () => get().selectedIds.size,

  getSelectedItems: () => {
    const ids = get().selectedIds;
    return Array.from(ids).map(id => ({
      id,
      type: selectionMap.get(id) || 'requirements'
    }));
  }
}));
