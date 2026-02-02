# Local MCP Architecture Requirements

| Field | Value |
|-------|-------|
| **Document ID** | REQ-MEM-003 |
| **Status** | Draft |
| **Compliance** | ISO/IEC/IEEE 29148:2018 |

---

## 1. Introduction

### 1.1 Purpose

This document specifies requirements for redesigning the Claude Code Long-Term Memory System architecture. The current Docker-based approach where the MCP server runs inside a container is fundamentally flawed for the intended use case. This specification defines a new architecture where:

- The MCP server runs locally as a per-project dependency
- Databases (Qdrant, Neo4j) remain as shared Docker infrastructure
- Project isolation is achieved through API parameters, not container boundaries

### 1.2 Problem Statement

**Current Architecture (Wrong):**
```
┌─────────────────────────────────────────────────────┐
│                    Docker                            │
│  ┌─────────────┐  ┌─────────┐  ┌─────────┐         │
│  │ MCP Server  │  │ Qdrant  │  │ Neo4j   │         │
│  │ (per proj)  │  │         │  │         │         │
│  └─────────────┘  └─────────┘  └─────────┘         │
│        ↑                                            │
│   Volume mount required for project access          │
└─────────────────────────────────────────────────────┘
```

**Problems with Current Approach:**
1. MCP server in Docker requires volume mounting project directories
2. Volume mounts create complexity and permission issues
3. Cannot easily switch projects without reconfiguration
4. Docker adds latency to every MCP tool call
5. stdio transport through Docker exec is fragile
6. Development/debugging of MCP server is cumbersome

**Target Architecture (Correct):**
```
┌──────────────────────────────────────────────────────┐
│                   Developer Machine                   │
│                                                       │
│  ┌─────────────────────────────────────────────────┐ │
│  │              Project Directory                   │ │
│  │  ├── .claude/mcp.json  (MCP config)             │ │
│  │  ├── .venv/            (includes memory-mcp)    │ │
│  │  └── src/              (project code)           │ │
│  └─────────────────────────────────────────────────┘ │
│                         │                             │
│                         │ stdio                       │
│                         ▼                             │
│  ┌─────────────────────────────────────────────────┐ │
│  │           MCP Server (local process)            │ │
│  │           Runs from project venv                │ │
│  └──────────────────┬──────────────────────────────┘ │
│                     │                                 │
│          ┌──────────┴──────────┐                     │
│          ▼                     ▼                     │
│  ┌──────────────┐      ┌──────────────┐             │
│  │    Docker    │      │    Docker    │             │
│  │    Qdrant    │      │    Neo4j     │             │
│  │  (shared)    │      │  (shared)    │             │
│  └──────────────┘      └──────────────┘             │
└──────────────────────────────────────────────────────┘
```

### 1.3 Scope

**In Scope:**
- MCP server packaging as pip-installable Python package
- Local stdio-only MCP transport
- Per-project configuration model
- Global configuration for shared services
- Project isolation via API parameters
- Database connection management

**Out of Scope:**
- Changes to memory types or MCP tool functionality (REQ-MEM-001 remains authoritative)
- Database schema changes
- HTTP transport for MCP server
- MCP server running in Docker
- Multi-user or collaborative features
- Cloud-hosted database options (future consideration)

### 1.4 Definitions

| Term | Definition |
|------|------------|
| **Local MCP** | MCP server running as a native process on the developer's machine |
| **Shared Infrastructure** | Docker containers (Qdrant, Neo4j) shared across all projects |
| **Project Isolation** | Logical separation of project data within shared databases |
| **Global Config** | Configuration shared across all projects (API keys, database connections) |
| **Per-Project Config** | Configuration specific to a single project (project_id) |

---

## 2. Stakeholder Requirements

### 2.1 Stakeholder Identification

| Stakeholder | Role | Needs |
|-------------|------|-------|
| Solo Developer | Primary user | Simple setup, works across multiple projects |
| Claude Code | MCP client | Reliable stdio communication, fast responses |
| Project | Context | Isolated memory space, consistent project_id |

### 2.2 Stakeholder Needs

**REQ-MEM-003-STK-001:** Developer shall be able to add memory capabilities to any project by installing a single pip package.
- **Priority:** Must Have
- **Rationale:** Reduces friction for adoption; familiar Python workflow

**REQ-MEM-003-STK-002:** Developer shall be able to work on multiple projects with completely isolated memory spaces using shared database infrastructure.
- **Priority:** Must Have
- **Rationale:** Avoids running multiple database instances; simplifies resource management

**REQ-MEM-003-STK-003:** Developer shall configure database connections and API keys once, not per-project.
- **Priority:** Must Have
- **Rationale:** Reduces repetitive configuration; secrets in one secure location

**REQ-MEM-003-STK-004:** Claude Code shall communicate with memory service via stdio without Docker intermediaries.
- **Priority:** Must Have
- **Rationale:** Eliminates Docker exec latency and fragility

### 2.3 Constraints

**REQ-MEM-003-CON-001:** MCP server shall NOT run inside Docker containers.
- **Priority:** Must Have
- **Rationale:** Core architectural requirement; Docker adds unnecessary complexity

**REQ-MEM-003-CON-002:** MCP server shall use stdio transport exclusively (no HTTP server).
- **Priority:** Must Have
- **Rationale:** Simplifies deployment; HTTP not needed for local single-user scenario

**REQ-MEM-003-CON-003:** Databases (Qdrant, Neo4j) shall run in Docker as shared infrastructure.
- **Priority:** Must Have
- **Rationale:** Databases benefit from containerization; easy to start/stop/upgrade

**REQ-MEM-003-CON-004:** Project isolation shall be achieved via API parameters, not container or volume boundaries.
- **Priority:** Must Have
- **Rationale:** Enables shared infrastructure while maintaining data separation

---

## 3. System Requirements

### 3.1 Functional Requirements

#### 3.1.1 Package Distribution

**REQ-MEM-003-FN-001:** The system shall be distributed as a pip-installable Python package named `claude-memory-mcp`.
- **Priority:** Must Have
- **Verification:** Package installs successfully via `pip install claude-memory-mcp`

**REQ-MEM-003-FN-002:** The package shall be installable as a project development dependency (in project's virtual environment).
- **Priority:** Must Have
- **Verification:** `pip install -e ".[dev]"` or `pip install claude-memory-mcp` in project venv

**REQ-MEM-003-FN-003:** The package shall provide a command-line entry point `claude-memory-mcp` for MCP server invocation.
- **Priority:** Must Have
- **Verification:** `claude-memory-mcp --help` returns usage information

**REQ-MEM-003-FN-004:** The package shall support Python 3.11+ as minimum version.
- **Priority:** Must Have
- **Verification:** Package metadata specifies `python_requires >= 3.11`

#### 3.1.2 MCP Server Runtime

**REQ-MEM-003-FN-010:** The MCP server shall run as a local native process, not inside Docker.
- **Priority:** Must Have
- **Verification:** Process runs with local PID, no Docker container involved

**REQ-MEM-003-FN-011:** The MCP server shall communicate via stdio transport exclusively.
- **Priority:** Must Have
- **Verification:** Server reads from stdin, writes to stdout; no HTTP listener

**REQ-MEM-003-FN-012:** The MCP server shall accept `--project-id` command-line argument to set the active project context.
- **Priority:** Must Have
- **Verification:** `claude-memory-mcp --project-id my-project` sets project context

**REQ-MEM-003-FN-013:** The MCP server shall pass project_id to all database operations for isolation.
- **Priority:** Must Have
- **Verification:** All Qdrant collections and Neo4j queries are scoped by project_id

**REQ-MEM-003-FN-014:** The MCP server shall validate project_id format (alphanumeric, hyphens, underscores; 1-64 characters).
- **Priority:** Should Have
- **Verification:** Invalid project_id returns clear error message

#### 3.1.3 Configuration Model

**REQ-MEM-003-FN-020:** The system shall support a global configuration file at `~/.config/claude-memory/config.toml`.
- **Priority:** Must Have
- **Verification:** Server reads configuration from specified path

**REQ-MEM-003-FN-021:** Global configuration shall include database connection settings:
- `qdrant.host` (default: localhost)
- `qdrant.port` (default: 6333)
- `qdrant.api_key` (optional)
- `neo4j.uri` (default: bolt://localhost:7687)
- `neo4j.user` (default: neo4j)
- `neo4j.password` (required if auth enabled)
- **Priority:** Must Have
- **Verification:** Server connects using configured values

**REQ-MEM-003-FN-022:** Global configuration shall include API key settings:
- `voyage.api_key` (required for embeddings)
- `voyage.model` (default: voyage-code-3)
- **Priority:** Must Have
- **Verification:** Embedding requests use configured API key

**REQ-MEM-003-FN-023:** The system shall support environment variable overrides for all configuration values using prefix `CLAUDE_MEMORY_`.
- **Priority:** Should Have
- **Verification:** `CLAUDE_MEMORY_QDRANT_HOST=remote.host` overrides config file

**REQ-MEM-003-FN-024:** The system shall provide a configuration initialization command: `claude-memory-mcp init-config`.
- **Priority:** Should Have
- **Verification:** Command creates config file with documented defaults

**REQ-MEM-003-FN-025:** Per-project configuration shall be limited to project_id, passed via command-line argument.
- **Priority:** Must Have
- **Verification:** No per-project config file required; project_id from CLI arg

#### 3.1.4 Project Isolation

**REQ-MEM-003-FN-030:** Each project shall have completely isolated data within shared databases.
- **Priority:** Must Have
- **Verification:** Data from project A is never visible when querying as project B

**REQ-MEM-003-FN-031:** Qdrant collections shall be prefixed with project_id: `{project_id}_{collection_name}`.
- **Priority:** Must Have
- **Verification:** Collections created with correct prefix

**REQ-MEM-003-FN-032:** Neo4j nodes shall include `project_id` property; all queries shall filter by project_id.
- **Priority:** Must Have
- **Verification:** Cypher queries include `WHERE n.project_id = $project_id`

**REQ-MEM-003-FN-033:** The system shall prevent cross-project data access even if project_id is known.
- **Priority:** Must Have
- **Verification:** API enforces project_id from server initialization, not per-request

**REQ-MEM-003-FN-034:** The `set_project` MCP tool shall be removed; project_id is immutable for server lifetime.
- **Priority:** Must Have
- **Verification:** No `set_project` tool exposed; attempting to call returns error

#### 3.1.5 Database Infrastructure

**REQ-MEM-003-FN-040:** The system shall provide a Docker Compose file for database infrastructure only.
- **Priority:** Must Have
- **Verification:** `docker-compose.yml` contains only Qdrant and Neo4j services

**REQ-MEM-003-FN-041:** Docker Compose shall use named volumes for data persistence:
- `claude-memory-qdrant-data`
- `claude-memory-neo4j-data`
- **Priority:** Must Have
- **Verification:** Volumes persist across container restarts

**REQ-MEM-003-FN-042:** Database containers shall expose ports on localhost only (127.0.0.1).
- **Priority:** Must Have
- **Verification:** Ports bound to 127.0.0.1, not 0.0.0.0

**REQ-MEM-003-FN-043:** The system shall provide a startup script or command to verify database connectivity.
- **Priority:** Should Have
- **Verification:** `claude-memory-mcp check-db` returns connection status

### 3.2 Non-Functional Requirements

#### 3.2.1 Performance

**REQ-MEM-003-NFR-PERF-001:** MCP tool invocations shall complete with less than 50ms overhead compared to Docker-based approach.
- **Priority:** Should Have
- **Verification:** Benchmark comparison of local vs Docker MCP

**REQ-MEM-003-NFR-PERF-002:** Server startup time shall be under 2 seconds.
- **Priority:** Should Have
- **Verification:** Time from invocation to ready for first request

#### 3.2.2 Usability

**REQ-MEM-003-NFR-USE-001:** A new project shall be configured for memory in under 5 minutes.
- **Priority:** Must Have
- **Verification:** Timed walkthrough: install package, create mcp.json, verify working

**REQ-MEM-003-NFR-USE-002:** Error messages shall clearly indicate whether the issue is configuration, database connectivity, or API key related.
- **Priority:** Must Have
- **Verification:** Error messages include category and remediation steps

**REQ-MEM-003-NFR-USE-003:** The system shall fail fast with clear errors if databases are not running.
- **Priority:** Must Have
- **Verification:** Immediate error on startup if Qdrant/Neo4j unreachable

#### 3.2.3 Security

**REQ-MEM-003-NFR-SEC-001:** API keys shall never be stored in per-project configuration files.
- **Priority:** Must Have
- **Verification:** Code review; mcp.json contains no secrets

**REQ-MEM-003-NFR-SEC-002:** Global configuration file shall have restricted permissions (600) when created.
- **Priority:** Should Have
- **Verification:** `init-config` sets appropriate file permissions

**REQ-MEM-003-NFR-SEC-003:** Database connections shall support authentication when configured.
- **Priority:** Must Have
- **Verification:** Connections work with authenticated Qdrant/Neo4j

#### 3.2.4 Reliability

**REQ-MEM-003-NFR-REL-001:** The system shall handle database unavailability gracefully, returning clear errors.
- **Priority:** Must Have
- **Verification:** MCP tools return structured errors when DB unreachable

**REQ-MEM-003-NFR-REL-002:** The system shall reconnect to databases automatically if connection is lost during operation.
- **Priority:** Should Have
- **Verification:** Transient network issues don't require server restart

---

## 4. Interface Requirements

### 4.1 Command-Line Interface

**REQ-MEM-003-INT-CLI-001:** The package shall provide entry point `claude-memory-mcp` with subcommands:
- `claude-memory-mcp` (no args) - Start MCP server (requires --project-id)
- `claude-memory-mcp --project-id <id>` - Start MCP server for project
- `claude-memory-mcp init-config` - Create global config file
- `claude-memory-mcp check-db` - Verify database connectivity
- `claude-memory-mcp --version` - Show version
- `claude-memory-mcp --help` - Show help
- **Priority:** Must Have
- **Verification:** All subcommands functional

### 4.2 Claude Code Integration

**REQ-MEM-003-INT-MCP-001:** Per-project MCP configuration shall be in `{project-root}/.claude/mcp.json`.
- **Priority:** Must Have
- **Verification:** Claude Code reads and uses configuration

**REQ-MEM-003-INT-MCP-002:** The mcp.json entry shall follow this structure:
```json
{
  "mcpServers": {
    "memory": {
      "command": "claude-memory-mcp",
      "args": ["--project-id", "my-project-name"]
    }
  }
}
```
- **Priority:** Must Have
- **Verification:** Claude Code successfully connects to memory server

**REQ-MEM-003-INT-MCP-003:** If using a project virtual environment, mcp.json shall reference the venv Python:
```json
{
  "mcpServers": {
    "memory": {
      "command": ".venv/bin/claude-memory-mcp",
      "args": ["--project-id", "my-project-name"]
    }
  }
}
```
- **Priority:** Must Have
- **Verification:** Server runs from project venv with correct dependencies

### 4.3 Configuration File Format

**REQ-MEM-003-INT-CFG-001:** Global configuration shall use TOML format at `~/.config/claude-memory/config.toml`:
```toml
# Claude Memory MCP Configuration

[qdrant]
host = "localhost"
port = 6333
# api_key = "optional-if-auth-enabled"

[neo4j]
uri = "bolt://localhost:7687"
user = "neo4j"
password = "your-password-here"

[voyage]
api_key = "your-voyage-api-key"
model = "voyage-code-3"

[server]
log_level = "INFO"
```
- **Priority:** Must Have
- **Verification:** Server parses and uses all configuration values

---

## 5. Data Requirements

### 5.1 Configuration Data

**REQ-MEM-003-DATA-001:** Global configuration file location shall follow XDG Base Directory specification:
- Linux/macOS: `~/.config/claude-memory/config.toml`
- Windows: `%APPDATA%\claude-memory\config.toml`
- **Priority:** Should Have
- **Verification:** Correct path used per platform

**REQ-MEM-003-DATA-002:** Configuration shall support the following precedence (highest to lowest):
1. Command-line arguments
2. Environment variables (CLAUDE_MEMORY_* prefix)
3. Global configuration file
4. Built-in defaults
- **Priority:** Must Have
- **Verification:** Override behavior works correctly

### 5.2 Project Isolation Data Model

**REQ-MEM-003-DATA-010:** Project ID shall be validated against pattern: `^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$`
- **Priority:** Must Have
- **Verification:** Invalid IDs rejected with clear error

**REQ-MEM-003-DATA-011:** Project ID shall be case-sensitive; `MyProject` and `myproject` are distinct.
- **Priority:** Must Have
- **Verification:** Separate data spaces for different casings

---

## 6. Deployment Requirements

### 6.1 Package Distribution

**REQ-MEM-003-DEP-001:** Package shall be published to PyPI as `claude-memory-mcp`.
- **Priority:** Must Have
- **Verification:** `pip install claude-memory-mcp` succeeds from PyPI

**REQ-MEM-003-DEP-002:** Package shall include all dependencies in setup.py/pyproject.toml.
- **Priority:** Must Have
- **Verification:** Fresh venv install works without manual dependency installation

**REQ-MEM-003-DEP-003:** Package shall not include database binaries or Docker images.
- **Priority:** Must Have
- **Verification:** Package size reasonable; no embedded services

### 6.2 Database Infrastructure

**REQ-MEM-003-DEP-010:** Simplified docker-compose.yml for database-only infrastructure:
```yaml
version: '3.8'

services:
  qdrant:
    image: qdrant/qdrant:latest
    container_name: claude-memory-qdrant
    ports:
      - "127.0.0.1:6333:6333"
      - "127.0.0.1:6334:6334"
    volumes:
      - claude-memory-qdrant-data:/qdrant/storage
    restart: unless-stopped

  neo4j:
    image: neo4j:5-community
    container_name: claude-memory-neo4j
    ports:
      - "127.0.0.1:7474:7474"
      - "127.0.0.1:7687:7687"
    volumes:
      - claude-memory-neo4j-data:/data
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD:-changeme}
    restart: unless-stopped

volumes:
  claude-memory-qdrant-data:
  claude-memory-neo4j-data:
```
- **Priority:** Must Have
- **Verification:** `docker-compose up -d` starts both databases

**REQ-MEM-003-DEP-011:** Documentation shall clearly separate database setup (one-time) from project setup (per-project).
- **Priority:** Must Have
- **Verification:** README has distinct sections for each

### 6.3 Developer Workflow

**REQ-MEM-003-DEP-020:** Typical setup workflow shall be:

**One-time (shared infrastructure):**
```bash
# 1. Start databases
cd claude-memory-mcp/docker
docker-compose up -d

# 2. Initialize global config
claude-memory-mcp init-config
# Edit ~/.config/claude-memory/config.toml with API keys
```

**Per-project:**
```bash
# 1. Add to project dependencies
pip install claude-memory-mcp
# or add to requirements-dev.txt / pyproject.toml

# 2. Create .claude/mcp.json
mkdir -p .claude
cat > .claude/mcp.json << 'EOF'
{
  "mcpServers": {
    "memory": {
      "command": ".venv/bin/claude-memory-mcp",
      "args": ["--project-id", "my-project"]
    }
  }
}
EOF

# 3. Start using Claude Code - memory tools available
```
- **Priority:** Must Have
- **Verification:** Workflow documented and tested

---

## 7. Verification Requirements

### 7.1 Testing Requirements

**REQ-MEM-003-VER-001:** Unit tests shall verify configuration loading from all sources (file, env, CLI).
- **Verification:** pytest tests for config module

**REQ-MEM-003-VER-002:** Integration tests shall verify project isolation across two concurrent projects.
- **Verification:** Test creates data in project A, verifies invisible from project B

**REQ-MEM-003-VER-003:** Integration tests shall verify MCP stdio transport works correctly.
- **Verification:** Simulated Claude Code client communicates successfully

**REQ-MEM-003-VER-004:** End-to-end tests shall verify complete workflow from pip install to working memory tools.
- **Verification:** Scripted test on clean environment

### 7.2 Acceptance Criteria

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Fresh Install | Clean machine with Docker | Follow README setup | Memory tools work in Claude Code |
| Project Isolation | Two projects configured | Query from project A | Only project A data returned |
| Database Down | Databases not running | Start MCP server | Clear error message within 5 seconds |
| Config Missing | No global config file | Start MCP server | Error with instructions to run init-config |
| Multiple Projects | Projects A and B exist | Switch between projects | Each has isolated, persistent memory |

---

## 8. Migration Considerations

### 8.1 From Current Docker-Based Approach

**REQ-MEM-003-MIG-001:** Existing data in Docker volumes shall remain accessible after migration.
- **Priority:** Should Have
- **Verification:** Data created with old approach visible with new approach

**REQ-MEM-003-MIG-002:** Documentation shall include migration guide for existing users.
- **Priority:** Should Have
- **Verification:** Step-by-step migration instructions

**REQ-MEM-003-MIG-003:** The `set_project` MCP tool shall return deprecation warning before removal.
- **Priority:** Could Have
- **Verification:** Tool returns warning message for transition period

---

## 9. Out of Scope

The following items are explicitly NOT part of this requirements document:

1. **MCP Tool Changes** - Memory types, tool signatures, and functionality remain as specified in REQ-MEM-001
2. **HTTP Transport** - Only stdio transport is supported; no HTTP server
3. **Cloud Databases** - Only local Docker databases supported (cloud is future consideration)
4. **Multi-User** - Single developer use case only
5. **GUI/Dashboard** - Command-line only
6. **Automatic Project Detection** - Project ID must be explicitly configured
7. **MCP Server in Docker** - Explicitly prohibited by requirements

---

## 10. Document Control

| Field | Value |
|-------|-------|
| **Author** | Requirements Agent |
| **Status** | Draft |
| **Stakeholder Decisions** | Per-project pip install; global config for shared services; stdio only |

### Open Questions

1. Should the package also be published to conda-forge for Anaconda users?
2. Should there be a `claude-memory-mcp doctor` command for troubleshooting?
3. What happens if project_id is not provided - error or use directory name as fallback?

### Requirements Summary

| Category | Must Have | Should Have | Could Have |
|----------|-----------|-------------|------------|
| Functional | 15 | 5 | 0 |
| Non-Functional | 5 | 4 | 0 |
| Interface | 4 | 1 | 0 |
| Data | 3 | 1 | 0 |
| Deployment | 4 | 2 | 0 |
| **Total** | **31** | **13** | **0** |

---

*End of Requirements Document*
