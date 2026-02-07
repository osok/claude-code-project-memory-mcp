/**
 * Memory Filters Component
 *
 * Filter controls for the memory browser.
 */
import { useState } from 'react';
import { Filter, X, ChevronDown, ChevronUp, Calendar } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { useFilterStore } from '@/stores/filter-store';
import { MEMORY_TYPES, type MemoryType } from '@/types';
import { cn } from '@/lib/utils';

interface MemoryFiltersProps {
  className?: string;
}

export function MemoryFilters({ className }: MemoryFiltersProps) {
  const [expanded, setExpanded] = useState(false);
  const {
    memoryType,
    dateRange,
    searchText,
    metadataFilters,
    setMemoryType,
    setDateRange,
    setSearchText,
    setMetadataFilter,
    removeMetadataFilter,
    clearFilters,
    hasActiveFilters,
    getFilterSummary
  } = useFilterStore();

  const activeFilters = getFilterSummary();

  return (
    <div className={cn('space-y-2', className)}>
      {/* Filter toggle and search */}
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Input
            placeholder="Search memories..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            className="pr-8"
          />
          {searchText && (
            <button
              onClick={() => setSearchText('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
        <Button
          variant={hasActiveFilters() ? 'default' : 'outline'}
          size="sm"
          onClick={() => setExpanded(!expanded)}
        >
          <Filter className="h-4 w-4 mr-2" />
          Filters
          {hasActiveFilters() && (
            <Badge variant="secondary" className="ml-2">
              {activeFilters.length}
            </Badge>
          )}
          {expanded ? (
            <ChevronUp className="h-4 w-4 ml-2" />
          ) : (
            <ChevronDown className="h-4 w-4 ml-2" />
          )}
        </Button>
      </div>

      {/* Active filters chips */}
      {activeFilters.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {activeFilters.map((filter, index) => (
            <Badge key={index} variant="secondary" className="gap-1">
              {filter}
              <button
                onClick={() => {
                  // Parse and remove the specific filter
                  if (filter.startsWith('Type:')) {
                    setMemoryType('all');
                  } else if (filter.startsWith('Date:')) {
                    setDateRange({});
                  } else if (filter.startsWith('Search:')) {
                    setSearchText('');
                  } else {
                    const key = filter.split(':')[0];
                    removeMetadataFilter(key);
                  }
                }}
                className="ml-1 hover:text-destructive"
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
          <Button variant="ghost" size="sm" onClick={clearFilters}>
            Clear all
          </Button>
        </div>
      )}

      {/* Expanded filters panel */}
      {expanded && (
        <div className="rounded-md border p-4 space-y-4 bg-muted/30">
          {/* Type filter */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Memory Type</label>
            <select
              value={memoryType}
              onChange={(e) => setMemoryType(e.target.value as MemoryType | 'all')}
              className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm"
            >
              <option value="all">All Types</option>
              {MEMORY_TYPES.map((type) => (
                <option key={type} value={type}>
                  {type.replace('_', ' ')}
                </option>
              ))}
            </select>
          </div>

          {/* Date range filter */}
          <div className="space-y-2">
            <label className="text-sm font-medium flex items-center gap-2">
              <Calendar className="h-4 w-4" />
              Date Range
            </label>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs text-muted-foreground">From</label>
                <Input
                  type="date"
                  value={dateRange.start || ''}
                  onChange={(e) => setDateRange({ ...dateRange, start: e.target.value || undefined })}
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground">To</label>
                <Input
                  type="date"
                  value={dateRange.end || ''}
                  onChange={(e) => setDateRange({ ...dateRange, end: e.target.value || undefined })}
                />
              </div>
            </div>
          </div>

          {/* Metadata filters */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Metadata Filters</label>
            <div className="space-y-2">
              {Object.entries(metadataFilters).map(([key, value]) => (
                <div key={key} className="flex gap-2">
                  <Input
                    value={key}
                    disabled
                    className="w-1/3 bg-muted"
                  />
                  <Input
                    value={value}
                    onChange={(e) => setMetadataFilter(key, e.target.value)}
                    className="flex-1"
                  />
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => removeMetadataFilter(key)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              ))}
              <AddMetadataFilter
                onAdd={(key, value) => setMetadataFilter(key, value)}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

interface AddMetadataFilterProps {
  onAdd: (key: string, value: string) => void;
}

function AddMetadataFilter({ onAdd }: AddMetadataFilterProps) {
  const [key, setKey] = useState('');
  const [value, setValue] = useState('');

  const handleAdd = () => {
    if (key && value) {
      onAdd(key, value);
      setKey('');
      setValue('');
    }
  };

  return (
    <div className="flex gap-2">
      <Input
        placeholder="Key"
        value={key}
        onChange={(e) => setKey(e.target.value)}
        className="w-1/3"
      />
      <Input
        placeholder="Value"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
        className="flex-1"
      />
      <Button
        variant="outline"
        size="icon"
        onClick={handleAdd}
        disabled={!key || !value}
      >
        +
      </Button>
    </div>
  );
}

export default MemoryFilters;
