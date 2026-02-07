/**
 * Graph Canvas Component
 *
 * vis-network wrapper component for graph visualization.
 */
import { useEffect, useRef, useImperativeHandle, forwardRef, useCallback } from 'react';
import { Network, DataSet, Options, Data } from 'vis-network/standalone';
import { getMemoryTypeColor, MEMORY_TYPE_COLORS } from '@/lib/utils';
import type { GraphData, GraphNode, GraphEdge } from '@/types';

// Create vis-network groups config from our color map
const VIS_GROUPS: Record<string, { color: { background: string; border: string; highlight: { background: string }; hover: { background: string } } }> = {};
for (const [type, color] of Object.entries(MEMORY_TYPE_COLORS)) {
  VIS_GROUPS[type] = {
    color: {
      background: color,
      border: color,
      highlight: { background: color },
      hover: { background: color }
    }
  };
}

export interface GraphCanvasRef {
  network: Network | null;
  zoomIn: () => void;
  zoomOut: () => void;
  fit: () => void;
  resetView: () => void;
  togglePhysics: (enabled: boolean) => void;
  setLayout: (layout: 'force' | 'hierarchical') => void;
  selectNode: (nodeId: string) => void;
  highlightPath: (nodeIds: string[]) => void;
  clearHighlight: () => void;
}

interface GraphCanvasProps {
  data: GraphData | null;
  isLoading?: boolean;
  onNodeClick?: (node: GraphNode) => void;
  onNodeDoubleClick?: (node: GraphNode) => void;
  onEdgeClick?: (edge: GraphEdge) => void;
  onBackgroundClick?: () => void;
  selectedNodeId?: string | null;
  highlightedNodeIds?: string[];
  className?: string;
}

export const GraphCanvas = forwardRef<GraphCanvasRef, GraphCanvasProps>(
  function GraphCanvas(
    {
      data,
      isLoading = false,
      onNodeClick,
      onNodeDoubleClick,
      onEdgeClick,
      onBackgroundClick,
      selectedNodeId,
      highlightedNodeIds = [],
      className
    },
    ref
  ) {
    const containerRef = useRef<HTMLDivElement>(null);
    const networkRef = useRef<Network | null>(null);
    const nodesDataSetRef = useRef<DataSet<unknown> | null>(null);
    const edgesDataSetRef = useRef<DataSet<unknown> | null>(null);
    const dataRef = useRef<GraphData | null>(null);

    // Keep data reference updated
    dataRef.current = data;

    // Create network options
    const getOptions = useCallback((layout: 'force' | 'hierarchical' = 'force'): Options => {
      const baseOptions: Options = {
        groups: VIS_GROUPS,
        nodes: {
          shape: 'dot',
          size: 20,
          font: {
            size: 12,
            color: 'hsl(var(--foreground))',
            face: 'system-ui, sans-serif'
          },
          borderWidth: 2,
          borderWidthSelected: 3,
          shadow: true
        },
        edges: {
          font: {
            size: 10,
            align: 'middle',
            color: 'hsl(var(--muted-foreground))'
          },
          smooth: {
            type: 'curvedCW',
            roundness: 0.2
          },
          arrows: {
            to: {
              enabled: true,
              scaleFactor: 0.5
            }
          },
          color: {
            color: 'hsl(var(--border))',
            highlight: 'hsl(var(--primary))',
            hover: 'hsl(var(--primary))'
          }
        },
        interaction: {
          hover: true,
          tooltipDelay: 200,
          zoomView: true,
          dragView: true,
          selectConnectedEdges: true,
          hoverConnectedEdges: true
        },
        physics: {
          enabled: true,
          solver: 'repulsion',
          repulsion: {
            nodeDistance: 300,
            centralGravity: 0.01,
            springLength: 400,
            springConstant: 0.001,
            damping: 0.09
          },
          stabilization: {
            enabled: true,
            iterations: 500,
            updateInterval: 25
          }
        }
      };

      if (layout === 'hierarchical') {
        baseOptions.layout = {
          hierarchical: {
            enabled: true,
            direction: 'UD',
            sortMethod: 'directed',
            nodeSpacing: 150,
            levelSeparation: 150
          }
        };
        baseOptions.physics = {
          enabled: false
        };
      }

      return baseOptions;
    }, []);

    // Initialize or update network
    useEffect(() => {
      if (!containerRef.current || !data) return;

      // Transform nodes for vis-network with random initial positions
      const nodes = data.nodes.map((node, index) => ({
        id: node.id,
        label: node.label.length > 30 ? node.label.substring(0, 27) + '...' : node.label,
        title: `${node.type}: ${node.label}`,
        // Spread nodes in a circle to give physics a good starting point
        x: Math.cos(2 * Math.PI * index / data.nodes.length) * 500 + (Math.random() - 0.5) * 200,
        y: Math.sin(2 * Math.PI * index / data.nodes.length) * 500 + (Math.random() - 0.5) * 200,
        color: {
          background: getMemoryTypeColor(node.type),
          border: getMemoryTypeColor(node.type),
          highlight: {
            background: getMemoryTypeColor(node.type),
            border: 'hsl(var(--primary))'
          },
          hover: {
            background: getMemoryTypeColor(node.type),
            border: 'hsl(var(--primary))'
          }
        },
        group: node.type
      }));

      // Transform edges for vis-network
      const edges = data.edges.map(edge => ({
        id: edge.id,
        from: edge.from,
        to: edge.to,
        label: edge.label,
        title: edge.type
      }));

      // Create or update datasets
      if (networkRef.current) {
        // Update existing network
        nodesDataSetRef.current?.clear();
        nodesDataSetRef.current?.add(nodes);
        edgesDataSetRef.current?.clear();
        edgesDataSetRef.current?.add(edges);
      } else {
        // Create new network
        nodesDataSetRef.current = new DataSet(nodes);
        edgesDataSetRef.current = new DataSet(edges);

        const networkData: Data = {
          nodes: nodesDataSetRef.current,
          edges: edgesDataSetRef.current
        };

        networkRef.current = new Network(
          containerRef.current,
          networkData,
          getOptions()
        );

        // Event handlers
        networkRef.current.on('click', (params) => {
          if (params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            const node = dataRef.current?.nodes.find(n => n.id === nodeId);
            if (node && onNodeClick) {
              onNodeClick(node);
            }
          } else if (params.edges.length > 0) {
            const edgeId = params.edges[0];
            const edge = dataRef.current?.edges.find(e => e.id === edgeId);
            if (edge && onEdgeClick) {
              onEdgeClick(edge);
            }
          } else {
            onBackgroundClick?.();
          }
        });

        networkRef.current.on('doubleClick', (params) => {
          if (params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            const node = dataRef.current?.nodes.find(n => n.id === nodeId);
            if (node && onNodeDoubleClick) {
              onNodeDoubleClick(node);
            }
          }
        });
      }

      return () => {
        // Cleanup on unmount only
      };
    }, [data, getOptions, onNodeClick, onNodeDoubleClick, onEdgeClick, onBackgroundClick]);

    // Cleanup on unmount
    useEffect(() => {
      return () => {
        networkRef.current?.destroy();
        networkRef.current = null;
      };
    }, []);

    // Handle selected node highlighting
    useEffect(() => {
      if (!networkRef.current || !selectedNodeId) return;
      networkRef.current.selectNodes([selectedNodeId]);
    }, [selectedNodeId]);

    // Handle highlighted nodes (for path tracing)
    useEffect(() => {
      if (!networkRef.current || !nodesDataSetRef.current) return;

      const allNodeIds = data?.nodes.map(n => n.id) || [];

      if (highlightedNodeIds.length === 0) {
        // Reset all nodes to normal opacity
        const updates = allNodeIds.map(id => ({
          id,
          opacity: 1
        }));
        nodesDataSetRef.current.update(updates);
      } else {
        // Dim non-highlighted nodes
        const updates = allNodeIds.map(id => ({
          id,
          opacity: highlightedNodeIds.includes(id) ? 1 : 0.3
        }));
        nodesDataSetRef.current.update(updates);
      }
    }, [highlightedNodeIds, data]);

    // Expose methods via ref
    useImperativeHandle(ref, () => ({
      network: networkRef.current,

      zoomIn: () => {
        const scale = networkRef.current?.getScale() || 1;
        networkRef.current?.moveTo({ scale: scale * 1.3 });
      },

      zoomOut: () => {
        const scale = networkRef.current?.getScale() || 1;
        networkRef.current?.moveTo({ scale: scale / 1.3 });
      },

      fit: () => {
        networkRef.current?.fit({
          animation: {
            duration: 500,
            easingFunction: 'easeInOutQuad'
          }
        });
      },

      resetView: () => {
        networkRef.current?.fit();
        networkRef.current?.moveTo({
          position: { x: 0, y: 0 },
          scale: 1
        });
      },

      togglePhysics: (enabled: boolean) => {
        networkRef.current?.setOptions({
          physics: { enabled }
        });
      },

      setLayout: (layout: 'force' | 'hierarchical') => {
        networkRef.current?.setOptions(getOptions(layout));
        if (layout === 'force') {
          networkRef.current?.stabilize();
        }
      },

      selectNode: (nodeId: string) => {
        networkRef.current?.selectNodes([nodeId]);
        networkRef.current?.focus(nodeId, {
          scale: 1.5,
          animation: {
            duration: 500,
            easingFunction: 'easeInOutQuad'
          }
        });
      },

      highlightPath: (nodeIds: string[]) => {
        if (!nodesDataSetRef.current || !data) return;

        const allNodeIds = data.nodes.map(n => n.id);
        const updates = allNodeIds.map(id => ({
          id,
          opacity: nodeIds.includes(id) ? 1 : 0.2
        }));
        nodesDataSetRef.current.update(updates);
      },

      clearHighlight: () => {
        if (!nodesDataSetRef.current || !data) return;

        const updates = data.nodes.map(n => ({
          id: n.id,
          opacity: 1
        }));
        nodesDataSetRef.current.update(updates);
      }
    }), [data, getOptions]);

    return (
      <div className={className}>
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/50 z-10">
            <div className="flex flex-col items-center gap-2">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
              <span className="text-sm text-muted-foreground">Loading graph...</span>
            </div>
          </div>
        )}
        <div
          ref={containerRef}
          className="w-full h-full"
          style={{ minHeight: '400px' }}
        />
      </div>
    );
  }
);

export default GraphCanvas;
