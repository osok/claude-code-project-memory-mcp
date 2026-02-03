import { z } from "zod";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { ToolContext } from "../context.js";
import { MEMORY_TYPES } from "../types/memory.js";
import { logger } from "../utils/logger.js";

const MemoryTypeSchema = z.enum(MEMORY_TYPES);

const RelationshipSchema = z.object({
  type: z.string(),
  target_id: z.string().uuid()
});

function needsGraphNode(memoryType: string): boolean {
  return ["component", "function", "design", "requirements"].includes(memoryType);
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
        const embedding = await ctx.voyage.embed(input.content);
        const memoryId = crypto.randomUUID();
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
            await ctx.neo4j.createNode(
              input.memory_type.charAt(0).toUpperCase() + input.memory_type.slice(1),
              memoryId,
              input.metadata || {}
            );

            // Create relationships
            if (input.relationships) {
              for (const rel of input.relationships) {
                await ctx.neo4j.createRelationship(
                  memoryId,
                  rel.type,
                  rel.target_id
                );
              }
            }
          } catch (error) {
            logger.warn("Failed to create graph node", { error: String(error) });
          }
        }

        return toolResult({ memory_id: memoryId, status: "created" });
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
            const memoryId = crypto.randomUUID();
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
