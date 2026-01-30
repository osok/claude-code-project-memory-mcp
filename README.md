# Claude Code Sub-Agents for Large Projects

A comprehensive framework of specialized sub-agents for Claude Code, designed for the complete software development lifecycle of large-scale applications.

## Overview

This framework provides 25 coordinated AI agents that work together to build your application:

- **Requirements Agent** - Elicits requirements using ISO 29148 standard
- **Architect Agent** - Makes technology and structure decisions
- **Design Orchestrator** - Coordinates 9 specialized design agents
- **Developer Agent** - Writes code following best practices
- **Test Agents** - Plan, write, and run tests
- **Code Review Agents** - Check requirements, security, integration
- **Documentation Agent** - Creates user and developer docs

The **Task Manager** coordinates everything, tracking what's done and what's next.

## Quick Start

### 1. Create Your Project

```bash
gh repo create my-project --template osok/claude-code-startup-large-projects --clone
cd my-project
```

### 2. Initialize

```
initialize
```

### 3. Begin Work

```
lets begin
```

This will:
- Check for existing requirements in `requirement-docs/`
- If none exist, help you create them
- If they exist, ask for your approval
- Once approved, run the full agent workflow

Use `continue` to resume work in new sessions.

## Included Agents (25 total)

### Core Workflow Agents

| Agent | What It Does |
|-------|--------------|
| **Requirements** | Interviews you to understand what to build |
| **Architect** | Makes technology choices, defines structure |
| **Requirements Analyzer** | Parses ISO 29148 requirements structure |
| **Design Orchestrator** | Coordinates specialized design agents |
| **Task Manager** | Coordinates agents, tracks progress |

### Specialized Design Agents

| Agent | Output Prefix | What It Does |
|-------|---------------|--------------|
| **UI/UX Design** | 01-, 90- | UI/UX patterns and style guides |
| **Data Design** | 02- | Data architecture and models |
| **Security Design** | 03- | Security architecture and threat models |
| **Library Design** | 10- | Shared component libraries |
| **Backend Design** | 20- | Backend services and APIs |
| **Frontend Design** | 30- | Frontend applications |
| **Agent Design** | 40- | Background workers and jobs |
| **Integration Design** | 50- | API contracts between systems |
| **Infrastructure Design** | 60- | Cloud, Docker, deployment |

### Implementation Agents

| Agent | What It Does |
|-------|--------------|
| **Data Agent** | Defines schemas and data structures |
| **Deployment** | Docker, env configs, infrastructure |
| **Developer** | Writes application code |
| **Documentation** | Writes user and developer docs |

### Testing Agents

| Agent | What It Does |
|-------|--------------|
| **Test Designer** | Plans what tests are needed |
| **Test Coder** | Writes test code |
| **Test Runner** | Runs tests, reports results |
| **Test Debugger** | Deep debugging across all layers |

### Code Review Agents

| Agent | What It Does |
|-------|--------------|
| **Code Reviewer - Requirements** | Verifies completeness against requirements |
| **Code Reviewer - Security** | Checks OWASP vulnerabilities |
| **Code Reviewer - Integration** | Finds stubs, wiring gaps |

## Language Support

Pre-built conventions for 27 technologies:

**Backend**: Go, Java, Python, TypeScript, Rust, C#/.NET, Ruby, PHP, Kotlin, Scala, Elixir

**Frontend**: React, Vue, Angular, Svelte, Next.js, Nuxt

**Mobile**: Swift, Kotlin Android, Flutter/Dart, React Native

**Infrastructure**: Terraform, Kubernetes, Bash/Shell, SQL

**Emerging**: Zig, Solidity

## Project Structure

```
your-project/
├── .claude/agents/       # Agent definitions
├── CLAUDE.md             # Project memory and status
├── conventions/          # Coding standards by language
├── requirement-docs/     # ISO 29148 requirements
├── design-docs/          # Generated design documents
├── design-templates/     # Design document templates
├── project-docs/         # Task lists, ADRs, schemas
├── developer-docs/       # Docs for contributors
└── user-docs/            # Docs for end users
```

## Commands

| Command | When to Use |
|---------|-------------|
| `initialize` | Once, after cloning |
| `lets begin` | Start new work - checks requirements, gets approval, runs workflow |
| `continue` | Resume work in new session |

## How It Works

1. **Document-based coordination** - Agents communicate via markdown files
2. **Task Manager as orchestrator** - One agent controls workflow
3. **Schemas as source of truth** - Data Agent maintains authoritative schemas
4. **Smart failure routing** - Test failures route to appropriate agents

## Workflow

```mermaid
flowchart TB
    subgraph Requirements["📋 Requirements Phase"]
        REQ[Requirements Agent]
    end

    subgraph Architecture["🏗️ Architecture Phase"]
        ARCH[Architect Agent]
    end

    subgraph Design["📐 Design Phase"]
        RA[Requirements Analyzer]
        DO[Design Orchestrator]

        subgraph Foundation["Foundation Layer"]
            direction LR
            UIUX[UI/UX Design]
            DATA_D[Data Design]
            SEC_D[Security Design]
        end

        subgraph Core["Core Layer"]
            direction LR
            LIB[Library Design]
            BACK[Backend Design]
        end

        subgraph Application["Application Layer"]
            direction LR
            FRONT[Frontend Design]
            AGENT_D[Agent Design]
        end

        INT_D[Integration Design]
        INFRA[Infrastructure Design]
    end

    subgraph Planning["📝 Planning Phase"]
        direction LR
        TD[Test Designer]
        DA[Data Agent]
        TM[Task Manager]
    end

    subgraph Implementation["💻 Implementation Phase"]
        DEV[Developer]
    end

    subgraph Review["🔍 Review Phase"]
        direction LR
        CR_REQ[Code Reviewer<br/>Requirements]
        CR_SEC[Code Reviewer<br/>Security]
        CR_INT[Code Reviewer<br/>Integration]
    end

    subgraph TestPrep["🧪 Test Prep Phase"]
        direction LR
        TD2[Test Designer]
        DOC[Documentation]
        DEPLOY[Deployment]
    end

    subgraph Testing["✅ Testing Phase"]
        TC[Test Coder]
        TR[Test Runner]
        TDB[Test Debugger]
    end

    subgraph Finalize["📚 Finalize Phase"]
        DOC2[Documentation]
    end

    %% Main Flow
    REQ --> ARCH
    ARCH --> RA
    RA --> DO
    DO --> Foundation
    Foundation --> Core
    Core --> Application
    Application --> INT_D
    INT_D --> INFRA
    INFRA --> Planning
    TD & DA --> TM
    TM --> DEV
    DEV --> Review
    CR_REQ & CR_SEC & CR_INT --> FIX{Gaps Found?}
    FIX -->|Yes| TM
    TM -.->|Design Gap| DO
    TM -.->|Data Gap| DA
    TM -.->|Code Gap| DEV
    FIX -->|No| TestPrep
    TD2 & DOC & DEPLOY --> TC
    TC --> TR
    TR --> PASS{Tests Pass?}
    PASS -->|No| TDB
    TDB --> TM
    TM -.->|Route Fix| DEV
    TM -.->|Route Fix| TC
    TM -.->|Route Fix| DO
    PASS -->|Yes| DOC2
    DOC2 --> DONE((Complete))

    %% Styling
    classDef phase fill:#e1f5fe,stroke:#01579b
    classDef agent fill:#fff3e0,stroke:#e65100
    classDef decision fill:#fce4ec,stroke:#880e4f
    classDef done fill:#e8f5e9,stroke:#1b5e20

    class REQ,ARCH,RA,DO,UIUX,DATA_D,SEC_D,LIB,BACK,FRONT,AGENT_D,INT_D,INFRA,TD,DA,TM,DEV,CR_REQ,CR_SEC,CR_INT,TD2,DOC,DEPLOY,TC,TR,TDB,DOC2 agent
    class FIX,PASS decision
    class DONE done
```

### Workflow Phases

| Phase | Agents | Output |
|-------|--------|--------|
| **Requirements** | Requirements | `requirement-docs/` |
| **Architecture** | Architect | `project-docs/adrs/` |
| **Design** | Requirements Analyzer → Design Orchestrator → 9 Specialized Agents | `design-docs/` |
| **Planning** | Test Designer, Data Agent, Task Manager | Test plan, schemas, task list |
| **Implementation** | Developer | Application code |
| **Review** | 3 Code Reviewers (parallel) | Review reports |
| **Test Prep** | Test Designer, Documentation, Deployment | Updated plans, docs, env |
| **Testing** | Test Coder → Test Runner → Test Debugger | Tests, results, fixes |
| **Finalize** | Documentation | Final docs |

## Tips

- Be specific in requirements - more detail = better output
- Answer agent questions thoughtfully
- Review designs before implementation
- Use `continue` to resume sessions

## License

MIT
