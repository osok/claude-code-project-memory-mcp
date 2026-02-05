/**
 * Memory Detail Component
 *
 * Displays full details of a selected memory in the detail panel.
 * Supports expand view, syntax highlighting, and markdown rendering.
 * REQ-007-FN-010 to REQ-007-FN-012
 */
import { useState } from 'react';
import { Copy, Edit, Trash2, ExternalLink, Clock, Calendar, Maximize2, ChevronDown, ChevronRight, FileCode, Tag } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useMemory } from '@/hooks/use-memories';
import { useRelatedNodes } from '@/hooks/use-graph';
import { cn, formatDate, formatRelativeTime, copyToClipboard, truncate } from '@/lib/utils';
import { useUIStore } from '@/stores/ui-store';
import { SyntaxHighlighter } from '@/components/common/SyntaxHighlighter';
import { MarkdownRenderer, isMarkdownContent } from '@/components/common/MarkdownRenderer';
import { ExpandedDetailPanel } from '@/components/layout/ExpandedDetailPanel';
import type { MemoryType } from '@/types';

interface MemoryDetailProps {
  type: string;
  id: string;
  onEdit?: () => void;
  onDelete?: () => void;
  onNavigate?: (type: string, id: string) => void;
}

export function MemoryDetail({ type, id, onEdit, onDelete, onNavigate }: MemoryDetailProps) {
  const { data: memory, isLoading, error } = useMemory(type, id);
  const { data: related } = useRelatedNodes(id, 1);
  const { addToast } = useUIStore();
  const [isExpanded, setIsExpanded] = useState(false);
  const [showMetadata, setShowMetadata] = useState(true);
  const [showRelated, setShowRelated] = useState(false);

  const handleCopyId = async () => {
    const success = await copyToClipboard(id);
    if (success) {
      addToast({ title: 'ID copied to clipboard', variant: 'success', duration: 2000 });
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-6 bg-muted rounded w-1/2" />
        <div className="h-4 bg-muted rounded w-1/4" />
        <div className="h-32 bg-muted rounded" />
      </div>
    );
  }

  if (error || !memory) {
    return (
      <div className="text-center py-8">
        <p className="text-destructive">Failed to load memory</p>
        <p className="text-sm text-muted-foreground">{(error as Error)?.message || 'Unknown error'}</p>
      </div>
    );
  }

  // Extract key metadata for quick view
  const filePath = memory.metadata?.file_path as string | undefined;
  const language = memory.metadata?.language as string | undefined;
  const hasMetadata = Object.keys(memory.metadata).length > 0;
  const hasRelated = related && related.nodes.length > 0;

  // Prepare content and metadata sections for expanded view
  const contentSection = (
    <ContentDisplay
      content={memory.content}
      type={memory.type}
      metadata={memory.metadata}
      maxHeight="none"
    />
  );

  const metadataSection = (
    <>
      {/* Timestamps */}
      <div className="flex gap-4 text-sm text-muted-foreground mb-4">
        <div className="flex items-center gap-1">
          <Calendar className="h-4 w-4" />
          <span>Created {formatDate(memory.created_at)}</span>
        </div>
        <div className="flex items-center gap-1">
          <Clock className="h-4 w-4" />
          <span>Updated {formatRelativeTime(memory.updated_at)}</span>
        </div>
      </div>

      {/* Metadata Table */}
      {hasMetadata && (
        <div className="rounded-md border">
          <table className="w-full text-sm">
            <tbody>
              {Object.entries(memory.metadata).map(([key, value]) => (
                <tr key={key} className="border-b last:border-0">
                  <td className="px-3 py-2 font-medium bg-muted/50 w-1/3">{key}</td>
                  <td className="px-3 py-2 font-mono text-xs break-all">
                    {formatMetadataValue(value)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Related Memories */}
      {hasRelated && (
        <div className="mt-4">
          <h4 className="text-sm font-medium mb-2">Related Memories ({related.nodes.length})</h4>
          <div className="space-y-1 max-h-40 overflow-y-auto">
            {related.nodes.slice(0, 10).map((node) => (
              <button
                key={node.id}
                onClick={() => onNavigate?.(node.type, node.id)}
                className="flex items-center gap-2 w-full p-2 rounded hover:bg-muted text-left"
              >
                <Badge variant={node.type as MemoryType} className="shrink-0">
                  {node.type}
                </Badge>
                <span className="text-sm truncate">{node.label}</span>
                <ExternalLink className="h-3 w-3 ml-auto text-muted-foreground" />
              </button>
            ))}
          </div>
        </div>
      )}
    </>
  );

  return (
    <>
      {/* Expanded Modal View */}
      <ExpandedDetailPanel
        open={isExpanded}
        onClose={() => setIsExpanded(false)}
        title={`${memory.type} - ${memory.memory_id.slice(0, 8)}...`}
        contentSection={contentSection}
        metadataSection={metadataSection}
        actionsSection={
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={onEdit}>
              <Edit className="h-4 w-4 mr-2" />
              Edit
            </Button>
            <Button variant="destructive" size="sm" onClick={onDelete}>
              <Trash2 className="h-4 w-4 mr-2" />
              Delete
            </Button>
          </div>
        }
      />

      {/* Normal Detail View */}
      <div className="flex flex-col h-full">
        {/* Header - Fixed */}
        <div className="shrink-0 space-y-3 pb-3 border-b">
          {/* Type and Actions Row */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Badge variant={memory.type as MemoryType} className="text-sm">
                {memory.type}
              </Badge>
              {memory.deleted && (
                <Badge variant="destructive">Deleted</Badge>
              )}
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setIsExpanded(true)}
              title="Expand (full screen)"
            >
              <Maximize2 className="h-4 w-4" />
            </Button>
          </div>

          {/* ID Row */}
          <div className="flex items-center gap-2">
            <code className="text-xs font-mono bg-muted px-2 py-1 rounded truncate flex-1">
              {memory.memory_id}
            </code>
            <Button variant="ghost" size="icon" className="h-6 w-6 shrink-0" onClick={handleCopyId}>
              <Copy className="h-3 w-3" />
            </Button>
          </div>

          {/* Quick Info - File path and language if available */}
          {(filePath || language) && (
            <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
              {filePath && (
                <div className="flex items-center gap-1 bg-muted/50 px-2 py-1 rounded">
                  <FileCode className="h-3 w-3" />
                  <span className="truncate max-w-[200px]" title={filePath}>
                    {filePath.split('/').pop()}
                  </span>
                </div>
              )}
              {language && (
                <div className="flex items-center gap-1 bg-muted/50 px-2 py-1 rounded">
                  <Tag className="h-3 w-3" />
                  <span>{language}</span>
                </div>
              )}
            </div>
          )}

          {/* Timestamps */}
          <div className="flex gap-4 text-xs text-muted-foreground">
            <div className="flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              <span>{formatRelativeTime(memory.created_at)}</span>
            </div>
            <div className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              <span>Updated {formatRelativeTime(memory.updated_at)}</span>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={onEdit}>
              <Edit className="h-4 w-4 mr-2" />
              Edit
            </Button>
            <Button variant="destructive" size="sm" onClick={onDelete}>
              <Trash2 className="h-4 w-4 mr-2" />
              Delete
            </Button>
          </div>
        </div>

        {/* Scrollable Content Area */}
        <div className="flex-1 overflow-auto py-3 space-y-3">
          {/* Metadata Section - Collapsible */}
          {hasMetadata && (
            <div className="border rounded-md">
              <button
                className="w-full flex items-center justify-between px-3 py-2 text-sm font-medium hover:bg-muted/50"
                onClick={() => setShowMetadata(!showMetadata)}
              >
                <span>Metadata ({Object.keys(memory.metadata).length})</span>
                {showMetadata ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              </button>
              {showMetadata && (
                <div className="border-t">
                  <table className="w-full text-sm">
                    <tbody>
                      {Object.entries(memory.metadata).map(([key, value]) => (
                        <tr key={key} className="border-b last:border-0">
                          <td className="px-3 py-2 font-medium bg-muted/50 w-1/3 text-xs">{key}</td>
                          <td className="px-3 py-2 font-mono text-xs break-all">
                            {formatMetadataValue(value)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* Content Section */}
          <div className="space-y-2">
            <h3 className="font-semibold text-sm">Content</h3>
            <ContentDisplay
              content={memory.content}
              type={memory.type}
              metadata={memory.metadata}
              maxHeight="400px"
            />
          </div>

          {/* Related Memories - Collapsible */}
          {hasRelated && (
            <div className="border rounded-md">
              <button
                className="w-full flex items-center justify-between px-3 py-2 text-sm font-medium hover:bg-muted/50"
                onClick={() => setShowRelated(!showRelated)}
              >
                <span>Related Memories ({related.nodes.length})</span>
                {showRelated ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              </button>
              {showRelated && (
                <div className="border-t p-2 space-y-1">
                  {related.nodes.slice(0, 10).map((node) => (
                    <button
                      key={node.id}
                      onClick={() => onNavigate?.(node.type, node.id)}
                      className="flex items-center gap-2 w-full p-2 rounded hover:bg-muted text-left"
                    >
                      <Badge variant={node.type as MemoryType} className="shrink-0">
                        {node.type}
                      </Badge>
                      <span className="text-sm truncate">{node.label}</span>
                      <ExternalLink className="h-3 w-3 ml-auto text-muted-foreground" />
                    </button>
                  ))}
                  {related.nodes.length > 10 && (
                    <p className="text-xs text-muted-foreground text-center py-2">
                      + {related.nodes.length - 10} more
                    </p>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Relationships (edges) */}
          {related && related.edges.length > 0 && (
            <div className="space-y-2">
              <h3 className="font-semibold text-sm">Relationships</h3>
              <div className="space-y-1">
                {related.edges.map((edge) => (
                  <div key={edge.id} className="flex items-center gap-2 text-sm text-muted-foreground">
                    <span className="font-mono text-xs">{truncate(edge.from, 8)}</span>
                    <span className="px-2 py-0.5 bg-muted rounded text-xs">{edge.label}</span>
                    <span className="font-mono text-xs">{truncate(edge.to, 8)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

interface ContentDisplayProps {
  content: string;
  type: string;
  metadata?: Record<string, unknown>;
  maxHeight?: string;
}

function ContentDisplay({ content, type, metadata = {}, maxHeight = '400px' }: ContentDisplayProps) {
  const isCode = type === 'function' || type === 'code_pattern';

  // For code types, use syntax highlighting
  if (isCode) {
    const language = metadata.language as string | undefined;
    const filePath = metadata.file_path as string | undefined;

    return (
      <div
        className="overflow-auto rounded-md border"
        style={{ maxHeight: maxHeight !== 'none' ? maxHeight : undefined }}
      >
        <SyntaxHighlighter
          code={content}
          language={language}
          filePath={filePath}
          showLineNumbers={content.split('\n').length > 5}
        />
      </div>
    );
  }

  // For design, requirements, and other text types, check if markdown
  const looksLikeMarkdown = isMarkdownContent(content);

  if (looksLikeMarkdown) {
    return (
      <div
        className="overflow-auto"
        style={{ maxHeight: maxHeight !== 'none' ? maxHeight : undefined }}
      >
        <MarkdownRenderer
          content={content}
          showToggle={true}
          defaultView="rendered"
        />
      </div>
    );
  }

  // Plain text fallback
  return (
    <div
      className="bg-muted/50 p-3 rounded-md text-sm whitespace-pre-wrap break-words overflow-auto"
      style={{ maxHeight: maxHeight !== 'none' ? maxHeight : undefined }}
    >
      {content}
    </div>
  );
}

function formatMetadataValue(value: unknown): string {
  if (value === null || value === undefined) return '-';
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (typeof value === 'object') return JSON.stringify(value, null, 2);
  return String(value);
}

export default MemoryDetail;
