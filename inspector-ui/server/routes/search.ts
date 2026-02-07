/**
 * Search Routes
 *
 * Semantic search, code search, and duplicate detection.
 */
import { Router, Request, Response, NextFunction } from 'express';
import { z } from 'zod';
import type { ServerContext } from '../context.js';

export const searchRouter = Router();

// Request type with context
interface ContextRequest extends Request {
  context: ServerContext;
}

// Validation schemas
const semanticSearchSchema = z.object({
  query: z.string().min(1),
  types: z.array(z.string()).optional(),
  limit: z.number().int().positive().max(100).default(25),
  dateRange: z.object({
    start: z.string().optional(),
    end: z.string().optional()
  }).optional()
});

const codeSearchSchema = z.object({
  code: z.string().min(1),
  language: z.string().optional(),
  threshold: z.number().min(0).max(1).default(0.85),
  limit: z.number().int().positive().max(100).default(25)
});

const duplicateSearchSchema = z.object({
  content: z.string().min(1),
  type: z.string(),
  threshold: z.number().min(0).max(1).default(0.90),
  excludeId: z.string().optional()
});

/**
 * POST /api/search
 * Semantic search across memories
 */
searchRouter.post('/', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const contextReq = req as ContextRequest;
    const { qdrant, voyage, projectId } = contextReq.context;
    const startTime = Date.now();

    const input = semanticSearchSchema.parse(req.body);

    // Generate embedding for query
    const queryEmbedding = await voyage.embed(input.query);

    // Determine which collections to search
    const types = input.types || [
      'requirements', 'design', 'code_pattern', 'component',
      'function', 'test_history', 'session', 'user_preference'
    ];

    const collections = types.map(t => `memory_${t}_${projectId}`);

    // Search with vector
    const results = await qdrant.search({
      collections,
      vector: queryEmbedding,
      limit: input.limit,
      filter: {
        must: [
          { key: 'deleted', match: { value: false } },
          { key: 'project_id', match: { value: projectId } }
        ]
      }
    });

    // Apply date filter if specified
    let filteredResults = results;
    if (input.dateRange?.start || input.dateRange?.end) {
      filteredResults = results.filter(r => {
        const createdAt = new Date(String(r.payload.created_at));
        if (input.dateRange?.start && createdAt < new Date(input.dateRange.start)) {
          return false;
        }
        if (input.dateRange?.end && createdAt > new Date(input.dateRange.end)) {
          return false;
        }
        return true;
      });
    }

    // Format results
    const formattedResults = filteredResults.map(r => ({
      memory: {
        memory_id: r.id,
        type: String(r.payload.type),
        content: String(r.payload.content),
        metadata: r.payload.metadata as Record<string, unknown>,
        created_at: String(r.payload.created_at),
        updated_at: String(r.payload.updated_at),
        deleted: Boolean(r.payload.deleted),
        project_id: String(r.payload.project_id)
      },
      score: r.score
    }));

    const duration = Date.now() - startTime;

    res.json({
      results: formattedResults,
      count: formattedResults.length,
      duration: duration
    });
  } catch (error) {
    next(error);
  }
});

/**
 * POST /api/search/code
 * Code similarity search
 */
searchRouter.post('/code', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const contextReq = req as ContextRequest;
    const { qdrant, voyage, projectId } = contextReq.context;
    const startTime = Date.now();

    const input = codeSearchSchema.parse(req.body);

    // Generate embedding for code
    const codeEmbedding = await voyage.embed(input.code);

    // Search in function and code_pattern collections
    const collections = [
      `memory_function_${projectId}`,
      `memory_code_pattern_${projectId}`
    ];

    // Build filter
    const mustConditions: Array<{ key: string; match: { value: unknown } }> = [
      { key: 'deleted', match: { value: false } },
      { key: 'project_id', match: { value: projectId } }
    ];

    // Add language filter if specified
    if (input.language) {
      mustConditions.push({ key: 'metadata.language', match: { value: input.language } });
    }

    const results = await qdrant.search({
      collections,
      vector: codeEmbedding,
      limit: input.limit * 2, // Get more for threshold filtering
      filter: { must: mustConditions }
    });

    // Filter by threshold
    const thresholdResults = results.filter(r => r.score >= input.threshold);

    // Format results
    const formattedResults = thresholdResults.slice(0, input.limit).map(r => {
      const metadata = r.payload.metadata as Record<string, unknown>;
      return {
        memory: {
          memory_id: r.id,
          type: String(r.payload.type),
          content: String(r.payload.content),
          metadata,
          created_at: String(r.payload.created_at),
          updated_at: String(r.payload.updated_at),
          deleted: Boolean(r.payload.deleted),
          project_id: String(r.payload.project_id)
        },
        score: r.score,
        filePath: metadata.file_path ? String(metadata.file_path) : undefined,
        functionName: metadata.function_name ? String(metadata.function_name) : undefined,
        language: metadata.language ? String(metadata.language) : undefined
      };
    });

    const duration = Date.now() - startTime;

    res.json({
      results: formattedResults,
      count: formattedResults.length,
      duration: duration,
      threshold: input.threshold
    });
  } catch (error) {
    next(error);
  }
});

/**
 * POST /api/search/duplicates
 * Find potential duplicates of content
 */
searchRouter.post('/duplicates', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const contextReq = req as ContextRequest;
    const { qdrant, voyage, projectId } = contextReq.context;
    const startTime = Date.now();

    const input = duplicateSearchSchema.parse(req.body);

    // Generate embedding for content
    const contentEmbedding = await voyage.embed(input.content);

    // Search in specified type collection
    const collection = `memory_${input.type}_${projectId}`;

    const results = await qdrant.search({
      collections: [collection],
      vector: contentEmbedding,
      limit: 20, // Get top 20 potential duplicates
      filter: {
        must: [
          { key: 'deleted', match: { value: false } },
          { key: 'project_id', match: { value: projectId } }
        ]
      }
    });

    // Filter by threshold and exclude self
    const duplicates = results
      .filter(r => r.score >= input.threshold)
      .filter(r => !input.excludeId || r.id !== input.excludeId)
      .map(r => ({
        memory: {
          memory_id: r.id,
          type: String(r.payload.type),
          content: String(r.payload.content),
          metadata: r.payload.metadata as Record<string, unknown>,
          created_at: String(r.payload.created_at),
          updated_at: String(r.payload.updated_at),
          deleted: Boolean(r.payload.deleted),
          project_id: String(r.payload.project_id)
        },
        score: r.score,
        similarity: Math.round(r.score * 100) + '%'
      }));

    const duration = Date.now() - startTime;

    res.json({
      duplicates,
      count: duplicates.length,
      duration: duration,
      threshold: input.threshold
    });
  } catch (error) {
    next(error);
  }
});
