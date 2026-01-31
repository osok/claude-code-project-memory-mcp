# Claude Code Memory Service - API Reference

This document provides complete reference documentation for all 23 MCP tools provided by the Claude Code Memory Service.

## Overview

The Memory Service provides tools for persistent memory management across development sessions:

| Category | Tools | Purpose |
|----------|-------|---------|
| Memory CRUD | 5 | Create, read, update, delete memories |
| Search | 5 | Semantic search and duplicate detection |
| Indexing | 4 | Codebase parsing and indexing |
| Analysis | 4 | Design consistency and traceability |
| Maintenance | 5 | Normalization and backup |

---

## Memory CRUD Tools

### memory_add

Add a new memory to the system.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| memory_type | string | Yes | One of: `requirements`, `design`, `code_pattern`, `component`, `function`, `test_history`, `session`, `user_preference` |
| content | string | Yes | Primary content for embedding (max 100KB) |
| metadata | object | No | Type-specific metadata fields |
| relationships | array | No | Relationships to create |

**Example:**

```json
{
  "memory_type": "requirements",
  "content": "The system shall support semantic search with sub-200ms latency",
  "metadata": {
    "requirement_id": "REQ-MEM-FN-001",
    "title": "Search Latency",
    "priority": "High",
    "status": "Approved"
  }
}
```

**Returns:**

```json
{
  "memory_id": "550e8400-e29b-41d4-a716-446655440000",
  "memory_type": "requirements",
  "conflicts": [],
  "status": "created"
}
```

---

### memory_update

Update an existing memory.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| memory_id | string | Yes | UUID of the memory |
| memory_type | string | Yes | Type of memory |
| content | string | No | New content (triggers embedding regeneration) |
| metadata | object | No | Fields to update |

**Example:**

```json
{
  "memory_id": "550e8400-e29b-41d4-a716-446655440000",
  "memory_type": "requirements",
  "metadata": {
    "status": "Implemented"
  }
}
```

---

### memory_delete

Delete a memory (soft delete by default).

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| memory_id | string | Yes | UUID of the memory |
| memory_type | string | Yes | Type of memory |
| hard_delete | boolean | No | If true, permanently delete (default: false) |

---

### memory_get

Retrieve a memory by ID.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| memory_id | string | Yes | UUID of the memory |
| memory_type | string | Yes | Type of memory |
| include_relationships | boolean | No | Include related memories (default: false) |

---

### memory_bulk_add

Add multiple memories in batch.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| memories | array | Yes | Array of memory objects (each with memory_type and content) |

**Returns:**

```json
{
  "added_count": 10,
  "added_ids": ["...", "..."],
  "errors": []
}
```

---

## Search Tools

### memory_search

Search memories using semantic similarity.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| query | string | Yes | Natural language search query |
| memory_types | array | No | Filter by memory types |
| time_range | object | No | Filter by time `{"start": "ISO", "end": "ISO"}` |
| limit | integer | No | Maximum results (default: 10) |

**Example:**

```json
{
  "query": "authentication implementation",
  "memory_types": ["design", "requirements"],
  "limit": 5
}
```

**Returns:**

```json
{
  "query": "authentication implementation",
  "result_count": 3,
  "results": [
    {
      "id": "...",
      "memory_type": "design",
      "content": "...",
      "score": 0.8542,
      "metadata": {...}
    }
  ]
}
```

---

### code_search

Search for similar code patterns.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| query | string | Yes | Code snippet or description |
| language | string | No | Programming language filter |
| limit | integer | No | Maximum results (default: 10) |

**Example:**

```json
{
  "query": "async function that validates user input",
  "language": "python",
  "limit": 5
}
```

---

### graph_query

Execute a Cypher graph query (read-only operations only).

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| cypher | string | Yes | Cypher query (no mutating operations) |
| parameters | object | No | Query parameters |

**Example:**

```json
{
  "cypher": "MATCH (f:Function)-[:CALLS]->(g:Function) WHERE f.name = $name RETURN g",
  "parameters": {"name": "process_data"}
}
```

---

### find_duplicates

Find duplicate functions or code patterns.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| code | string | Yes | Code to check for duplicates |
| language | string | No | Programming language filter |
| threshold | float | No | Similarity threshold 0.70-0.95 (default: 0.85) |

**Example:**

```json
{
  "code": "def process_data(input: str, options: dict) -> Result: ...",
  "language": "python",
  "threshold": 0.85
}
```

**Returns:**

```json
{
  "threshold": 0.85,
  "duplicate_count": 2,
  "duplicates": [
    {
      "id": "...",
      "name": "process_data",
      "file_path": "src/processor.py",
      "similarity": 0.92
    }
  ]
}
```

---

### get_related

Get entities related by graph relationships.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| entity_id | string | Yes | Starting entity ID |
| relationship_types | array | No | Filter by relationship types: `CALLS`, `IMPORTS`, `EXTENDS`, etc. |
| direction | string | No | `outgoing`, `incoming`, or `both` (default: `both`) |
| depth | integer | No | Traversal depth 1-5 (default: 1) |

---

## Indexing Tools

### index_file

Index a single source file.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| file_path | string | Yes | Path to file (must be within project) |
| force | boolean | No | Force re-index even if unchanged |

**Returns:**

```json
{
  "status": "indexed",
  "file_path": "src/module.py",
  "functions_extracted": 5,
  "classes_extracted": 2,
  "imports_extracted": 10
}
```

---

### index_directory

Index a directory recursively.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| directory_path | string | Yes | Path to directory |
| extensions | array | No | File extensions to include (e.g., `[".py", ".ts"]`) |
| exclude | array | No | Patterns to exclude |
| force | boolean | No | Force re-index all files |

---

### index_status

Get indexing job status or overall statistics.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| job_id | string | No | Specific job ID (returns overall stats if not provided) |

---

### reindex

Trigger reindexing of the codebase.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| directory_path | string | Yes | Directory to reindex |
| scope | string | No | `full` (clear first) or `changed` (incremental, default) |
| extensions | array | No | File extensions to include |
| exclude | array | No | Patterns to exclude |

---

## Analysis Tools

### check_consistency

Check if a component follows established patterns.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| component_id | string | Yes | Component to check |
| pattern_types | array | No | Types to check: `Template`, `Convention` (default: both) |

**Returns:**

```json
{
  "component_id": "...",
  "matching_patterns": [...],
  "potential_deviations": [...],
  "consistency_score": 0.85
}
```

---

### validate_fix

Validate that a proposed fix aligns with design.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| fix_description | string | Yes | Description of the proposed fix |
| affected_component | string | No | Component being fixed |

**Returns:**

```json
{
  "design_alignment_score": 0.82,
  "requirements_alignment_score": 0.75,
  "overall_alignment_score": 0.79,
  "related_designs": [...],
  "related_requirements": [...],
  "recommendation": "Fix aligns well with design"
}
```

---

### get_design_context

Get design context for a component or feature.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| component_id | string | Conditional | Component to get context for |
| query | string | Conditional | Description of feature/area |

*One of `component_id` or `query` is required.*

---

### trace_requirements

Trace a requirement to its implementations and tests.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| requirement_id | string | Yes | Requirement ID (e.g., `REQ-MEM-FN-001`) |

**Returns:**

```json
{
  "requirement": {...},
  "implementing_components": [...],
  "verifying_tests": [...],
  "related_designs": [...],
  "coverage": {
    "implementation_count": 3,
    "test_count": 5,
    "design_count": 1
  }
}
```

---

## Maintenance Tools

### normalize_memory

Start a normalization job.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| phases | array | No | Specific phases: `snapshot`, `deduplication`, `orphan_detection`, `embedding_refresh`, `cleanup`, `validation`, `swap` |
| dry_run | boolean | No | Report changes without applying (default: false) |

---

### normalize_status

Get normalization job status.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| job_id | string | No | Job ID (returns overall status if not provided) |

---

### memory_statistics

Get comprehensive memory system statistics.

**Parameters:** None required.

**Returns:**

```json
{
  "memory_counts": {
    "requirements": {"total": 50, "active": 48, "deleted": 2},
    "function": {"total": 1000, "active": 980, "deleted": 20}
  },
  "sync_status": {
    "synced": 1000,
    "pending": 5,
    "failed": 0
  },
  "storage": {
    "qdrant": {"connected": true},
    "neo4j": {"connected": true}
  },
  "cache": {
    "entries": 500,
    "hit_rate": 0.85
  }
}
```

---

### export_memory

Export memories to JSONL format.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| memory_types | array | No | Types to export (default: all) |
| filters | object | No | Additional filters |
| output_path | string | No | Path to write export (must be within project) |

---

### import_memory

Import memories from JSONL format.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| input_path | string | Conditional | Path to JSONL file |
| data | string | Conditional | JSONL data as string |
| conflict_resolution | string | No | `skip`, `overwrite`, or `error` (default: `skip`) |

*One of `input_path` or `data` is required.*

---

## Memory Types

| Type | Description | Key Fields |
|------|-------------|------------|
| `requirements` | Project requirements | `requirement_id`, `title`, `priority`, `status` |
| `design` | ADRs and design decisions | `design_type`, `title`, `decision`, `rationale` |
| `code_pattern` | Reusable code patterns | `pattern_name`, `pattern_type`, `code_template` |
| `component` | System components | `component_id`, `component_type`, `file_path` |
| `function` | Indexed functions | `name`, `signature`, `file_path`, `start_line` |
| `test_history` | Test execution history | `test_name`, `test_file`, `status` |
| `session` | Development sessions | `session_id`, `summary`, `key_decisions` |
| `user_preference` | User preferences | `category`, `key`, `value`, `scope` |

---

## Relationship Types

| Type | Description |
|------|-------------|
| `CALLS` | Function calls another function |
| `IMPORTS` | Module imports another module |
| `EXTENDS` | Class extends another class |
| `IMPLEMENTS` | Class implements interface |
| `SATISFIES` | Component satisfies requirement |
| `FOLLOWS_PATTERN` | Code follows pattern |
| `TESTED_BY` | Requirement tested by test |
| `ADDRESSES` | Design addresses requirement |

---

## Error Handling

All tools return errors in a consistent format:

```json
{
  "error": "Error message describing what went wrong"
}
```

Common errors:
- `"Memory not found"` - Invalid memory ID
- `"Unknown memory type"` - Invalid memory type value
- `"Path must be within project directory"` - Path traversal attempt
- `"Threshold must be between 0.70 and 0.95"` - Invalid parameter range
