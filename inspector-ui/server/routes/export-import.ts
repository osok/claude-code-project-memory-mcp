/**
 * Export/Import Routes
 *
 * Memory export and import functionality.
 */
import { Router, Request, Response, NextFunction } from 'express';
import { z } from 'zod';
import type { ServerContext } from '../context.js';

export const exportImportRouter = Router();

// Request type with context
interface ContextRequest extends Request {
  context: ServerContext;
}

// Validation schemas
const exportInputSchema = z.object({
  types: z.array(z.string()).optional(),
  includeDeleted: z.boolean().default(false)
});

const importInputSchema = z.object({
  memories: z.array(z.object({
    type: z.string(),
    content: z.string(),
    metadata: z.record(z.unknown()).optional(),
    memory_id: z.string().optional(),
    created_at: z.string().optional()
  })),
  conflictResolution: z.enum(['skip', 'overwrite', 'error']).default('skip')
});

/**
 * POST /api/export
 * Export memories to JSONL format
 */
exportImportRouter.post('/', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const contextReq = req as ContextRequest;
    const { qdrant, projectId } = contextReq.context;

    const input = exportInputSchema.parse(req.body);

    const types = input.types || [
      'requirements', 'design', 'code_pattern', 'component',
      'function', 'test_history', 'session', 'user_preference'
    ];

    const lines: string[] = [];
    const exportMeta = {
      exportedAt: new Date().toISOString(),
      projectId,
      types,
      version: '1.0'
    };

    // Add metadata as first line
    lines.push(JSON.stringify({ _meta: exportMeta }));

    for (const type of types) {
      const collectionName = `memory_${type}_${projectId}`;

      try {
        const filter: { must: Array<{ key: string; match: { value: unknown } }> } = {
          must: [{ key: 'project_id', match: { value: projectId } }]
        };

        if (!input.includeDeleted) {
          filter.must.push({ key: 'deleted', match: { value: false } });
        }

        const points = await qdrant.scroll(collectionName, { filter, limit: 10000 });

        for (const point of points) {
          const payload = point.payload as Record<string, unknown>;
          lines.push(JSON.stringify({
            memory_id: point.id,
            type,
            content: payload.content,
            metadata: payload.metadata,
            created_at: payload.created_at,
            updated_at: payload.updated_at,
            deleted: payload.deleted,
            project_id: payload.project_id
          }));
        }
      } catch {
        // Collection might not exist, skip
      }
    }

    // Set response headers for file download
    const filename = `memories-${projectId}-${new Date().toISOString().split('T')[0]}.jsonl`;
    res.setHeader('Content-Type', 'application/x-ndjson');
    res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);

    res.send(lines.join('\n'));
  } catch (error) {
    next(error);
  }
});

/**
 * POST /api/import
 * Import memories from JSONL data
 */
exportImportRouter.post('/import', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const contextReq = req as ContextRequest;
    const { qdrant, voyage, neo4j, projectId } = contextReq.context;

    const input = importInputSchema.parse(req.body);

    const results = {
      imported: 0,
      skipped: 0,
      errors: [] as string[]
    };

    for (const memory of input.memories) {
      try {
        const memoryId = memory.memory_id || crypto.randomUUID();
        const collectionName = `memory_${memory.type}_${projectId}`;

        // Check if memory exists
        let exists = false;
        try {
          const existing = await qdrant.get(collectionName, memoryId);
          exists = !!existing;
        } catch {
          exists = false;
        }

        if (exists) {
          switch (input.conflictResolution) {
            case 'skip':
              results.skipped++;
              continue;
            case 'error':
              results.errors.push(`Memory already exists: ${memoryId}`);
              continue;
            case 'overwrite':
              // Continue to upsert
              break;
          }
        }

        // Generate embedding
        const embedding = await voyage.embed(memory.content);
        const now = new Date().toISOString();

        // Store in Qdrant
        await qdrant.upsert(collectionName, [{
          id: memoryId,
          vector: embedding,
          payload: {
            type: memory.type,
            content: memory.content,
            metadata: memory.metadata || {},
            created_at: memory.created_at || now,
            updated_at: now,
            deleted: false,
            project_id: projectId
          }
        }]);

        // Store in Neo4j
        await neo4j.createNode({
          id: memoryId,
          type: memory.type,
          content: memory.content.substring(0, 500),
          metadata: memory.metadata || {},
          project_id: projectId
        });

        results.imported++;
      } catch (err) {
        results.errors.push(`Failed to import memory: ${(err as Error).message}`);
      }
    }

    res.json({
      success: true,
      results
    });
  } catch (error) {
    next(error);
  }
});
