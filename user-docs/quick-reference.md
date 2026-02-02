# Memory Service Quick Reference

**Purpose:** This is a *development-time* memory service for Claude Code. It stores project context, design decisions, and code patterns to help Claude maintain continuity across coding sessions. This is NOT runtime memory for your application—it's tooling that helps Claude build your application better.

**Use cases:**
- Remember architectural decisions (ADRs) across sessions
- Detect duplicate code before implementing
- Track requirements and their implementations
- Index codebase for semantic code search

**Project Isolation:** Data is isolated per `PROJECT_ID`. Each project gets its own namespaced collections and filtered graph data.

All 25 MCP tools organized by category.

---

## Memory CRUD (5 tools)

### memory_add
Create a new memory.
```json
{"memory_type": "design", "content": "ADR: Use JWT auth", "metadata": {"title": "ADR-001"}}
```
| Param | Required | Description |
|-------|----------|-------------|
| memory_type | Yes | `requirements`, `design`, `code_pattern`, `component`, `function`, `test_history`, `session`, `user_preference` |
| content | Yes | Primary content (max 100KB) |
| metadata | No | Type-specific fields |
| relationships | No | Links to other memories |

### memory_get
Retrieve a memory by ID.
```json
{"memory_id": "uuid", "memory_type": "design", "include_relationships": true}
```

### memory_update
Update an existing memory.
```json
{"memory_id": "uuid", "memory_type": "design", "metadata": {"status": "Implemented"}}
```

### memory_delete
Delete a memory (soft delete by default).
```json
{"memory_id": "uuid", "memory_type": "design", "hard_delete": false}
```

### memory_bulk_add
Add multiple memories in batch.
```json
{"memories": [{"memory_type": "requirements", "content": "..."}, ...]}
```

---

## Search (5 tools)

### memory_search
Semantic search across memories.
```json
{"query": "authentication patterns", "memory_types": ["design", "code_pattern"], "limit": 5}
```
| Param | Required | Description |
|-------|----------|-------------|
| query | Yes | Natural language search |
| memory_types | No | Filter by types |
| time_range | No | `{"start": "ISO", "end": "ISO"}` |
| limit | No | Max results (default: 10) |

### code_search
Find similar code patterns.
```json
{"query": "validate user input async", "language": "python", "limit": 5}
```

### find_duplicates
Check if similar function already exists.
```json
{"code": "def process_data(input: str):", "language": "python", "threshold": 0.85}
```
| Param | Required | Description |
|-------|----------|-------------|
| code | Yes | Code to check |
| language | No | Language filter |
| threshold | No | Similarity 0.70-0.95 (default: 0.85) |

### get_related
Get entities related by graph relationships.
```json
{"entity_id": "uuid", "relationship_types": ["CALLS", "IMPORTS"], "direction": "both", "depth": 2}
```

### graph_query
Execute read-only Cypher query.
```json
{"cypher": "MATCH (f:Function)-[:CALLS]->(g) WHERE f.name = $name RETURN g", "parameters": {"name": "main"}}
```

---

## Indexing (4 tools)

### index_file
Index a single source file.
```json
{"file_path": "src/module.py", "force": false}
```

### index_directory
Index a directory recursively.
```json
{"directory_path": "src/", "extensions": [".py", ".ts"], "exclude": ["**/test/**"], "force": false}
```

### index_status
Get indexing job status.
```json
{"job_id": "uuid"}
```
*Omit job_id for overall statistics.*

### reindex
Trigger codebase reindexing.
```json
{"directory_path": "src/", "scope": "changed", "extensions": [".py"]}
```
| Param | Required | Description |
|-------|----------|-------------|
| directory_path | Yes | Directory to reindex |
| scope | No | `full` (clear first) or `changed` (default) |

---

## Analysis (4 tools)

### get_design_context
Get ADRs/patterns for a feature or component.
```json
{"query": "user authentication"}
```
*Or use `component_id` instead of `query`.*

### check_consistency
Verify component follows established patterns.
```json
{"component_id": "uuid", "pattern_types": ["Template", "Convention"]}
```
Returns: `consistency_score`, `matching_patterns`, `potential_deviations`

### validate_fix
Validate proposed fix aligns with design.
```json
{"fix_description": "Add rate limiting to auth endpoint", "affected_component": "AuthService"}
```
Returns: `design_alignment_score`, `requirements_alignment_score`, `recommendation`

### trace_requirements
Trace requirement to implementations and tests.
```json
{"requirement_id": "REQ-AUTH-001"}
```
Returns: `implementing_components`, `verifying_tests`, `coverage`

---

## Maintenance (5 tools)

### memory_statistics
Get system health and counts.
```json
{}
```
Returns: `memory_counts`, `sync_status`, `storage`, `cache`

### normalize_memory
Run normalization (dedup, cleanup).
```json
{"phases": ["deduplication", "orphan_detection"], "dry_run": true}
```
| Phases | Description |
|--------|-------------|
| snapshot | Create backup |
| deduplication | Remove duplicates |
| orphan_detection | Find orphaned nodes |
| embedding_refresh | Regenerate embeddings |
| cleanup | Remove soft-deleted |
| validation | Verify integrity |

### normalize_status
Get normalization job status.
```json
{"job_id": "uuid"}
```

### export_memory
Export memories to JSONL.
```json
{"memory_types": ["design", "requirements"], "output_path": "backup.jsonl"}
```

### import_memory
Import from JSONL.
```json
{"input_path": "backup.jsonl", "conflict_resolution": "skip"}
```
| conflict_resolution | Description |
|---------------------|-------------|
| skip | Skip duplicates (default) |
| overwrite | Replace existing |
| error | Fail on duplicate |

---

## Memory Types

| Type | Key Metadata Fields |
|------|---------------------|
| `requirements` | `requirement_id`, `title`, `priority`, `status` |
| `design` | `design_type`, `title`, `decision`, `rationale` |
| `code_pattern` | `pattern_name`, `pattern_type`, `code_template`, `language` |
| `component` | `component_id`, `component_type`, `file_path` |
| `function` | `name`, `signature`, `file_path`, `start_line` |
| `test_history` | `test_name`, `test_file`, `status` |
| `session` | `session_id`, `summary`, `key_decisions`, `files_modified` |
| `user_preference` | `category`, `key`, `value`, `scope` |

## Relationship Types

| Type | Usage |
|------|-------|
| `SATISFIES` | Component -> Requirement |
| `IMPLEMENTS` | Function -> Design |
| `FOLLOWS_PATTERN` | Code -> Pattern |
| `TESTED_BY` | Requirement -> Test |
| `CALLS` | Function -> Function |
| `IMPORTS` | Module -> Module |
| `EXTENDS` | Class -> Class |
| `ADDRESSES` | Design -> Requirement |

---

## Project Management (2 tools)

### set_project
**REQUIRED at session start.** Switch to a project context for data isolation.
```json
{"project_id": "my-project-name"}
```
| Param | Required | Description |
|-------|----------|-------------|
| project_id | Yes | Unique identifier (lowercase alphanumeric + hyphens) |

### get_project
Get current project context.
```json
{}
```
Returns: `project_id`, `qdrant_collection_prefix`, `example_collections`

---

## Workflow Summary

| When | Tools |
|------|-------|
| Session start | **`set_project`** (required!), then `memory_search` for context |
| Before coding | `code_search`, `find_duplicates`, `get_design_context` |
| During coding | `validate_fix`, `check_consistency` |
| After coding | `memory_add` (design/session), `index_file` |
| Maintenance | `memory_statistics`, `normalize_memory`, `export_memory` |

---

Full documentation: [API Reference](api-reference.md) | [Integration Template](integration-template.md)
