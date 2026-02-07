/**
 * MemoryList Component Tests
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryList } from '@/components/browser/MemoryList';
import type { Memory, PaginationState } from '@/types';

// Mock the stores
vi.mock('@/stores/selection-store', () => ({
  useSelectionStore: () => ({
    selectedIds: new Set<string>(),
    toggleSelection: vi.fn(),
    selectAll: vi.fn(),
    clearSelection: vi.fn(),
    isSelected: vi.fn().mockReturnValue(false)
  })
}));

vi.mock('@/stores/ui-store', () => ({
  useUIStore: () => ({
    addToast: vi.fn()
  })
}));

const mockMemories: Memory[] = [
  {
    memory_id: 'mem-001',
    type: 'requirements',
    content: 'Test requirement content',
    metadata: { title: 'Test Requirement' },
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    deleted: false,
    project_id: 'test-project'
  },
  {
    memory_id: 'mem-002',
    type: 'design',
    content: 'Test design content',
    metadata: { title: 'Test Design' },
    created_at: '2024-01-02T00:00:00Z',
    updated_at: '2024-01-02T00:00:00Z',
    deleted: false,
    project_id: 'test-project'
  }
];

const defaultPagination: PaginationState = {
  page: 1,
  pageSize: 25,
  sort: 'updated_at',
  order: 'desc'
};

describe('MemoryList', () => {
  const mockOnPaginationChange = vi.fn();
  const mockOnSelect = vi.fn();
  const mockOnEdit = vi.fn();
  const mockOnDelete = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state', () => {
    render(
      <MemoryList
        memories={[]}
        isLoading={true}
        pagination={defaultPagination}
        total={0}
        onPaginationChange={mockOnPaginationChange}
        onSelect={mockOnSelect}
      />
    );

    // Should show skeleton loader
    expect(document.querySelector('.animate-pulse')).toBeTruthy();
  });

  it('renders empty state when no memories', () => {
    render(
      <MemoryList
        memories={[]}
        isLoading={false}
        pagination={defaultPagination}
        total={0}
        onPaginationChange={mockOnPaginationChange}
        onSelect={mockOnSelect}
      />
    );

    expect(screen.getByText('No memories found')).toBeTruthy();
  });

  it('renders memory list correctly', () => {
    render(
      <MemoryList
        memories={mockMemories}
        isLoading={false}
        pagination={defaultPagination}
        total={mockMemories.length}
        onPaginationChange={mockOnPaginationChange}
        onSelect={mockOnSelect}
      />
    );

    // Check that memories are rendered
    expect(screen.getByText('requirements')).toBeTruthy();
    expect(screen.getByText('design')).toBeTruthy();
    expect(screen.getByText('Test requirement content')).toBeTruthy();
    expect(screen.getByText('Test design content')).toBeTruthy();
  });

  it('calls onSelect when row is clicked', () => {
    render(
      <MemoryList
        memories={mockMemories}
        isLoading={false}
        pagination={defaultPagination}
        total={mockMemories.length}
        onPaginationChange={mockOnPaginationChange}
        onSelect={mockOnSelect}
      />
    );

    // Click on first row
    const rows = screen.getAllByRole('row');
    fireEvent.click(rows[1]); // Skip header row

    expect(mockOnSelect).toHaveBeenCalledWith(mockMemories[0]);
  });

  it('displays pagination info correctly', () => {
    render(
      <MemoryList
        memories={mockMemories}
        isLoading={false}
        pagination={{ ...defaultPagination, page: 1, pageSize: 10 }}
        total={25}
        onPaginationChange={mockOnPaginationChange}
        onSelect={mockOnSelect}
      />
    );

    expect(screen.getByText('Showing 1-2 of 25')).toBeTruthy();
  });

  it('handles pagination button clicks', () => {
    render(
      <MemoryList
        memories={mockMemories}
        isLoading={false}
        pagination={{ ...defaultPagination, page: 2 }}
        total={50}
        onPaginationChange={mockOnPaginationChange}
        onSelect={mockOnSelect}
      />
    );

    const previousButton = screen.getByText('Previous');
    fireEvent.click(previousButton);

    expect(mockOnPaginationChange).toHaveBeenCalledWith({ page: 1 });
  });
});
