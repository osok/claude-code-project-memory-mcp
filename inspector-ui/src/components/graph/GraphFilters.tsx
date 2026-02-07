/**
 * Graph Filters Component
 *
 * Filter controls for the graph visualization.
 */
import { useState } from 'react';
import { Filter, X, ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { MEMORY_TYPES, type MemoryType } from '@/types';
import { cn, getMemoryTypeColor } from '@/lib/utils';

// Common relationship types in the memory system
const RELATIONSHIP_TYPES = [
  'IMPLEMENTS',
  'DEPENDS_ON',
  'EXTENDS',
  'CALLS',
  'TESTS',
  'RELATED_TO',
  'CONTAINS',
  'USES'
] as const;

type RelationshipType = typeof RELATIONSHIP_TYPES[number];

export interface GraphFilterState {
  types: MemoryType[];
  relationshipTypes: string[];
  depth: number;
  limit: number;
  showOrphans: boolean;
}

interface GraphFiltersProps {
  filters: GraphFilterState;
  onChange: (filters: GraphFilterState) => void;
  onApply: () => void;
  className?: string;
}

export function GraphFilters({
  filters,
  onChange,
  onApply,
  className
}: GraphFiltersProps) {
  const [expanded, setExpanded] = useState(true);

  const handleTypeToggle = (type: MemoryType) => {
    const newTypes = filters.types.includes(type)
      ? filters.types.filter(t => t !== type)
      : [...filters.types, type];
    onChange({ ...filters, types: newTypes });
  };

  const handleRelationshipToggle = (type: string) => {
    const newTypes = filters.relationshipTypes.includes(type)
      ? filters.relationshipTypes.filter(t => t !== type)
      : [...filters.relationshipTypes, type];
    onChange({ ...filters, relationshipTypes: newTypes });
  };

  const handleSelectAllTypes = () => {
    onChange({ ...filters, types: [...MEMORY_TYPES] });
  };

  const handleClearTypes = () => {
    onChange({ ...filters, types: [] });
  };

  const handleSelectAllRelationships = () => {
    onChange({ ...filters, relationshipTypes: [...RELATIONSHIP_TYPES] });
  };

  const handleClearRelationships = () => {
    onChange({ ...filters, relationshipTypes: [] });
  };

  const hasActiveFilters =
    filters.types.length > 0 ||
    filters.relationshipTypes.length > 0 ||
    filters.depth !== 2 ||
    filters.limit !== 100 ||
    !filters.showOrphans;

  return (
    <div className={cn('rounded-md border bg-card', className)}>
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center justify-between w-full p-3 hover:bg-muted/50"
      >
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4" />
          <span className="font-medium">Filters</span>
          {hasActiveFilters && (
            <Badge variant="secondary" className="text-xs">
              Active
            </Badge>
          )}
        </div>
        {expanded ? (
          <ChevronUp className="h-4 w-4" />
        ) : (
          <ChevronDown className="h-4 w-4" />
        )}
      </button>

      {/* Filter content */}
      {expanded && (
        <div className="p-3 pt-0 space-y-4">
          {/* Memory Types */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium">Memory Types</label>
              <div className="flex gap-1">
                <button
                  onClick={handleSelectAllTypes}
                  className="text-xs text-primary hover:underline"
                >
                  All
                </button>
                <span className="text-xs text-muted-foreground">/</span>
                <button
                  onClick={handleClearTypes}
                  className="text-xs text-primary hover:underline"
                >
                  None
                </button>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-1">
              {MEMORY_TYPES.map((type) => (
                <label
                  key={type}
                  className="flex items-center gap-2 p-1.5 rounded hover:bg-muted cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={filters.types.includes(type)}
                    onChange={() => handleTypeToggle(type)}
                    className="rounded"
                  />
                  <span
                    className="w-2 h-2 rounded-full"
                    style={{ backgroundColor: getMemoryTypeColor(type) }}
                  />
                  <span className="text-xs capitalize truncate">
                    {type.replace('_', ' ')}
                  </span>
                </label>
              ))}
            </div>
          </div>

          {/* Relationship Types */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium">Relationship Types</label>
              <div className="flex gap-1">
                <button
                  onClick={handleSelectAllRelationships}
                  className="text-xs text-primary hover:underline"
                >
                  All
                </button>
                <span className="text-xs text-muted-foreground">/</span>
                <button
                  onClick={handleClearRelationships}
                  className="text-xs text-primary hover:underline"
                >
                  None
                </button>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-1">
              {RELATIONSHIP_TYPES.map((type) => (
                <label
                  key={type}
                  className="flex items-center gap-2 p-1.5 rounded hover:bg-muted cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={filters.relationshipTypes.includes(type)}
                    onChange={() => handleRelationshipToggle(type)}
                    className="rounded"
                  />
                  <span className="text-xs">{type}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Depth slider */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium">Traversal Depth</label>
              <span className="text-sm text-muted-foreground">{filters.depth}</span>
            </div>
            <input
              type="range"
              min={1}
              max={5}
              value={filters.depth}
              onChange={(e) => onChange({ ...filters, depth: Number(e.target.value) })}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>1 hop</span>
              <span>5 hops</span>
            </div>
          </div>

          {/* Limit */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Node Limit</label>
            <select
              value={filters.limit}
              onChange={(e) => onChange({ ...filters, limit: Number(e.target.value) })}
              className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm"
            >
              <option value={50}>50 nodes</option>
              <option value={100}>100 nodes</option>
              <option value={200}>200 nodes</option>
              <option value={500}>500 nodes</option>
              <option value={1000}>1000 nodes</option>
            </select>
          </div>

          {/* Show orphans toggle */}
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={filters.showOrphans}
              onChange={(e) => onChange({ ...filters, showOrphans: e.target.checked })}
              className="rounded"
            />
            <span className="text-sm">Show orphan nodes</span>
          </label>

          {/* Apply button */}
          <Button onClick={onApply} className="w-full">
            Apply Filters
          </Button>
        </div>
      )}
    </div>
  );
}

export default GraphFilters;
