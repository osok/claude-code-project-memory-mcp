/**
 * Node Details Component
 *
 * Shows detailed information about a selected graph node.
 */
import { ExternalLink, GitBranch, Copy } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useUIStore } from '@/stores/ui-store';
import { cn, getMemoryTypeColor, copyToClipboard, truncate } from '@/lib/utils';
import type { GraphNode, MemoryType } from '@/types';

interface NodeDetailsProps {
  node: GraphNode | null;
  connectedNodesCount?: number;
  onViewFull?: (node: GraphNode) => void;
  onExpandNeighbors?: (node: GraphNode) => void;
  onClose?: () => void;
  className?: string;
}

export function NodeDetails({
  node,
  connectedNodesCount = 0,
  onViewFull,
  onExpandNeighbors,
  onClose,
  className
}: NodeDetailsProps) {
  const { addToast } = useUIStore();

  if (!node) {
    return (
      <div className={cn('rounded-md border bg-card p-4', className)}>
        <div className="text-center text-muted-foreground py-8">
          <p className="text-sm">Click on a node to see details</p>
        </div>
      </div>
    );
  }

  const handleCopyId = async () => {
    const success = await copyToClipboard(node.id);
    if (success) {
      addToast({ title: 'Node ID copied', variant: 'success', duration: 2000 });
    }
  };

  const formatValue = (value: unknown): string => {
    if (value === null || value === undefined) return '-';
    if (typeof value === 'boolean') return value ? 'Yes' : 'No';
    if (typeof value === 'object') return JSON.stringify(value);
    return String(value);
  };

  // Filter out internal/empty metadata
  const displayMetadata = Object.entries(node.metadata || {}).filter(
    ([key, value]) =>
      value !== null &&
      value !== undefined &&
      value !== '' &&
      !key.startsWith('_')
  );

  return (
    <div className={cn('rounded-md border bg-card', className)}>
      {/* Header */}
      <div className="p-4 border-b">
        <div className="flex items-start justify-between gap-2">
          <div className="space-y-1">
            <Badge
              variant={node.type as MemoryType}
              className="mb-1"
            >
              {node.type}
            </Badge>
            <h3 className="font-medium text-sm leading-tight">
              {truncate(node.label, 50)}
            </h3>
          </div>
          <div
            className="w-4 h-4 rounded-full shrink-0 mt-1"
            style={{ backgroundColor: getMemoryTypeColor(node.type) }}
          />
        </div>

        {/* ID with copy */}
        <div className="flex items-center gap-1 mt-2">
          <code className="text-xs font-mono text-muted-foreground truncate">
            {node.id}
          </code>
          <Button
            variant="ghost"
            size="icon"
            className="h-5 w-5 shrink-0"
            onClick={handleCopyId}
          >
            <Copy className="h-3 w-3" />
          </Button>
        </div>
      </div>

      {/* Connection info */}
      <div className="px-4 py-2 border-b bg-muted/30">
        <div className="flex items-center gap-2 text-sm">
          <GitBranch className="h-4 w-4 text-muted-foreground" />
          <span>{connectedNodesCount} connected nodes</span>
          {node.distance !== undefined && (
            <span className="text-muted-foreground">
              (depth: {node.distance})
            </span>
          )}
        </div>
      </div>

      {/* Metadata */}
      {displayMetadata.length > 0 && (
        <div className="p-4 border-b">
          <h4 className="text-xs font-medium text-muted-foreground mb-2">
            METADATA
          </h4>
          <div className="space-y-1">
            {displayMetadata.slice(0, 6).map(([key, value]) => (
              <div key={key} className="flex gap-2 text-xs">
                <span className="font-medium text-muted-foreground min-w-[80px]">
                  {key}:
                </span>
                <span className="truncate" title={formatValue(value)}>
                  {truncate(formatValue(value), 40)}
                </span>
              </div>
            ))}
            {displayMetadata.length > 6 && (
              <p className="text-xs text-muted-foreground">
                +{displayMetadata.length - 6} more fields
              </p>
            )}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="p-4 space-y-2">
        <Button
          variant="default"
          size="sm"
          className="w-full"
          onClick={() => onViewFull?.(node)}
        >
          <ExternalLink className="h-4 w-4 mr-2" />
          View Full Details
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="w-full"
          onClick={() => onExpandNeighbors?.(node)}
        >
          <GitBranch className="h-4 w-4 mr-2" />
          Expand Neighbors
        </Button>
      </div>
    </div>
  );
}

export default NodeDetails;
