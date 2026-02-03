import { readFileSync, existsSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import TOML from "toml";
import { logger } from "./utils/logger.js";

export interface VoyageConfig {
  api_key: string;
}

export interface QdrantConfig {
  url: string;
}

export interface Neo4jConfig {
  uri: string;
  user: string;
  password: string;
}

export interface Config {
  voyage: VoyageConfig;
  qdrant: QdrantConfig;
  neo4j: Neo4jConfig;
}

interface TomlConfig {
  voyage?: { api_key?: string };
  qdrant?: { url?: string };
  neo4j?: { uri?: string; user?: string; password?: string };
}

export function loadConfig(): Config {
  const configPath = join(homedir(), ".config", "claude-memory", "config.toml");

  // Start with defaults
  const config: Config = {
    voyage: {
      api_key: process.env["CLAUDE_MEMORY_VOYAGE_API_KEY"] || ""
    },
    qdrant: {
      url: process.env["CLAUDE_MEMORY_QDRANT_URL"] || "http://localhost:6333"
    },
    neo4j: {
      uri: process.env["CLAUDE_MEMORY_NEO4J_URI"] || "bolt://localhost:7687",
      user: process.env["CLAUDE_MEMORY_NEO4J_USER"] || "neo4j",
      password: process.env["CLAUDE_MEMORY_NEO4J_PASSWORD"] || ""
    }
  };

  // Load from TOML if exists
  if (existsSync(configPath)) {
    try {
      const tomlContent = readFileSync(configPath, "utf-8");
      const fileConfig = TOML.parse(tomlContent) as TomlConfig;

      // Merge with precedence: env > file > defaults
      if (fileConfig.voyage?.api_key && !process.env["CLAUDE_MEMORY_VOYAGE_API_KEY"]) {
        config.voyage.api_key = fileConfig.voyage.api_key;
      }
      if (fileConfig.qdrant?.url && !process.env["CLAUDE_MEMORY_QDRANT_URL"]) {
        config.qdrant.url = fileConfig.qdrant.url;
      }
      if (fileConfig.neo4j?.uri && !process.env["CLAUDE_MEMORY_NEO4J_URI"]) {
        config.neo4j.uri = fileConfig.neo4j.uri;
      }
      if (fileConfig.neo4j?.user && !process.env["CLAUDE_MEMORY_NEO4J_USER"]) {
        config.neo4j.user = fileConfig.neo4j.user;
      }
      if (fileConfig.neo4j?.password && !process.env["CLAUDE_MEMORY_NEO4J_PASSWORD"]) {
        config.neo4j.password = fileConfig.neo4j.password;
      }

      logger.info("Loaded config from TOML", { path: configPath });
    } catch (error) {
      logger.warn("Failed to parse config.toml", { error: String(error) });
    }
  } else {
    logger.debug("No config.toml found, using defaults/env", { path: configPath });
  }

  return config;
}

export function validateConfig(config: Config): void {
  if (!config.voyage.api_key) {
    throw new Error("Voyage API key is required. Set CLAUDE_MEMORY_VOYAGE_API_KEY or add to config.toml");
  }
}
