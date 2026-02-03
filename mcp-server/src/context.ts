import { QdrantAdapter } from "./storage/qdrant.js";
import { Neo4jAdapter } from "./storage/neo4j.js";
import { VoyageClient } from "./embedding/voyage.js";
import { loadConfig, validateConfig, type Config } from "./config.js";
import { logger } from "./utils/logger.js";

export interface ToolContext {
  projectId: string;
  qdrant: QdrantAdapter;
  neo4j: Neo4jAdapter;
  voyage: VoyageClient;
  config: Config;
  collectionName: (memoryType: string) => string;
  allCollections: () => string[];
}

export async function createContext(projectId: string): Promise<ToolContext> {
  logger.info("Creating tool context", { projectId });

  const config = loadConfig();
  validateConfig(config);

  const qdrant = new QdrantAdapter(config.qdrant.url, projectId);
  const neo4j = new Neo4jAdapter(
    config.neo4j.uri,
    config.neo4j.user,
    config.neo4j.password,
    projectId
  );
  const voyage = new VoyageClient(config.voyage.api_key);

  // Verify connectivity
  try {
    await neo4j.verifyConnectivity();
  } catch (error) {
    logger.warn("Neo4j connection failed - graph features will be unavailable", {
      error: String(error)
    });
  }

  // Ensure collections exist
  await qdrant.ensureAllCollections();

  logger.info("Tool context created successfully");

  return {
    projectId,
    qdrant,
    neo4j,
    voyage,
    config,
    collectionName: (memoryType: string) => qdrant.collectionName(memoryType),
    allCollections: () => qdrant.allCollections()
  };
}
