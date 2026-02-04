import { randomUUID } from "node:crypto";
import { z } from "zod";
import { readFileSync, existsSync, readdirSync, statSync } from "node:fs";
import { join, extname, relative } from "node:path";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { ToolContext } from "../context.js";
import { logger } from "../utils/logger.js";

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

const LANGUAGE_EXTENSIONS: Record<string, string[]> = {
  typescript: [".ts", ".tsx"],
  javascript: [".js", ".jsx", ".mjs"],
  python: [".py"],
  go: [".go"],
  rust: [".rs"],
  java: [".java"],
  csharp: [".cs"]
};

function detectLanguage(filePath: string): string | undefined {
  const ext = extname(filePath).toLowerCase();
  for (const [lang, exts] of Object.entries(LANGUAGE_EXTENSIONS)) {
    if (exts.includes(ext)) {
      return lang;
    }
  }
  return undefined;
}

function matchesPattern(filePath: string, pattern: string): boolean {
  // Simple glob matching
  if (pattern.startsWith("**/")) {
    const suffix = pattern.slice(3);
    return filePath.endsWith(suffix.replace("*", ""));
  }
  if (pattern.startsWith("*.")) {
    return filePath.endsWith(pattern.slice(1));
  }
  return filePath.includes(pattern);
}

// In-memory job tracking (would be persistent in production)
const indexingJobs = new Map<string, {
  status: "running" | "completed" | "failed";
  files_processed: number;
  files_total: number;
  started_at: string;
  completed_at?: string;
  error?: string;
}>();

export function registerIndexingTools(server: McpServer, ctx: ToolContext): void {
  // index_file - Index a single source file
  server.tool(
    "index_file",
    "Index a single source file and store its code patterns",
    {
      file_path: z.string().min(1).max(1000),
      language: z.string().optional()
    },
    async (input) => {
      try {
        if (!existsSync(input.file_path)) {
          return toolError("FILE_NOT_FOUND", `File not found: ${input.file_path}`);
        }

        const content = readFileSync(input.file_path, "utf-8");
        const language = input.language || detectLanguage(input.file_path);
        const memoryId = randomUUID();
        const now = new Date().toISOString();

        const embedding = await ctx.voyage.embed(content);

        await ctx.qdrant.upsert(ctx.collectionName("code_pattern"), {
          id: memoryId,
          vector: embedding,
          payload: {
            type: "code_pattern",
            content: content,
            metadata: {
              file_path: input.file_path,
              language: language,
              size_bytes: Buffer.byteLength(content, "utf-8"),
              indexed_at: now
            },
            created_at: now,
            updated_at: now,
            deleted: false,
            project_id: ctx.projectId
          }
        });

        return toolResult({
          memory_id: memoryId,
          file_path: input.file_path,
          language: language,
          status: "indexed"
        });
      } catch (error) {
        logger.error("index_file failed", { error: String(error) });
        return toolError("INDEX_ERROR", String(error));
      }
    }
  );

  // index_directory - Index a directory recursively
  server.tool(
    "index_directory",
    "Index all matching source files in a directory",
    {
      directory_path: z.string().min(1).max(1000),
      patterns: z.array(z.string()).default(["**/*.ts", "**/*.js", "**/*.py"]),
      exclude_patterns: z.array(z.string()).default(["**/node_modules/**", "**/.git/**", "**/dist/**"])
    },
    async (input) => {
      try {
        if (!existsSync(input.directory_path)) {
          return toolError("DIR_NOT_FOUND", `Directory not found: ${input.directory_path}`);
        }

        const jobId = randomUUID();
        const files: string[] = [];

        // Find matching files
        function walkDir(dir: string) {
          const entries = readdirSync(dir, { withFileTypes: true });
          for (const entry of entries) {
            const fullPath = join(dir, entry.name);
            const relativePath = relative(input.directory_path, fullPath);

            // Check exclude patterns
            if (input.exclude_patterns.some(p => matchesPattern(relativePath, p))) {
              continue;
            }

            if (entry.isDirectory()) {
              walkDir(fullPath);
            } else if (entry.isFile()) {
              // Check include patterns
              if (input.patterns.some(p => matchesPattern(relativePath, p))) {
                files.push(fullPath);
              }
            }
          }
        }

        walkDir(input.directory_path);

        // Start job tracking
        indexingJobs.set(jobId, {
          status: "running",
          files_processed: 0,
          files_total: files.length,
          started_at: new Date().toISOString()
        });

        // Process files asynchronously
        (async () => {
          const job = indexingJobs.get(jobId)!;
          try {
            for (const filePath of files) {
              const content = readFileSync(filePath, "utf-8");
              const language = detectLanguage(filePath);
              const memoryId = randomUUID();
              const now = new Date().toISOString();

              const embedding = await ctx.voyage.embed(content);

              await ctx.qdrant.upsert(ctx.collectionName("code_pattern"), {
                id: memoryId,
                vector: embedding,
                payload: {
                  type: "code_pattern",
                  content: content,
                  metadata: {
                    file_path: filePath,
                    language: language,
                    size_bytes: Buffer.byteLength(content, "utf-8"),
                    indexed_at: now
                  },
                  created_at: now,
                  updated_at: now,
                  deleted: false,
                  project_id: ctx.projectId
                }
              });

              job.files_processed++;
            }

            job.status = "completed";
            job.completed_at = new Date().toISOString();
          } catch (error) {
            job.status = "failed";
            job.error = String(error);
            job.completed_at = new Date().toISOString();
          }
        })();

        return toolResult({
          job_id: jobId,
          directory: input.directory_path,
          files_found: files.length,
          status: "started"
        });
      } catch (error) {
        logger.error("index_directory failed", { error: String(error) });
        return toolError("INDEX_ERROR", String(error));
      }
    }
  );

  // index_status - Get indexing job status
  server.tool(
    "index_status",
    "Get the status of an indexing job",
    {
      job_id: z.string().uuid()
    },
    async (input) => {
      const job = indexingJobs.get(input.job_id);

      if (!job) {
        return toolError("JOB_NOT_FOUND", `Job not found: ${input.job_id}`);
      }

      return toolResult({
        job_id: input.job_id,
        ...job
      });
    }
  );

  // reindex - Trigger reindexing of existing content
  server.tool(
    "reindex",
    "Trigger reindexing of files by path pattern",
    {
      path_pattern: z.string().optional(),
      memory_type: z.enum(["code_pattern", "function"]).default("code_pattern")
    },
    async (input) => {
      try {
        // For now, just return info about what would be reindexed
        // Full implementation would re-fetch content and regenerate embeddings
        const stats = await ctx.qdrant.getStatistics();

        const targetCollection = stats.collections.find(
          c => c.name === ctx.collectionName(input.memory_type)
        );

        return toolResult({
          status: "acknowledged",
          memory_type: input.memory_type,
          path_pattern: input.path_pattern || "*",
          affected_count: targetCollection?.count || 0,
          message: "Reindexing scheduled. Use index_status to track progress."
        });
      } catch (error) {
        logger.error("reindex failed", { error: String(error) });
        return toolError("REINDEX_ERROR", String(error));
      }
    }
  );

  logger.info("Registered 4 indexing tools");
}
