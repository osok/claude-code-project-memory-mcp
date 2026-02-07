/**
 * Memory Inspector API Server
 *
 * Express backend for the Memory Inspector UI.
 * Reuses adapters from mcp-server for database access.
 */
import express, { Express, Request, Response, NextFunction } from 'express';
import cors from 'cors';
import { createContext, ServerContext } from './context.js';
import { errorHandler } from './middleware/error-handler.js';
import { requestLogger } from './middleware/request-logger.js';

// Import adapters for per-request instantiation
import { QdrantAdapter } from '../../mcp-server/src/storage/qdrant.js';
import { Neo4jAdapter } from '../../mcp-server/src/storage/neo4j.js';

// Route imports
import { memoriesRouter } from './routes/memories.js';
import { searchRouter } from './routes/search.js';
import { graphRouter } from './routes/graph.js';
import { statsRouter } from './routes/stats.js';
import { normalizeRouter } from './routes/normalize.js';
import { exportImportRouter } from './routes/export-import.js';
import { indexFilesRouter } from './routes/index-files.js';
import { configRouter } from './routes/config.js';

const DEFAULT_PORT = 3002;
const HOST = '127.0.0.1'; // localhost only for security

let server: ReturnType<Express['listen']> | null = null;
let context: ServerContext | null = null;

// Cache for project-specific adapters
const adapterCache = new Map<string, { qdrant: QdrantAdapter; neo4j: Neo4jAdapter }>();

export async function startServer(port: number = DEFAULT_PORT): Promise<void> {
  const app = express();

  // Initialize server context with adapters
  context = await createContext();

  // Cache the default adapters
  adapterCache.set(context.projectId, {
    qdrant: context.qdrant,
    neo4j: context.neo4j
  });

  // Middleware
  app.use(cors({
    origin: ['http://localhost:5173', 'http://127.0.0.1:5173'],
    credentials: true
  }));
  app.use(express.json({ limit: '10mb' }));
  app.use(requestLogger);

  // Inject context into request, using X-Project-Id header if provided
  app.use((req: Request, _res: Response, next: NextFunction) => {
    const requestedProjectId = req.headers['x-project-id'] as string | undefined;
    const projectId = requestedProjectId || context!.projectId;

    // Get or create adapters for this project
    let adapters = adapterCache.get(projectId);
    if (!adapters) {
      // Create new adapters for this project (they connect to the same databases)
      // Use credentials from context (loaded from config.toml or env vars)
      adapters = {
        qdrant: new QdrantAdapter(context!.qdrantUrl, projectId),
        neo4j: new Neo4jAdapter(
          context!.neo4jUri,
          context!.neo4jUser,
          context!.neo4jPassword,
          projectId
        )
      };
      adapterCache.set(projectId, adapters);
    }

    // Create request-specific context
    const requestContext: ServerContext = {
      ...context!,
      projectId,
      qdrant: adapters.qdrant,
      neo4j: adapters.neo4j
    };

    (req as Request & { context: ServerContext }).context = requestContext;
    next();
  });

  // API Routes
  app.use('/api/memories', memoriesRouter);
  app.use('/api/search', searchRouter);
  app.use('/api/graph', graphRouter);
  app.use('/api/stats', statsRouter);
  app.use('/api/normalize', normalizeRouter);
  app.use('/api/export', exportImportRouter);
  app.use('/api/import', exportImportRouter);
  app.use('/api/index', indexFilesRouter);
  app.use('/api/config', configRouter);

  // Health check
  app.get('/api/health', (_req, res) => {
    res.json({ status: 'ok', timestamp: new Date().toISOString() });
  });

  // Error handler (must be last)
  app.use(errorHandler);

  // Start server
  server = app.listen(port, HOST, () => {
    console.log(`Memory Inspector API listening on http://${HOST}:${port}`);
    console.log(`  - Default Project ID: ${context?.projectId ?? 'default'}`);
    console.log(`  - Qdrant: ${context?.qdrantUrl ?? 'not configured'}`);
    console.log(`  - Neo4j: ${context?.neo4jUri ?? 'not configured'}`);
    console.log(`  - Dynamic project switching enabled via X-Project-Id header`);
  });

  // Graceful shutdown
  process.on('SIGINT', () => shutdown('SIGINT'));
  process.on('SIGTERM', () => shutdown('SIGTERM'));
}

async function shutdown(signal: string): Promise<void> {
  console.log(`\nReceived ${signal}, shutting down gracefully...`);

  // Close all cached Neo4j adapters
  for (const [projectId, adapters] of adapterCache) {
    try {
      await adapters.neo4j.close();
    } catch (err) {
      console.error(`Error closing Neo4j adapter for ${projectId}:`, err);
    }
  }
  adapterCache.clear();

  if (server) {
    server.close(() => {
      console.log('Server closed');
      process.exit(0);
    });
  } else {
    process.exit(0);
  }
}

// CLI entry point
const port = parseInt(process.env.INSPECTOR_PORT || String(DEFAULT_PORT), 10);
startServer(port).catch((err) => {
  console.error('Failed to start server:', err);
  process.exit(1);
});
