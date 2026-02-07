# Agent Memory Integration Guide

This document explains how sub-agents should integrate with the Claude Code Long-Term Memory System.

## Overview

The memory system stores project knowledge for retrieval across sessions. Agents should **actively store** what they learn and **actively retrieve** relevant context.

## Memory Types

| Type | Description | When to Store | Agents |
|------|-------------|---------------|--------|
| `requirements` | Requirements docs, user stories, acceptance criteria | After requirements elicitation/analysis | Requirements, Requirements Analyzer |
| `design` | Design docs, component designs, UI/UX specs | After creating/updating designs | All Design Agents |
| `architecture` | ADRs, architecture decisions, system design | After architectural decisions | Architect |
| `component` | Components, modules, services | After identifying/implementing components | Developer, Design Agents |
| `function` | Functions, methods, class definitions | After code indexing | Developer (via index tools) |
| `code_pattern` | Code patterns, snippets, implementations | After code indexing | Developer (via index tools) |
| `test_result` | Test execution results (pass/fail, coverage) | After test runs | Test Runner |
| `test_history` | Historical test trends, flaky tests | Periodically | Test Runner, Test Debugger |
| `session` | Session state, phase completions | At phase transitions | Task Manager |
| `user_preference` | User preferences and customizations | When user expresses preferences | Any agent |

## When to Store Memories

### Requirements Agent
```typescript
// After eliciting requirements
memory_add({
  memory_type: "requirements",
  content: `# ${requirementId}\n\n${fullRequirementText}`,
  metadata: {
    requirement_id: "REQ-001-FN-001",
    category: "functional",
    priority: "high",
    work_seq: "001"
  }
});
```

### Architect Agent
```typescript
// After creating an ADR
memory_add({
  memory_type: "architecture",
  content: `# ADR-001: ${title}\n\n## Context\n${context}\n\n## Decision\n${decision}\n\n## Consequences\n${consequences}`,
  metadata: {
    adr_id: "ADR-001",
    status: "accepted",
    work_seq: "001"
  }
});
```

### Design Agents
```typescript
// After creating component design
memory_add({
  memory_type: "design",
  content: fullDesignDocument,
  metadata: {
    component: "UserAuthService",
    design_type: "backend",
    work_seq: "001"
  }
});

// Store component info
memory_add({
  memory_type: "component",
  content: `Component: ${name}\n\nPurpose: ${purpose}\n\nInterfaces: ${interfaces}`,
  metadata: {
    name: "UserAuthService",
    type: "service",
    path: "src/services/auth",
    dependencies: ["UserRepository", "JWTService"]
  }
});
```

### Developer Agent
```typescript
// After implementing a component, index the files
index_directory({
  directory_path: "src/services/auth",
  patterns: ["**/*.ts"],
  exclude_patterns: ["**/*.test.ts", "**/node_modules/**"]
});

// Or index documentation
index_docs({
  directory_path: "project-docs",
  patterns: ["**/*.md"],
  exclude_patterns: ["**/README.md"]
});
```

### Test Runner Agent
```typescript
// After test execution
memory_add({
  memory_type: "test_result",
  content: `Test Run: ${timestamp}\n\nComponent: ${component}\n\nResults:\n- Total: ${total}\n- Passed: ${passed}\n- Failed: ${failed}\n- Coverage: ${coverage}%`,
  metadata: {
    component: "UserAuthService",
    test_type: "unit",  // or "integration", "e2e"
    total_tests: 42,
    passed: 40,
    failed: 2,
    coverage: 85.5,
    duration_ms: 12345,
    work_seq: "001"
  }
});
```

### Task Manager Agent
```typescript
// At phase transitions
memory_add({
  memory_type: "session",
  content: `Phase Completed: ${phase}\n\nWork: ${workSeq}\n\nNext Phase: ${nextPhase}`,
  metadata: {
    work_seq: "001",
    phase: "implementation",
    completed_at: new Date().toISOString()
  }
});
```

## When to Search Memories

### Before Starting Work
```typescript
// Search for existing context
const results = await memory_search({
  query: `${componentName} requirements design architecture`,
  memory_types: ["requirements", "design", "architecture", "component"],
  limit: 10
});
```

### Before Implementing
```typescript
// Find related code patterns
const patterns = await code_search({
  code_snippet: "similar function signature or pattern",
  language: "typescript",
  limit: 5
});

// Get design context
const context = await get_design_context({
  component_name: "UserAuthService",
  include_related: true
});
```

### Before Testing
```typescript
// Check test history for flaky tests
const history = await memory_search({
  query: `${componentName} test failures flaky`,
  memory_types: ["test_result", "test_history"],
  limit: 5
});
```

### During Code Review
```typescript
// Validate against requirements
const traceability = await trace_requirements({
  requirement_text: "User must be able to login with email"
});

// Check consistency
const consistency = await check_consistency({
  code: newCode,
  component_name: "UserAuthService"
});
```

## Relationship Types

The system automatically creates relationships when memories are added. These are the relationship types:

| Relationship | From → To | Meaning |
|--------------|-----------|---------|
| `IMPLEMENTS` | design → requirements | Design implements requirement |
| `IMPLEMENTS` | component → design | Component implements design |
| `GUIDES` | architecture → design | ADR guides design decisions |
| `GUIDES` | architecture → component | ADR guides component |
| `CONTAINS` | component → function | Component contains function |
| `TESTS` | test_result → component | Test tests component |
| `VERIFIES` | test_result → requirements | Test verifies requirement |
| `DEPENDS_ON` | component → component | Component depends on component |
| `RELATED_TO` | * → * | Semantically similar |

## Best Practices

1. **Store early, store often** - Add memories as soon as you have meaningful content
2. **Include metadata** - Always include `work_seq`, component names, IDs for traceability
3. **Search before creating** - Check if similar content exists first
4. **Use specific queries** - Include requirement IDs, component names in searches
5. **Index code after implementation** - Use `index_directory` after creating files
6. **Index docs on project init** - Use `index_docs` to bootstrap memory from existing docs
7. **Store test results** - Every test run should create a `test_result` memory
8. **Store decisions** - Important decisions should become `architecture` memories

## Project Initialization

When starting work on a project, agents should:

```typescript
// 1. Index existing documentation
await index_docs({
  directory_path: "requirement-docs",
  patterns: ["**/*.md"]
});

await index_docs({
  directory_path: "design-docs",
  patterns: ["**/*.md"]
});

await index_docs({
  directory_path: "project-docs/adrs",
  patterns: ["**/*.md"]
});

// 2. Index existing code
await index_directory({
  directory_path: "src",
  patterns: ["**/*.ts", "**/*.tsx", "**/*.js", "**/*.jsx"],
  exclude_patterns: ["**/node_modules/**", "**/dist/**", "**/*.test.*"]
});

// 3. Check memory statistics
const stats = await memory_statistics();
console.log("Memory initialized:", stats);
```

## Metadata Conventions

Always include these metadata fields when applicable:

| Field | Description | Example |
|-------|-------------|---------|
| `work_seq` | Current work sequence number | "001" |
| `component` | Component name | "UserAuthService" |
| `requirement_id` | Requirement ID | "REQ-001-FN-001" |
| `adr_id` | ADR ID | "ADR-001" |
| `file_path` | Source file path | "src/services/auth.ts" |
| `test_type` | Type of test | "unit", "integration", "e2e" |
| `category` | Category/classification | "functional", "security" |
