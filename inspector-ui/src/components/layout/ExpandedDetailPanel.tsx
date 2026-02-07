/**
 * Expanded Detail Panel Component
 *
 * Full-viewport modal for viewing memory details with a resizable
 * content/metadata split layout. REQ-007-FN-001 to REQ-007-FN-008
 */
import { ReactNode, useEffect, useState, useRef } from 'react';
import { X, Minimize2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface ExpandedDetailPanelProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  contentSection: ReactNode;
  metadataSection: ReactNode;
  actionsSection?: ReactNode;
}

const MIN_CONTENT_HEIGHT = 100;
const MIN_METADATA_HEIGHT = 100;
const DEFAULT_SPLIT_RATIO = 0.75; // 75% content, 25% metadata

export function ExpandedDetailPanel({
  open,
  onClose,
  title,
  contentSection,
  metadataSection,
  actionsSection
}: ExpandedDetailPanelProps) {
  const [splitRatio, setSplitRatio] = useState(DEFAULT_SPLIT_RATIO);
  const [isDragging, setIsDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && open) {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [open, onClose]);

  // Handle splitter drag
  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (!containerRef.current) return;

      const containerRect = containerRef.current.getBoundingClientRect();
      const containerHeight = containerRect.height;
      const mouseY = e.clientY - containerRect.top;

      // Calculate new ratio, clamping to ensure minimum sizes
      const minContentRatio = MIN_CONTENT_HEIGHT / containerHeight;
      const maxContentRatio = 1 - (MIN_METADATA_HEIGHT / containerHeight);
      const newRatio = Math.max(minContentRatio, Math.min(maxContentRatio, mouseY / containerHeight));

      setSplitRatio(newRatio);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging]);

  if (!open) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-50 bg-black/80"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Panel */}
      <div
        className="fixed inset-4 z-50 flex flex-col rounded-lg border bg-background shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="expanded-panel-title"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b px-6 py-4">
          <h2 id="expanded-panel-title" className="text-lg font-semibold">
            {title || 'Memory Details'}
          </h2>
          <div className="flex items-center gap-2">
            {actionsSection}
            <Button
              variant="ghost"
              size="icon"
              onClick={onClose}
              title="Collapse (Esc)"
            >
              <Minimize2 className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={onClose}
              title="Close"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Split Content Area */}
        <div
          ref={containerRef}
          className="flex-1 flex flex-col overflow-hidden"
        >
          {/* Content Section */}
          <div
            className="overflow-auto border-b"
            style={{ height: `${splitRatio * 100}%` }}
          >
            <div className="p-6">
              <h3 className="text-sm font-medium text-muted-foreground mb-3">
                Content
              </h3>
              {contentSection}
            </div>
          </div>

          {/* Resizable Splitter */}
          <div
            className={cn(
              'h-2 bg-border cursor-ns-resize flex items-center justify-center hover:bg-primary/20 transition-colors',
              isDragging && 'bg-primary/30'
            )}
            onMouseDown={handleMouseDown}
            role="separator"
            aria-orientation="horizontal"
            aria-label="Resize content and metadata sections"
          >
            <div className="w-12 h-1 rounded-full bg-muted-foreground/30" />
          </div>

          {/* Metadata Section */}
          <div
            className="overflow-auto"
            style={{ height: `${(1 - splitRatio) * 100}%` }}
          >
            <div className="p-6">
              <h3 className="text-sm font-medium text-muted-foreground mb-3">
                Metadata
              </h3>
              {metadataSection}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

export default ExpandedDetailPanel;
