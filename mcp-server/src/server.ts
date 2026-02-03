import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { registerTools } from "./tools/index.js";
import { createContext } from "./context.js";
import { logger } from "./utils/logger.js";

export async function createServer(projectId: string): Promise<McpServer> {
  logger.info("Creating MCP server", { projectId });

  const server = new McpServer({
    name: "memory",
    version: "1.0.0"
  });

  const context = await createContext(projectId);
  registerTools(server, context);

  logger.info("MCP server created with all tools registered");

  return server;
}

export async function startServer(projectId: string): Promise<void> {
  const server = await createServer(projectId);
  const transport = new StdioServerTransport();

  logger.info("Starting MCP server with stdio transport");

  await server.connect(transport);

  // Handle graceful shutdown
  process.on("SIGINT", async () => {
    logger.info("Received SIGINT, shutting down");
    await server.close();
    process.exit(0);
  });

  process.on("SIGTERM", async () => {
    logger.info("Received SIGTERM, shutting down");
    await server.close();
    process.exit(0);
  });
}
