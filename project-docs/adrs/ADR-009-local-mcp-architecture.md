# ADR-009: Local MCP Architecture (Native Process vs Docker)

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Date** | 2026-02-02 |
| **Deciders** | Architecture Team |
| **Requirements** | REQ-MEM-002-CON-001, REQ-MEM-002-FN-010, REQ-MEM-002-STK-004 |

## Context

The Claude Code Long-Term Memory System was initially implemented with the MCP server running inside a Docker container alongside Qdrant and Neo4j databases. This approach created several operational challenges:

1. **Volume Mount Complexity**: The MCP server inside Docker required volume mounts to access project files, creating permission issues and path translation complexity.

2. **Performance Overhead**: Every MCP tool call incurred Docker exec latency, impacting responsiveness.

3. **stdio Transport Fragility**: Routing stdio through Docker exec is error-prone and adds complexity.

4. **Development Friction**: Debugging and iterating on the MCP server required container rebuilds.

5. **Multi-Project Support**: Switching projects required either multiple containers or complex reconfiguration.

## Decision

**We will run the MCP server as a native local process on the developer's machine, distributed as a pip-installable Python package, while keeping databases (Qdrant, Neo4j) as shared Docker infrastructure.**

### Architecture

```
Developer Machine
+--------------------------------------------------+
|                                                  |
|  +-------------------------------------------+   |
|  |          Project Directory                |   |
|  |  .claude/mcp.json (project config)        |   |
|  |  .venv/ (includes claude-memory-mcp)      |   |
|  +-------------------------------------------+   |
|                       |                          |
|                       | stdio                    |
|                       v                          |
|  +-------------------------------------------+   |
|  |       MCP Server (local Python process)   |   |
|  |       claude-memory-mcp --project-id X    |   |
|  +-------------------------------------------+   |
|                       |                          |
|          +------------+------------+             |
|          v                         v             |
|  +---------------+       +------------------+    |
|  |    Docker     |       |      Docker      |    |
|  |    Qdrant     |       |      Neo4j       |    |
|  |  (shared)     |       |    (shared)      |    |
|  +---------------+       +------------------+    |
+--------------------------------------------------+
```

### Key Design Choices

1. **Package Distribution**: pip-installable as `claude-memory-mcp`
2. **Transport**: stdio only (no HTTP server for MCP)
3. **Project Isolation**: Via `--project-id` argument passed at server startup
4. **Configuration**:
   - Global: `~/.config/claude-memory/config.toml` (DB connections, API keys)
   - Per-project: Only project_id, passed via CLI
5. **Database Infrastructure**: Docker containers for Qdrant and Neo4j, shared across all projects

## Rationale

### Benefits

| Aspect | Docker MCP | Local MCP | Improvement |
|--------|-----------|-----------|-------------|
| File Access | Volume mounts required | Native filesystem | No path translation |
| Latency | ~50-100ms Docker exec overhead | Native process | 50-100ms faster |
| stdio | Fragile through Docker | Direct pipes | More reliable |
| Multi-project | Multiple containers or restart | Just pass --project-id | Zero friction |
| Debugging | Container logs, rebuild | Standard Python debugging | Much easier |
| Installation | Docker image pull | pip install | Familiar Python workflow |

### Why Keep Databases in Docker

1. **Resource Isolation**: Databases benefit from container resource limits
2. **Easy Management**: Start/stop/upgrade via docker-compose
3. **Data Persistence**: Named volumes survive container restarts
4. **No Native Install**: Avoids installing Qdrant/Neo4j natively
5. **Shared Infrastructure**: One database instance serves all projects

### Project Isolation Strategy

Project isolation is achieved via:
- Qdrant: Collections prefixed with `{project_id}_`
- Neo4j: All nodes include `project_id` property, queries filter by project_id

This is enforced at the adapter level, not by container boundaries.

## Alternatives Considered

### 1. Keep Everything in Docker
- **Rejected**: Volume mounts for project access too problematic
- **Issue**: Cannot easily switch projects without reconfiguration

### 2. All Native (Including Databases)
- **Rejected**: Installing Qdrant/Neo4j natively is complex
- **Issue**: Users would need to manage database processes manually

### 3. HTTP-based MCP Transport
- **Rejected**: Adds complexity without benefit for single-user local scenario
- **Issue**: Would require port management, CORS, authentication

### 4. Runtime Project Switching via Tool
- **Rejected**: Complexity of reinitializing all adapters mid-session
- **Issue**: Error-prone, potential data isolation bugs

## Consequences

### Positive

1. **Simpler User Experience**: `pip install claude-memory-mcp` + start databases
2. **Better Performance**: No Docker exec overhead for tool calls
3. **Reliable stdio**: Direct pipe communication
4. **Multi-project Ready**: Project switching via config, no restart needed
5. **Easy Development**: Standard Python development workflow

### Negative

1. **Two Runtimes**: Users need both Python venv and Docker
2. **Global Config**: Must manage `~/.config/claude-memory/config.toml`
3. **No set_project**: Must restart with different --project-id (mitigated by mcp.json per project)

### Migration Impact

1. Existing Docker-only users must:
   - Keep databases running via simplified docker-compose
   - Install `claude-memory-mcp` package
   - Create global config file
   - Update mcp.json to point to local process

2. Data migration: None required - database schema unchanged

## Implementation Notes

### Entry Point

```bash
claude-memory-mcp --project-id my-project
claude-memory-mcp init-config
claude-memory-mcp check-db
```

### Configuration Precedence

1. CLI arguments (highest)
2. Environment variables (CLAUDE_MEMORY_*)
3. Global config file (~/.config/claude-memory/config.toml)
4. Built-in defaults (lowest)

### mcp.json Example

```json
{
  "mcpServers": {
    "memory": {
      "command": ".venv/bin/claude-memory-mcp",
      "args": ["--project-id", "my-project"]
    }
  }
}
```

## Compliance

- **REQ-MEM-002-CON-001**: MCP server shall NOT run inside Docker - SATISFIED
- **REQ-MEM-002-FN-010**: MCP server runs as local native process - SATISFIED
- **REQ-MEM-002-STK-004**: stdio without Docker intermediaries - SATISFIED
- **REQ-MEM-002-FN-034**: set_project tool removed - SATISFIED
