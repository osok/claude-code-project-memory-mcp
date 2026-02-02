# Claude Code Long-Term Memory System

## Project Overview

A development-time memory service for Claude Code that maintains context across coding sessions. Stores project decisions, code patterns, and requirements to help Claude build applications better.

## Current Work

| Field | Value |
|-------|-------|
| **Seq** | 003 |
| **Name** | Local MCP Architecture |
| **Requirements** | [REQ-MEM-003-local-mcp-architecture.md](requirement-docs/REQ-MEM-003-local-mcp-architecture.md) |
| **Task List** | [003-task-list-local-mcp.md](project-docs/003-task-list-local-mcp.md) |
| **Status** | Complete |

### Description

Redesigning the memory service architecture so that:
- MCP server runs locally as a pip-installable package (NOT in Docker)
- Databases (Qdrant, Neo4j) remain in Docker as shared infrastructure
- Project isolation via `--project-id` CLI argument at server startup
- Global config at `~/.config/claude-memory/config.toml`
- stdio transport only (no HTTP API for MCP)

## Previous Work

| Seq | Name | Requirements | Status |
|-----|------|--------------|--------|
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
├── src/memory_service/     # Main service code
│   ├── api/                # MCP server, HTTP server, CLI
│   ├── core/               # Memory manager, query engine
│   ├── embedding/          # Voyage client, embedding service
│   ├── models/             # Pydantic models
│   ├── parsing/            # Code parsing extractors
│   ├── storage/            # Qdrant and Neo4j adapters
│   └── utils/              # Logging, metrics
├── docker/                 # Database infrastructure only
├── project-docs/           # Design docs, ADRs, task lists
├── requirement-docs/       # Requirements specifications
├── user-docs/              # User documentation
└── .claude/agents/         # Agent definitions
```

## Key Commands

```bash
# Start databases
cd docker && docker-compose up -d

# Run tests
pytest src/tests/unit/ -v
pytest src/tests/integration/ -v

# Lint
ruff check src/
ruff format src/
```
