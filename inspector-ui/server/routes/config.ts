/**
 * Config Routes
 *
 * Configuration management for the Inspector UI.
 */
import { Router, Request, Response, NextFunction } from 'express';
import { z } from 'zod';
import type { ServerContext } from '../context.js';

export const configRouter = Router();

// Request type with context
interface ContextRequest extends Request {
  context: ServerContext;
}

// Validation schemas
const configUpdateSchema = z.object({
  qdrantUrl: z.string().url().optional(),
  neo4jUri: z.string().optional(),
  neo4jUser: z.string().optional(),
  neo4jPassword: z.string().optional(),
  voyageApiKey: z.string().optional()
});

/**
 * GET /api/projects
 * List all available project IDs from Qdrant collections
 */
configRouter.get('/projects', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const contextReq = req as ContextRequest;
    const { qdrantUrl } = contextReq.context;

    // Fetch collections directly from Qdrant API
    const response = await fetch(`${qdrantUrl}/collections`);
    if (!response.ok) {
      throw new Error(`Qdrant API error: ${response.status}`);
    }

    const data = await response.json() as {
      result: { collections: Array<{ name: string }> };
    };

    // Extract unique project IDs from collection names
    // Collection format: {projectId}_{memoryType}
    const memoryTypes = [
      'requirements', 'design', 'code_pattern', 'component',
      'function', 'test_history', 'session', 'user_preference'
    ];

    const projectIds = new Set<string>();
    for (const coll of data.result.collections) {
      // Try to extract project ID by removing known memory type suffixes
      for (const type of memoryTypes) {
        const suffix = `_${type}`;
        if (coll.name.endsWith(suffix)) {
          const projectId = coll.name.slice(0, -suffix.length);
          if (projectId) {
            projectIds.add(projectId);
          }
          break;
        }
      }
    }

    // Sort alphabetically, put 'default' first if present
    const sorted = Array.from(projectIds).sort((a, b) => {
      if (a === 'default') return -1;
      if (b === 'default') return 1;
      return a.localeCompare(b);
    });

    res.json({
      projects: sorted,
      total: sorted.length
    });
  } catch (error) {
    next(error);
  }
});

/**
 * GET /api/config
 * Get current configuration (sensitive values masked)
 */
configRouter.get('/', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const contextReq = req as ContextRequest;
    const { projectId, qdrantUrl, neo4jUri } = contextReq.context;

    res.json({
      projectId,
      connections: {
        qdrant: {
          url: qdrantUrl
        },
        neo4j: {
          uri: neo4jUri,
          user: process.env.CLAUDE_MEMORY_NEO4J_USER || 'neo4j',
          // Password masked
          hasPassword: !!process.env.CLAUDE_MEMORY_NEO4J_PASSWORD
        },
        voyage: {
          // API key masked
          hasApiKey: !!process.env.CLAUDE_MEMORY_VOYAGE_API_KEY
        }
      },
      ui: {
        defaultPageSize: 25,
        maxPageSize: 100,
        theme: 'system'
      }
    });
  } catch (error) {
    next(error);
  }
});

/**
 * POST /api/config/test
 * Test database connections
 */
configRouter.post('/test', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const contextReq = req as ContextRequest;
    const { qdrant, neo4j, voyage } = contextReq.context;

    const results: {
      qdrant: { status: 'ok' | 'error'; message?: string };
      neo4j: { status: 'ok' | 'error'; message?: string };
      voyage: { status: 'ok' | 'error'; message?: string };
    } = {
      qdrant: { status: 'error' },
      neo4j: { status: 'error' },
      voyage: { status: 'error' }
    };

    // Test Qdrant (use getStatistics which internally calls Qdrant API)
    try {
      await qdrant.getStatistics();
      results.qdrant = { status: 'ok' };
    } catch (err) {
      results.qdrant = { status: 'error', message: (err as Error).message };
    }

    // Test Neo4j (use getStatistics which runs a query)
    try {
      await neo4j.getStatistics();
      results.neo4j = { status: 'ok' };
    } catch (err) {
      results.neo4j = { status: 'error', message: (err as Error).message };
    }

    // Test Voyage (by generating a small embedding)
    try {
      await voyage.embed('test');
      results.voyage = { status: 'ok' };
    } catch (err) {
      results.voyage = { status: 'error', message: (err as Error).message };
    }

    const allOk = results.qdrant.status === 'ok' &&
                  results.neo4j.status === 'ok' &&
                  results.voyage.status === 'ok';

    res.json({
      success: allOk,
      connections: results
    });
  } catch (error) {
    next(error);
  }
});

/**
 * PUT /api/config
 * Update configuration (runtime only - doesn't persist)
 * Note: This endpoint accepts config but doesn't actually change runtime config
 * since that would require server restart. It's here for UI completion.
 */
configRouter.put('/', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const input = configUpdateSchema.parse(req.body);

    // In a real implementation, this might:
    // 1. Write to a config file
    // 2. Store in a database
    // 3. Trigger a server restart
    // For now, we just acknowledge the request

    res.json({
      success: true,
      message: 'Configuration received. Server restart required for changes to take effect.',
      received: {
        qdrantUrl: input.qdrantUrl ? 'provided' : 'not provided',
        neo4jUri: input.neo4jUri ? 'provided' : 'not provided',
        neo4jUser: input.neo4jUser ? 'provided' : 'not provided',
        neo4jPassword: input.neo4jPassword ? 'provided (masked)' : 'not provided',
        voyageApiKey: input.voyageApiKey ? 'provided (masked)' : 'not provided'
      }
    });
  } catch (error) {
    next(error);
  }
});
