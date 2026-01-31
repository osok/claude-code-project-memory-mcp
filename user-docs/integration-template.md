# Claude Code Memory Service - Integration Template

This template shows how to integrate the Memory Service into your project's `CLAUDE.md` file to enable persistent memory across development sessions.

## Quick Integration

Add this section to your project's `CLAUDE.md`:

```markdown
## Memory Service Integration

This project uses the Claude Code Memory Service for persistent context.

### Available Memory Tools

| Tool | When to Use |
|------|-------------|
| `memory_search` | Find relevant memories for current task |
| `code_search` | Find similar code patterns before implementing |
| `find_duplicates` | Check if similar function already exists |
| `get_design_context` | Get design context before implementing features |
| `trace_requirements` | Trace requirement implementation status |

### Memory Workflow

1. **Starting a session**: Use `memory_search` to retrieve relevant context
2. **Before implementing**: Use `find_duplicates` and `code_search`
3. **After implementing**: Use `memory_add` to record key decisions
4. **End of session**: Use `memory_add` for session summary
```

## Detailed Integration Template

Copy this full template to your `CLAUDE.md`:

```markdown
---

## Memory Service

This project uses the Claude Code Memory Service for:
- Persistent context across sessions
- Duplicate code detection
- Design alignment verification
- Requirements traceability

### Tool Usage Guide

#### Session Management

**At session start:**
```
Use memory_search to find relevant context:
- Previous session summaries
- Related requirements
- Applicable patterns
```

**At session end:**
```
Use memory_add with memory_type="session" to record:
- What was accomplished
- Key decisions made
- Open questions
```

#### Before Writing Code

**Check for existing patterns:**
```json
{
  "tool": "code_search",
  "query": "description of what you're about to implement",
  "language": "python"
}
```

**Check for duplicates:**
```json
{
  "tool": "find_duplicates",
  "code": "def function_signature(...)",
  "threshold": 0.85
}
```

**Get design context:**
```json
{
  "tool": "get_design_context",
  "query": "feature or component description"
}
```

#### During Implementation

**Validate fix alignment:**
```json
{
  "tool": "validate_fix",
  "fix_description": "Description of the fix",
  "affected_component": "component-name"
}
```

**Check consistency:**
```json
{
  "tool": "check_consistency",
  "component_id": "component-uuid"
}
```

#### After Changes

**Record design decisions:**
```json
{
  "tool": "memory_add",
  "memory_type": "design",
  "content": "Decision description",
  "metadata": {
    "design_type": "ADR",
    "title": "ADR-XXX: Decision Title",
    "decision": "What was decided",
    "rationale": "Why it was decided"
  }
}
```

**Record new patterns:**
```json
{
  "tool": "memory_add",
  "memory_type": "code_pattern",
  "content": "Pattern description",
  "metadata": {
    "pattern_name": "Pattern Name",
    "pattern_type": "Template",
    "language": "Python",
    "code_template": "def example():\n    pass",
    "usage_context": "When to use this pattern"
  }
}
```

### When to Use Each Memory Type

| Type | Store When... |
|------|---------------|
| `requirements` | New requirement defined or clarified |
| `design` | Architectural decision made (ADR) |
| `code_pattern` | Reusable pattern identified |
| `component` | New component created |
| `function` | *Automatic via indexing* |
| `test_history` | *Automatic via test runner* |
| `session` | End of development session |
| `user_preference` | User preference expressed |

### Example Session Workflow

```
1. User: "Implement user authentication"

2. Claude actions:
   - memory_search: "user authentication requirements patterns"
   - get_design_context: "authentication"
   - code_search: "authentication login password"
   - find_duplicates: (for proposed functions)

3. Implementation...

4. Claude actions:
   - memory_add: Record ADR if new decision
   - memory_add: Record session summary
```

### Indexing Workflow

When significant code changes are made:

```json
{
  "tool": "index_directory",
  "directory_path": "src/",
  "extensions": [".py", ".ts"],
  "force": false
}
```

For new files:
```json
{
  "tool": "index_file",
  "file_path": "src/new_module.py"
}
```

### Maintenance Commands

| Command | Purpose |
|---------|---------|
| `memory_statistics` | View system health |
| `normalize_memory` | Clean up duplicates, orphans |
| `export_memory` | Backup memories |
| `import_memory` | Restore from backup |

---
```

## Usage Patterns

### Pattern 1: Context-Aware Implementation

Before implementing any feature:

```
1. Search for related memories
2. Find similar existing code
3. Check for duplicates
4. Get design context
5. Implement with awareness of existing patterns
6. Record new decisions
```

### Pattern 2: Design Validation

When proposing changes:

```
1. Use validate_fix with description
2. Review alignment scores
3. Check related requirements
4. Proceed if alignment > 0.7
5. If low alignment, review design docs first
```

### Pattern 3: Requirements Traceability

When implementing requirements:

```
1. Use trace_requirements with REQ-ID
2. Note existing implementations
3. Note existing tests
4. Ensure new code connects to requirement
5. Update test coverage
```

### Pattern 3: Session Continuity

At end of each session:

```json
{
  "tool": "memory_add",
  "memory_type": "session",
  "content": "Summary of work done and state left in",
  "metadata": {
    "summary": "Implemented feature X, fixed bug Y",
    "key_decisions": [
      "Chose approach A over B because...",
      "Deferred Z to next session"
    ],
    "files_modified": [
      "src/feature_x.py",
      "tests/test_feature_x.py"
    ],
    "open_questions": [
      "Need to review performance of..."
    ]
  }
}
```

## Relationship Types

When creating memories, link them appropriately:

| Relationship | From → To |
|--------------|-----------|
| `SATISFIES` | Component → Requirement |
| `IMPLEMENTS` | Function → Design |
| `FOLLOWS_PATTERN` | Code → Pattern |
| `TESTED_BY` | Requirement → Test |
| `CALLS` | Function → Function |
| `IMPORTS` | Module → Module |
| `EXTENDS` | Class → Class |

Example with relationship:

```json
{
  "tool": "memory_add",
  "memory_type": "component",
  "content": "AuthService - Handles user authentication",
  "metadata": {...},
  "relationships": [
    {
      "target_id": "req-auth-001-uuid",
      "type": "SATISFIES"
    }
  ]
}
```

## Tips

1. **Search before adding**: Always search first to avoid duplicates
2. **Be specific**: Include enough context in content for good embedding
3. **Use metadata**: Structure information in type-specific fields
4. **Link memories**: Create relationships for traceability
5. **Session summaries**: Always create on significant milestones
6. **Index regularly**: Keep function index current with changes
