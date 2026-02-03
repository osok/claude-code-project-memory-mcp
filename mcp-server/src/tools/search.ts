import { z } from "zod";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { ToolContext } from "../context.js";
import { MEMORY_TYPES } from "../types/memory.js";
import { logger } from "../utils/logger.js";

const MemoryTypeSchema = z.enum(MEMORY_TYPES);

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

export function registerSearchTools(server: McpServer, ctx: ToolContext): void {
  // memory_search - Semantic search across memories
  server.tool(
    "memory_search",
    "Semantic search across memories using natural language",
    {
      query: z.string().min(1).max(10000),
      memory_types: z.array(MemoryTypeSchema).optional(),
      limit: z.number().min(1).max(100).default(10),
      time_range: z.object({
        start: z.string().datetime().optional(),
        end: z.string().datetime().optional()
      }).optional()
    },
    async (input) => {
      try {
        const embedding = await ctx.voyage.embed(input.query);

        const collections = input.memory_types
          ? input.memory_types.map(t => ctx.collectionName(t))
          : ctx.allCollections();

        const results = await ctx.qdrant.search({
          collections,
          vector: embedding,
          limit: input.limit,
          filter: {
            must: [
              { key: "project_id", match: { value: ctx.projectId } },
              { key: "deleted", match: { value: false } }
            ]
          }
        });

        // Filter by time range if specified
        let filtered = results;
        if (input.time_range) {
          filtered = results.filter(r => {
            const createdAt = r.payload["created_at"] as string | undefined;
            if (!createdAt) return true;

            const date = new Date(createdAt);
            if (input.time_range?.start && date < new Date(input.time_range.start)) {
              return false;
            }
            if (input.time_range?.end && date > new Date(input.time_range.end)) {
              return false;
            }
            return true;
          });
        }

        return toolResult({
          query: input.query,
          count: filtered.length,
          results: filtered.map(r => ({
            memory_id: r.id,
            type: r.payload["type"],
            content: r.payload["content"],
            metadata: r.payload["metadata"],
            score: r.score,
            created_at: r.payload["created_at"]
          }))
        });
      } catch (error) {
        logger.error("memory_search failed", { error: String(error) });
        return toolError("SEARCH_ERROR", String(error));
      }
    }
  );

  // code_search - Find similar code patterns
  server.tool(
    "code_search",
    "Search for similar code patterns",
    {
      code_snippet: z.string().min(1).max(50000),
      language: z.string().optional(),
      limit: z.number().min(1).max(50).default(10)
    },
    async (input) => {
      try {
        const embedding = await ctx.voyage.embed(input.code_snippet);

        const collections = [
          ctx.collectionName("code_pattern"),
          ctx.collectionName("function")
        ];

        const filter: { must: Array<{ key: string; match: { value: unknown } }> } = {
          must: [
            { key: "project_id", match: { value: ctx.projectId } },
            { key: "deleted", match: { value: false } }
          ]
        };

        if (input.language) {
          filter.must.push({ key: "metadata.language", match: { value: input.language } });
        }

        const results = await ctx.qdrant.search({
          collections,
          vector: embedding,
          limit: input.limit,
          filter
        });

        return toolResult({
          count: results.length,
          results: results.map(r => ({
            memory_id: r.id,
            type: r.payload["type"],
            content: r.payload["content"],
            metadata: r.payload["metadata"],
            score: r.score
          }))
        });
      } catch (error) {
        logger.error("code_search failed", { error: String(error) });
        return toolError("CODE_SEARCH_ERROR", String(error));
      }
    }
  );

  // find_duplicates - Check for duplicate or near-duplicate content
  server.tool(
    "find_duplicates",
    "Find duplicate or near-duplicate memories",
    {
      content: z.string().min(1).max(100000),
      memory_type: MemoryTypeSchema,
      threshold: z.number().min(0).max(1).default(0.95)
    },
    async (input) => {
      try {
        const embedding = await ctx.voyage.embed(input.content);
        const collection = ctx.collectionName(input.memory_type);

        const results = await ctx.qdrant.search({
          collections: [collection],
          vector: embedding,
          limit: 10,
          filter: {
            must: [
              { key: "project_id", match: { value: ctx.projectId } },
              { key: "deleted", match: { value: false } }
            ]
          }
        });

        const duplicates = results.filter(r => r.score >= input.threshold);

        return toolResult({
          has_duplicates: duplicates.length > 0,
          threshold: input.threshold,
          duplicates: duplicates.map(r => ({
            memory_id: r.id,
            similarity: r.score,
            content_preview: String(r.payload["content"]).substring(0, 200)
          }))
        });
      } catch (error) {
        logger.error("find_duplicates failed", { error: String(error) });
        return toolError("DUPLICATE_SEARCH_ERROR", String(error));
      }
    }
  );

  // get_related - Get related entities via graph traversal
  server.tool(
    "get_related",
    "Get entities related to a memory via graph relationships",
    {
      entity_id: z.string().uuid(),
      relationship_types: z.array(z.string()).optional(),
      depth: z.number().min(1).max(5).default(1)
    },
    async (input) => {
      try {
        const related = await ctx.neo4j.getRelated(
          input.entity_id,
          input.relationship_types,
          input.depth
        );

        return toolResult({
          source_id: input.entity_id,
          depth: input.depth,
          count: related.length,
          related: related
        });
      } catch (error) {
        logger.error("get_related failed", { error: String(error) });
        return toolError("GRAPH_ERROR", String(error), "Check Neo4j connection");
      }
    }
  );

  // graph_query - Execute read-only Cypher queries
  server.tool(
    "graph_query",
    "Execute a read-only Cypher query on the knowledge graph",
    {
      cypher: z.string().min(1).max(10000),
      params: z.record(z.unknown()).optional()
    },
    async (input) => {
      try {
        const results = await ctx.neo4j.query(input.cypher, input.params || {});

        return toolResult({
          count: results.length,
          results: results
        });
      } catch (error) {
        logger.error("graph_query failed", { error: String(error) });
        return toolError("CYPHER_ERROR", String(error), "Only MATCH queries are allowed");
      }
    }
  );

  logger.info("Registered 5 search tools");
}
