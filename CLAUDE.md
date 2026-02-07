# Claude Code Long-Term Memory System

## Project Overview

A development-time memory service for Claude Code that maintains context across coding sessions. Stores project decisions, code patterns, and requirements to help Claude build applications better.

## Current Work

| Field | Value |
|-------|-------|
| **Seq** | 007 |
| **Name** | Browser Details Enhancements |
| **Requirements** | [REQ-MEM-007-browser-details-enhancements.md](requirement-docs/REQ-MEM-007-browser-details-enhancements.md) |
| **Task List** | [007-task-list-browser-enhancements.md](project-docs/007-task-list-browser-enhancements.md) |
| **Status** | Implementation |

### Description

Enhancements to the Memory Inspector UI and MCP Server:
- **Inspector UI:** Expandable Details Panel, syntax highlighting, markdown rendering, project switch auto-refresh, table columns/resizing, pagination fix, graph filter fix
- **MCP Server:** Test result cleanup, automated function extraction

## Previous Work

| Seq | Name | Requirements | Status |
|-----|------|--------------|--------|
| 006 | Memory Inspector UI | [REQ-MEM-006-memory-inspector-ui.md](requirement-docs/REQ-MEM-006-memory-inspector-ui.md) | Implementation Complete |
| 005 | NPX-Based MCP Server | [REQ-MEM-005-npx-mcp-server.md](requirement-docs/REQ-MEM-005-npx-mcp-server.md) | Implementation Complete |
| 004 | MCP Tool Access Fix | [REQ-MEM-004-mcp-tool-access.md](requirement-docs/REQ-MEM-004-mcp-tool-access.md) | Abandoned - Python MCP unreliable |
| 003 | Local MCP Architecture | [REQ-MEM-003-local-mcp-architecture.md](requirement-docs/REQ-MEM-003-local-mcp-architecture.md) | Complete |
| 001 | Initial Memory System | [requirements-memory-docs.md](requirement-docs/requirements-memory-docs.md) | Complete |

<!-- PROJECT-SPECIFIC -->
## Project Structure

```
├── mcp-server/             # TypeScript MCP server
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
<!-- END PROJECT-SPECIFIC -->

---

## Development Workflow

This project uses an agentic development workflow. See `.claude/agents/` for agent definitions.

**To begin work:** Say "begin work" to start the task-manager agent.

**To continue:** Say "continue" to resume from the task list.

---

## Sub-Agent Index

### Core Workflow Agents

| Agent | Purpose | Docs |
|-------|---------|------|
| Requirements | Interactive requirements elicitation (ISO 29148) | .claude/agents/requirements.md |
| Architect | Architectural decisions, ADRs, standards | .claude/agents/architect.md |
| Requirements Analyzer | Parse ISO 29148 requirements structure | .claude/agents/requirements-analyzer.md |
| Design Orchestrator | Coordinate design document generation | .claude/agents/design-orchestrator.md |
| Task Manager | Orchestrates workflow, tracks tasks | .claude/agents/task-manager.md |

### Specialized Design Agents

| Agent | Purpose | Output Prefix | Docs |
|-------|---------|---------------|------|
| UI/UX Design | UI/UX and style guides | 01-, 90- | .claude/agents/ui-ux-design-agent.md |
| Data Design | Data architecture designs | 02- | .claude/agents/data-design-agent.md |
| Security Design | Security architecture | 03- | .claude/agents/security-design-agent.md |
| Library Design | Component library designs | 10- | .claude/agents/library-design-agent.md |
| Backend Design | Backend service designs | 20- | .claude/agents/backend-design-agent.md |
| Frontend Design | Frontend application designs | 30- | .claude/agents/frontend-design-agent.md |
| Agent Design | Background worker designs | 40- | .claude/agents/agent-design-agent.md |
| Integration Design | API contracts | 50- | .claude/agents/integration-design-agent.md |
| Infrastructure Design | Cloud/Docker/ECS designs | 60- | .claude/agents/infrastructure-design-agent.md |

### Data & Infrastructure Agents

| Agent | Purpose | Docs |
|-------|---------|------|
| Data Agent | Schemas, data dictionaries, migrations | .claude/agents/data-agent.md |
| Deployment | Docker compose, AWS CDK, .env | .claude/agents/deployment.md |

### Development Agents

| Agent | Purpose | Docs |
|-------|---------|------|
| Developer | Implements code following conventions | .claude/agents/developer.md |
| Documentation | User docs, developer docs, code docs | .claude/agents/documentation.md |

### Testing Agents

| Agent | Purpose | Docs |
|-------|---------|------|
| Test Designer | Plans tests from design | .claude/agents/test-designer.md |
| Test Coder | Writes test code | .claude/agents/test-coder.md |
| Test Runner | Executes and categorizes tests | .claude/agents/test-runner.md |
| Test Debugger | Deep debugging, routes fixes | .claude/agents/test-debugger.md |

### Code Review Agents

| Agent | Purpose | Docs |
|-------|---------|------|
| Code Reviewer - Requirements | Completeness against requirements | .claude/agents/code-reviewer-requirements.md |
| Code Reviewer - Security | OWASP vulnerabilities | .claude/agents/code-reviewer-security.md |
| Code Reviewer - Integration | Stubs, wiring gaps | .claude/agents/code-reviewer-integration.md |

### Utility Agents

| Agent | Purpose | Docs |
|-------|---------|------|
| Upgrade | Syncs framework files from source (user-invocable only) | .claude/agents/upgrade.md |

---

## Unified Agent Workflow

| Phase | Step | Agent(s) | Output |
|-------|------|----------|--------|
| **Requirements** | 1 | @requirements | Elicit and document requirements (ISO 29148) → `requirement-docs/` |
| **Orchestration** | 2 | @task-manager | **Orchestrates all remaining phases (2-17). Sole activity log writer.** |
| **Architecture** | 3 | @architect | Architectural decisions, ADRs → `project-docs/adrs/` |
| **Design** | 4 | @requirements-analyzer | Parse requirements structure |
| | 5 | @design-orchestrator | Coordinate specialized design agents |
| | 5a | └─ Foundation | @ui-ux-design, @data-design, @security-design (parallel) |
| | 5b | └─ Core | @library-design, @backend-design (parallel) |
| | 5c | └─ Application | @frontend-design, @agent-design (parallel) |
| | 5d | └─ Integration | @integration-design |
| | 5e | └─ Infrastructure | @infrastructure-design |
| | | | Output: `design-docs/` with prefixed documents |
| **Planning** | 6 | @test-designer, @data-agent | Plan tests; define schemas (parallel) |
| | 6a | @task-manager | Create task list |
| **Implementation** | 7 | @developer(s) | Implement code |
| **Review** | 8 | Code reviewers (3) | @code-reviewer-requirements, @code-reviewer-security, @code-reviewer-integration (parallel) |
| | 8a | @task-manager | Collect findings into tracker (CR-IDs), route each to correct agent |
| | 8b | @test-designer | Assess findings for test impact, update test plan |
| | 9 | Routed agents | Fix findings: @architect / @design-orchestrator / @developer as appropriate |
| | 9a | @task-manager | Record resolutions in findings tracker |
| | 10 | Code reviewers (re-review) | Verify fixes, check for new issues (only reviewers that had findings) |
| | 10a | Loop to Step 9 | If still-open or new findings, until all verified |
| **Test Prep** | 11 | @test-designer | Review/update test plan |
| | 12 | @documentation, @deployment | Docs and env setup (parallel) |
| **Testing** | 13 | @test-coder → @test-runner | Write & run tests |
| | 14 | @test-debugger | On failure: diagnose |
| | 15 | @task-manager → Agent | Route fix |
| | 16 | Loop to Step 13 | Until all pass |
| **Finalize** | 17 | @documentation | Final updates |

**Do NOT duplicate design documents for each work item.** Create work-specific docs (`{seq}-requirements-*.md`, `{seq}-design-*.md`) but update foundational docs (01-, 02-, 03-, etc.) in place. See design-orchestrator.md for the full update pattern.

---

## Key Decisions & Concepts

1. **Task Manager as Sole Writer** - Only Task Manager modifies task lists
2. **Schemas as Source of Truth** - Data Agent maintains authoritative schemas
3. **Convention Files** - Developer/Test Coder load language-specific conventions
4. **Design Templates** - Comprehensive templates for each component type
5. **Mid-Task Requests** - Agents can request work; Task Manager queues
6. **Test Runner Routing** - Routes failures to appropriate agents
7. **No Dates** - All documents are timeless
8. **Environment Isolation** - NEVER pollute the host machine's global environment (see below)

---

## CRITICAL: Environment Isolation

**NEVER install packages, dependencies, or tools globally on the host machine.**

| Language | Isolation Method | Setup Command |
|----------|------------------|---------------|
| Python | Virtual environment | `python -m venv .venv && source .venv/bin/activate` |
| Node.js | Local node_modules | `npm install` (no -g flag) |
| Ruby | Bundler with path | `bundle config set --local path 'vendor/bundle'` |
| Go | Go modules | `go mod init` (default behavior) |
| Rust | Cargo (project-local) | Default behavior |
| Java | Maven/Gradle (project-local) | Default behavior |

**Python:** Always create venv before any `pip install`. Never use `sudo pip install`. Add `.venv/`, `__pycache__/` to `.gitignore`.
**Node.js:** Never use `npm install -g` or `yarn global add`. Use `npx` for CLI tools. Add `node_modules/` to `.gitignore`.
**Enforcement:** Deployment Agent sets up environment before installs. Developer Agent verifies environment is active. Test agents use project environment.

---

## Requirement ID Conventions

Requirements include the sequence number to link them to specific work items.

| Pattern | Type | Example |
|---------|------|---------|
| `STK-{SEQ}-NNN` | Stakeholder | STK-002-001 |
| `REQ-{SEQ}-FN-NNN` | Functional | REQ-002-FN-001 |
| `REQ-{SEQ}-INT-UI-NNN` | UI Interface | REQ-002-INT-UI-001 |
| `REQ-{SEQ}-INT-API-NNN` | API Interface | REQ-002-INT-API-001 |
| `REQ-{SEQ}-DATA-NNN` | Data | REQ-002-DATA-001 |
| `REQ-{SEQ}-NFR-PERF-NNN` | Performance | REQ-002-NFR-PERF-001 |
| `REQ-{SEQ}-NFR-SEC-NNN` | Security | REQ-002-NFR-SEC-001 |
| `REQ-{SEQ}-NFR-ACC-NNN` | Accessibility | REQ-002-NFR-ACC-001 |
| `REQ-{SEQ}-NFR-AVAIL-NNN` | Availability | REQ-002-NFR-AVAIL-001 |
| `REQ-{SEQ}-VER-NNN` | Verification | REQ-002-VER-001 |
| `REQ-{SEQ}-DEP-NNN` | Deployment | REQ-002-DEP-001 |

**Note:** `{SEQ}` is the 3-digit sequence number from Current Work (e.g., 001, 002).

---

## Document Sequence Tracker

| Seq | Short Name | Component | Requirements | Design | Task List | Status |
|-----|------------|-----------|--------------|--------|-----------|--------|
| 001 | Initial Memory System | | requirements-memory-docs.md | N/A | N/A | Complete |
| 003 | Local MCP Architecture | | REQ-MEM-003-local-mcp-architecture.md | N/A | N/A | Complete |
| 004 | MCP Tool Access Fix | | REQ-MEM-004-mcp-tool-access.md | N/A | N/A | Abandoned |
| 005 | NPX-Based MCP Server | | REQ-MEM-005-npx-mcp-server.md | 005-design-npx-mcp-server.md | 005-task-list-npx-mcp-server.md | Implementation Complete |
| 006 | Memory Inspector UI | | REQ-MEM-006-memory-inspector-ui.md | 006-design-memory-inspector.md | 006-task-list-memory-inspector.md | Implementation Complete |
| 007 | Browser Details Enhancements | inspector-ui | REQ-MEM-007-browser-details-enhancements.md | N/A (update existing) | 007-task-list-browser-enhancements.md | Implementation |

---

## Commands

| Command | Meaning |
|---------|---------|
| `initialize` | Reset project, ask what to build |
| `new work` | Start new work item with fresh sequence, interview for requirements |
| `lets begin` | Check requirements, collect if missing, get approval, start workflow |
| `continue` | Resume current work from task list |
| `list components` | Show all components from COMPONENTS.md (supports type filtering) |
| `target {id}` | Set active component for subsequent work |
| `show component {id}` | Display full details of a component |
| `add component` | Interactively add a component to COMPONENTS.md |
| `impact {id}` | Show components affected by changes to target |
| `untarget` | Clear the active component targeting |

### `initialize` Workflow

When user says `initialize`, perform these actions **before** asking what to build:

1. **Reset Current Work section** to blank state (Seq/Name = pending, Status = Not Started, Phase = Awaiting Requirements)
2. **Reset README.md** to minimal template with project name placeholder
3. **Reset Document Sequence Tracker** - Clear all rows except header
4. **Clear project artifacts** (if they exist):
   - Delete files in `requirement-docs/` (except `README.md` and `_sample-requirements.md`)
   - Delete files in `design-docs/` (except templates)
   - Delete files in `project-docs/` (except `adrs/` folder structure)
   - Clear `project-docs/activity.log` if it exists
   - **Do NOT delete `COMPONENTS.md`** -- preserved across resets
5. **After all resets complete**, ask: "What would you like to build?"

### `new work` Workflow

Creates a new work item without resetting existing project artifacts.

1. **Determine next sequence number** from Document Sequence Tracker (3-digit zero-padded, e.g., 001 → 002 → 003)
2. **Prompt for work description**, generate `short_name` (lowercase, hyphens, max 30 chars), confirm with user
3. **Check for component targeting** (if `COMPONENTS.md` exists, ask if work is for a specific component)
4. **Update Current Work section** in CLAUDE.md with new seq, short_name, status=Requirements Gathering. If component-scoped, add Component field and Component Context sub-section (see Component Context rules below)
5. **If component-scoped**, update component status to `active` in `COMPONENTS.md` (both Summary table and detail section) — follows the Component Status Lifecycle
6. **Update Document Sequence Tracker** with new row (seq, short_name, component if targeted, status=Requirements)
7. **Create requirements document scaffold** in `requirement-docs/` with ISO 29148 structure
8. **Ask user about requirements source:** upload/paste OR interview
9. **If interview selected**, invoke @requirements agent for elicitation

### `lets begin` Workflow

1. **Check for requirements** in `requirement-docs/` (skip README.md and _sample-requirements.md)
2. **If no requirements exist:** Invoke @requirements agent to collect interactively
3. **If requirements exist:** Present summary, ask user for approval. If no, allow modifications
4. **Once approved:** Update Current Work, **invoke @task-manager** to orchestrate all remaining phases (steps 2-17 of Unified Agent Workflow)

**Important:** Task Manager is the orchestrator from step 2 onward. Do NOT invoke @architect or design agents directly — Task Manager invokes them so that all agent actions are logged to the activity log.

### `continue` Workflow

Resumes work from the current task list. **Task Manager is the primary coordinator for all resumed work.**

1. **Invoke @task-manager** to coordinate ALL continued work
2. Task Manager loads CLAUDE.md context, task list, activity log, and Component Context if present
3. Resets any stale `in-progress` tasks to `pending` (interrupted session)
4. Finds next actionable `pending` task with all dependencies `complete`
5. Routes task to correct agent, passing component context if present
6. Updates task list and activity log immediately on completion
7. Repeats until all tasks complete, user intervention required, or phase transition needed

**Important:** Always use `continue` to let Task Manager coordinate. Do not invoke individual agents directly.

---

### Component Status Lifecycle

Components follow a three-state lifecycle:

```
pending → active → complete
```

| Status | Meaning | Transition Trigger |
|--------|---------|-------------------|
| `pending` | Registered but no work started | Set on `add component` |
| `active` | Currently being worked on | Set on `target {id}` or `new work` (when component-scoped) |
| `complete` | All work finished, tests passing | Set by Task Manager when all tasks for the component are done |

**Rules:**
- `add component` always sets status to `pending`
- `target {id}` sets status to `active` (component is now being worked on)
- `new work` sets status to `active` when the work item is scoped to a component
- Task Manager sets status to `complete` when the component's work item finishes all phases (implementation, review, testing all pass)
- `untarget` does NOT revert status — once `active`, it stays `active` until completed
- A `complete` component can be re-targeted for new work (status returns to `active`)

### Component Commands

Component commands require `COMPONENTS.md` at the project root. If absent: "No COMPONENTS.md found. Create one with `add component` or manually. See `COMPONENTS.EXAMPLE.md` for the expected format."

| Canonical Command | Also Recognized As |
|-------------------|--------------------|
| `list components` | "show all components", "what components exist", "show components" |
| `target {id}` | "work on {id}", "switch to {id}", "focus on {id}" |
| `show component {id}` | "tell me about {id}", "what is {id}", "describe {id}" |
| `add component` | "register a component", "new component", "create component" |
| `impact {id}` | "what depends on {id}", "blast radius of {id}", "who uses {id}" |
| `untarget` | "clear component", "stop targeting", "unfocus" |

### `list components`

1. Check `COMPONENTS.md` exists, read and validate manifest
2. Display table with columns: ID, Name, Type, Path, Status
3. Apply type filter if specified (e.g., "list agent components")
4. Display count summary by type

### `target {id}`

1. Look up `## {id}` in `COMPONENTS.md`. If not found, show valid IDs and suggest closest match
2. Extract all fields from component's detail section
3. **Update component status to `active`** in both the Summary table and the detail section of `COMPONENTS.md`
4. Write `**Component:** {id}` to Current Work (after Name, before Status)
5. Write `### Component Context` sub-section with hydrated metadata
6. Display component details. If already targeted, previous target is replaced silently

### `show component {id}`

1. Look up `## {id}` in `COMPONENTS.md`. If not found, show valid IDs
2. Extract all fields, compute reverse dependencies, check for associated docs
3. Display full component details including dependencies and dependents

### `add component`

1. If `COMPONENTS.md` doesn't exist, offer to create it
2. Prompt for required fields: ID (`[a-z][a-z0-9-]{0,39}`), Name, Type (frontend/backend/library/agent/gateway/infrastructure/other), Path, Description
3. Prompt for optional fields: Language, Dependencies, Deployment, Port, Owner
4. Validate ID uniqueness and format, warn on unknown dependency references
5. Set Status to `pending` (do NOT prompt for status — it follows the lifecycle automatically)
6. Add row to Summary table and new H2 section to `COMPONENTS.md`
7. Ask about scaffolding the source directory

### `impact {id}`

1. Look up `## {id}` in `COMPONENTS.md`. If not found, show valid IDs
2. BFS on reverse dependency graph: find direct dependents, then transitive dependents (track visited nodes for cycles)
3. Display direct and transitive dependents with total count

### `untarget`

1. If no `**Component:**` field in Current Work, display "No component is currently targeted."
2. Remove `**Component:**` line and `### Component Context` sub-section, preserve all other fields

### Component Context Rules

When a component is targeted, Current Work gains `**Component:** {id}` (after Name, before Status) and a `### Component Context` sub-section with a metadata table from COMPONENTS.md.

1. Field is omitted entirely when no component is targeted (backward compatible)
2. Only fields with values are included
3. When a different component is targeted, previous context is replaced
4. `untarget` removes both the field and the sub-section
5. All agents read this section from CLAUDE.md to scope work — Developer uses Path/Language/Dependencies, Test agents use Path/Language, reviewers use Path/Dependencies, Task Manager uses all fields

---

## Model Configuration

**Default Model:** `opus` — Override in agent YAML front-matter with `model: sonnet` or `model: haiku`.

| Agent Category | Model | Rationale |
|----------------|-------|-----------|
| Architecture, Security, Design, Code Reviewers, Task Manager | opus | Complex reasoning and trade-offs |
| Developer, Test Coder, Test Runner, Documentation | sonnet | Standard implementation work |
| Exploration, simple validation | haiku | Quick searches, simple transforms |

---

## Activity Log

Traceability of all agent actions. Designed for machine parsing. Full schema and writer protocol in task-manager.md.

- **File:** `project-docs/activity.log`
- **Format:** JSONL (one JSON object per line, UTF-8)
- **Sole Writer:** Task Manager (adds `log_seq`, `work_seq`, `timestamp`, `parent_log_seq`, `duration_ms` to agent entries)

### Action Types

| Action | Description | When to Log |
|--------|-------------|-------------|
| `START` | Agent began execution | When agent is invoked |
| `COMPLETE` | Agent finished successfully | When agent returns success |
| `ERROR` | Agent encountered an error | When agent fails |
| `DECISION` | Significant decision made | When architectural/design choice is made |
| `FILE_CREATE` | New file created | When a new file is written |
| `FILE_MODIFY` | Existing file modified | When an existing file is changed |
| `BLOCKED` | Agent blocked, waiting on dependency | When agent cannot proceed |
| `UNBLOCKED` | Agent unblocked, resuming work | When blocking condition resolved |
| `REVIEW_PASS` | Code review passed | When reviewer approves |
| `REVIEW_FAIL` | Code review failed | When reviewer finds issues |
| `TEST_PASS` | Test(s) passed | When test execution succeeds |
| `TEST_FAIL` | Test(s) failed | When test execution fails |

### Phase Values

`requirements` | `architecture` | `design` | `planning` | `implementation` | `review` | `testing` | `documentation` | `deployment`

---

## Parallel Execution

### Design Phase Waves

| Wave | Agents | Dependencies |
|------|--------|--------------|
| Foundation | UI-UX Design, Data Design, Security Design | None |
| Core | Library Design, Backend Design | Foundation complete |
| Application | Frontend Design, Agent Design | Core complete |
| Integration | Integration Design | Application complete |
| Infrastructure | Infrastructure Design | Integration complete |

### Implementation Phase

Parallel Developer agents when: different source directories, no shared utility modifications, separate database tables.

### Testing Phase

Parallel test execution when: independent modules, no shared fixtures requiring sequential setup, database isolation per suite.

### Conflict Resolution

Task Manager detects file conflicts. First completion wins; subsequent agents rebase. Design doc conflicts escalated to user.

---

## Exit Criteria

Task Manager validates exit criteria before phase transitions. Blocks if not met. Allows user override with explicit acknowledgment.

| Phase | Criteria |
|-------|----------|
| **Design** | All required design docs created, requirements traceability complete, no unresolved questions, user approval |
| **Implementation** | All code reviewers pass (no critical/high), no TODO/FIXME in committed code, no stubs, builds without errors, Conventional Commits |
| **Testing** | Coverage minimum 70% (configurable), all tests passing, no critical/high security findings, performance benchmarks met |
| **Documentation** | User docs complete, developer docs complete, API docs generated, README updated |

---

## Git Requirements

All projects must use Git for version control.

### Branch Strategy

| Branch Pattern | Purpose |
|----------------|---------|
| `main` | Stable, protected - production-ready code |
| `feature/<task-id>-<short-desc>` | Per task/component implementation |
| `fix/<issue-id>-<short-desc>` | Bug fixes |

### Commit Format (Conventional Commits)

```
<type>(<scope>): <description>

[optional body]

Refs: REQ-XXX-FN-NNN
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### Conflict Resolution

1. Developer resolves conflicts following existing code patterns
2. Design doc conflicts escalated to user
3. Task Manager tracks conflict resolution status

---

## Memory Integration (MCP)

**Required Dependency:** [claude-code-project-memory-mcp](https://github.com/osok/claude-code-project-memory-mcp) MCP server. Install and configure before using this framework.

### Memory Types

| Type | Purpose | Primary Writers | Primary Readers |
|------|---------|-----------------|-----------------|
| `requirements` | Stored requirements with IDs | Requirements Agent | All agents |
| `design` | Architectural decisions, patterns, ADRs | Architect, Design Agents | All agents |
| `code_pattern` | Indexed source code patterns | Developer, Test Coder | Developer, Test Coder |
| `component` | Component specs, schemas, API endpoints | Design Agents, Data Agent | All agents |
| `function` | Function-level code index | Auto-indexed | Developer, Test Coder |
| `test_history` | Test results, failures, diagnoses, reviews | Test Runner, Test Debugger, Reviewers | Test Agents, Task Manager |
| `session` | Session state, phase completions | Task Manager | Task Manager |
| `user_preference` | User preferences and customizations | User interactions | All agents |

### Memory Operations Reference

| Operation | Description |
|-----------|-------------|
| `memory_search` | Semantic search across memories — use before any work |
| `memory_add` / `memory_bulk_add` | Store new memory(s) — after completing significant work |
| `memory_get` / `memory_update` | Retrieve or update by ID |
| `find_duplicates` | Find near-duplicate memories — before adding |
| `get_design_context` | Get design decisions for a component |
| `trace_requirements` | Trace requirements to implementations |
| `code_search` | Find similar code patterns |
| `check_consistency` | Validate code follows established patterns |
| `validate_fix` | Validate fix against design |
| `index_file` / `index_directory` | Index source files for code_search |
| `memory_statistics` | Check system health |
| `normalize_memory` | Deduplicate and consolidate |
| `export_memory` / `import_memory` | Backup and restore |
| `graph_query` / `get_related` / `reindex` | Advanced graph queries and reindexing |

### Code Consistency Enforcement

All code must look like it was designed and developed by one person. Components of the same type must follow identical patterns.

1. **Pattern Conformance** — Search memory for existing components of the same type; follow their structure exactly
2. **Base Class Reuse** — Never reimplement functionality from base classes or shared utilities
3. **Structural Uniformity** — Same file organization, constructors, lifecycle methods, configuration
4. **Naming Consistency** — Follow conventions established by the first component of that type

See developer.md for detailed enforcement steps. Code reviewers flag structural mismatches, base class reimplementation, and naming/organization deviations.

### Memory Best Practices

- Search before creating (avoid duplicates)
- Use specific queries with requirement IDs and component names
- Store actionable data with `work_seq` and category metadata
- Index new source files after creating them
- Run `normalize_memory` periodically

### Memory Initialization

**On `initialize`:** Check `memory_statistics()`, index codebase with `index_directory`, store project overview and user preferences.
**On `continue`:** Search for last session state (`memory_types: ["session"]`), load context for current phase.

---

## Working Principles

- Blunt, honest feedback over false agreement
- Right matters more than feelings
- Keep markdown lean - enough for intent, no more
- Document decisions and rationale
