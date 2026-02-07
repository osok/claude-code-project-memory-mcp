import { randomUUID } from "node:crypto";
import { z } from "zod";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { ToolContext } from "../context.js";
import { MEMORY_TYPES } from "../types/memory.js";
import { logger } from "../utils/logger.js";

/**
 * REQ-007-FN-060, FN-061: Test result suite cleanup
 * When storing test results with suite_name/suite_id, automatically cleanup
 * old test results from the same suite.
 */
async function cleanupOldTestResults(
  ctx: ToolContext,
  suiteName: string | undefined,
  suiteId: string | undefined,
  keepCount: number = 10
): Promise<number> {
  if (!suiteName && !suiteId) {
    return 0;
  }

  const collection = ctx.collectionName("test_result");
  let cleanedCount = 0;

  try {
    // Build filter for suite matching
    const mustConditions: Array<{ key: string; match: { value: unknown } }> = [
      { key: "project_id", match: { value: ctx.projectId } },
      { key: "deleted", match: { value: false } }
    ];

    if (suiteId) {
      mustConditions.push({ key: "metadata.suite_id", match: { value: suiteId } });
    } else if (suiteName) {
      mustConditions.push({ key: "metadata.suite_name", match: { value: suiteName } });
    }

    // Get existing test results for this suite
    const existingResults = await ctx.qdrant.scroll(collection, {
      filter: { must: mustConditions },
      limit: 1000
    });

    // Sort by created_at descending (newest first)
    const sorted = existingResults.points.sort((a, b) => {
      const aTime = String((a.payload as Record<string, unknown>).created_at || "");
      const bTime = String((b.payload as Record<string, unknown>).created_at || "");
      return bTime.localeCompare(aTime);
    });

    // Mark old results as deleted (keep the newest 'keepCount')
    const toDelete = sorted.slice(keepCount);
    const now = new Date().toISOString();

    for (const point of toDelete) {
      await ctx.qdrant.upsert(collection, {
        id: point.id as string,
        vector: point.vector as number[],
        payload: {
          ...point.payload,
          deleted: true,
          updated_at: now
        }
      });
      cleanedCount++;
    }

    if (cleanedCount > 0) {
      logger.info("Cleaned up old test results", {
        suite_name: suiteName,
        suite_id: suiteId,
        cleaned_count: cleanedCount
      });
    }
  } catch (error) {
    // Collection might not exist yet, ignore
    logger.debug("Could not cleanup old test results", { error: String(error) });
  }

  return cleanedCount;
}

const MemoryTypeSchema = z.enum(MEMORY_TYPES);

const RelationshipSchema = z.object({
  type: z.string(),
  target_id: z.string().uuid()
});

// Memory types that should create Neo4j graph nodes for relationship tracking
const GRAPH_ELIGIBLE_TYPES = [
  "requirements",    // Requirements → implemented by designs/components
  "design",          // Designs → implement requirements, guide components
  "architecture",    // ADRs → guide designs and components
  "component",       // Components → contain functions, implement designs
  "function",        // Functions → belong to components
  "test_result"      // Test results → verify components/requirements
];

function needsGraphNode(memoryType: string): boolean {
  return GRAPH_ELIGIBLE_TYPES.includes(memoryType);
}

// Infer relationship type based on source and target memory types
function inferRelationshipType(sourceType: string, targetType: string): string {
  // Architecture guides everything
  if (sourceType === "architecture" && targetType === "requirements") return "GUIDES";
  if (sourceType === "architecture" && targetType === "design") return "GUIDES";
  if (sourceType === "architecture" && targetType === "component") return "GUIDES";

  // Design implements requirements
  if (sourceType === "design" && targetType === "requirements") return "IMPLEMENTS";
  if (sourceType === "requirements" && targetType === "design") return "IMPLEMENTED_BY";

  // Components implement designs
  if (sourceType === "component" && targetType === "design") return "IMPLEMENTS";
  if (sourceType === "design" && targetType === "component") return "IMPLEMENTED_BY";

  // Functions belong to components
  if (sourceType === "function" && targetType === "component") return "BELONGS_TO";
  if (sourceType === "component" && targetType === "function") return "CONTAINS";

  // Test results verify components and requirements
  if (sourceType === "test_result" && targetType === "component") return "TESTS";
  if (sourceType === "test_result" && targetType === "requirements") return "VERIFIES";
  if (sourceType === "component" && targetType === "test_result") return "TESTED_BY";
  if (sourceType === "requirements" && targetType === "test_result") return "VERIFIED_BY";

  // Components can depend on other components
  if (sourceType === "component" && targetType === "component") return "DEPENDS_ON";

  // Default: semantic similarity
  return "RELATED_TO";
}

function toolResult(data: unknown) {
  return {
    content: [{
      type: "text" as const,
      text: JSON.stringify(data, null, 2)
    }]
  };
}

function toolError(code: string, message: string, suggestion?: string) {
  return toolResult({
    error: {
      code,
      message,
      suggestion
    }
  });
}

export function registerMemoryCrudTools(server: McpServer, ctx: ToolContext): void {
  // memory_add - Create a new memory
  server.tool(
    "memory_add",
    "Create a new memory with embedding",
    {
      memory_type: MemoryTypeSchema,
      content: z.string().min(1).max(100000),
      metadata: z.record(z.unknown()).optional(),
      relationships: z.array(RelationshipSchema).optional()
    },
    async (input) => {
      try {
        // REQ-007-FN-061: Auto-cleanup old test results when storing new suite results
        let cleanedCount = 0;
        if (input.memory_type === "test_result" && input.metadata) {
          const suiteName = input.metadata.suite_name as string | undefined;
          const suiteId = input.metadata.suite_id as string | undefined;
          cleanedCount = await cleanupOldTestResults(ctx, suiteName, suiteId);
        }

        const embedding = await ctx.voyage.embed(input.content);
        const memoryId = randomUUID();
        const now = new Date().toISOString();

        const collection = ctx.collectionName(input.memory_type);
        await ctx.qdrant.upsert(collection, {
          id: memoryId,
          vector: embedding,
          payload: {
            type: input.memory_type,
            content: input.content,
            metadata: input.metadata || {},
            created_at: now,
            updated_at: now,
            deleted: false,
            project_id: ctx.projectId
          }
        });

        // Create Neo4j node if applicable
        if (needsGraphNode(input.memory_type)) {
          try {
            // Store content summary in Neo4j for meaningful graph labels
            const contentSummary = input.content.substring(0, 500);
            await ctx.neo4j.createNode(
              input.memory_type.charAt(0).toUpperCase() + input.memory_type.slice(1),
              memoryId,
              {
                content: contentSummary,
                ...(input.metadata || {})
              }
            );

            // Create explicit relationships if provided
            if (input.relationships) {
              for (const rel of input.relationships) {
                await ctx.neo4j.createRelationship(
                  memoryId,
                  rel.type,
                  rel.target_id
                );
              }
            }

            // Auto-infer relationships by semantic similarity
            // Search other graph-eligible types for related memories
            const autoRelationships: Array<{ targetId: string; type: string }> = [];
            const graphTypes = GRAPH_ELIGIBLE_TYPES.filter(t => t !== input.memory_type);

            for (const searchType of graphTypes) {
              try {
                const searchCollection = ctx.collectionName(searchType);
                const similar = await ctx.qdrant.searchSimilar(searchCollection, embedding, 3, 0.75);

                for (const match of similar) {
                  const targetId = match.id;
                  // Determine relationship type based on source/target types
                  const relType = inferRelationshipType(input.memory_type, searchType);
                  autoRelationships.push({ targetId, type: relType });
                }
              } catch {
                // Collection may not exist yet, skip silently
              }
            }

            // Create auto-inferred relationships
            for (const rel of autoRelationships) {
              try {
                await ctx.neo4j.createRelationship(memoryId, rel.type, rel.targetId);
                logger.info("Auto-created relationship", { from: memoryId, type: rel.type, to: rel.targetId });
              } catch (error) {
                logger.warn("Failed to create auto-relationship", { error: String(error) });
              }
            }
          } catch (error) {
            logger.warn("Failed to create graph node", { error: String(error) });
          }
        }

        const autoRelCount = needsGraphNode(input.memory_type) ? undefined : 0;
        return toolResult({
          memory_id: memoryId,
          status: "created",
          ...(autoRelCount !== undefined ? { auto_relationships: autoRelCount } : {}),
          ...(cleanedCount > 0 ? { old_test_results_cleaned: cleanedCount } : {})
        });
      } catch (error) {
        logger.error("memory_add failed", { error: String(error) });
        return toolError("CREATE_ERROR", String(error));
      }
    }
  );

  // memory_get - Retrieve memory by ID
  server.tool(
    "memory_get",
    "Retrieve a memory by its ID",
    {
      memory_id: z.string().uuid(),
      memory_type: MemoryTypeSchema
    },
    async (input) => {
      try {
        const collection = ctx.collectionName(input.memory_type);
        const point = await ctx.qdrant.get(collection, input.memory_id);

        if (!point) {
          return toolError("NOT_FOUND", "Memory not found", "Check the memory_id and memory_type");
        }

        if (point.payload["deleted"] === true) {
          return toolError("DELETED", "Memory has been deleted");
        }

        return toolResult({
          memory_id: point.id,
          type: point.payload["type"],
          content: point.payload["content"],
          metadata: point.payload["metadata"],
          created_at: point.payload["created_at"],
          updated_at: point.payload["updated_at"]
        });
      } catch (error) {
        logger.error("memory_get failed", { error: String(error) });
        return toolError("GET_ERROR", String(error));
      }
    }
  );

  // memory_update - Update an existing memory
  server.tool(
    "memory_update",
    "Update an existing memory's content or metadata",
    {
      memory_id: z.string().uuid(),
      memory_type: MemoryTypeSchema,
      content: z.string().min(1).max(100000).optional(),
      metadata: z.record(z.unknown()).optional()
    },
    async (input) => {
      try {
        const collection = ctx.collectionName(input.memory_type);
        const existing = await ctx.qdrant.get(collection, input.memory_id);

        if (!existing) {
          return toolError("NOT_FOUND", "Memory not found");
        }

        if (existing.payload["deleted"] === true) {
          return toolError("DELETED", "Cannot update deleted memory");
        }

        const now = new Date().toISOString();
        let newVector = existing.vector;

        // Re-embed if content changed
        if (input.content && input.content !== existing.payload["content"]) {
          newVector = await ctx.voyage.embed(input.content);
        }

        const newPayload = {
          ...existing.payload,
          content: input.content || existing.payload["content"],
          metadata: input.metadata
            ? { ...(existing.payload["metadata"] as Record<string, unknown>), ...input.metadata }
            : existing.payload["metadata"],
          updated_at: now
        };

        await ctx.qdrant.upsert(collection, {
          id: input.memory_id,
          vector: newVector,
          payload: newPayload
        });

        // Update Neo4j node if applicable
        if (needsGraphNode(input.memory_type) && input.metadata) {
          try {
            await ctx.neo4j.updateNode(input.memory_id, input.metadata);
          } catch (error) {
            logger.warn("Failed to update graph node", { error: String(error) });
          }
        }

        return toolResult({ memory_id: input.memory_id, status: "updated" });
      } catch (error) {
        logger.error("memory_update failed", { error: String(error) });
        return toolError("UPDATE_ERROR", String(error));
      }
    }
  );

  // memory_delete - Soft delete a memory
  server.tool(
    "memory_delete",
    "Delete a memory (soft delete)",
    {
      memory_id: z.string().uuid(),
      memory_type: MemoryTypeSchema
    },
    async (input) => {
      try {
        const collection = ctx.collectionName(input.memory_type);
        const deleted = await ctx.qdrant.softDelete(collection, input.memory_id);

        if (!deleted) {
          return toolError("NOT_FOUND", "Memory not found");
        }

        // Mark deleted in Neo4j if applicable
        if (needsGraphNode(input.memory_type)) {
          try {
            await ctx.neo4j.deleteNode(input.memory_id);
          } catch (error) {
            logger.warn("Failed to delete graph node", { error: String(error) });
          }
        }

        return toolResult({ memory_id: input.memory_id, status: "deleted" });
      } catch (error) {
        logger.error("memory_delete failed", { error: String(error) });
        return toolError("DELETE_ERROR", String(error));
      }
    }
  );

  // memory_bulk_add - Batch add memories
  server.tool(
    "memory_bulk_add",
    "Add multiple memories in a single operation",
    {
      memories: z.array(z.object({
        memory_type: MemoryTypeSchema,
        content: z.string().min(1).max(100000),
        metadata: z.record(z.unknown()).optional()
      })).min(1).max(100)
    },
    async (input) => {
      try {
        const results: Array<{ memory_id: string; status: string }> = [];
        const now = new Date().toISOString();

        // Group by memory type for batch embedding
        const byType = new Map<string, Array<{ content: string; metadata?: Record<string, unknown> }>>();

        for (const mem of input.memories) {
          const list = byType.get(mem.memory_type) || [];
          list.push({ content: mem.content, metadata: mem.metadata });
          byType.set(mem.memory_type, list);
        }

        for (const [memoryType, items] of byType) {
          const texts = items.map(i => i.content);
          const embeddings = await ctx.voyage.embedBatch(texts);

          const points = items.map((item, i) => {
            const memoryId = randomUUID();
            results.push({ memory_id: memoryId, status: "created" });

            return {
              id: memoryId,
              vector: embeddings[i]!,
              payload: {
                type: memoryType,
                content: item.content,
                metadata: item.metadata || {},
                created_at: now,
                updated_at: now,
                deleted: false,
                project_id: ctx.projectId
              }
            };
          });

          const collection = ctx.collectionName(memoryType);
          await ctx.qdrant.upsertBatch(collection, points);
        }

        return toolResult({
          created: results.length,
          memories: results
        });
      } catch (error) {
        logger.error("memory_bulk_add failed", { error: String(error) });
        return toolError("BULK_ADD_ERROR", String(error));
      }
    }
  );

  logger.info("Registered 5 memory CRUD tools");
}
