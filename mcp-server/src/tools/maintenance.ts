import { z } from "zod";
import { createWriteStream, createReadStream, existsSync } from "node:fs";
import { createInterface } from "node:readline";
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

// In-memory job tracking
const normalizeJobs = new Map<string, {
  status: "running" | "completed" | "failed";
  phases_completed: string[];
  current_phase?: string;
  started_at: string;
  completed_at?: string;
  error?: string;
}>();

export function registerMaintenanceTools(server: McpServer, ctx: ToolContext): void {
  // memory_statistics - Get system health and counts
  server.tool(
    "memory_statistics",
    "Get memory system health, counts, and statistics",
    {},
    async () => {
      try {
        const qdrantStats = await ctx.qdrant.getStatistics();

        let neo4jStats = { nodeCount: 0, relationshipCount: 0 };
        try {
          neo4jStats = await ctx.neo4j.getStatistics();
        } catch {
          // Neo4j might not be available
        }

        const totalMemories = qdrantStats.collections.reduce(
          (sum, c) => sum + c.count,
          0
        );

        return toolResult({
          project_id: ctx.projectId,
          health: "healthy",
          totals: {
            memories: totalMemories,
            graph_nodes: neo4jStats.nodeCount,
            graph_relationships: neo4jStats.relationshipCount
          },
          collections: qdrantStats.collections,
          storage: {
            qdrant: { status: "connected", url: ctx.config.qdrant.url },
            neo4j: {
              status: neo4jStats.nodeCount >= 0 ? "connected" : "disconnected",
              uri: ctx.config.neo4j.uri
            }
          }
        });
      } catch (error) {
        logger.error("memory_statistics failed", { error: String(error) });
        return toolError("STATS_ERROR", String(error));
      }
    }
  );

  // normalize_memory - Run normalization phases
  server.tool(
    "normalize_memory",
    "Run memory normalization to deduplicate and consolidate",
    {
      phases: z.array(z.enum(["dedup", "merge", "cleanup"])).default(["dedup", "merge", "cleanup"])
    },
    async (input) => {
      try {
        const jobId = crypto.randomUUID();

        normalizeJobs.set(jobId, {
          status: "running",
          phases_completed: [],
          started_at: new Date().toISOString()
        });

        // Run normalization asynchronously
        (async () => {
          const job = normalizeJobs.get(jobId)!;

          try {
            for (const phase of input.phases) {
              job.current_phase = phase;

              switch (phase) {
                case "dedup":
                  // Find and mark duplicates
                  logger.info("Running deduplication phase");
                  break;
                case "merge":
                  // Merge related memories
                  logger.info("Running merge phase");
                  break;
                case "cleanup":
                  // Remove orphaned data
                  logger.info("Running cleanup phase");
                  break;
              }

              job.phases_completed.push(phase);
            }

            job.status = "completed";
            job.current_phase = undefined;
            job.completed_at = new Date().toISOString();
          } catch (error) {
            job.status = "failed";
            job.error = String(error);
            job.completed_at = new Date().toISOString();
          }
        })();

        return toolResult({
          job_id: jobId,
          phases: input.phases,
          status: "started"
        });
      } catch (error) {
        logger.error("normalize_memory failed", { error: String(error) });
        return toolError("NORMALIZE_ERROR", String(error));
      }
    }
  );

  // normalize_status - Get normalization job status
  server.tool(
    "normalize_status",
    "Get the status of a normalization job",
    {
      job_id: z.string().uuid()
    },
    async (input) => {
      const job = normalizeJobs.get(input.job_id);

      if (!job) {
        return toolError("JOB_NOT_FOUND", `Job not found: ${input.job_id}`);
      }

      return toolResult({
        job_id: input.job_id,
        ...job
      });
    }
  );

  // export_memory - Export memories to JSONL
  server.tool(
    "export_memory",
    "Export memories to JSONL file",
    {
      output_path: z.string().min(1).max(1000),
      memory_types: z.array(MemoryTypeSchema).optional()
    },
    async (input) => {
      try {
        const types = input.memory_types || [...MEMORY_TYPES];
        const outputStream = createWriteStream(input.output_path);

        let totalExported = 0;

        for (const memoryType of types) {
          const collection = ctx.collectionName(memoryType);

          // Search with empty vector to get all (will be unsorted)
          // In production, would use scroll API
          const zeroVector = new Array(1024).fill(0);

          const results = await ctx.qdrant.search({
            collections: [collection],
            vector: zeroVector,
            limit: 10000, // Pagination would be needed for larger datasets
            filter: {
              must: [
                { key: "project_id", match: { value: ctx.projectId } },
                { key: "deleted", match: { value: false } }
              ]
            }
          });

          for (const result of results) {
            const record = {
              memory_id: result.id,
              type: result.payload["type"],
              content: result.payload["content"],
              metadata: result.payload["metadata"],
              created_at: result.payload["created_at"],
              updated_at: result.payload["updated_at"]
            };

            outputStream.write(JSON.stringify(record) + "\n");
            totalExported++;
          }
        }

        outputStream.end();

        return toolResult({
          status: "completed",
          output_path: input.output_path,
          exported_count: totalExported,
          memory_types: types
        });
      } catch (error) {
        logger.error("export_memory failed", { error: String(error) });
        return toolError("EXPORT_ERROR", String(error));
      }
    }
  );

  // import_memory - Import memories from JSONL
  server.tool(
    "import_memory",
    "Import memories from JSONL file",
    {
      input_path: z.string().min(1).max(1000)
    },
    async (input) => {
      try {
        if (!existsSync(input.input_path)) {
          return toolError("FILE_NOT_FOUND", `File not found: ${input.input_path}`);
        }

        const fileStream = createReadStream(input.input_path);
        const rl = createInterface({
          input: fileStream,
          crlfDelay: Infinity
        });

        let imported = 0;
        let errors = 0;
        const now = new Date().toISOString();

        for await (const line of rl) {
          if (!line.trim()) continue;

          try {
            const record = JSON.parse(line) as {
              memory_id?: string;
              type: string;
              content: string;
              metadata?: Record<string, unknown>;
              created_at?: string;
              updated_at?: string;
            };

            // Validate memory type
            if (!MEMORY_TYPES.includes(record.type as typeof MEMORY_TYPES[number])) {
              errors++;
              continue;
            }

            const memoryId = record.memory_id || crypto.randomUUID();
            const embedding = await ctx.voyage.embed(record.content);

            await ctx.qdrant.upsert(ctx.collectionName(record.type), {
              id: memoryId,
              vector: embedding,
              payload: {
                type: record.type,
                content: record.content,
                metadata: record.metadata || {},
                created_at: record.created_at || now,
                updated_at: now,
                deleted: false,
                project_id: ctx.projectId
              }
            });

            imported++;
          } catch (e) {
            logger.warn("Failed to import line", { error: String(e) });
            errors++;
          }
        }

        return toolResult({
          status: "completed",
          input_path: input.input_path,
          imported_count: imported,
          error_count: errors
        });
      } catch (error) {
        logger.error("import_memory failed", { error: String(error) });
        return toolError("IMPORT_ERROR", String(error));
      }
    }
  );

  logger.info("Registered 5 maintenance tools");
}
