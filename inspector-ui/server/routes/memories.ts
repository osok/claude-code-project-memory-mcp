/**
 * Memory Routes
 *
 * CRUD operations for memories.
 */
import { Router, Request, Response, NextFunction } from 'express';
import { z } from 'zod';
import type { ServerContext } from '../context.js';
import { createError } from '../middleware/error-handler.js';

export const memoriesRouter = Router();

// Request type with context
interface ContextRequest extends Request {
  context: ServerContext;
}

// Validation schemas
const paginationSchema = z.object({
  page: z.coerce.number().int().positive().default(1),
  limit: z.coerce.number().int().positive().max(100).default(25),
  sort: z.enum(['created_at', 'updated_at']).default('updated_at'),
  order: z.enum(['asc', 'desc']).default('desc')
});

const filterSchema = z.object({
  type: z.string().optional(),
  types: z.string().optional(), // comma-separated
  search: z.string().optional(),
  startDate: z.string().optional(),
  endDate: z.string().optional(),
  deleted: z.coerce.boolean().default(false)
});

const memoryInputSchema = z.object({
  type: z.enum([
    'requirements', 'design', 'code_pattern', 'component',
    'function', 'test_history', 'session', 'user_preference'
  ]),
  content: z.string().min(1),
  metadata: z.record(z.unknown()).optional(),
  relationships: z.array(z.object({
    targetId: z.string(),
    type: z.string()
  })).optional()
});

const bulkDeleteSchema = z.object({
  ids: z.array(z.object({
    type: z.string(),
    id: z.string()
  })).min(1),
  hard: z.boolean().default(false)
});

/**
 * GET /api/memories
 * List memories with pagination and filtering
 */
memoriesRouter.get('/', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const contextReq = req as ContextRequest;
    const { projectId, qdrantUrl } = contextReq.context;

    // Validate query params
    const pagination = paginationSchema.parse(req.query);
    const filters = filterSchema.parse(req.query);

    // Build Qdrant filter
    const mustConditions: Array<{ key: string; match: { value: unknown } }> = [
      { key: 'project_id', match: { value: projectId } }
    ];

    if (!filters.deleted) {
      mustConditions.push({ key: 'deleted', match: { value: false } });
    }

    // Get all memories from collections
    const collections = filters.types
      ? filters.types.split(',')
      : filters.type
        ? [filters.type]
        : ['requirements', 'design', 'code_pattern', 'component', 'function', 'test_history', 'session', 'user_preference'];

    let allMemories: Array<{
      memory_id: string;
      type: string;
      content: string;
      metadata: Record<string, unknown>;
      created_at: string;
      updated_at: string;
      deleted: boolean;
      project_id: string;
    }> = [];

    // Helper to scroll through Qdrant collection
    async function scrollCollection(collectionName: string): Promise<void> {
      let offset: string | number | null = null;

      do {
        const scrollBody: Record<string, unknown> = {
          limit: 100,
          with_payload: true,
          filter: { must: mustConditions }
        };
        if (offset !== null) {
          scrollBody.offset = offset;
        }

        const response = await fetch(
          `${qdrantUrl}/collections/${collectionName}/points/scroll`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(scrollBody)
          }
        );

        if (!response.ok) {
          // Collection might not exist
          break;
        }

        const data = await response.json() as {
          result: {
            points: Array<{
              id: string | number;
              payload: Record<string, unknown>;
            }>;
            next_page_offset: string | number | null;
          };
        };

        for (const point of data.result.points) {
          const payload = point.payload;
          allMemories.push({
            memory_id: String(point.id),
            type: String(payload.type || collectionName.split('_').pop()),
            content: String(payload.content || ''),
            metadata: (payload.metadata as Record<string, unknown>) || {},
            created_at: String(payload.created_at || ''),
            updated_at: String(payload.updated_at || ''),
            deleted: Boolean(payload.deleted),
            project_id: String(payload.project_id || projectId)
          });
        }

        offset = data.result.next_page_offset;
      } while (offset !== null);
    }

    // Fetch from all collections
    for (const collection of collections) {
      // Collection naming: {projectId}_{memoryType}
      const collectionName = `${projectId}_${collection}`;
      try {
        await scrollCollection(collectionName);
      } catch (e) {
        // Collection might not exist, skip
        console.log(`Error scrolling ${collectionName}:`, e);
      }
    }

    // Apply text search filter
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      allMemories = allMemories.filter(m =>
        m.content.toLowerCase().includes(searchLower) ||
        JSON.stringify(m.metadata).toLowerCase().includes(searchLower)
      );
    }

    // Apply date range filter
    if (filters.startDate) {
      const startDate = new Date(filters.startDate);
      allMemories = allMemories.filter(m => new Date(m.created_at) >= startDate);
    }
    if (filters.endDate) {
      const endDate = new Date(filters.endDate);
      allMemories = allMemories.filter(m => new Date(m.created_at) <= endDate);
    }

    // Sort
    allMemories.sort((a, b) => {
      const aVal = pagination.sort === 'created_at' ? a.created_at : a.updated_at;
      const bVal = pagination.sort === 'created_at' ? b.created_at : b.updated_at;
      const cmp = aVal.localeCompare(bVal);
      return pagination.order === 'desc' ? -cmp : cmp;
    });

    // Paginate
    const total = allMemories.length;
    const offset = (pagination.page - 1) * pagination.limit;
    const memories = allMemories.slice(offset, offset + pagination.limit);

    res.json({
      memories,
      total,
      page: pagination.page,
      pageSize: pagination.limit,
      hasMore: offset + pagination.limit < total
    });
  } catch (error) {
    next(error);
  }
});

/**
 * GET /api/memories/:type/:id
 * Get a single memory by type and ID
 */
memoriesRouter.get('/:type/:id', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const contextReq = req as ContextRequest;
    const { qdrant, projectId } = contextReq.context;
    const { type, id } = req.params;

    // Use same naming as QdrantAdapter: ${projectId}_${type}
    const collectionName = `${projectId}_${type}`;
    const point = await qdrant.get(collectionName, id);

    if (!point) {
      throw createError(`Memory not found: ${type}/${id}`, 404, 'NOT_FOUND');
    }

    const payload = point.payload as Record<string, unknown>;
    const memory = {
      memory_id: String(point.id),
      type,
      content: String(payload.content || ''),
      metadata: (payload.metadata as Record<string, unknown>) || {},
      created_at: String(payload.created_at || ''),
      updated_at: String(payload.updated_at || ''),
      deleted: Boolean(payload.deleted),
      project_id: String(payload.project_id || projectId)
    };

    res.json(memory);
  } catch (error) {
    next(error);
  }
});

/**
 * POST /api/memories
 * Create a new memory
 */
memoriesRouter.post('/', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const contextReq = req as ContextRequest;
    const { qdrant, voyage, neo4j, projectId } = contextReq.context;

    const input = memoryInputSchema.parse(req.body);
    const now = new Date().toISOString();
    const memoryId = crypto.randomUUID();

    // Generate embedding
    const embedding = await voyage.embed(input.content);

    // Store in Qdrant - use same naming as QdrantAdapter: ${projectId}_${type}
    const collectionName = `${projectId}_${input.type}`;
    await qdrant.upsert(collectionName, [{
      id: memoryId,
      vector: embedding,
      payload: {
        type: input.type,
        content: input.content,
        metadata: input.metadata || {},
        created_at: now,
        updated_at: now,
        deleted: false,
        project_id: projectId
      }
    }]);

    // Store in Neo4j - use correct signature: createNode(label, memoryId, properties)
    await neo4j.createNode(
      input.type, // label (e.g., 'requirements', 'design')
      memoryId,
      {
        type: input.type,
        content: input.content.substring(0, 500), // Truncate for label
        metadata: input.metadata || {}
      }
    );

    // Create relationships if specified - signature: createRelationship(sourceId, relationshipType, targetId)
    if (input.relationships) {
      for (const rel of input.relationships) {
        await neo4j.createRelationship(memoryId, rel.type, rel.targetId);
      }
    }

    const memory = {
      memory_id: memoryId,
      type: input.type,
      content: input.content,
      metadata: input.metadata || {},
      created_at: now,
      updated_at: now,
      deleted: false,
      project_id: projectId
    };

    res.status(201).json(memory);
  } catch (error) {
    next(error);
  }
});

/**
 * PUT /api/memories/:type/:id
 * Update an existing memory
 */
memoriesRouter.put('/:type/:id', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const contextReq = req as ContextRequest;
    const { qdrant, voyage, neo4j, projectId } = contextReq.context;
    const { type, id } = req.params;

    // Get existing memory - use same naming as QdrantAdapter: ${projectId}_${type}
    const collectionName = `${projectId}_${type}`;
    const existing = await qdrant.get(collectionName, id);
    if (!existing) {
      throw createError(`Memory not found: ${type}/${id}`, 404, 'NOT_FOUND');
    }

    const existingPayload = existing.payload as Record<string, unknown>;

    // Validate update data
    const updateSchema = memoryInputSchema.partial().omit({ type: true });
    const updates = updateSchema.parse(req.body);

    const now = new Date().toISOString();
    const newContent = updates.content ?? String(existingPayload.content);
    const newMetadata = updates.metadata ?? (existingPayload.metadata as Record<string, unknown>);

    // Re-generate embedding if content changed
    let embedding = existing.vector;
    if (updates.content && updates.content !== existingPayload.content) {
      embedding = await voyage.embed(updates.content);
    }

    // Update in Qdrant
    await qdrant.upsert(collectionName, [{
      id,
      vector: embedding as number[],
      payload: {
        type,
        content: newContent,
        metadata: newMetadata,
        created_at: existingPayload.created_at,
        updated_at: now,
        deleted: existingPayload.deleted,
        project_id: projectId
      }
    }]);

    // Update in Neo4j
    await neo4j.updateNode(id, {
      content: newContent.substring(0, 500),
      metadata: newMetadata
    });

    // Update relationships if specified
    // Note: Neo4jAdapter doesn't have deleteRelationships method, so we only add new relationships
    // TODO: Add deleteRelationships to Neo4jAdapter if full relationship replacement is needed
    if (updates.relationships) {
      for (const rel of updates.relationships) {
        // createRelationship signature: (sourceId, relationshipType, targetId)
        await neo4j.createRelationship(id, rel.type, rel.targetId);
      }
    }

    const memory = {
      memory_id: id,
      type,
      content: newContent,
      metadata: newMetadata,
      created_at: String(existingPayload.created_at),
      updated_at: now,
      deleted: Boolean(existingPayload.deleted),
      project_id: projectId
    };

    res.json(memory);
  } catch (error) {
    next(error);
  }
});

/**
 * DELETE /api/memories/:type/:id
 * Delete a memory (soft by default, hard with ?hard=true)
 */
memoriesRouter.delete('/:type/:id', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const contextReq = req as ContextRequest;
    const { qdrant, neo4j, projectId } = contextReq.context;
    const { type, id } = req.params;
    const hard = req.query.hard === 'true';

    // Use same naming as QdrantAdapter: ${projectId}_${type}
    const collectionName = `${projectId}_${type}`;

    if (hard) {
      // Hard delete - remove from both stores
      await qdrant.delete(collectionName, [id]);
      await neo4j.deleteNode(id);
    } else {
      // Soft delete - mark as deleted
      const existing = await qdrant.get(collectionName, id);
      if (!existing) {
        throw createError(`Memory not found: ${type}/${id}`, 404, 'NOT_FOUND');
      }

      const payload = existing.payload as Record<string, unknown>;
      await qdrant.upsert(collectionName, [{
        id,
        vector: existing.vector as number[],
        payload: {
          ...payload,
          deleted: true,
          updated_at: new Date().toISOString()
        }
      }]);
    }

    res.json({ success: true, id, hard });
  } catch (error) {
    next(error);
  }
});

/**
 * POST /api/memories/bulk-delete
 * Delete multiple memories
 */
memoriesRouter.post('/bulk-delete', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const contextReq = req as ContextRequest;
    const { qdrant, neo4j, projectId } = contextReq.context;

    const input = bulkDeleteSchema.parse(req.body);
    const deleted: string[] = [];

    for (const { type, id } of input.ids) {
      // Use same naming as QdrantAdapter: ${projectId}_${type}
      const collectionName = `${projectId}_${type}`;

      if (input.hard) {
        await qdrant.delete(collectionName, [id]);
        await neo4j.deleteNode(id);
      } else {
        const existing = await qdrant.get(collectionName, id);
        if (existing) {
          const payload = existing.payload as Record<string, unknown>;
          await qdrant.upsert(collectionName, [{
            id,
            vector: existing.vector as number[],
            payload: {
              ...payload,
              deleted: true,
              updated_at: new Date().toISOString()
            }
          }]);
        }
      }
      deleted.push(id);
    }

    res.json({ success: true, deleted, count: deleted.length, hard: input.hard });
  } catch (error) {
    next(error);
  }
});
