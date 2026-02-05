/**
 * Detail Panel
 *
 * Resizable slide-out panel for viewing memory details.
 * REQ-007-FN-010: Expandable details panel
 */
import { ReactNode, useEffect, useState, useRef, useCallback } from 'react';
import { X, GripVertical } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { useUIStore } from '@/stores/ui-store';

interface DetailPanelProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
}

const MIN_WIDTH = 320;
const MAX_WIDTH = 800;

export function DetailPanel({ open, onClose, title, children }: DetailPanelProps) {
  const { detailPanelPixelWidth, setDetailPanelPixelWidth } = useUIStore();
  const [isDragging, setIsDragging] = useState(false);
  const panelRef = useRef<HTMLElement>(null);
  const dragStartX = useRef(0);
  const dragStartWidth = useRef(0);

  // Handle Escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && open) {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [open, onClose]);

  // Handle resize drag
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
    dragStartX.current = e.clientX;
    dragStartWidth.current = detailPanelPixelWidth;
  }, [detailPanelPixelWidth]);

  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      // Calculate new width (dragging left increases width, right decreases)
      const delta = dragStartX.current - e.clientX;
      const newWidth = Math.max(MIN_WIDTH, Math.min(MAX_WIDTH, dragStartWidth.current + delta));
      setDetailPanelPixelWidth(newWidth);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    // Prevent text selection while dragging
    document.body.style.userSelect = 'none';
    document.body.style.cursor = 'ew-resize';

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
    };
  }, [isDragging, setDetailPanelPixelWidth]);

  if (!open) return null;

  return (
    <>
      {/* Backdrop for mobile */}
      <div
        className="fixed inset-0 z-40 bg-black/50 md:hidden"
        onClick={onClose}
      />

      {/* Panel */}
      <aside
        ref={panelRef}
        className={cn(
          'fixed right-0 top-14 bottom-8 z-50 flex flex-col border-l bg-background shadow-lg transition-transform duration-300',
          open ? 'translate-x-0' : 'translate-x-full'
        )}
        style={{ width: `${detailPanelPixelWidth}px` }}
      >
        {/* Resize Handle */}
        <div
          className={cn(
            'absolute left-0 top-0 bottom-0 w-1 cursor-ew-resize group hover:bg-primary/30 transition-colors z-10',
            isDragging && 'bg-primary/50'
          )}
          onMouseDown={handleMouseDown}
          role="separator"
          aria-orientation="vertical"
          aria-label="Resize panel"
        >
          <div className={cn(
            'absolute left-0 top-1/2 -translate-y-1/2 -translate-x-1/2 p-1 rounded bg-border opacity-0 group-hover:opacity-100 transition-opacity',
            isDragging && 'opacity-100'
          )}>
            <GripVertical className="h-4 w-4 text-muted-foreground" />
          </div>
        </div>

        {/* Header */}
        <div className="flex items-center justify-between border-b px-4 py-3">
          <h2 className="font-semibold">{title || 'Details'}</h2>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-4">
          {children}
        </div>
      </aside>
    </>
  );
}
