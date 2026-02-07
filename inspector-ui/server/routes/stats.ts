/**
 * Stats Routes
 *
 * System statistics and health information.
 */
import { Router, Request, Response, NextFunction } from 'express';
import type { ServerContext } from '../context.js';

export const statsRouter = Router();

// Request type with context
interface ContextRequest extends Request {
  context: ServerContext;
}

/**
 * GET /api/stats
 * Get system statistics
 */
statsRouter.get('/', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const contextReq = req as ContextRequest;
    const { qdrant, neo4j, projectId, qdrantUrl, neo4jUri } = contextReq.context;

    // Get memory counts from Qdrant using adapter's getStatistics
    let qdrantStatus: 'connected' | 'disconnected' | 'error' = 'disconnected';
    const counts: Record<string, number> = {};
    let totalCount = 0;

    try {
      const qdrantStats = await qdrant.getStatistics();
      qdrantStatus = 'connected';

      // Parse collection names to extract memory types
      // Format: {projectId}_{memoryType}
      for (const coll of qdrantStats.collections) {
        const prefix = `${projectId}_`;
        if (coll.name.startsWith(prefix)) {
          const memoryType = coll.name.slice(prefix.length);
          counts[memoryType] = coll.count;
          totalCount += coll.count;
        }
      }
    } catch {
      qdrantStatus = 'error';
    }

    // Ensure all memory types are represented
    const memoryTypes = [
      'requirements', 'design', 'code_pattern', 'component',
      'function', 'test_history', 'session', 'user_preference'
    ];
    for (const type of memoryTypes) {
      if (!(type in counts)) {
        counts[type] = 0;
      }
    }

    // Get Neo4j statistics
    let neo4jStatus: 'connected' | 'disconnected' | 'error' = 'disconnected';
    let neo4jNodeCount = 0;
    let neo4jRelationshipCount = 0;

    try {
      const neo4jStats = await neo4j.getStatistics();
      neo4jStatus = 'connected';
      neo4jNodeCount = neo4jStats.nodeCount;
      neo4jRelationshipCount = neo4jStats.relationshipCount;
    } catch {
      neo4jStatus = 'error';
    }

    // Estimate storage (rough estimate based on counts)
    const estimatedStorageMB = totalCount * 0.005; // ~5KB per memory average

    res.json({
      projectId,
      counts: {
        total: totalCount,
        byType: counts
      },
      connections: {
        qdrant: {
          status: qdrantStatus,
          url: qdrantUrl
        },
        neo4j: {
          status: neo4jStatus,
          uri: neo4jUri,
          nodeCount: neo4jNodeCount,
          relationshipCount: neo4jRelationshipCount
        }
      },
      storage: {
        estimatedMB: Math.round(estimatedStorageMB * 100) / 100
      },
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    next(error);
  }
});
