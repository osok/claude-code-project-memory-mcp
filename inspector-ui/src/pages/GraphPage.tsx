/**
 * Graph Page
 *
 * Graph visualization using vis-network with filters, controls, and tools.
 */
import { useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  GraphCanvas,
  GraphControls,
  GraphFilters,
  GraphLegend,
  NodeDetails,
  RequirementTrace,
  CypherEditor,
  type GraphCanvasRef,
  type GraphFilterState,
  type LayoutType
} from '@/components/graph';
import { useGraphOverview, useRelatedNodes } from '@/hooks/use-graph';
import type { GraphNode, GraphData, MemoryType } from '@/types';

export default function GraphPage() {
  const navigate = useNavigate();
  const canvasRef = useRef<GraphCanvasRef>(null);

  // State
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [highlightedNodeIds, setHighlightedNodeIds] = useState<string[]>([]);
  const [expandedNodeId, setExpandedNodeId] = useState<string | null>(null);
  const [cypherGraphData, setCypherGraphData] = useState<GraphData | null>(null);

  const [filters, setFilters] = useState<GraphFilterState>({
    types: [],
    relationshipTypes: [],
    depth: 2,
    limit: 100,
    showOrphans: true
  });

  // Queries
  const { data: graphData, isLoading, refetch } = useGraphOverview({
    types: filters.types.length > 0 ? filters.types : undefined,
    relationshipTypes: filters.relationshipTypes.length > 0 ? filters.relationshipTypes : undefined,
    limit: filters.limit
  });

  const { data: relatedData } = useRelatedNodes(
    expandedNodeId || '',
    filters.depth
  );

  // Merge data - use cypher results if available, otherwise use overview
  const displayData: GraphData | null = cypherGraphData || (relatedData ? {
    nodes: [...(graphData?.nodes || []), ...relatedData.nodes.filter(
      n => !graphData?.nodes.some(gn => gn.id === n.id)
    )],
    edges: [...(graphData?.edges || []), ...relatedData.edges.filter(
      e => !graphData?.edges.some(ge => ge.id === e.id)
    )]
  } : graphData) || null;

  // Handlers
  const handleNodeClick = useCallback((node: GraphNode) => {
    setSelectedNode(node);
  }, []);

  const handleNodeDoubleClick = useCallback((node: GraphNode) => {
    setExpandedNodeId(node.id);
    canvasRef.current?.selectNode(node.id);
  }, []);

  const handleBackgroundClick = useCallback(() => {
    setSelectedNode(null);
    setHighlightedNodeIds([]);
  }, []);

  const handleZoomIn = useCallback(() => {
    canvasRef.current?.zoomIn();
  }, []);

  const handleZoomOut = useCallback(() => {
    canvasRef.current?.zoomOut();
  }, []);

  const handleFit = useCallback(() => {
    canvasRef.current?.fit();
  }, []);

  const handleResetView = useCallback(() => {
    canvasRef.current?.resetView();
    setSelectedNode(null);
    setHighlightedNodeIds([]);
    setCypherGraphData(null);
    setExpandedNodeId(null);
  }, []);

  const handleTogglePhysics = useCallback((enabled: boolean) => {
    canvasRef.current?.togglePhysics(enabled);
  }, []);

  const handleLayoutChange = useCallback((layout: LayoutType) => {
    canvasRef.current?.setLayout(layout);
  }, []);

  const handleRefresh = useCallback(() => {
    setCypherGraphData(null);
    setExpandedNodeId(null);
    refetch();
  }, [refetch]);

  const handleApplyFilters = useCallback(() => {
    setCypherGraphData(null);
    setExpandedNodeId(null);
    refetch();
  }, [refetch]);

  const handleViewFullDetails = useCallback((node: GraphNode) => {
    navigate(`/browser/${node.type}?id=${node.id}`);
  }, [navigate]);

  const handleExpandNeighbors = useCallback((node: GraphNode) => {
    setExpandedNodeId(node.id);
    canvasRef.current?.selectNode(node.id);
  }, []);

  const handleHighlightPath = useCallback((nodeIds: string[]) => {
    setHighlightedNodeIds(nodeIds);
    if (nodeIds.length > 0) {
      canvasRef.current?.highlightPath(nodeIds);
    } else {
      canvasRef.current?.clearHighlight();
    }
  }, []);

  const handleCypherGraphResult = useCallback((graph: GraphData) => {
    setCypherGraphData(graph);
    setSelectedNode(null);
    setHighlightedNodeIds([]);
    // Fit the new graph into view
    setTimeout(() => {
      canvasRef.current?.fit();
    }, 100);
  }, []);

  const handleTypeFilterClick = useCallback((type: MemoryType) => {
    const newTypes = filters.types.includes(type)
      ? filters.types.filter(t => t !== type)
      : [...filters.types, type];
    setFilters(f => ({ ...f, types: newTypes }));
  }, [filters.types]);

  const handleRelationshipFilterClick = useCallback((type: string) => {
    const newTypes = filters.relationshipTypes.includes(type)
      ? filters.relationshipTypes.filter(t => t !== type)
      : [...filters.relationshipTypes, type];
    setFilters(f => ({ ...f, relationshipTypes: newTypes }));
  }, [filters.relationshipTypes]);

  // Calculate connected nodes count for selected node
  const connectedNodesCount = selectedNode
    ? (displayData?.edges.filter(
        e => e.from === selectedNode.id || e.to === selectedNode.id
      ).length || 0)
    : 0;

  return (
    <div className="flex h-[calc(100vh-180px)] gap-4">
      {/* Main graph area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Controls */}
        <GraphControls
          onZoomIn={handleZoomIn}
          onZoomOut={handleZoomOut}
          onFit={handleFit}
          onResetView={handleResetView}
          onTogglePhysics={handleTogglePhysics}
          onLayoutChange={handleLayoutChange}
          onRefresh={handleRefresh}
          isLoading={isLoading}
          nodeCount={displayData?.nodes.length || 0}
          edgeCount={displayData?.edges.length || 0}
          className="mb-4"
        />

        {/* Canvas */}
        <div className="flex-1 h-0 min-h-[400px] rounded-md border bg-muted/20 relative overflow-hidden">
          <GraphCanvas
            ref={canvasRef}
            data={displayData}
            isLoading={isLoading}
            onNodeClick={handleNodeClick}
            onNodeDoubleClick={handleNodeDoubleClick}
            onBackgroundClick={handleBackgroundClick}
            selectedNodeId={selectedNode?.id}
            highlightedNodeIds={highlightedNodeIds}
            className="w-full h-full"
          />
        </div>
      </div>

      {/* Right sidebar */}
      <aside className="w-80 flex flex-col gap-4 overflow-y-auto">
        <Tabs defaultValue="details" className="flex-1 flex flex-col">
          <TabsList className="w-full">
            <TabsTrigger value="details" className="flex-1">Details</TabsTrigger>
            <TabsTrigger value="filters" className="flex-1">Filters</TabsTrigger>
            <TabsTrigger value="tools" className="flex-1">Tools</TabsTrigger>
          </TabsList>

          <TabsContent value="details" className="flex-1 overflow-y-auto space-y-4 mt-4">
            <NodeDetails
              node={selectedNode}
              connectedNodesCount={connectedNodesCount}
              onViewFull={handleViewFullDetails}
              onExpandNeighbors={handleExpandNeighbors}
            />
            <GraphLegend
              nodes={displayData?.nodes || []}
              edges={displayData?.edges || []}
              onTypeClick={handleTypeFilterClick}
              onRelationshipClick={handleRelationshipFilterClick}
              activeTypes={filters.types}
              activeRelationships={filters.relationshipTypes}
            />
          </TabsContent>

          <TabsContent value="filters" className="flex-1 overflow-y-auto mt-4">
            <GraphFilters
              filters={filters}
              onChange={setFilters}
              onApply={handleApplyFilters}
            />
          </TabsContent>

          <TabsContent value="tools" className="flex-1 overflow-y-auto space-y-4 mt-4">
            <RequirementTrace
              onNavigate={(type, id) => navigate(`/browser/${type}?id=${id}`)}
              onHighlightPath={handleHighlightPath}
            />
            <CypherEditor
              onGraphResult={handleCypherGraphResult}
            />
          </TabsContent>
        </Tabs>
      </aside>
    </div>
  );
}
