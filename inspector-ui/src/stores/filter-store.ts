/**
 * Filter Store
 *
 * Zustand store for filter state.
 */
import { create } from 'zustand';
import type { MemoryType } from '@/types';

interface FilterState {
  // Browser filters
  memoryType: MemoryType | 'all';
  dateRange: {
    start?: string;
    end?: string;
  };
  searchText: string;
  metadataFilters: Record<string, string>;

  // Actions
  setMemoryType: (type: MemoryType | 'all') => void;
  setDateRange: (range: { start?: string; end?: string }) => void;
  setSearchText: (text: string) => void;
  setMetadataFilter: (key: string, value: string) => void;
  removeMetadataFilter: (key: string) => void;
  clearFilters: () => void;

  // Computed
  hasActiveFilters: () => boolean;
  getFilterSummary: () => string[];
  getFilterParams: () => Record<string, string | undefined>;
}

const initialState = {
  memoryType: 'all' as const,
  dateRange: {},
  searchText: '',
  metadataFilters: {}
};

export const useFilterStore = create<FilterState>((set, get) => ({
  ...initialState,

  setMemoryType: (type) => set({ memoryType: type }),

  setDateRange: (range) => set({ dateRange: range }),

  setSearchText: (text) => set({ searchText: text }),

  setMetadataFilter: (key, value) => set(state => ({
    metadataFilters: { ...state.metadataFilters, [key]: value }
  })),

  removeMetadataFilter: (key) => set(state => {
    const { [key]: _, ...rest } = state.metadataFilters;
    return { metadataFilters: rest };
  }),

  clearFilters: () => set(initialState),

  hasActiveFilters: () => {
    const state = get();
    return (
      state.memoryType !== 'all' ||
      !!state.dateRange.start ||
      !!state.dateRange.end ||
      !!state.searchText ||
      Object.keys(state.metadataFilters).length > 0
    );
  },

  getFilterSummary: () => {
    const state = get();
    const summary: string[] = [];

    if (state.memoryType !== 'all') {
      summary.push(`Type: ${state.memoryType}`);
    }

    if (state.dateRange.start || state.dateRange.end) {
      const range = [
        state.dateRange.start || 'any',
        state.dateRange.end || 'any'
      ].join(' - ');
      summary.push(`Date: ${range}`);
    }

    if (state.searchText) {
      summary.push(`Search: "${state.searchText}"`);
    }

    Object.entries(state.metadataFilters).forEach(([key, value]) => {
      summary.push(`${key}: ${value}`);
    });

    return summary;
  },

  getFilterParams: () => {
    const state = get();
    return {
      search: state.searchText || undefined,
      dateStart: state.dateRange.start,
      dateEnd: state.dateRange.end
    };
  }
}));
