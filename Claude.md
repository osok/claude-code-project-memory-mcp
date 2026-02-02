# Claude Code Sub-Agents Project

A collection of specialized sub-agents for the complete software development lifecycle: requirements, design, development, testing, and deployment.

---

## Current Work

<!-- This section tracks active work. Clear when complete. -->

**Seq:** 002
**Name:** Claude Code Long-Term Memory System
**Status:** In Progress

**Task List:** [TASK-LIST-memory-system.md](project-docs/TASK-LIST-memory-system.md)

**Current Phase:** Test Execution & Fixes

**Summary:** Persistent memory infrastructure for Claude Code using Qdrant + Neo4j with MCP integration. Enables context persistence, duplicate detection, design alignment, and consistency enforcement across multi-session development. Unit tests: 742/742 passing (100%), 78.32% coverage (target 80%). Next: integration tests, E2E tests, performance tests, then continue coverage improvement to 80%.

**Artifacts:**
- Requirements: [requirements-memory-docs.md](requirement-docs/requirements-memory-docs.md) (156 requirements)
- Architecture: [project-docs/adrs/](project-docs/adrs/) (8 ADRs)
- Design: [design-docs/](design-docs/) (8 design documents)
- Test Plan: [002-test-plan.md](project-docs/002-test-plan.md) (278 test cases)
- Testing Strategy: [testing-strategy.md](project-docs/testing-strategy.md)
- Mock Application: [mock-src/](mock-src/) (Python, TypeScript, Go)
- Schemas: [project-docs/schemas/](project-docs/schemas/) (4 schema files)
- Task List: [TASK-LIST-memory-system.md](project-docs/TASK-LIST-memory-system.md) (171 tasks)

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
| **Architecture** | 2 | @architect | Architectural decisions, ADRs → `project-docs/adrs/` |
| **Design** | 3 | @requirements-analyzer | Parse requirements structure |
| | 4 | @design-orchestrator | Coordinate specialized design agents |
| | 4a | └─ Foundation | @ui-ux-design, @data-design, @security-design (parallel) |
| | 4b | └─ Core | @library-design, @backend-design (parallel) |
| | 4c | └─ Application | @frontend-design, @agent-design (parallel) |
| | 4d | └─ Integration | @integration-design |
| | 4e | └─ Infrastructure | @infrastructure-design |
| | | | Output: `design-docs/` with prefixed documents |
| **Planning** | 5 | @test-designer, @data-agent | Plan tests; define schemas (parallel) |
| | 6 | @task-manager | Create task list, orchestrate |
| **Implementation** | 7 | @developer(s) | Implement code |
| **Review** | 8 | Code reviewers (3) | @code-reviewer-requirements, @code-reviewer-security, @code-reviewer-integration (parallel) |
| | 9 | @developer(s) | Fix gaps |
| | 10 | Loop to Step 8 | Until resolved |
| **Test Prep** | 11 | @test-designer | Review/update test plan |
| | 12 | @documentation, @deployment | Docs and env setup (parallel) |
| **Testing** | 13 | @test-coder → @test-runner | Write & run tests |
| | 14 | @test-debugger | On failure: diagnose |
| | 15 | @task-manager → Agent | Route fix |
| | 16 | Loop to Step 13 | Until all pass |
| **Finalize** | 17 | @documentation | Final updates |

### Design Document Prefixes

| Prefix | Type | Agent |
|--------|------|-------|
| 00- | Overview/traceability | @design-orchestrator |
| 01- | Style guide | @ui-ux-design |
| 02- | Data architecture | @data-design |
| 03- | Security architecture | @security-design |
| 10- | Component libraries | @library-design |
| 20- | Backend services | @backend-design |
| 30- | Frontend applications | @frontend-design |
| 40- | Agents/workers | @agent-design |
| 50- | Integration contracts | @integration-design |
| 60- | Infrastructure | @infrastructure-design |
| 90- | UI/UX designs | @ui-ux-design |

### Design Document Strategy

**Do NOT duplicate design documents for each work item.** Instead:

1. **Work-specific documents** (created per work item):
   - `requirement-docs/{seq}-requirements-{short_name}.md` - Requirements for this work
   - `design-docs/{seq}-design-{short_name}.md` - Design overview for this work

2. **Foundational documents** (updated, not duplicated):
   - `design-docs/01-style-guide.md` - Single style guide, updated as needed
   - `design-docs/02-data-architecture.md` - Single data architecture, updated
   - `design-docs/03-security-architecture.md` - Single security doc, updated
   - All other prefixed docs (10-, 20-, 30-, etc.) - Updated to incorporate new work

**Update Pattern:**
- Design agents check if foundational doc exists
- If exists: Add new sections/updates for current work, preserve existing content
- If not exists: Create the foundational doc
- Reference the work sequence in updates: "Added for Seq {NNN}: {short_name}"

**Example:** When adding user authentication (Seq 002):
- CREATE: `002-requirements-user-auth.md`, `002-design-user-auth.md`
- UPDATE: `02-data-architecture.md` (add User entity), `03-security-architecture.md` (add auth model)

---

## Folder Structure

```
project/
├── .claude/agents/       # Sub-agent definitions
├── CLAUDE.md             # This file - project index
├── conventions/          # Language-specific conventions
│   ├── developer/        # 27 language dev conventions
│   └── testing/          # 27 language test conventions
├── requirement-docs/     # ISO 29148 requirements
├── design-docs/          # Design documents (prefixed by type)
│   ├── 00-design-overview.md
│   ├── 01-style-guide.md
│   ├── 02-data-architecture.md
│   ├── 03-security-architecture.md
│   ├── 10-*, 20-*, 30-*, etc.
│   └── ...
├── design-templates/     # Design document templates
├── project-docs/         # Task lists and project artifacts
│   ├── adrs/             # Architecture Decision Records
│   └── schemas/          # Data schemas
├── developer-docs/       # Documentation for contributors
└── user-docs/            # Documentation for users
```

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

This protects the user's local development environment from corruption, version conflicts, and unintended side effects.

### Required Isolation by Language

| Language | Isolation Method | Setup Command |
|----------|------------------|---------------|
| Python | Virtual environment | `python -m venv .venv && source .venv/bin/activate` |
| Node.js | Local node_modules | `npm install` (default behavior, no -g flag) |
| Ruby | Bundler with path | `bundle config set --local path 'vendor/bundle'` |
| Go | Go modules | `go mod init` (default behavior) |
| Rust | Cargo (project-local) | Default behavior |
| Java | Maven/Gradle (project-local) | Default behavior |

### Python-Specific Requirements

1. **Always create venv first** before any pip install:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # or: .venv\Scripts\activate  # Windows
   ```

2. **Never use** `pip install` without an active venv
3. **Never use** `sudo pip install`
4. **Add to .gitignore**: `.venv/`, `venv/`, `__pycache__/`

### Node.js-Specific Requirements

1. **Never use** `npm install -g` or `yarn global add`
2. Use `npx` for CLI tools instead of global installs
3. **Add to .gitignore**: `node_modules/`

### Enforcement

- Deployment Agent must set up project environment before any installs
- Developer Agent must verify environment is active before installing
- Test agents must use project environment for test execution

---

## Task List Management

**MANDATORY: Update the task list before marking any work complete.**

### Requirements

1. **Before Ending a Session** - Update task statuses in the task list file to reflect completed work
2. **Before Marking Complete** - No task or phase can be marked complete until the task list is updated
3. **Status Values** - Use consistent status values:
   - `Not Started` - Work has not begun
   - `**Complete**` - Work is finished (bold)
   - `Stub` - Placeholder implementation exists
   - `Partial` - Some work done, more needed
   - `Blocked` - Cannot proceed due to dependency

### Update Checklist

Before completing a work session:

- [ ] Update individual task statuses in the phase tables
- [ ] Update the Summary table at the bottom with phase completion status
- [ ] Add notes to the Notes column indicating where code was implemented
- [ ] Remove or update any "Needs implementation" notes for completed tasks

### Enforcement

Agents MUST update the task list when:
- A task is completed
- A stub implementation is created
- Work is blocked by a dependency
- Switching to a different task

Failure to update the task list results in loss of progress visibility across sessions.

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

| Seq | Short Name | Requirements | Design | Task List | Status |
|-----|------------|--------------|--------|-----------|--------|
| 002 | Memory System | requirements-memory-docs.md | design-docs/*.md | TASK-LIST-memory-system.md | Implementation |

---

## Commands

| Command | Meaning |
|---------|---------|
| `initialize` | Reset project, ask what to build |
| `new work` | Start new work item with fresh sequence, interview for requirements |
| `lets begin` | Check requirements, collect if missing, get approval, start workflow |
| `continue` | **Spawn @task-manager** to resume and coordinate current work |

### `continue` Workflow

When user says `continue`, immediately spawn the **Task Manager agent** to coordinate work:

1. **Spawn Task Manager** - Use the Task tool to invoke `@task-manager` agent
2. **Task Manager reads context:**
   - Current Work section in CLAUDE.md
   - Task list file referenced in Current Work
   - Current phase and status
3. **Task Manager coordinates:**
   - Identifies next tasks to work on
   - Spawns appropriate specialized agents (Developer, Test Coder, Test Runner, etc.)
   - Updates task statuses as work completes
   - Reports progress to user
4. **Work continues** until:
   - All pending tasks in current phase complete
   - A blocking issue is encountered
   - User interrupts or redirects

**CRITICAL:** Do NOT attempt to do the work directly. Always delegate to Task Manager for proper orchestration, parallelization, and task tracking.

### `initialize` Workflow

When user says `initialize`, perform these actions **before** asking what to build:

1. **Reset Current Work section** to blank state:
   ```markdown
   ## Current Work

   <!-- This section tracks active work. Clear when complete. -->

   **Seq:** (pending)
   **Name:** (pending)
   **Status:** Not Started

   **Task List:** (none)

   **Current Phase:** Awaiting Requirements

   **Summary:** (none)
   ```

2. **Reset README.md** to minimal template:
   ```markdown
   # Project Name

   (Project description will be added after requirements are defined)

   ## Getting Started

   See [CLAUDE.md](CLAUDE.md) for development workflow.
   ```

3. **Reset Document Sequence Tracker** - Clear all rows except header

4. **Clear project artifacts** (if they exist):
   - Delete files in `requirement-docs/` (except `README.md` and `_sample-requirements.md`)
   - Delete files in `design-docs/` (except templates)
   - Delete files in `project-docs/` (except `adrs/` folder structure)
   - Clear `project-docs/activity.log` if it exists

5. **After all resets complete**, ask: "What would you like to build?"

---

### `new work` Workflow

Creates a new work item without resetting existing project artifacts.

1. **Determine next sequence number:**
   - Read Document Sequence Tracker to find highest existing sequence
   - Increment by 1 (e.g., if highest is 001, new is 002)
   - Format as 3-digit zero-padded string

2. **Prompt for work description:**
   - Ask: "What is this work about? Provide a brief description."
   - From description, generate a `short_name` (lowercase, hyphens, max 30 chars)
   - Confirm short name with user: "Short name will be: `{short_name}`. OK?"

3. **Update CLAUDE.md Current Work section:**
   ```markdown
   ## Current Work

   <!-- This section tracks active work. Clear when complete. -->

   **Seq:** {new_seq}
   **Name:** {short_name}
   **Status:** Requirements Gathering

   **Task List:** (pending)

   **Current Phase:** Requirements

   **Summary:** {user's description}
   ```

4. **Create requirements document scaffold:**
   - Create `requirement-docs/{seq}-requirements-{short_name}.md`
   - Initialize with ISO/IEC/IEEE 29148:2018 structure (empty sections)

5. **Ask user about requirements source:**
   - Option A: "I'll upload/paste my requirements" → User provides content, agent formats to ISO 29148
   - Option B: "Interview me to gather requirements" → Proceed to requirements interview

6. **If interview selected, conduct requirements elicitation:**
   - Focus on gathering information for each ISO 29148 section
   - See Requirements Interview Guide below

7. **Update Document Sequence Tracker** with new row

---

### Requirements Interview Guide

Structured interview to gather ISO/IEC/IEEE 29148:2018 compliant requirements. **No traceability matrix required.**

#### Phase 1: Introduction (Section 1)

1. **Purpose:** "What problem does this system solve? Who is it for?"
2. **Scope:** "What are the major components or modules?"
3. **Definitions:** "Are there domain-specific terms I should know?"

#### Phase 2: Stakeholders (Section 2)

1. **Users:** "Who will use this system? What are their roles?"
2. **Needs:** "What does each user type need to accomplish?"
3. **Constraints:** "Are there budget, timeline, or technology constraints?"

#### Phase 3: System Requirements (Section 3)

1. **Functional:** "What should the system DO? List the main features."
   - For each feature: "What are the acceptance criteria?"
   - Probe: "What happens on success? On failure? Edge cases?"
2. **Non-Functional:**
   - Performance: "Any speed or capacity requirements?"
   - Security: "Authentication? Authorization? Data protection needs?"
   - Accessibility: "WCAG compliance level needed?"
   - Availability: "Uptime requirements? Disaster recovery?"

#### Phase 4: Interfaces (Section 4)

1. **User Interfaces:** "Describe the screens or pages needed."
2. **API Interfaces:** "What APIs are needed? Who consumes them?"
3. **External Integrations:** "Any third-party systems to integrate with?"

#### Phase 5: Data (Section 5)

1. **Entities:** "What are the main data objects? (users, orders, etc.)"
2. **Relationships:** "How do these relate to each other?"
3. **Retention:** "Any data retention or deletion requirements?"

#### Phase 6: Verification (Section 7)

1. **Testing:** "What test coverage is expected?"
2. **Acceptance:** "How will you know the system is complete?"

#### Phase 7: Deployment (Section 8)

1. **Environments:** "Development, staging, production needs?"
2. **Infrastructure:** "Cloud provider? On-premise? Containerized?"

#### Interview Principles

- Ask one question at a time, wait for response
- Confirm understanding before moving to next topic
- Number requirements as they emerge (REQ-{SEQ}-FN-001, etc.)
- Each requirement: clear, testable, single concern
- Use priority labels: Must Have, Should Have, Could Have, Won't Have
- Continue until user confirms section is complete before moving on
- Update requirements document in real-time as answers come in

---

### `lets begin` Workflow

1. **Check for requirements** in `requirement-docs/`
   - Skip `README.md` and `_sample-requirements.md`
   - Look for actual project requirement documents

2. **If no requirements exist:**
   - Invoke @requirements agent
   - Interactively collect requirements from user
   - Create requirement document in `requirement-docs/`

3. **If requirements exist:**
   - Present summary of found requirements
   - Ask user: "Are these requirements approved to proceed?"
   - If no: Allow user to modify or add requirements
   - If yes: Continue to step 4

4. **Once approved:**
   - Update Current Work section with new sequence
   - Invoke @architect for architecture decisions
   - Continue through Unified Agent Workflow (steps 2-17)

---

## Model Configuration

**Default Model:** `opus`

Agents inherit the default model unless explicitly overridden in their YAML front-matter.

### Override Mechanism

In agent YAML front-matter:
```yaml
model: opus      # Use opus (default)
model: sonnet    # Override to sonnet
model: haiku     # Override to haiku
```

### Model Selection Guidance

| Model | Use For | Example Agents |
|-------|---------|----------------|
| opus | Complex reasoning, architecture, security analysis | Architect, Security Design, Requirements |
| sonnet | Standard coding, implementation, documentation | Developer, Test Coder, Documentation |
| haiku | Exploration, quick searches, simple transformations | Explore agents, simple validation |

### Recommendations by Agent Type

| Agent Category | Recommended Model | Rationale |
|----------------|-------------------|-----------|
| Architecture & Security | opus | Requires deep reasoning about trade-offs |
| Design Agents | opus | Complex design decisions |
| Developer | sonnet | Standard implementation work |
| Test Agents | sonnet | Test implementation and execution |
| Code Reviewers | opus | Thorough analysis required |
| Documentation | sonnet | Straightforward content generation |
| Task Manager | opus | Orchestration and decision-making |

---

## Activity Log

Provides traceability of all agent actions during workflow execution. Designed for machine parsing to enable graphical visualization of requirement fulfillment.

### Log Location & Format

- **File:** `project-docs/activity.log`
- **Format:** JSON Lines (JSONL) - one JSON object per line
- **Encoding:** UTF-8

### Log Entry Schema

Each log entry is a single-line JSON object:

```json
{
  "seq": 1,
  "timestamp": "2024-03-15T10:30:00Z",
  "agent": "developer",
  "action": "START",
  "phase": "implementation",
  "parent_seq": null,
  "requirements": ["REQ-AUTH-FN-001", "REQ-AUTH-FN-002"],
  "task_id": "TASK-001",
  "details": "Implementing user authentication API",
  "files_created": [],
  "files_modified": [],
  "decisions": [],
  "errors": [],
  "duration_ms": null
}
```

### Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `seq` | integer | Yes | Global sequence number, monotonically increasing |
| `timestamp` | string | Yes | ISO 8601 timestamp with timezone (UTC preferred) |
| `agent` | string | Yes | Agent name (e.g., "developer", "architect", "test-runner") |
| `action` | string | Yes | Action type (see Action Types below) |
| `phase` | string | Yes | Workflow phase (see Phase Values below) |
| `parent_seq` | integer/null | Yes | Sequence number of parent entry (for nested agent calls), null if top-level |
| `requirements` | array | Yes | Array of REQ-* IDs being addressed, empty array if none |
| `task_id` | string/null | Yes | Task list item reference (e.g., "TASK-001"), null if not task-related |
| `details` | string | Yes | Human-readable description of the activity |
| `files_created` | array | Yes | Array of file paths created during this activity |
| `files_modified` | array | Yes | Array of file paths modified during this activity |
| `decisions` | array | Yes | Array of key decisions made, empty if none |
| `errors` | array | Yes | Array of error messages, empty if none |
| `duration_ms` | integer/null | Yes | Duration in milliseconds (populated on COMPLETE/ERROR entries) |

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

| Phase | Description |
|-------|-------------|
| `requirements` | Requirements elicitation and documentation |
| `architecture` | Architectural decisions and ADRs |
| `design` | Design document creation |
| `planning` | Test planning and task creation |
| `implementation` | Code implementation |
| `review` | Code review |
| `testing` | Test execution and debugging |
| `documentation` | Documentation creation/updates |
| `deployment` | Deployment and infrastructure |

### Log Entry Block Format

Agents emit log entries in this JSON format for Task Manager to append:

```json
<log-entry>
{
  "agent": "agent-name",
  "action": "COMPLETE",
  "phase": "implementation",
  "requirements": ["REQ-XXX-FN-001"],
  "task_id": "TASK-001",
  "details": "Brief description of what was done",
  "files_created": ["src/new-file.ts"],
  "files_modified": ["src/existing-file.ts"],
  "decisions": ["Chose X over Y because Z"],
  "errors": []
}
</log-entry>
```

**Note:** Agents do NOT include `seq`, `timestamp`, `parent_seq`, or `duration_ms` - Task Manager adds these when writing to the log.

### Log Writer Responsibility

Task Manager is the sole writer to `activity.log`:

1. **Initialize Log** - Create `project-docs/activity.log` if it doesn't exist
2. **Track Sequence** - Maintain global sequence counter across all entries
3. **Add Metadata** - Add `seq`, `timestamp`, `parent_seq`, `duration_ms` to agent entries
4. **Validate Entries** - Ensure all required fields are present
5. **Append Atomically** - Write complete JSON line (no partial writes)

### Example Log Entries

```jsonl
{"seq":1,"timestamp":"2024-03-15T10:30:00Z","agent":"task-manager","action":"START","phase":"implementation","parent_seq":null,"requirements":[],"task_id":null,"details":"Beginning implementation phase","files_created":[],"files_modified":[],"decisions":[],"errors":[],"duration_ms":null}
{"seq":2,"timestamp":"2024-03-15T10:30:05Z","agent":"developer","action":"START","phase":"implementation","parent_seq":1,"requirements":["REQ-AUTH-FN-001","REQ-AUTH-FN-002"],"task_id":"TASK-001","details":"Implementing user authentication API","files_created":[],"files_modified":[],"decisions":[],"errors":[],"duration_ms":null}
{"seq":3,"timestamp":"2024-03-15T10:35:00Z","agent":"developer","action":"FILE_CREATE","phase":"implementation","parent_seq":2,"requirements":["REQ-AUTH-FN-001"],"task_id":"TASK-001","details":"Created authentication handler","files_created":["src/auth/handler.go"],"files_modified":[],"decisions":["Using JWT for stateless auth"],"errors":[],"duration_ms":null}
{"seq":4,"timestamp":"2024-03-15T10:45:00Z","agent":"developer","action":"COMPLETE","phase":"implementation","parent_seq":1,"requirements":["REQ-AUTH-FN-001","REQ-AUTH-FN-002"],"task_id":"TASK-001","details":"User authentication API implemented","files_created":["src/auth/handler.go","src/auth/middleware.go"],"files_modified":["src/routes.go"],"decisions":["Using JWT for stateless auth","Added rate limiting middleware"],"errors":[],"duration_ms":895000}
```

### Visualization Capabilities

This log format enables:

| Visualization | Fields Used |
|---------------|-------------|
| **Requirement Timeline** | `timestamp`, `requirements`, `action` |
| **Agent Activity Graph** | `agent`, `parent_seq`, `seq` |
| **Phase Swimlanes** | `phase`, `timestamp`, `agent` |
| **Requirement Coverage Heatmap** | `requirements`, `action` |
| **File Dependency Graph** | `files_created`, `files_modified`, `agent` |
| **Blocked/Unblocked Analysis** | `action` (BLOCKED/UNBLOCKED), `duration_ms` |
| **Task Progress Gantt** | `task_id`, `timestamp`, `action`, `duration_ms` |
| **Error Analysis** | `errors`, `agent`, `phase` |
| **Decision Audit Trail** | `decisions`, `agent`, `requirements` |

---

## Parallel Execution

Documents opportunities for concurrent agent execution to improve throughput.

### Design Phase (Supported)

| Wave | Agents | Dependencies |
|------|--------|--------------|
| Foundation | UI-UX Design, Data Design, Security Design | None |
| Core | Library Design, Backend Design | Foundation complete |
| Application | Frontend Design, Agent Design | Core complete |
| Integration | Integration Design | Application complete |
| Infrastructure | Infrastructure Design | Integration complete |

### Implementation Phase

Multiple Developer agents can work in parallel when:
- Components have no shared file dependencies
- No circular import requirements
- Independent data models

**Independence Criteria:**
- Different source directories
- No shared utility modifications
- Separate database tables/collections

### Testing Phase

Parallel test execution when:
- Test suites target independent modules
- No shared test fixtures requiring sequential setup
- Database isolation per test suite

### Documentation Phase

| Parallel Work | Dependencies |
|---------------|--------------|
| User docs, Developer docs | None (can run concurrently) |
| API docs | Requires implementation complete |

### Merge/Integration Points

1. **After Design Phase** - All design docs reviewed for consistency
2. **After Implementation** - Integration testing validates connections
3. **After Testing** - Final documentation reflects tested behavior

### Conflict Resolution

1. Task Manager detects file conflicts in parallel work
2. First completion wins; subsequent agents rebase
3. Conflicting changes escalated to user for resolution

### Task Manager Coordination

- Tracks which agents are running in parallel
- Maintains dependency graph
- Blocks dependent work until prerequisites complete
- Reports parallel execution status to user

---

## Exit Criteria

Defines completion requirements for each workflow phase.

### Design Phase Exit Criteria

- [ ] All required design documents created (per Design Document Prefixes)
- [ ] Requirements traceability complete (all REQ-* IDs mapped)
- [ ] No unresolved design questions
- [ ] User approval obtained

### Implementation Phase Exit Criteria

- [ ] All code reviewers pass (no critical/high issues)
- [ ] No TODO/FIXME markers in committed code
- [ ] All interfaces implemented (no stubs)
- [ ] Code compiles/builds without errors
- [ ] Git commits follow Conventional Commits format

### Testing Phase Exit Criteria

- [ ] Test coverage minimum: 70% (configurable per project)
- [ ] All tests passing
- [ ] No critical/high security findings
- [ ] Performance benchmarks met (if defined in requirements)

### Documentation Phase Exit Criteria

- [ ] User documentation complete
- [ ] Developer documentation complete
- [ ] API documentation generated
- [ ] README updated

### Exit Criteria Enforcement

Task Manager validates exit criteria before phase transitions:
1. Check all criteria for current phase
2. Block transition if criteria not met
3. Report specific failures to user
4. Allow user override with explicit acknowledgment

---

## Git Requirements

All projects must use Git for version control.

### Branch Strategy

| Branch Pattern | Purpose |
|----------------|---------|
| `main` | Stable, protected - production-ready code |
| `feature/<task-id>-<short-desc>` | Per task/component implementation |
| `fix/<issue-id>-<short-desc>` | Bug fixes |

### Commit Message Format (Conventional Commits)

```
<type>(<scope>): <description>

[optional body]

Refs: REQ-XXX-FN-NNN
```

### Commit Types

| Type | Description |
|------|-------------|
| feat | New feature |
| fix | Bug fix |
| docs | Documentation only |
| style | Formatting, no code change |
| refactor | Code restructure, no behavior change |
| test | Adding/updating tests |
| chore | Build, tooling, dependencies |

### Git Workflow

1. **Branch Creation** - Developer creates feature branch when starting task
2. **Commits** - After implementation passes code review
3. **Additional Commits** - After test suite passes, after documentation updates
4. **Push** - Only when Task Manager instructs
5. **Merge** - Task Manager coordinates merges to main

### Conflict Resolution

1. Developer detects conflicts during rebase/merge
2. Developer resolves conflicts following existing code patterns
3. Conflicts in design docs escalated to user
4. Task Manager tracks conflict resolution status

---

## Testing Strategy

**MANDATORY: Test against real code, not mocks.**

Full documentation: [project-docs/testing-strategy.md](project-docs/testing-strategy.md)

### Key Principles

1. **Use `mock-src/`** - A comprehensive mock application for testing code parsing, indexing, and relationship detection
2. **Don't mock infrastructure being tested** - Mock external APIs (embeddings), but not the parsing/indexing being validated
3. **Known expected results** - Test against defined expected outputs in `conftest_mock_src.py`

### Mock Application Location

```
mock-src/
├── python/tasktracker/     # Python: dataclasses, services, repositories
├── typescript/src/         # TypeScript: interfaces, classes, services
├── go/pkg/                 # Go: structs, handlers
├── requirements/           # Mock requirements document
└── designs/                # Mock architecture document
```

### Test Fixtures

Use these fixtures instead of creating temporary test files:

| Fixture | Description |
|---------|-------------|
| `mock_src_python` | Path to Python mock app |
| `mock_codebase` | Alias for E2E tests (replaces `temp_codebase`) |
| `expected_python_functions` | Known function extraction results |
| `expected_relationships` | Known relationship extraction results |

### Example

```python
def test_function_extraction(mock_src_python: Path, expected_python_functions: list):
    """Test against known mock-src results, not mocked data."""
    results = parse_directory(mock_src_python)
    for expected in expected_python_functions:
        assert any(f["name"] == expected["name"] for f in results)
```

---

## Working Principles

- Blunt, honest feedback over false agreement
- Right matters more than feelings
- Keep markdown lean - enough for intent, no more
- Document decisions and rationale
