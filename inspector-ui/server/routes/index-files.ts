/**
 * Index Files Routes
 *
 * File and directory indexing operations.
 */
import { Router, Request, Response, NextFunction } from 'express';
import { z } from 'zod';
import * as fs from 'fs/promises';
import * as path from 'path';
import type { ServerContext } from '../context.js';
import { createError } from '../middleware/error-handler.js';

export const indexFilesRouter = Router();

// Request type with context
interface ContextRequest extends Request {
  context: ServerContext;
}

// In-memory job storage
const indexJobs = new Map<string, {
  id: string;
  type: 'file' | 'directory' | 'reindex';
  status: 'pending' | 'running' | 'complete' | 'failed';
  path: string;
  startedAt: string;
  completedAt?: string;
  filesProcessed: number;
  filesTotal: number;
  errors: string[];
}>();

// Validation schemas
const indexFileSchema = z.object({
  path: z.string().min(1),
  language: z.string().optional()
});

const indexDirectorySchema = z.object({
  path: z.string().min(1),
  patterns: z.array(z.string()).default(['*.ts', '*.js', '*.py', '*.go', '*.java']),
  excludePatterns: z.array(z.string()).default(['node_modules', 'dist', '.git', '__pycache__', 'vendor'])
});

const reindexSchema = z.object({
  path: z.string().min(1),
  scope: z.enum(['full', 'changed']).default('changed')
});

// Language detection by extension
const LANGUAGE_MAP: Record<string, string> = {
  '.ts': 'typescript',
  '.tsx': 'typescript',
  '.js': 'javascript',
  '.jsx': 'javascript',
  '.py': 'python',
  '.go': 'go',
  '.java': 'java',
  '.rs': 'rust',
  '.rb': 'ruby',
  '.php': 'php',
  '.cs': 'csharp',
  '.cpp': 'cpp',
  '.c': 'c',
  '.h': 'c',
  '.hpp': 'cpp',
  '.swift': 'swift',
  '.kt': 'kotlin',
  '.scala': 'scala',
  '.sql': 'sql',
  '.sh': 'bash',
  '.bash': 'bash',
  '.zsh': 'bash',
  '.yml': 'yaml',
  '.yaml': 'yaml',
  '.json': 'json',
  '.md': 'markdown'
};

/**
 * POST /api/index/file
 * Index a single file
 */
indexFilesRouter.post('/file', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const contextReq = req as ContextRequest;
    const { qdrant, voyage, neo4j, projectId } = contextReq.context;

    const input = indexFileSchema.parse(req.body);

    // Validate file exists
    try {
      await fs.access(input.path);
    } catch {
      throw createError(`File not found: ${input.path}`, 404, 'FILE_NOT_FOUND');
    }

    // Read file content
    const content = await fs.readFile(input.path, 'utf-8');
    const stats = await fs.stat(input.path);

    // Detect language
    const ext = path.extname(input.path);
    const language = input.language || LANGUAGE_MAP[ext] || 'unknown';

    // Generate embedding
    const embedding = await voyage.embed(content);
    const now = new Date().toISOString();
    const memoryId = crypto.randomUUID();

    // Determine memory type based on content
    const type = detectMemoryType(content, input.path);
    const collectionName = `memory_${type}_${projectId}`;

    // Store in Qdrant
    await qdrant.upsert(collectionName, [{
      id: memoryId,
      vector: embedding,
      payload: {
        type,
        content,
        metadata: {
          file_path: input.path,
          language,
          file_size: stats.size,
          modified_at: stats.mtime.toISOString()
        },
        created_at: now,
        updated_at: now,
        deleted: false,
        project_id: projectId
      }
    }]);

    // Store in Neo4j
    await neo4j.createNode({
      id: memoryId,
      type,
      content: content.substring(0, 500),
      metadata: {
        file_path: input.path,
        language
      },
      project_id: projectId
    });

    res.json({
      success: true,
      memoryId,
      type,
      language,
      path: input.path,
      size: stats.size
    });
  } catch (error) {
    next(error);
  }
});

/**
 * POST /api/index/directory
 * Index a directory (async job)
 */
indexFilesRouter.post('/directory', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const contextReq = req as ContextRequest;
    const input = indexDirectorySchema.parse(req.body);

    // Validate directory exists
    try {
      const stats = await fs.stat(input.path);
      if (!stats.isDirectory()) {
        throw createError(`Not a directory: ${input.path}`, 400, 'NOT_A_DIRECTORY');
      }
    } catch (err) {
      if ((err as NodeJS.ErrnoException).code === 'ENOENT') {
        throw createError(`Directory not found: ${input.path}`, 404, 'DIR_NOT_FOUND');
      }
      throw err;
    }

    // Create job
    const jobId = crypto.randomUUID();
    const job = {
      id: jobId,
      type: 'directory' as const,
      status: 'pending' as const,
      path: input.path,
      startedAt: new Date().toISOString(),
      filesProcessed: 0,
      filesTotal: 0,
      errors: [] as string[]
    };

    indexJobs.set(jobId, job);

    // Run indexing asynchronously
    runDirectoryIndex(jobId, contextReq.context, input.path, input.patterns, input.excludePatterns);

    res.status(202).json({ jobId, status: 'pending' });
  } catch (error) {
    next(error);
  }
});

/**
 * POST /api/index/reindex
 * Reindex files at a path
 */
indexFilesRouter.post('/reindex', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const contextReq = req as ContextRequest;
    const input = reindexSchema.parse(req.body);

    const jobId = crypto.randomUUID();
    const job = {
      id: jobId,
      type: 'reindex' as const,
      status: 'pending' as const,
      path: input.path,
      startedAt: new Date().toISOString(),
      filesProcessed: 0,
      filesTotal: 0,
      errors: [] as string[]
    };

    indexJobs.set(jobId, job);

    // For reindex, we delete existing entries and re-index
    runReindex(jobId, contextReq.context, input.path, input.scope);

    res.status(202).json({ jobId, status: 'pending' });
  } catch (error) {
    next(error);
  }
});

/**
 * GET /api/index/status/:jobId
 * Get indexing job status
 */
indexFilesRouter.get('/status/:jobId', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { jobId } = req.params;
    const job = indexJobs.get(jobId);

    if (!job) {
      throw createError(`Job not found: ${jobId}`, 404, 'NOT_FOUND');
    }

    res.json(job);
  } catch (error) {
    next(error);
  }
});

/**
 * DELETE /api/index/cancel/:jobId
 * Cancel an indexing job (if possible)
 */
indexFilesRouter.delete('/cancel/:jobId', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { jobId } = req.params;
    const job = indexJobs.get(jobId);

    if (!job) {
      throw createError(`Job not found: ${jobId}`, 404, 'NOT_FOUND');
    }

    if (job.status === 'pending' || job.status === 'running') {
      job.status = 'failed';
      job.completedAt = new Date().toISOString();
      job.errors.push('Job cancelled by user');
    }

    res.json({ success: true, jobId });
  } catch (error) {
    next(error);
  }
});

/**
 * Run directory indexing
 */
async function runDirectoryIndex(
  jobId: string,
  context: ServerContext,
  dirPath: string,
  patterns: string[],
  excludePatterns: string[]
): Promise<void> {
  const job = indexJobs.get(jobId);
  if (!job) return;

  job.status = 'running';

  try {
    // Find all matching files
    const files = await findMatchingFiles(dirPath, patterns, excludePatterns);
    job.filesTotal = files.length;

    const { qdrant, voyage, neo4j, projectId } = context;

    for (const filePath of files) {
      if (job.status === 'failed') break; // Check for cancellation

      try {
        const content = await fs.readFile(filePath, 'utf-8');
        const stats = await fs.stat(filePath);
        const ext = path.extname(filePath);
        const language = LANGUAGE_MAP[ext] || 'unknown';

        const embedding = await voyage.embed(content);
        const now = new Date().toISOString();
        const memoryId = crypto.randomUUID();
        const type = detectMemoryType(content, filePath);
        const collectionName = `memory_${type}_${projectId}`;

        await qdrant.upsert(collectionName, [{
          id: memoryId,
          vector: embedding,
          payload: {
            type,
            content,
            metadata: {
              file_path: filePath,
              language,
              file_size: stats.size,
              modified_at: stats.mtime.toISOString()
            },
            created_at: now,
            updated_at: now,
            deleted: false,
            project_id: projectId
          }
        }]);

        await neo4j.createNode({
          id: memoryId,
          type,
          content: content.substring(0, 500),
          metadata: { file_path: filePath, language },
          project_id: projectId
        });

        job.filesProcessed++;
      } catch (err) {
        job.errors.push(`Failed to index ${filePath}: ${(err as Error).message}`);
      }
    }

    job.status = 'complete';
    job.completedAt = new Date().toISOString();
  } catch (err) {
    job.status = 'failed';
    job.completedAt = new Date().toISOString();
    job.errors.push(`Directory indexing failed: ${(err as Error).message}`);
  }
}

/**
 * Run reindex operation
 */
async function runReindex(
  jobId: string,
  context: ServerContext,
  dirPath: string,
  scope: 'full' | 'changed'
): Promise<void> {
  const job = indexJobs.get(jobId);
  if (!job) return;

  job.status = 'running';

  try {
    const { qdrant, voyage, neo4j, projectId } = context;

    // If full scope, delete existing entries for this path
    if (scope === 'full') {
      // Find and delete existing memories for this path
      const memoryTypes = ['function', 'code_pattern', 'component'];

      for (const type of memoryTypes) {
        const collectionName = `memory_${type}_${projectId}`;

        try {
          const points = await qdrant.scroll(collectionName, {
            filter: {
              must: [
                { key: 'project_id', match: { value: projectId } }
              ]
            },
            limit: 10000
          });

          const toDelete: string[] = [];
          for (const point of points) {
            const payload = point.payload as Record<string, unknown>;
            const metadata = payload.metadata as Record<string, unknown>;
            const filePath = metadata?.file_path as string;

            if (filePath && filePath.startsWith(dirPath)) {
              toDelete.push(String(point.id));
            }
          }

          if (toDelete.length > 0) {
            await qdrant.delete(collectionName, toDelete);
            for (const id of toDelete) {
              await neo4j.deleteNode(id);
            }
          }
        } catch {
          // Collection might not exist
        }
      }
    }

    // Re-index
    const defaultPatterns = ['*.ts', '*.js', '*.py', '*.go', '*.java'];
    const defaultExcludes = ['node_modules', 'dist', '.git', '__pycache__', 'vendor'];

    await runDirectoryIndex(jobId, context, dirPath, defaultPatterns, defaultExcludes);
  } catch (err) {
    job.status = 'failed';
    job.completedAt = new Date().toISOString();
    job.errors.push(`Reindex failed: ${(err as Error).message}`);
  }
}

/**
 * Find files matching patterns
 */
async function findMatchingFiles(
  dirPath: string,
  patterns: string[],
  excludePatterns: string[]
): Promise<string[]> {
  const files: string[] = [];

  async function walk(currentPath: string): Promise<void> {
    const entries = await fs.readdir(currentPath, { withFileTypes: true });

    for (const entry of entries) {
      const fullPath = path.join(currentPath, entry.name);

      // Check exclusions
      if (excludePatterns.some(p => entry.name === p || fullPath.includes(`/${p}/`))) {
        continue;
      }

      if (entry.isDirectory()) {
        await walk(fullPath);
      } else if (entry.isFile()) {
        // Check if file matches any pattern
        const ext = path.extname(entry.name);
        const matches = patterns.some(p => {
          if (p.startsWith('*.')) {
            return ext === p.slice(1);
          }
          return entry.name === p;
        });

        if (matches) {
          files.push(fullPath);
        }
      }
    }
  }

  await walk(dirPath);
  return files;
}

/**
 * Detect memory type based on content and path
 */
function detectMemoryType(content: string, filePath: string): string {
  const pathLower = filePath.toLowerCase();
  const contentLower = content.toLowerCase();

  // Test files
  if (pathLower.includes('test') || pathLower.includes('spec')) {
    return 'test_history';
  }

  // Function definitions
  if (
    contentLower.includes('function ') ||
    contentLower.includes('def ') ||
    contentLower.includes('func ') ||
    contentLower.includes('=>')
  ) {
    return 'function';
  }

  // Component files
  if (
    pathLower.includes('component') ||
    contentLower.includes('react') ||
    contentLower.includes('export default')
  ) {
    return 'component';
  }

  // Default to code_pattern
  return 'code_pattern';
}
