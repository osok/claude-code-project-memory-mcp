/**
 * Graph Legend Component
 *
 * Shows color legend for memory types and relationship types.
 * Only displays types that are actually present in the graph data.
 */
import { useState, useMemo } from 'react';
import { ChevronDown, ChevronUp, CircleDot, ArrowRight } from 'lucide-react';
import type { MemoryType, GraphNode, GraphEdge } from '@/types';
import { cn, getMemoryTypeColor } from '@/lib/utils';

// Relationship type descriptions (used when relationships exist)
const RELATIONSHIP_DESCRIPTIONS: Record<string, string> = {
  'IMPLEMENTS': 'Implementation of requirement',
  'IMPLEMENTS_REQ': 'Implementation of requirement',
  'DEPENDS_ON': 'Dependency relationship',
  'EXTENDS': 'Extension/inheritance',
  'CALLS': 'Function/method call',
  'TESTS': 'Test coverage',
  'VERIFIES': 'Verification relationship',
  'RELATED_TO': 'General relationship',
  'CONTAINS': 'Container relationship',
  'USES': 'Usage relationship'
};

interface GraphLegendProps {
  /** Nodes in the current graph (to derive available types) */
  nodes?: GraphNode[];
  /** Edges in the current graph (to derive relationship types) */
  edges?: GraphEdge[];
  onTypeClick?: (type: MemoryType) => void;
  onRelationshipClick?: (type: string) => void;
  activeTypes?: MemoryType[];
  activeRelationships?: string[];
  className?: string;
}

export function GraphLegend({
  nodes = [],
  edges = [],
  onTypeClick,
  onRelationshipClick,
  activeTypes = [],
  activeRelationships = [],
  className
}: GraphLegendProps) {
  const [expandedNodes, setExpandedNodes] = useState(true);
  const [expandedEdges, setExpandedEdges] = useState(true);

  // Compute node type counts from actual data
  const nodeTypeCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const node of nodes) {
      const type = node.type || 'unknown';
      counts.set(type, (counts.get(type) || 0) + 1);
    }
    return counts;
  }, [nodes]);

  // Compute relationship type counts from actual data
  const edgeTypeCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const edge of edges) {
      const type = edge.type || edge.label || 'unknown';
      counts.set(type, (counts.get(type) || 0) + 1);
    }
    return counts;
  }, [edges]);

  // Get available types (only those in the data)
  const availableNodeTypes = useMemo(() => {
    return Array.from(nodeTypeCounts.keys()).sort();
  }, [nodeTypeCounts]);

  const availableEdgeTypes = useMemo(() => {
    return Array.from(edgeTypeCounts.keys()).sort();
  }, [edgeTypeCounts]);

  const formatTypeName = (type: string): string => {
    return type
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  return (
    <div className={cn('rounded-md border bg-card', className)}>
      {/* Node types section */}
      <div className="border-b">
        <button
          onClick={() => setExpandedNodes(!expandedNodes)}
          className="flex items-center justify-between w-full p-3 hover:bg-muted/50"
        >
          <div className="flex items-center gap-2">
            <CircleDot className="h-4 w-4" />
            <span className="font-medium text-sm">Node Types</span>
            <span className="text-xs text-muted-foreground">({nodes.length})</span>
          </div>
          {expandedNodes ? (
            <ChevronUp className="h-4 w-4" />
          ) : (
            <ChevronDown className="h-4 w-4" />
          )}
        </button>

        {expandedNodes && (
          <div className="px-3 pb-3 space-y-1">
            {availableNodeTypes.length === 0 ? (
              <p className="text-xs text-muted-foreground py-2">No nodes in graph</p>
            ) : (
              availableNodeTypes.map((type) => {
                const count = nodeTypeCounts.get(type) || 0;
                const isActive = activeTypes.length === 0 || activeTypes.includes(type as MemoryType);
                return (
                  <button
                    key={type}
                    onClick={() => onTypeClick?.(type as MemoryType)}
                    className={cn(
                      'flex items-center gap-2 w-full p-1.5 rounded text-left transition-opacity',
                      'hover:bg-muted',
                      !isActive && 'opacity-40'
                    )}
                  >
                    <span
                      className="w-3 h-3 rounded-full shrink-0"
                      style={{ backgroundColor: getMemoryTypeColor(type as MemoryType) }}
                    />
                    <span className="text-xs flex-1">{formatTypeName(type)}</span>
                    <span className="text-xs text-muted-foreground">{count}</span>
                  </button>
                );
              })
            )}
          </div>
        )}
      </div>

      {/* Relationship types section */}
      <div>
        <button
          onClick={() => setExpandedEdges(!expandedEdges)}
          className="flex items-center justify-between w-full p-3 hover:bg-muted/50"
        >
          <div className="flex items-center gap-2">
            <ArrowRight className="h-4 w-4" />
            <span className="font-medium text-sm">Relationships</span>
            <span className="text-xs text-muted-foreground">({edges.length})</span>
          </div>
          {expandedEdges ? (
            <ChevronUp className="h-4 w-4" />
          ) : (
            <ChevronDown className="h-4 w-4" />
          )}
        </button>

        {expandedEdges && (
          <div className="px-3 pb-3 space-y-1">
            {availableEdgeTypes.length === 0 ? (
              <p className="text-xs text-muted-foreground py-2">No relationships in graph</p>
            ) : (
              availableEdgeTypes.map((type) => {
                const count = edgeTypeCounts.get(type) || 0;
                const description = RELATIONSHIP_DESCRIPTIONS[type] || 'Custom relationship';
                const isActive = activeRelationships.length === 0 || activeRelationships.includes(type);
                return (
                  <button
                    key={type}
                    onClick={() => onRelationshipClick?.(type)}
                    className={cn(
                      'flex flex-col w-full p-1.5 rounded text-left transition-opacity',
                      'hover:bg-muted',
                      !isActive && 'opacity-40'
                    )}
                    title={description}
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className="text-xs font-medium">{type}</span>
                      <span className="text-xs text-muted-foreground">{count}</span>
                    </div>
                    <span className="text-[10px] text-muted-foreground">{description}</span>
                  </button>
                );
              })
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default GraphLegend;
