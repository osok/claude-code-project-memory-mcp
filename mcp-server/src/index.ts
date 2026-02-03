#!/usr/bin/env node
import { parseArgs } from "node:util";
import { startServer } from "./server.js";
import { logger } from "./utils/logger.js";

const PROJECT_ID_PATTERN = /^[a-z][a-z0-9_-]{0,62}$/;

function printUsage(): void {
  console.error(`
Usage: claude-memory-mcp --project-id <id>

Options:
  -p, --project-id <id>  Project identifier (required)
                         Must match: [a-z][a-z0-9_-]{0,62}
  -h, --help             Show this help message

Environment variables:
  CLAUDE_MEMORY_VOYAGE_API_KEY   Voyage AI API key (required)
  CLAUDE_MEMORY_QDRANT_URL       Qdrant URL (default: http://localhost:6333)
  CLAUDE_MEMORY_NEO4J_URI        Neo4j URI (default: bolt://localhost:7687)
  CLAUDE_MEMORY_NEO4J_USER       Neo4j user (default: neo4j)
  CLAUDE_MEMORY_NEO4J_PASSWORD   Neo4j password

Config file: ~/.config/claude-memory/config.toml
`);
}

try {
  const { values } = parseArgs({
    options: {
      "project-id": { type: "string", short: "p" },
      help: { type: "boolean", short: "h" }
    },
    strict: true
  });

  if (values.help) {
    printUsage();
    process.exit(0);
  }

  const projectId = values["project-id"];

  if (!projectId) {
    console.error("Error: --project-id is required");
    printUsage();
    process.exit(1);
  }

  if (!PROJECT_ID_PATTERN.test(projectId)) {
    console.error("Error: project-id must match pattern: [a-z][a-z0-9_-]{0,62}");
    process.exit(1);
  }

  logger.info("Starting claude-memory-mcp", { projectId });

  startServer(projectId).catch((error) => {
    logger.error("Fatal error", { error: String(error) });
    process.exit(1);
  });

} catch (error) {
  console.error(`Error: ${error instanceof Error ? error.message : String(error)}`);
  printUsage();
  process.exit(1);
}
