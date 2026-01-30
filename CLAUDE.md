# Claude Code Sub-Agents Project

A collection of specialized sub-agents for the complete software development lifecycle: requirements, design, development, testing, and deployment.

---

## Current Work

<!-- This section tracks active work. Clear when complete. -->

**Seq:** 001
**Name:** Framework Enhancements v2
**Status:** Complete

**Task List:** [TASK-LIST-framework-enhancements.md](TASK-LIST-framework-enhancements.md)

**Current Phase:** All Phases Complete

**Summary:** Comprehensive enhancements including model configuration, activity logging, git integration, CI/CD, observability, exit criteria, secrets management, dependency policies, environment parity, database migrations, and parallelism documentation.

We are NOT using this workflow of agents to build anything. Rather they are the project. This will be used as a template for future development. All tasks in the task-list have been completed.

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

---

## Requirement ID Conventions

| Pattern | Type |
|---------|------|
| `STK-NNN` | Stakeholder |
| `REQ-XXX-FN-NNN` | Functional |
| `REQ-INT-UI/API-NNN` | Interface |
| `REQ-DATA-NNN` | Data |
| `REQ-NFR-PERF/SEC/ACC/AVAIL-NNN` | Non-functional |
| `REQ-VER-NNN` | Verification |
| `REQ-DEP-NNN` | Deployment |

---

## Document Sequence Tracker

| Seq | Short Name | Requirements | Design | Task List | Status |
|-----|------------|--------------|--------|-----------|--------|
| 001 | Framework Enhancements v2 | N/A | N/A | TASK-LIST-framework-enhancements.md | Complete |

---

## Commands

| Command | Meaning |
|---------|---------|
| `initialize` | Reset project, ask what to build |
| `lets begin` | Check requirements, collect if missing, get approval, start workflow |
| `continue` | Resume current work from task list |

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

Provides traceability of all agent actions during workflow execution.

### Log Location

`project-docs/activity.log`

### Log Entry Format

```
[YYYY-MM-DD HH:MM:SS] [AGENT-NAME] [ACTION] Details
```

### Action Types

| Action | Description |
|--------|-------------|
| START | Agent began execution |
| COMPLETE | Agent finished successfully |
| ERROR | Agent encountered an error |
| DECISION | Significant decision made |
| FILE_MODIFY | Existing file modified |
| FILE_CREATE | New file created |
| BLOCKED | Agent blocked, waiting on dependency |
| UNBLOCKED | Agent unblocked, resuming work |

### Log Entry Block Format

Agents emit log entries in this format for Task Manager to append:

```xml
<log-entry>
  <agent>agent-name</agent>
  <action>ACTION_TYPE</action>
  <details>Description of what occurred</details>
  <files>file1.md, file2.ts</files>
  <decisions>Key decision made (if any)</decisions>
  <errors>Error message (if any)</errors>
</log-entry>
```

### Log Writer Responsibility

Task Manager is the sole writer to `activity.log`. Agents emit `<log-entry>` blocks in their responses; Task Manager appends entries after each agent completes.

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

## Working Principles

- Blunt, honest feedback over false agreement
- Right matters more than feelings
- Keep markdown lean - enough for intent, no more
- Document decisions and rationale
