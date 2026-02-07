/**
 * Graph Controls Component
 *
 * Control buttons for the graph visualization (zoom, layout, etc).
 */
import { useState } from 'react';
import {
  ZoomIn,
  ZoomOut,
  Maximize,
  RefreshCw,
  Pause,
  Play,
  LayoutGrid,
  Network
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

export type LayoutType = 'force' | 'hierarchical';

interface GraphControlsProps {
  onZoomIn: () => void;
  onZoomOut: () => void;
  onFit: () => void;
  onResetView: () => void;
  onTogglePhysics: (enabled: boolean) => void;
  onLayoutChange: (layout: LayoutType) => void;
  onRefresh: () => void;
  isLoading?: boolean;
  nodeCount?: number;
  edgeCount?: number;
  className?: string;
}

export function GraphControls({
  onZoomIn,
  onZoomOut,
  onFit,
  onResetView,
  onTogglePhysics,
  onLayoutChange,
  onRefresh,
  isLoading = false,
  nodeCount = 0,
  edgeCount = 0,
  className
}: GraphControlsProps) {
  const [physicsEnabled, setPhysicsEnabled] = useState(true);
  const [currentLayout, setCurrentLayout] = useState<LayoutType>('force');

  const handleTogglePhysics = () => {
    const newState = !physicsEnabled;
    setPhysicsEnabled(newState);
    onTogglePhysics(newState);
  };

  const handleLayoutChange = (layout: LayoutType) => {
    setCurrentLayout(layout);
    onLayoutChange(layout);
    // Disable physics for hierarchical layout
    if (layout === 'hierarchical') {
      setPhysicsEnabled(false);
      onTogglePhysics(false);
    }
  };

  return (
    <div className={cn('flex items-center gap-2 flex-wrap', className)}>
      {/* Zoom controls */}
      <div className="flex items-center gap-1 border rounded-md p-1">
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={onZoomIn}
          title="Zoom in"
        >
          <ZoomIn className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={onZoomOut}
          title="Zoom out"
        >
          <ZoomOut className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={onFit}
          title="Fit to screen"
        >
          <Maximize className="h-4 w-4" />
        </Button>
      </div>

      {/* Layout controls */}
      <div className="flex items-center gap-1 border rounded-md p-1">
        <Button
          variant={currentLayout === 'force' ? 'secondary' : 'ghost'}
          size="icon"
          className="h-8 w-8"
          onClick={() => handleLayoutChange('force')}
          title="Force-directed layout"
        >
          <Network className="h-4 w-4" />
        </Button>
        <Button
          variant={currentLayout === 'hierarchical' ? 'secondary' : 'ghost'}
          size="icon"
          className="h-8 w-8"
          onClick={() => handleLayoutChange('hierarchical')}
          title="Hierarchical layout"
        >
          <LayoutGrid className="h-4 w-4" />
        </Button>
      </div>

      {/* Physics toggle */}
      <Button
        variant={physicsEnabled ? 'secondary' : 'outline'}
        size="sm"
        onClick={handleTogglePhysics}
        title={physicsEnabled ? 'Pause physics simulation' : 'Resume physics simulation'}
        disabled={currentLayout === 'hierarchical'}
      >
        {physicsEnabled ? (
          <>
            <Pause className="h-4 w-4 mr-1" />
            Physics
          </>
        ) : (
          <>
            <Play className="h-4 w-4 mr-1" />
            Physics
          </>
        )}
      </Button>

      {/* Refresh */}
      <Button
        variant="outline"
        size="sm"
        onClick={onRefresh}
        disabled={isLoading}
      >
        <RefreshCw className={cn('h-4 w-4 mr-1', isLoading && 'animate-spin')} />
        Refresh
      </Button>

      {/* Stats */}
      <div className="text-sm text-muted-foreground ml-auto">
        {nodeCount} nodes, {edgeCount} edges
      </div>
    </div>
  );
}

export default GraphControls;
