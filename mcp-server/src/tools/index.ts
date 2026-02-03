import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { ToolContext } from "../context.js";
import { registerMemoryCrudTools } from "./memory-crud.js";
import { registerSearchTools } from "./search.js";
import { registerIndexingTools } from "./indexing.js";
import { registerAnalysisTools } from "./analysis.js";
import { registerMaintenanceTools } from "./maintenance.js";
import { logger } from "../utils/logger.js";

export function registerTools(server: McpServer, ctx: ToolContext): void {
  logger.info("Registering tools");

  // Memory CRUD (5 tools)
  registerMemoryCrudTools(server, ctx);

  // Search (5 tools)
  registerSearchTools(server, ctx);

  // Indexing (4 tools)
  registerIndexingTools(server, ctx);

  // Analysis (4 tools)
  registerAnalysisTools(server, ctx);

  // Maintenance (5 tools)
  registerMaintenanceTools(server, ctx);

  logger.info("All 23 tools registered");
}
