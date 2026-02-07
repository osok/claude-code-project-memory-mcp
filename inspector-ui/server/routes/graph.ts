/**
 * Graph Routes
 *
 * Graph visualization, traversal, and Cypher queries.
 */
import { Router, Request, Response, NextFunction } from 'express';
import { z } from 'zod';
import type { ServerContext } from '../context.js';
import { createError } from '../middleware/error-handler.js';

export const graphRouter = Router();

// Request type with context
interface ContextRequest extends Request {
  context: ServerContext;
}

// Validation schemas
const overviewSchema = z.object({
  types: z.string().optional(), // comma-separated
  limit: z.coerce.number().int().positive().max(500).default(100),
  relationshipTypes: z.string().optional() // comma-separated
});

const relatedSchema = z.object({
  depth: z.coerce.number().int().positive().max(5).default(2),
  types: z.string().optional(), // comma-separated memory types
  relationshipTypes: z.string().optional() // comma-separated
});

const cypherQuerySchema = z.object({
  cypher: z.string().min(1),
  params: z.record(z.unknown()).optional()
});

// Read-only Cypher validation
const WRITE_KEYWORDS = ['CREATE', 'MERGE', 'DELETE', 'SET', 'REMOVE', 'DETACH'];

function isReadOnlyQuery(cypher: string): boolean {
  const upperCypher = cypher.toUpperCase();
  return !WRITE_KEYWORDS.some(keyword => upperCypher.includes(keyword));
}

/**
 * GET /api/graph/overview
 * Get graph overview for visualization
 */
graphRouter.get('/overview', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const contextReq = req as ContextRequest;
    const { neo4j, projectId } = contextReq.context;

    const input = overviewSchema.parse(req.query);
    // Filter out empty strings from types array
    const types = input.types?.split(',').filter(t => t.trim().length > 0) || [];
    const relationshipTypes = input.relationshipTypes?.split(',').filter(t => t.trim().length > 0) || [];

    // Build type filter - Neo4j stores types as labels (capitalized)
    // Map memory types to Neo4j labels
    const typeLabels: Record<string, string> = {
      'requirements': 'Requirements',
      'design': 'Design',
      'code_pattern': 'Pattern',
      'component': 'Component',
      'function': 'Function',
      'test_history': 'Test',
      'session': 'Session',
      'user_preference': 'UserPreference',
      'architecture': 'Architecture'
    };

    // Build label filter for Cypher
    let typeLabelFilter = '';
    if (types.length > 0) {
      const labels = types.map(t => typeLabels[t] || t.charAt(0).toUpperCase() + t.slice(1));
      // Use label checking instead of property
      typeLabelFilter = `AND (${labels.map(l => `n:${l}`).join(' OR ')})`;
    }

    let targetTypeLabelFilter = '';
    if (types.length > 0) {
      const labels = types.map(t => typeLabels[t] || t.charAt(0).toUpperCase() + t.slice(1));
      targetTypeLabelFilter = `AND (${labels.map(l => `m:${l}`).join(' OR ')})`;
    }

    // Query 1: Get nodes with relationships
    let relationshipMatch = '-[r]->';
    if (relationshipTypes.length > 0) {
      relationshipMatch = `-[r:${relationshipTypes.join('|')}]->`;
    }

    const connectedCypher = `
      MATCH (n)${relationshipMatch}(m)
      WHERE n.project_id = $projectId ${typeLabelFilter}
        AND m.project_id = $projectId ${targetTypeLabelFilter}
      RETURN n, r, m
      LIMIT toInteger($limit)
    `;

    const connectedResult = await neo4j.query(connectedCypher, {
      projectId,
      limit: input.limit
    });

    // Query 2: Get orphan nodes (nodes without relationships)
    const orphanCypher = `
      MATCH (n)
      WHERE n.project_id = $projectId ${typeLabelFilter}
        AND NOT (n)--()
      RETURN n
      LIMIT toInteger($limit)
    `;

    const orphanResult = await neo4j.query(orphanCypher, {
      projectId,
      limit: input.limit
    });

    // Combine results - neo4j.query() returns array of record objects
    const allRecords = [...connectedResult, ...orphanResult];

    // Transform to graph data format
    const nodesMap = new Map<string, {
      id: string;
      label: string;
      type: string;
      metadata: Record<string, unknown>;
    }>();
    const edges: Array<{
      id: string;
      from: string;
      to: string;
      label: string;
      type: string;
    }> = [];

    for (const record of allRecords) {
      // Record is an object with n, r, m properties (or just n for orphans)
      // Node structure from neo4j-driver: { labels: string[], properties: {...} }
      const n = record.n as { labels?: string[]; properties: Record<string, unknown> } | undefined;
      const r = record.r as { type: string } | undefined;
      const m = record.m as { labels?: string[]; properties: Record<string, unknown> } | undefined;

      // Add source node
      if (n && n.properties) {
        const props = n.properties;
        const nodeId = String(props.memory_id || props.id || '');
        // Type is stored as node label (e.g., "Requirements"), not as a property
        const nodeType = n.labels?.[0]?.toLowerCase() || String(props.type || 'unknown');
        if (nodeId) {
          nodesMap.set(nodeId, {
            id: nodeId,
            // Use content if available, otherwise use component/document from metadata
            label: truncateLabel(String(props.content || props.component || props.document || nodeId)),
            type: nodeType,
            metadata: (props.metadata as Record<string, unknown>) || props
          });
        }
      }

      // Add target node
      if (m && m.properties) {
        const props = m.properties;
        const nodeId = String(props.memory_id || props.id || '');
        const nodeType = m.labels?.[0]?.toLowerCase() || String(props.type || 'unknown');
        if (nodeId) {
          nodesMap.set(nodeId, {
            id: nodeId,
            label: truncateLabel(String(props.content || props.component || props.document || nodeId)),
            type: nodeType,
            metadata: (props.metadata as Record<string, unknown>) || props
          });
        }
      }

      // Add edge
      const sourceId = n?.properties?.memory_id || n?.properties?.id;
      const targetId = m?.properties?.memory_id || m?.properties?.id;
      if (r && sourceId && targetId) {
        edges.push({
          id: `${sourceId}-${r.type}-${targetId}`,
          from: sourceId,
          to: targetId,
          label: r.type,
          type: r.type
        });
      }
    }

    res.json({
      nodes: Array.from(nodesMap.values()),
      edges
    });
  } catch (error) {
    next(error);
  }
});

/**
 * GET /api/graph/related/:id
 * Get nodes related to a specific memory
 */
graphRouter.get('/related/:id', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const contextReq = req as ContextRequest;
    const { neo4j, projectId } = contextReq.context;
    const { id } = req.params;

    const input = relatedSchema.parse(req.query);
    const types = input.types?.split(',') || [];
    const relationshipTypes = input.relationshipTypes?.split(',') || [];

    // Build relationship pattern
    let relationshipPattern = '*1..' + input.depth;
    if (relationshipTypes.length > 0) {
      relationshipPattern = `:${relationshipTypes.join('|')}*1..${input.depth}`;
    }

    // Build node filter
    let nodeFilter = '';
    if (types.length > 0) {
      nodeFilter = 'AND m.type IN $types';
    }

    // Query using memory_id which is what Neo4jAdapter stores
    const cypher = `
      MATCH path = (n {memory_id: $id})-[${relationshipPattern}]-(m)
      WHERE n.project_id = $projectId AND m.project_id = $projectId ${nodeFilter}
      RETURN DISTINCT m, relationships(path) as rels
      LIMIT 100
    `;

    const result = await neo4j.query(cypher, {
      id,
      projectId,
      types
    });

    // Transform results
    const nodesMap = new Map<string, {
      id: string;
      label: string;
      type: string;
      metadata: Record<string, unknown>;
      distance: number;
    }>();
    const edges: Array<{
      id: string;
      from: string;
      to: string;
      label: string;
      type: string;
    }> = [];

    // result is an array from neo4j.query()
    for (const record of result) {
      const m = record.m as { labels?: string[]; properties: Record<string, unknown> } | undefined;
      const rels = record.rels as Array<{ type: string; startNodeElementId?: string; endNodeElementId?: string; properties?: Record<string, unknown> }> | undefined;

      if (m && m.properties) {
        const props = m.properties;
        const nodeId = String(props.memory_id || props.id || '');
        const nodeType = m.labels?.[0]?.toLowerCase() || String(props.type || 'unknown');
        if (nodeId) {
          nodesMap.set(nodeId, {
            id: nodeId,
            label: truncateLabel(String(props.content || props.component || props.document || nodeId)),
            type: nodeType,
            metadata: (props.metadata as Record<string, unknown>) || props,
            distance: rels?.length || 1
          });
        }
      }

      // Add edges from path
      if (rels) {
        for (const rel of rels) {
          if (rel.startNodeElementId && rel.endNodeElementId) {
            const fromId = rel.properties?.from || rel.startNodeElementId;
            const toId = rel.properties?.to || rel.endNodeElementId;
            const edgeId = `${fromId}-${rel.type}-${toId}`;

            if (!edges.find(e => e.id === edgeId)) {
              edges.push({
                id: edgeId,
                from: String(fromId),
                to: String(toId),
                label: rel.type,
                type: rel.type
              });
            }
          }
        }
      }
    }

    res.json({
      sourceId: id,
      nodes: Array.from(nodesMap.values()),
      edges
    });
  } catch (error) {
    next(error);
  }
});

/**
 * GET /api/graph/trace/:reqId
 * Trace a requirement through implementations and tests
 */
graphRouter.get('/trace/:reqId', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const contextReq = req as ContextRequest;
    const { neo4j, projectId } = contextReq.context;
    const { reqId } = req.params;

    // Find requirement by ID pattern in metadata or content
    // Type is stored as label (Requirements), not as property
    const findReqCypher = `
      MATCH (req:Requirements)
      WHERE req.project_id = $projectId
        AND (req.content CONTAINS $reqId OR req.memory_id = $reqId)
      RETURN req
      LIMIT 1
    `;

    const reqResult = await neo4j.query(findReqCypher, { projectId, reqId });

    // reqResult is an array
    if (reqResult.length === 0) {
      throw createError(`Requirement not found: ${reqId}`, 404, 'NOT_FOUND');
    }

    const reqNode = reqResult[0].req as { labels?: string[]; properties: Record<string, unknown> };
    const reqMemoryId = String(reqNode.properties.memory_id || reqNode.properties.id || '');

    // Find implementing components - use memory_id
    const implCypher = `
      MATCH (req {memory_id: $reqId})<-[:IMPLEMENTS|IMPLEMENTS_REQ]-(impl)
      WHERE impl.project_id = $projectId
      RETURN impl
    `;

    const implResult = await neo4j.query(implCypher, { reqId: reqMemoryId, projectId });
    const implementations = implResult.map(r => {
      const impl = r.impl as { labels?: string[]; properties: Record<string, unknown> };
      const implId = String(impl.properties.memory_id || impl.properties.id || '');
      const implType = impl.labels?.[0]?.toLowerCase() || String(impl.properties.type || 'unknown');
      return {
        id: implId,
        type: implType,
        label: truncateLabel(String(impl.properties.content || impl.properties.component || implId)),
        metadata: (impl.properties.metadata as Record<string, unknown>) || impl.properties
      };
    });

    // Find verifying tests - use memory_id
    const testCypher = `
      MATCH (req {memory_id: $reqId})<-[:TESTS|VERIFIES]-(test)
      WHERE test.project_id = $projectId
      RETURN test
    `;

    const testResult = await neo4j.query(testCypher, { reqId: reqMemoryId, projectId });
    const tests = testResult.map(r => {
      const test = r.test as { labels?: string[]; properties: Record<string, unknown> };
      const testId = String(test.properties.memory_id || test.properties.id || '');
      const testType = test.labels?.[0]?.toLowerCase() || String(test.properties.type || 'unknown');
      return {
        id: testId,
        type: testType,
        label: truncateLabel(String(test.properties.content || test.properties.component || testId)),
        metadata: (test.properties.metadata as Record<string, unknown>) || test.properties
      };
    });

    res.json({
      requirement: {
        id: reqMemoryId,
        requirementId: reqId,
        content: reqNode.properties.content,
        metadata: reqNode.properties.metadata || {}
      },
      implementations,
      tests,
      coverage: {
        implementedCount: implementations.length,
        testedCount: tests.length,
        hasImplementation: implementations.length > 0,
        hasCoverage: tests.length > 0
      }
    });
  } catch (error) {
    next(error);
  }
});

/**
 * POST /api/graph/query
 * Execute a custom Cypher query (read-only)
 */
graphRouter.post('/query', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const contextReq = req as ContextRequest;
    const { neo4j } = contextReq.context;

    const input = cypherQuerySchema.parse(req.body);

    // Validate read-only
    if (!isReadOnlyQuery(input.cypher)) {
      throw createError(
        'Only read-only queries are allowed. Write operations (CREATE, MERGE, DELETE, SET, REMOVE) are not permitted.',
        400,
        'INVALID_QUERY'
      );
    }

    // Execute with timeout
    const startTime = Date.now();
    const result = await Promise.race([
      neo4j.query(input.cypher, input.params || {}),
      new Promise((_, reject) =>
        setTimeout(() => reject(new Error('Query timeout (30s)')), 30000)
      )
    ]) as Record<string, unknown>[];

    const duration = Date.now() - startTime;

    // Transform to table format - result is already an array of objects
    const rows = result;
    const columns = rows.length > 0 ? Object.keys(rows[0]) : [];

    // Extract nodes and edges if present
    const nodesMap = new Map<string, unknown>();
    const edges: unknown[] = [];

    for (const row of rows) {
      for (const [, value] of Object.entries(row)) {
        if (value && typeof value === 'object') {
          const v = value as Record<string, unknown>;
          if (v.properties && v.labels) {
            // It's a node - use memory_id which is what Neo4jAdapter stores
            const props = v.properties as Record<string, unknown>;
            const nodeId = props.memory_id || props.id;
            if (nodeId) {
              nodesMap.set(String(nodeId), {
                id: nodeId,
                labels: v.labels,
                properties: props
              });
            }
          } else if (v.type && v.startNodeElementId) {
            // It's a relationship
            edges.push({
              type: v.type,
              from: v.startNodeElementId,
              to: v.endNodeElementId,
              properties: v.properties
            });
          }
        }
      }
    }

    res.json({
      columns,
      rows,
      rowCount: rows.length,
      duration,
      graph: {
        nodes: Array.from(nodesMap.values()),
        edges
      }
    });
  } catch (error) {
    next(error);
  }
});

// Helper function to truncate labels for display
function truncateLabel(text: string, maxLength: number = 50): string {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength - 3) + '...';
}
