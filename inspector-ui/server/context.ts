/**
 * Server Context
 *
 * Holds initialized adapters and configuration for the Inspector API.
 * Reuses QdrantAdapter, Neo4jAdapter, and VoyageClient from mcp-server.
 */

// Import adapters from mcp-server
import { QdrantAdapter } from '../../mcp-server/src/storage/qdrant.js';
import { Neo4jAdapter } from '../../mcp-server/src/storage/neo4j.js';
import { VoyageClient } from '../../mcp-server/src/embedding/voyage.js';
import { loadConfig } from '../../mcp-server/src/config.js';

export interface ServerContext {
  qdrant: QdrantAdapter;
  neo4j: Neo4jAdapter;
  voyage: VoyageClient;
  projectId: string;
  qdrantUrl: string;
  neo4jUri: string;
  neo4jUser: string;
  neo4jPassword: string;
  close: () => Promise<void>;
}

export async function createContext(): Promise<ServerContext> {
  // Load configuration using mcp-server's config loader (no arguments)
  const config = loadConfig();

  // Get project ID from environment variable
  const projectId = process.env.INSPECTOR_PROJECT_ID || 'default';

  // Initialize adapters (positional args, not options objects)
  const qdrant = new QdrantAdapter(
    config.qdrant.url,
    projectId
  );

  const neo4j = new Neo4jAdapter(
    config.neo4j.uri,
    config.neo4j.user,
    config.neo4j.password,
    projectId
  );

  // Note: config uses snake_case (api_key)
  const voyage = new VoyageClient(config.voyage.api_key);

  // Verify database connectivity
  await neo4j.verifyConnectivity();

  return {
    qdrant,
    neo4j,
    voyage,
    projectId,
    qdrantUrl: config.qdrant.url,
    neo4jUri: config.neo4j.uri,
    neo4jUser: config.neo4j.user,
    neo4jPassword: config.neo4j.password,
    close: async () => {
      await neo4j.close();
      // QdrantAdapter doesn't require explicit close
    }
  };
}
