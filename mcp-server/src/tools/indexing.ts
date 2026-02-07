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

/**
 * Extracted function information
 * REQ-007-FN-071: Function metadata
 */
interface ExtractedFunction {
  name: string;
  body: string;
  startLine: number;
  endLine: number;
  signature: string;
  isAsync: boolean;
  isMethod: boolean;
  className?: string;
}

/**
 * Extract functions from JavaScript/TypeScript code
 * REQ-007-FN-072: Support JS/TS functions, arrow functions, and methods
 */
function extractJavaScriptFunctions(content: string): ExtractedFunction[] {
  const functions: ExtractedFunction[] = [];
  const lines = content.split('\n');

  // Regular function declarations
  const functionRegex = /^(\s*)(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)/gm;
  // Arrow functions (const name = async? (...) => ...)
  const arrowRegex = /^(\s*)(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*(?::\s*[^=]+)?\s*=>/gm;
  // Class method declarations
  const methodRegex = /^(\s*)(?:async\s+)?(\w+)\s*\(([^)]*)\)\s*(?::\s*[^{]+)?\s*\{/gm;
  // Class declarations (to track method context)
  const classRegex = /^(\s*)(?:export\s+)?class\s+(\w+)/gm;

  let currentClass: string | undefined;
  let classIndent = -1;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const lineNum = i + 1;

    // Track class context
    const classMatch = classRegex.exec(line);
    if (classMatch) {
      currentClass = classMatch[2];
      classIndent = classMatch[1].length;
    } else if (currentClass && line.trim().startsWith('}') && line.search(/\S/) <= classIndent) {
      currentClass = undefined;
      classIndent = -1;
    }

    // Check for function declaration
    functionRegex.lastIndex = 0;
    const funcMatch = functionRegex.exec(line);
    if (funcMatch) {
      const indent = funcMatch[1].length;
      const name = funcMatch[2];
      const isAsync = line.includes('async ');

      // Find the end of the function
      const endLine = findFunctionEnd(lines, i, indent);
      const body = lines.slice(i, endLine + 1).join('\n');

      functions.push({
        name,
        body,
        startLine: lineNum,
        endLine: endLine + 1,
        signature: line.trim().replace(/\s*\{.*$/, ''),
        isAsync,
        isMethod: false
      });
      continue;
    }

    // Check for arrow function
    arrowRegex.lastIndex = 0;
    const arrowMatch = arrowRegex.exec(line);
    if (arrowMatch) {
      const indent = arrowMatch[1].length;
      const name = arrowMatch[2];
      const isAsync = line.includes('async ');

      const endLine = findFunctionEnd(lines, i, indent);
      const body = lines.slice(i, endLine + 1).join('\n');

      functions.push({
        name,
        body,
        startLine: lineNum,
        endLine: endLine + 1,
        signature: line.trim().replace(/\s*=>\s*\{.*$/, ' =>').replace(/\s*=>\s*[^{].*$/, ' =>'),
        isAsync,
        isMethod: false
      });
      continue;
    }

    // Check for class method (only if inside a class and not a constructor/getter/setter)
    if (currentClass) {
      methodRegex.lastIndex = 0;
      const methodMatch = methodRegex.exec(line);
      if (methodMatch && !['constructor', 'get', 'set'].includes(methodMatch[2])) {
        const indent = methodMatch[1].length;
        const name = methodMatch[2];
        const isAsync = line.includes('async ');

        const endLine = findFunctionEnd(lines, i, indent);
        const body = lines.slice(i, endLine + 1).join('\n');

        functions.push({
          name,
          body,
          startLine: lineNum,
          endLine: endLine + 1,
          signature: line.trim().replace(/\s*\{.*$/, ''),
          isAsync,
          isMethod: true,
          className: currentClass
        });
      }
    }
  }

  return functions;
}

/**
 * Extract functions from Python code
 * REQ-007-FN-072: Support Python def and async def
 */
function extractPythonFunctions(content: string): ExtractedFunction[] {
  const functions: ExtractedFunction[] = [];
  const lines = content.split('\n');

  // def function_name(args):
  // async def function_name(args):
  const functionRegex = /^(\s*)(async\s+)?def\s+(\w+)\s*\(([^)]*)\)\s*(?:->\s*[^:]+)?:/;
  // class ClassName:
  const classRegex = /^(\s*)class\s+(\w+)/;

  let currentClass: string | undefined;
  let classIndent = -1;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const lineNum = i + 1;

    // Track class context
    const classMatch = classRegex.exec(line);
    if (classMatch) {
      currentClass = classMatch[2];
      classIndent = classMatch[1].length;
    } else if (currentClass && line.trim() && !line.trim().startsWith('#') && line.search(/\S/) <= classIndent) {
      currentClass = undefined;
      classIndent = -1;
    }

    const match = functionRegex.exec(line);
    if (match) {
      const indent = match[1].length;
      const isAsync = !!match[2];
      const name = match[3];

      // Find end of function (next line with same or less indentation that's not empty/comment)
      const endLine = findPythonFunctionEnd(lines, i, indent);
      const body = lines.slice(i, endLine + 1).join('\n');

      // Skip dunder methods for class methods
      const isDunder = name.startsWith('__') && name.endsWith('__');
      const isMethod = currentClass !== undefined && indent > classIndent;

      if (!isDunder || !isMethod) {
        functions.push({
          name,
          body,
          startLine: lineNum,
          endLine: endLine + 1,
          signature: line.trim(),
          isAsync,
          isMethod,
          className: isMethod ? currentClass : undefined
        });
      }
    }
  }

  return functions;
}

/**
 * Find the end of a brace-delimited function (JS/TS)
 */
function findFunctionEnd(lines: string[], startIndex: number, startIndent: number): number {
  let braceCount = 0;
  let foundOpening = false;

  for (let i = startIndex; i < lines.length; i++) {
    const line = lines[i];

    for (const char of line) {
      if (char === '{') {
        braceCount++;
        foundOpening = true;
      } else if (char === '}') {
        braceCount--;
      }
    }

    if (foundOpening && braceCount === 0) {
      return i;
    }
  }

  return lines.length - 1;
}

/**
 * Find the end of a Python function (indentation-based)
 */
function findPythonFunctionEnd(lines: string[], startIndex: number, funcIndent: number): number {
  const bodyIndent = funcIndent + 4; // Assume 4-space indent

  for (let i = startIndex + 1; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    // Skip empty lines and comments
    if (!trimmed || trimmed.startsWith('#')) {
      continue;
    }

    // Check indentation
    const currentIndent = line.search(/\S/);
    if (currentIndent !== -1 && currentIndent < bodyIndent) {
      return i - 1;
    }
  }

  return lines.length - 1;
}

/**
 * Extract functions based on language
 * REQ-007-FN-070
 */
function extractFunctions(content: string, language: string | undefined): ExtractedFunction[] {
  switch (language) {
    case 'javascript':
    case 'typescript':
      return extractJavaScriptFunctions(content);
    case 'python':
      return extractPythonFunctions(content);
    default:
      return [];
  }
}

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
  // REQ-007-FN-070 to FN-074: Function extraction during indexing
  server.tool(
    "index_file",
    "Index a single source file, store its code pattern, and extract individual functions",
    {
      file_path: z.string().min(1).max(1000),
      language: z.string().optional(),
      extract_functions: z.boolean().default(true)
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

        // Store the code pattern for the entire file
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

        // REQ-007-FN-070, FN-071, FN-072, FN-074: Extract and store functions
        let functionsExtracted = 0;
        const functionMemoryIds: string[] = [];

        if (input.extract_functions && language) {
          // REQ-007-FN-073: Remove old function memories for this file before adding new ones
          try {
            const existingFunctions = await ctx.qdrant.scroll(
              ctx.collectionName("function"),
              {
                filter: {
                  must: [
                    { key: "metadata.file_path", match: { value: input.file_path } },
                    { key: "project_id", match: { value: ctx.projectId } },
                    { key: "deleted", match: { value: false } }
                  ]
                },
                limit: 1000
              }
            );

            // Mark old functions as deleted
            for (const point of existingFunctions.points) {
              await ctx.qdrant.upsert(ctx.collectionName("function"), {
                id: point.id as string,
                vector: point.vector as number[],
                payload: {
                  ...point.payload,
                  deleted: true,
                  updated_at: now
                }
              });
            }

            if (existingFunctions.points.length > 0) {
              logger.info("Cleaned up old function memories", {
                file_path: input.file_path,
                count: existingFunctions.points.length
              });
            }
          } catch (error) {
            // Collection might not exist yet, ignore
            logger.debug("Could not clean up old functions", { error: String(error) });
          }

          // Extract functions
          const extractedFunctions = extractFunctions(content, language);

          // Store each function as a separate memory
          for (const func of extractedFunctions) {
            const funcMemoryId = randomUUID();
            const funcEmbedding = await ctx.voyage.embed(func.body);

            await ctx.qdrant.upsert(ctx.collectionName("function"), {
              id: funcMemoryId,
              vector: funcEmbedding,
              payload: {
                type: "function",
                content: func.body,
                metadata: {
                  function_name: func.name,
                  file_path: input.file_path,
                  language: language,
                  start_line: func.startLine,
                  end_line: func.endLine,
                  signature: func.signature,
                  is_async: func.isAsync,
                  is_method: func.isMethod,
                  class_name: func.className,
                  indexed_at: now
                },
                created_at: now,
                updated_at: now,
                deleted: false,
                project_id: ctx.projectId
              }
            });

            functionMemoryIds.push(funcMemoryId);
            functionsExtracted++;
          }

          logger.info("Extracted functions", {
            file_path: input.file_path,
            count: functionsExtracted
          });
        }

        return toolResult({
          memory_id: memoryId,
          file_path: input.file_path,
          language: language,
          status: "indexed",
          functions_extracted: functionsExtracted,
          function_memory_ids: functionMemoryIds
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

  // index_docs - Index documentation files (markdown) with intelligent type detection
  server.tool(
    "index_docs",
    "Index markdown documentation files with automatic type detection based on path",
    {
      directory_path: z.string().min(1).max(1000),
      patterns: z.array(z.string()).default(["**/*.md"]),
      exclude_patterns: z.array(z.string()).default(["**/node_modules/**", "**/.git/**", "**/dist/**", "**/README.md"])
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

            if (input.exclude_patterns.some(p => matchesPattern(relativePath, p))) {
              continue;
            }

            if (entry.isDirectory()) {
              walkDir(fullPath);
            } else if (entry.isFile()) {
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
              const memoryType = detectDocType(filePath);
              const memoryId = randomUUID();
              const now = new Date().toISOString();

              const embedding = await ctx.voyage.embed(content);
              const collection = ctx.collectionName(memoryType);

              await ctx.qdrant.upsert(collection, {
                id: memoryId,
                vector: embedding,
                payload: {
                  type: memoryType,
                  content: content,
                  metadata: {
                    file_path: filePath,
                    document: extractDocTitle(content, filePath),
                    size_bytes: Buffer.byteLength(content, "utf-8"),
                    indexed_at: now
                  },
                  created_at: now,
                  updated_at: now,
                  deleted: false,
                  project_id: ctx.projectId
                }
              });

              // Create graph node for graph-eligible doc types
              if (["requirements", "design", "architecture"].includes(memoryType)) {
                try {
                  const contentSummary = content.substring(0, 500);
                  await ctx.neo4j.createNode(
                    memoryType.charAt(0).toUpperCase() + memoryType.slice(1),
                    memoryId,
                    {
                      content: contentSummary,
                      document: extractDocTitle(content, filePath),
                      file_path: filePath
                    }
                  );

                  // Auto-infer relationships to other docs
                  const graphTypes = ["requirements", "design", "architecture", "component"].filter(t => t !== memoryType);
                  for (const searchType of graphTypes) {
                    try {
                      const searchCollection = ctx.collectionName(searchType);
                      const similar = await ctx.qdrant.searchSimilar(searchCollection, embedding, 3, 0.75);
                      for (const match of similar) {
                        const relType = inferDocRelationshipType(memoryType, searchType);
                        await ctx.neo4j.createRelationship(memoryId, relType, match.id);
                        logger.info("Auto-created doc relationship", { from: memoryId, type: relType, to: match.id });
                      }
                    } catch {
                      // Collection may not exist
                    }
                  }
                } catch (error) {
                  logger.warn("Failed to create graph node for doc", { error: String(error) });
                }
              }

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
        logger.error("index_docs failed", { error: String(error) });
        return toolError("INDEX_ERROR", String(error));
      }
    }
  );

  logger.info("Registered 5 indexing tools");
}

// Detect document type based on path patterns
function detectDocType(filePath: string): string {
  const lowerPath = filePath.toLowerCase();

  // Requirements patterns
  if (lowerPath.includes("requirement") || lowerPath.includes("req-") ||
      lowerPath.includes("/requirements/") || lowerPath.includes("user-stor")) {
    return "requirements";
  }

  // Architecture patterns (ADRs)
  if (lowerPath.includes("adr") || lowerPath.includes("architecture") ||
      lowerPath.includes("decision") || lowerPath.includes("/adrs/")) {
    return "architecture";
  }

  // Design patterns
  if (lowerPath.includes("design") || lowerPath.includes("spec") ||
      lowerPath.includes("ui-") || lowerPath.includes("ux-") ||
      lowerPath.includes("/design-docs/") || lowerPath.includes("/designs/")) {
    return "design";
  }

  // Default to design for other docs
  return "design";
}

// Extract document title from content or filename
function extractDocTitle(content: string, filePath: string): string {
  // Try to find markdown title (# Title)
  const titleMatch = content.match(/^#\s+(.+)$/m);
  if (titleMatch && titleMatch[1]) {
    return titleMatch[1].trim();
  }

  // Fall back to filename
  const basename = filePath.split("/").pop() || filePath;
  return basename.replace(/\.md$/i, "").replace(/[-_]/g, " ");
}

// Infer relationship type for documentation
function inferDocRelationshipType(sourceType: string, targetType: string): string {
  if (sourceType === "architecture" && targetType === "requirements") return "ADDRESSES";
  if (sourceType === "architecture" && targetType === "design") return "GUIDES";
  if (sourceType === "design" && targetType === "requirements") return "IMPLEMENTS";
  if (sourceType === "design" && targetType === "architecture") return "FOLLOWS";
  if (sourceType === "requirements" && targetType === "design") return "IMPLEMENTED_BY";
  return "RELATED_TO";
}
