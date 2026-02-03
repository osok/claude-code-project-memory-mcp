# Claude Code Long-Term Memory System

## Project Overview

A development-time memory service for Claude Code that maintains context across coding sessions. Stores project decisions, code patterns, and requirements to help Claude build applications better.

## Current Work

| Field | Value |
|-------|-------|
| **Seq** | 005 |
| **Name** | NPX-Based MCP Server |
| **Requirements** | [REQ-MEM-005-npx-mcp-server.md](requirement-docs/REQ-MEM-005-npx-mcp-server.md) |
| **Architecture** | [005-architecture-npx-mcp.md](project-docs/005-architecture-npx-mcp.md) |
| **Design** | [005-design-npx-mcp-server.md](design-docs/005-design-npx-mcp-server.md) |
| **Task List** | [005-task-list-npx-mcp-server.md](project-docs/005-task-list-npx-mcp-server.md) |
| **ADR** | [ADR-010-typescript-mcp-server.md](project-docs/adrs/ADR-010-typescript-mcp-server.md) |
| **Status** | Implementation Complete - Ready for Testing |

### Description

Replaced the Python MCP server with a TypeScript/Node.js implementation:
- Uses official `@modelcontextprotocol/sdk`
- npx-based invocation for reliability
- All 23 tools implemented
- Same backend databases (Qdrant, Neo4j)

### Completed Tasks

- T001-T008: Project structure, config, adapters, server setup
- T009-T031: All 23 tools implemented
- T032: npx entry point created
- T046-T048: Documentation updated

### Next Steps

1. Test MCP server with Claude Code
2. Run integration tests
3. Delete Python code (T049) after verification

## Previous Work

| Seq | Name | Requirements | Status |
|-----|------|--------------|--------|
| 004 | MCP Tool Access Fix | [REQ-MEM-004-mcp-tool-access.md](requirement-docs/REQ-MEM-004-mcp-tool-access.md) | Abandoned - Python MCP unreliable |
| 003 | Local MCP Architecture | [REQ-MEM-003-local-mcp-architecture.md](requirement-docs/REQ-MEM-003-local-mcp-architecture.md) | Complete |
| 001 | Initial Memory System | [requirements-memory-docs.md](requirement-docs/requirements-memory-docs.md) | Complete |

## Development Workflow

This project uses an agentic development workflow. See `.claude/agents/` for agent definitions.

**To begin work:** Say "begin work" to start the task-manager agent.

**To continue:** Say "continue" to resume from the task list.

### Workflow Order

1. Architect Agent → Requirements Analyzer → Design Orchestrator
2. Test Designer → Data Agent → Deployment Agent → Developer
3. Code Reviews (Requirements, Security, Integration)
4. Fix Phase → Test Coder → Test Runner → Documentation

## Project Structure

```
├── mcp-server/             # TypeScript MCP server (NEW)
│   ├── src/                # Source code
│   ├── package.json        # Dependencies
│   └── tsconfig.json       # TypeScript config
├── docker/                 # Database infrastructure
├── project-docs/           # Design docs, ADRs, task lists
├── requirement-docs/       # Requirements specifications
├── user-docs/              # User documentation
└── .claude/agents/         # Agent definitions
```

## Key Commands

```bash
# Start databases
cd docker && docker-compose up -d

# Build TypeScript MCP server
cd mcp-server && npm install && npm run build

# Run MCP server locally
node mcp-server/dist/index.js --project-id my-project

# Lint
cd mcp-server && npm run lint
```

## Key Documentation

- [Quick Reference](user-docs/quick-reference.md) - All 23 tools with examples
