# Framework Enhancement Task List

**Sequence:** 001
**Name:** Framework Enhancements v2
**Status:** Complete

---

## Overview

Comprehensive enhancements to the Claude Code Sub-Agents framework based on evaluation feedback. These changes improve flexibility, traceability, quality gates, and parallel execution capabilities.

---

## Tasks

### 1. Model Configuration System
**Status:** Complete
**Files:** CLAUDE.md, all 25 agent files

#### 1.1 Add Model Configuration Section to CLAUDE.md
- [x] Add `## Model Configuration` section after Commands
- [x] Define default model setting (opus)
- [x] Document override mechanism
- [x] Explain model selection guidance (opus for complex reasoning, sonnet for standard coding, haiku for exploration)

#### 1.2 Update Agent YAML Front-Matter
- [x] Update all 25 agents to show model inheritance: `model: ${default}` or specific override
- [x] Agents that may benefit from different models:
  - Explore agents: could use haiku
  - Developer: could use sonnet (updated)
  - Complex reasoning (Architect, Security): keep opus

**Files to modify:**
- `.claude/agents/requirements.md`
- `.claude/agents/architect.md`
- `.claude/agents/requirements-analyzer.md`
- `.claude/agents/design-orchestrator.md`
- `.claude/agents/task-manager.md`
- `.claude/agents/ui-ux-design-agent.md`
- `.claude/agents/data-design-agent.md`
- `.claude/agents/security-design-agent.md`
- `.claude/agents/library-design-agent.md`
- `.claude/agents/backend-design-agent.md`
- `.claude/agents/frontend-design-agent.md`
- `.claude/agents/agent-design-agent.md`
- `.claude/agents/integration-design-agent.md`
- `.claude/agents/infrastructure-design-agent.md`
- `.claude/agents/data-agent.md`
- `.claude/agents/deployment.md`
- `.claude/agents/developer.md`
- `.claude/agents/documentation.md`
- `.claude/agents/test-designer.md`
- `.claude/agents/test-coder.md`
- `.claude/agents/test-runner.md`
- `.claude/agents/test-debugger.md`
- `.claude/agents/code-reviewer-requirements.md`
- `.claude/agents/code-reviewer-security.md`
- `.claude/agents/code-reviewer-integration.md`

---

### 2. Framework Activity Log
**Status:** Complete
**Files:** CLAUDE.md, task-manager.md, all agents

#### 2.1 Define Log Specification in CLAUDE.md
- [x] Add `## Activity Log` section
- [x] Define log file location: `project-docs/activity.log`
- [x] Define log entry format:
  ```
  [YYYY-MM-DD HH:MM:SS] [AGENT-NAME] [ACTION] Details
  ```
- [x] Define action types: START, COMPLETE, ERROR, DECISION, FILE_MODIFY, FILE_CREATE, BLOCKED, UNBLOCKED

#### 2.2 Update Task Manager as Log Writer
- [x] Add log writer responsibility to task-manager.md
- [x] Define `<log-entry>` block format that agents emit
- [x] Task Manager appends entries after each agent completes
- [ ] Log rotation/archival policy (optional)

#### 2.3 Update All Agents to Emit Log Entries
- [x] Add "Output Format" section to each agent specifying log entry requirements
- [x] Each agent must emit `<log-entry>` block with:
  - Agent name
  - Action performed
  - Files affected (if any)
  - Key decisions made (if any)
  - Errors encountered (if any)

---

### 3. Git Integration
**Status:** Complete
**Files:** CLAUDE.md, task-manager.md, developer.md

#### 3.1 Add Git Requirements to CLAUDE.md
- [x] Add `## Git Requirements` section
- [x] Require git initialized for all projects
- [x] Define branch strategy:
  - `main` - stable, protected
  - `feature/<task-id>-<short-description>` - per task/component
  - `fix/<issue-id>-<short-description>` - for bug fixes
- [x] Define commit message format (Conventional Commits):
  ```
  <type>(<scope>): <description>

  [optional body]

  Refs: REQ-XXX-FN-NNN
  ```
- [x] Types: feat, fix, docs, style, refactor, test, chore
- [x] Require requirement ID references where applicable

#### 3.2 Update Task Manager for Git Orchestration
- [x] Add git status checks to workflow gates
- [x] Define when commits occur:
  - After implementation unit passes code review
  - After test suite passes
  - After documentation updates
- [x] Task Manager instructs Developer when to commit
- [x] Task Manager manages branch creation/merging

#### 3.3 Update Developer Agent for Git Execution
- [x] Add git execution responsibilities
- [x] Developer creates branches when instructed
- [x] Developer commits with proper message format
- [x] Developer does NOT push without Task Manager instruction
- [x] Add git conflict resolution guidance

---

### 4. Extend Infrastructure Agent (CI/CD)
**Status:** Complete
**Files:** infrastructure-design-agent.md, design-doc-template-infrastructure.md

#### 4.1 Update Infrastructure Design Agent
- [x] Add CI/CD pipeline design to agent responsibilities
- [x] Supported platforms:
  - GitHub Actions
  - GitLab CI
  - Azure DevOps
  - Jenkins
  - CircleCI
- [x] Pipeline stages to design:
  - Build
  - Test (unit, integration, e2e)
  - Security scanning
  - Deploy (dev, staging, prod)
- [x] Environment-specific pipeline variations

#### 4.2 Update Infrastructure Design Template
- [x] Add `## CI/CD Pipeline Design` section
- [x] Pipeline architecture diagram
- [x] Stage definitions with triggers
- [x] Environment promotion strategy
- [x] Rollback procedures
- [x] Secret injection in pipelines
- [x] Caching strategies
- [x] Artifact management

---

### 5. Extend Infrastructure Agent (Observability)
**Status:** Complete
**Files:** infrastructure-design-agent.md, design-doc-template-infrastructure.md

#### 5.1 Update Infrastructure Design Agent
- [x] Add observability design to agent responsibilities
- [x] Coverage areas:
  - Logging infrastructure (aggregation, retention)
  - Metrics and APM (Datadog, New Relic, CloudWatch, Prometheus)
  - Distributed tracing (Jaeger, Zipkin, X-Ray)
  - Alerting rules and escalation
  - Dashboards and visualization

#### 5.2 Update Infrastructure Design Template
- [x] Add `## Observability Design` section
- [x] Logging architecture (levels, format, aggregation)
- [x] Metrics collection strategy
- [x] Key performance indicators (KPIs)
- [x] Alert definitions (thresholds, severity, routing)
- [x] Dashboard specifications
- [x] On-call and escalation procedures
- [x] Runbook references

---

### 6. Exit Criteria in Task Manager
**Status:** Complete
**Files:** task-manager.md, CLAUDE.md

#### 6.1 Define Exit Criteria in CLAUDE.md
- [x] Add `## Exit Criteria` section
- [x] Define phase completion requirements:

**Design Phase:**
- [x] All required design documents created
- [x] Requirements traceability complete
- [x] No unresolved design questions

**Implementation Phase:**
- [x] All code reviewers pass (no critical/high issues)
- [x] No TODO/FIXME markers in committed code
- [x] All interfaces implemented (no stubs)

**Testing Phase:**
- [x] Test coverage minimum: 70% (configurable)
- [x] All tests passing
- [x] No critical/high security findings
- [x] Performance benchmarks met (if defined)

**Documentation Phase:**
- [x] User documentation complete
- [x] Developer documentation complete
- [x] API documentation generated

#### 6.2 Update Task Manager to Enforce Exit Criteria
- [x] Add exit criteria validation before phase transitions
- [x] Block phase completion if criteria not met
- [x] Report specific failures to user
- [x] Allow user override with acknowledgment

---

### 7. Secrets Management in Security Agent
**Status:** Complete
**Files:** security-design-agent.md, design-doc-template-security.md

#### 7.1 Update Security Design Agent
- [x] Add secrets management to agent responsibilities
- [x] Coverage areas:
  - Secret storage solutions (Vault, AWS Secrets Manager, Azure Key Vault)
  - Secret rotation policies
  - Access control for secrets
  - Secret injection patterns
  - Environment-specific secrets
  - Development vs production secrets

#### 7.2 Update Security Design Template
- [x] Add `## Secrets Management` section
- [x] Secret inventory and classification
- [x] Storage solution architecture
- [x] Rotation schedule and procedures
- [x] Access control matrix
- [x] Audit logging for secret access
- [x] Emergency secret rotation procedures
- [x] Local development secret handling

---

### 8. Dependency Management (Distributed)
**Status:** Complete
**Files:** security-design-agent.md, design-doc-template-security.md, backend-design-agent.md, frontend-design-agent.md, library-design-agent.md, developer.md

#### 8.1 Add Dependency Policies to Security Design Agent
- [x] Add dependency policy section to agent responsibilities
- [x] Policy areas:
  - Approved license types (MIT, Apache 2.0, BSD, etc.)
  - Prohibited licenses (GPL, AGPL for commercial)
  - Vulnerability thresholds (no critical, time-bound for high)
  - Scanning frequency requirements
  - Approved registries (npm, PyPI, Maven Central, etc.)
  - Internal/private registry policies

#### 8.2 Update Security Design Template
- [x] Add `## Dependency Security Policies` section
- [x] License allowlist/blocklist
- [x] Vulnerability policy matrix
- [x] Scanning tool requirements
- [x] Exception process for policy violations
- [x] Supply chain security measures

#### 8.3 Update Component Design Agents
- [x] Backend Design: Add dependency specification section
- [x] Frontend Design: Add dependency specification section
- [x] Library Design: Add shared dependency management section
- [x] Each must specify:
  - Required dependencies with version constraints
  - Justification for each dependency
  - License of each dependency
  - Alternatives considered

#### 8.4 Update Developer Agent
- [x] Add dependency validation responsibilities
- [x] Validate dependencies against Security policies before install
- [x] Run vulnerability scans as part of implementation
- [x] Report policy violations to Task Manager
- [x] Pin versions according to policy

---

### 9. Environment Parity in Deployment Agent
**Status:** Complete
**Files:** deployment.md

#### 9.1 Update Deployment Agent
- [x] Add environment parity to agent responsibilities
- [x] Coverage areas:
  - Environment definitions (dev, staging, prod)
  - Environment variable documentation
  - Parity validation checklist
  - Drift detection
  - Environment-specific configurations

#### 9.2 Add Environment Documentation Requirements
- [x] Environment variable inventory with:
  - Variable name
  - Purpose
  - Required/optional
  - Default value (if any)
  - Environment-specific values
  - Secret flag (yes/no)
- [x] Environment comparison matrix
- [x] Parity validation procedures

---

### 10. Database Migrations in Data Agent
**Status:** Complete
**Files:** data-agent.md

#### 10.1 Update Data Agent
- [x] Add migration strategy to agent responsibilities
- [x] Coverage areas:
  - Migration file generation
  - Naming conventions
  - Rollback strategy
  - Data seeding for dev/test
  - Migration testing requirements

#### 10.2 Define Migration Standards
- [x] Migration file naming: `YYYYMMDD_HHMMSS_<description>.sql` or framework equivalent
- [x] Each migration must have:
  - Up migration
  - Down migration (rollback)
  - Description
  - Requirement reference (if applicable)
- [x] Seed data organization:
  - Base seed (required for app to function)
  - Test seed (for testing scenarios)
  - Demo seed (for demonstrations)

---

### 11. Parallelism Documentation
**Status:** Complete
**Files:** CLAUDE.md

#### 11.1 Add Parallel Execution Section
- [x] Add `## Parallel Execution` section to CLAUDE.md
- [x] Document parallel opportunities:

**Design Phase (already supported):**
- Foundation: UI-UX, Data, Security (parallel)
- Core: Library, Backend (parallel)
- Application: Frontend, Agent (parallel)

**Implementation Phase (new):**
- Multiple Developer agents for independent components
- Components with no shared dependencies can be implemented in parallel

**Testing Phase (new):**
- Multiple Test Coder agents for different modules
- Test suites for independent components can run in parallel

**Documentation Phase (new):**
- User docs and Developer docs (parallel)

#### 11.2 Add Parallel Execution Guidelines
- [x] Define independence criteria for parallel work
- [x] Define merge/integration points
- [x] Conflict resolution procedures
- [x] Task Manager coordination requirements

---

## File Change Summary

| File | Changes |
|------|---------|
| CLAUDE.md | Model config, activity log, git requirements, exit criteria, parallelism |
| task-manager.md | Log writer, git orchestration, exit criteria enforcement |
| developer.md | Git execution, dependency validation |
| infrastructure-design-agent.md | CI/CD, observability |
| design-doc-template-infrastructure.md | CI/CD section, observability section |
| security-design-agent.md | Secrets management, dependency policies |
| design-doc-template-security.md | Secrets section, dependency policy section |
| backend-design-agent.md | Dependency specification |
| frontend-design-agent.md | Dependency specification |
| library-design-agent.md | Shared dependency management |
| deployment.md | Environment parity |
| data-agent.md | Migration strategy |
| All 25 agents | Model inheritance, log entry emission |

---

## Execution Order

1. **Phase 1: Foundation**
   - Task 1: Model Configuration System
   - Task 2: Framework Activity Log
   - Task 11: Parallelism Documentation

2. **Phase 2: Git & Quality**
   - Task 3: Git Integration
   - Task 6: Exit Criteria

3. **Phase 3: Infrastructure Extensions**
   - Task 4: CI/CD in Infrastructure Agent
   - Task 5: Observability in Infrastructure Agent

4. **Phase 4: Security Extensions**
   - Task 7: Secrets Management
   - Task 8: Dependency Management (Security policies)

5. **Phase 5: Component Updates**
   - Task 8 (continued): Dependency specs in design agents
   - Task 9: Environment Parity
   - Task 10: Database Migrations

6. **Phase 6: Final Updates**
   - Update all 25 agents for model inheritance and log emission

---

## Notes

- All changes maintain backward compatibility
- No dates in any documents
- Blunt, honest feedback over false agreement
- Keep markdown lean
