/**
 * Normalize Routes
 *
 * Memory normalization operations (deduplication, cleanup, etc.).
 */
import { Router, Request, Response, NextFunction } from 'express';
import { z } from 'zod';
import type { ServerContext } from '../context.js';
import { createError } from '../middleware/error-handler.js';

export const normalizeRouter = Router();

// Request type with context
interface ContextRequest extends Request {
  context: ServerContext;
}

// In-memory job storage (would be Redis/DB in production)
const jobs = new Map<string, {
  id: string;
  status: 'pending' | 'running' | 'complete' | 'failed';
  phases: string[];
  dryRun: boolean;
  startedAt: string;
  completedAt?: string;
  results: {
    phase: string;
    count: number;
    details: string[];
  }[];
  error?: string;
}>();

// Validation schemas
const normalizeInputSchema = z.object({
  phases: z.array(z.enum([
    'dedup',
    'orphan_detection',
    'cleanup',
    'embedding_refresh'
  ])).default(['dedup', 'orphan_detection', 'cleanup']),
  dryRun: z.boolean().default(false)
});

// REQ-007-FN-062: Test result cleanup input schema
const testResultCleanupSchema = z.object({
  suiteName: z.string().optional(),
  suiteId: z.string().optional(),
  olderThanDays: z.number().min(0).default(30),
  keepCount: z.number().min(0).default(10),
  dryRun: z.boolean().default(false)
});

/**
 * POST /api/normalize
 * Start a normalization job
 */
normalizeRouter.post('/', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const contextReq = req as ContextRequest;
    const input = normalizeInputSchema.parse(req.body);

    const jobId = crypto.randomUUID();
    const job = {
      id: jobId,
      status: 'pending' as const,
      phases: input.phases,
      dryRun: input.dryRun,
      startedAt: new Date().toISOString(),
      results: [] as { phase: string; count: number; details: string[] }[]
    };

    jobs.set(jobId, job);

    // Run normalization asynchronously
    runNormalization(jobId, contextReq.context, input.phases, input.dryRun).catch(err => {
      const job = jobs.get(jobId);
      if (job) {
        job.status = 'failed';
        job.error = err.message;
        job.completedAt = new Date().toISOString();
      }
    });

    res.status(202).json({ jobId, status: 'pending' });
  } catch (error) {
    next(error);
  }
});

/**
 * GET /api/normalize/:jobId
 * Get normalization job status
 */
normalizeRouter.get('/:jobId', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { jobId } = req.params;
    const job = jobs.get(jobId);

    if (!job) {
      throw createError(`Job not found: ${jobId}`, 404, 'NOT_FOUND');
    }

    res.json(job);
  } catch (error) {
    next(error);
  }
});

/**
 * POST /api/normalize/test-results
 * Clean up old test results
 * REQ-007-FN-062: Inspector UI action to clean test results
 */
normalizeRouter.post('/test-results', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const contextReq = req as ContextRequest;
    const input = testResultCleanupSchema.parse(req.body);
    const { qdrant, neo4j, projectId } = contextReq.context;

    const collectionName = `memory_test_result_${projectId}`;
    const details: string[] = [];
    let cleanedCount = 0;

    // Build filter conditions
    const mustConditions: Array<{ key: string; match: { value: unknown } }> = [
      { key: 'project_id', match: { value: projectId } },
      { key: 'deleted', match: { value: false } }
    ];

    if (input.suiteId) {
      mustConditions.push({ key: 'metadata.suite_id', match: { value: input.suiteId } });
    } else if (input.suiteName) {
      mustConditions.push({ key: 'metadata.suite_name', match: { value: input.suiteName } });
    }

    try {
      // Get test results
      const points = await qdrant.scroll(collectionName, {
        filter: { must: mustConditions },
        limit: 10000
      });

      // Group by suite
      const suiteGroups = new Map<string, typeof points.points>();
      for (const point of points.points) {
        const payload = point.payload as Record<string, unknown>;
        const metadata = payload.metadata as Record<string, unknown> | undefined;
        const suiteKey = String(metadata?.suite_id || metadata?.suite_name || 'unknown');

        const group = suiteGroups.get(suiteKey) || [];
        group.push(point);
        suiteGroups.set(suiteKey, group);
      }

      const now = new Date().toISOString();
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - input.olderThanDays);

      // Process each suite group
      for (const [suiteKey, suitePoints] of suiteGroups) {
        // Sort by created_at descending (newest first)
        const sorted = suitePoints.sort((a, b) => {
          const aPayload = a.payload as Record<string, unknown>;
          const bPayload = b.payload as Record<string, unknown>;
          const aTime = String(aPayload.created_at || '');
          const bTime = String(bPayload.created_at || '');
          return bTime.localeCompare(aTime);
        });

        // Filter by age and keep count
        const toDelete: typeof sorted = [];
        for (let i = 0; i < sorted.length; i++) {
          const point = sorted[i];
          const payload = point.payload as Record<string, unknown>;
          const createdAt = new Date(String(payload.created_at));

          // Keep the newest 'keepCount' regardless of age
          if (i < input.keepCount) continue;

          // Delete if older than cutoff
          if (createdAt < cutoffDate) {
            toDelete.push(point);
          }
        }

        if (toDelete.length > 0) {
          details.push(`Suite "${suiteKey}": ${toDelete.length} old results`);

          if (!input.dryRun) {
            for (const point of toDelete) {
              await qdrant.upsert(collectionName, [{
                id: String(point.id),
                vector: point.vector as number[],
                payload: {
                  ...(point.payload as Record<string, unknown>),
                  deleted: true,
                  updated_at: now
                }
              }]);

              // Also delete from Neo4j if exists
              try {
                await neo4j.deleteNode(String(point.id));
              } catch {
                // Node might not exist
              }
            }
          }

          cleanedCount += toDelete.length;
        }
      }
    } catch (err) {
      // Collection might not exist
      details.push(`Error: ${(err as Error).message}`);
    }

    res.json({
      status: input.dryRun ? 'dry_run' : 'complete',
      cleaned_count: cleanedCount,
      details: details.length > 0 ? details : ['No test results to clean'],
      params: {
        suite_name: input.suiteName,
        suite_id: input.suiteId,
        older_than_days: input.olderThanDays,
        keep_count: input.keepCount
      }
    });
  } catch (error) {
    next(error);
  }
});

/**
 * Run normalization phases
 */
async function runNormalization(
  jobId: string,
  context: ServerContext,
  phases: string[],
  dryRun: boolean
): Promise<void> {
  const job = jobs.get(jobId);
  if (!job) return;

  job.status = 'running';

  for (const phase of phases) {
    try {
      let result: { count: number; details: string[] };

      switch (phase) {
        case 'dedup':
          result = await runDeduplication(context, dryRun);
          break;
        case 'orphan_detection':
          result = await runOrphanDetection(context, dryRun);
          break;
        case 'cleanup':
          result = await runCleanup(context, dryRun);
          break;
        case 'embedding_refresh':
          result = await runEmbeddingRefresh(context, dryRun);
          break;
        default:
          result = { count: 0, details: ['Unknown phase'] };
      }

      job.results.push({ phase, ...result });
    } catch (err) {
      job.results.push({
        phase,
        count: 0,
        details: [`Error: ${(err as Error).message}`]
      });
    }
  }

  job.status = 'complete';
  job.completedAt = new Date().toISOString();
}

/**
 * Deduplication phase - find and optionally remove near-duplicates
 */
async function runDeduplication(
  context: ServerContext,
  dryRun: boolean
): Promise<{ count: number; details: string[] }> {
  const { qdrant, voyage, projectId } = context;
  const details: string[] = [];
  let duplicateCount = 0;

  const memoryTypes = [
    'requirements', 'design', 'code_pattern', 'component',
    'function', 'test_result', 'test_history', 'session', 'user_preference'
  ];

  for (const type of memoryTypes) {
    const collectionName = `memory_${type}_${projectId}`;

    try {
      // Get all memories in collection
      const points = await qdrant.scroll(collectionName, {
        filter: {
          must: [
            { key: 'deleted', match: { value: false } },
            { key: 'project_id', match: { value: projectId } }
          ]
        },
        limit: 1000
      });

      // Find duplicates (similarity > 0.95)
      const processed = new Set<string>();
      const duplicates: string[] = [];

      for (const point of points) {
        if (processed.has(String(point.id))) continue;
        processed.add(String(point.id));

        // Search for similar
        const similar = await qdrant.search({
          collections: [collectionName],
          vector: point.vector as number[],
          limit: 10,
          filter: {
            must: [
              { key: 'deleted', match: { value: false } },
              { key: 'project_id', match: { value: projectId } }
            ]
          }
        });

        for (const match of similar) {
          if (match.id !== String(point.id) && match.score > 0.95 && !processed.has(match.id)) {
            duplicates.push(match.id);
            processed.add(match.id);
          }
        }
      }

      if (duplicates.length > 0) {
        details.push(`${type}: ${duplicates.length} potential duplicates found`);
        duplicateCount += duplicates.length;

        if (!dryRun) {
          // Mark duplicates as deleted
          for (const dupId of duplicates) {
            const dup = await qdrant.get(collectionName, dupId);
            if (dup) {
              await qdrant.upsert(collectionName, [{
                id: dupId,
                vector: dup.vector as number[],
                payload: {
                  ...(dup.payload as Record<string, unknown>),
                  deleted: true,
                  updated_at: new Date().toISOString()
                }
              }]);
            }
          }
        }
      }
    } catch {
      // Collection might not exist
    }
  }

  return {
    count: duplicateCount,
    details: details.length > 0 ? details : ['No duplicates found']
  };
}

/**
 * Orphan detection - find graph nodes without corresponding vector data
 */
async function runOrphanDetection(
  context: ServerContext,
  dryRun: boolean
): Promise<{ count: number; details: string[] }> {
  const { qdrant, neo4j, projectId } = context;
  const details: string[] = [];
  let orphanCount = 0;

  // Get all Neo4j node IDs
  const nodeResult = await neo4j.query(
    'MATCH (n) WHERE n.project_id = $projectId RETURN n.id as id, n.type as type',
    { projectId }
  );

  for (const record of nodeResult.records) {
    const id = record.get('id');
    const type = record.get('type');

    if (!id || !type) continue;

    const collectionName = `memory_${type}_${projectId}`;

    try {
      const point = await qdrant.get(collectionName, id);
      if (!point) {
        orphanCount++;
        details.push(`Orphan: ${type}/${id} (no vector data)`);

        if (!dryRun) {
          await neo4j.deleteNode(id);
        }
      }
    } catch {
      // Collection might not exist
      orphanCount++;
      details.push(`Orphan: ${type}/${id} (collection missing)`);
    }
  }

  return {
    count: orphanCount,
    details: details.length > 0 ? details : ['No orphans found']
  };
}

/**
 * Cleanup phase - remove soft-deleted memories older than 30 days
 */
async function runCleanup(
  context: ServerContext,
  dryRun: boolean
): Promise<{ count: number; details: string[] }> {
  const { qdrant, neo4j, projectId } = context;
  const details: string[] = [];
  let cleanupCount = 0;

  const cutoffDate = new Date();
  cutoffDate.setDate(cutoffDate.getDate() - 30);

  const memoryTypes = [
    'requirements', 'design', 'code_pattern', 'component',
    'function', 'test_result', 'test_history', 'session', 'user_preference'
  ];

  for (const type of memoryTypes) {
    const collectionName = `memory_${type}_${projectId}`;

    try {
      const points = await qdrant.scroll(collectionName, {
        filter: {
          must: [
            { key: 'deleted', match: { value: true } },
            { key: 'project_id', match: { value: projectId } }
          ]
        },
        limit: 1000
      });

      const toDelete: string[] = [];
      for (const point of points) {
        const payload = point.payload as Record<string, unknown>;
        const updatedAt = new Date(String(payload.updated_at));
        if (updatedAt < cutoffDate) {
          toDelete.push(String(point.id));
        }
      }

      if (toDelete.length > 0) {
        details.push(`${type}: ${toDelete.length} memories to cleanup`);
        cleanupCount += toDelete.length;

        if (!dryRun) {
          await qdrant.delete(collectionName, toDelete);
          for (const id of toDelete) {
            await neo4j.deleteNode(id);
          }
        }
      }
    } catch {
      // Collection might not exist
    }
  }

  return {
    count: cleanupCount,
    details: details.length > 0 ? details : ['No memories to cleanup']
  };
}

/**
 * Embedding refresh - regenerate embeddings for memories with fallback vectors
 */
async function runEmbeddingRefresh(
  context: ServerContext,
  dryRun: boolean
): Promise<{ count: number; details: string[] }> {
  const { qdrant, voyage, projectId } = context;
  const details: string[] = [];
  let refreshCount = 0;

  const memoryTypes = [
    'requirements', 'design', 'code_pattern', 'component',
    'function', 'test_result', 'test_history', 'session', 'user_preference'
  ];

  for (const type of memoryTypes) {
    const collectionName = `memory_${type}_${projectId}`;

    try {
      const points = await qdrant.scroll(collectionName, {
        filter: {
          must: [
            { key: 'deleted', match: { value: false } },
            { key: 'project_id', match: { value: projectId } }
          ]
        },
        limit: 1000
      });

      // Detect fallback embeddings (all zeros or very low variance)
      const toRefresh: Array<{ id: string; content: string; payload: Record<string, unknown> }> = [];

      for (const point of points) {
        const vector = point.vector as number[];
        const allZeros = vector.every(v => v === 0);
        const variance = calculateVariance(vector);

        if (allZeros || variance < 0.001) {
          const payload = point.payload as Record<string, unknown>;
          toRefresh.push({
            id: String(point.id),
            content: String(payload.content),
            payload
          });
        }
      }

      if (toRefresh.length > 0) {
        details.push(`${type}: ${toRefresh.length} embeddings to refresh`);
        refreshCount += toRefresh.length;

        if (!dryRun) {
          for (const item of toRefresh) {
            const newEmbedding = await voyage.embed(item.content);
            await qdrant.upsert(collectionName, [{
              id: item.id,
              vector: newEmbedding,
              payload: {
                ...item.payload,
                updated_at: new Date().toISOString()
              }
            }]);
          }
        }
      }
    } catch {
      // Collection might not exist
    }
  }

  return {
    count: refreshCount,
    details: details.length > 0 ? details : ['No embeddings need refresh']
  };
}

function calculateVariance(arr: number[]): number {
  const n = arr.length;
  if (n === 0) return 0;
  const mean = arr.reduce((a, b) => a + b, 0) / n;
  return arr.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / n;
}
