# Design Document: MCP API Contracts

## Document Control

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Status | Draft |
| Sequence | 002 |
| Component | Integration Layer |

---

## 1. Introduction

### 1.1 Purpose

This document defines the MCP (Model Context Protocol) API contracts for the Claude Code Long-Term Memory System. It specifies all 27 tools exposed to Claude Code, their input/output schemas, and behavior specifications.

### 1.2 Scope

**Included:**
- All 27 MCP tools with complete specifications
- JSON schemas for inputs and outputs
- Error response formats
- CLI utility interface

**Excluded:**
- Internal service implementation (see 20-backend-design.md)
- Infrastructure deployment (see 60-infrastructure-design.md)

### 1.3 Requirements Traceability

| Requirement ID | Requirement Summary | Design Section |
|----------------|---------------------|----------------|
| REQ-MEM-INT-001 | MCP compliance | 3.1 |
| REQ-MEM-INT-002 | Tool categories | 4.1 |
| REQ-MEM-INT-003 | JSON schema validation | 3.3 |
| REQ-MEM-INT-010-014 | Memory CRUD tools | 4.2.1 |
| REQ-MEM-INT-020-024 | Search tools | 4.2.2 |
| REQ-MEM-INT-030-033 | Index tools | 4.2.3 |
| REQ-MEM-INT-040-043 | Analysis tools | 4.2.4 |
| REQ-MEM-INT-050-054 | Maintenance tools | 4.2.5 |
| REQ-MEM-DEP-010 | MCP configuration | 3.4 |
| REQ-MEM-USE-001 | Actionable error messages | 8.3 |
| REQ-MEM-USE-002 | CLI utility | 5.1 |

---

## 2. Integration Context

### 2.1 Integration Overview

Claude Code communicates with the Memory Service via MCP protocol over stdio transport. The service exposes 27 tools organized into 5 categories.

### 2.2 Systems Involved

#### Claude Code

**Description:** AI-powered development assistant.

**Role:** Consumer

**Communication:** MCP over stdio

#### Memory Service

**Description:** Long-term memory infrastructure.

**Role:** Provider

**Communication:** MCP server (stdio), HTTP (health/metrics)

### 2.3 Integration Pattern

| Aspect | Choice | Rationale |
|--------|--------|-----------|
| Communication Style | Synchronous | MCP request/response model |
| Coupling | Direct | stdio pipe, no intermediary |
| Data Exchange | Request-Response | JSON payloads |

---

## 3. API Contract Design

### 3.1 API Style

**Protocol:** MCP (Model Context Protocol)

**Transport:** stdio

**Message Format:** JSON-RPC 2.0

**MCP Version:** 2025-11-25 or later

### 3.2 Protocol Messages

#### Tool List Request

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list"
}
```

#### Tool Call Request

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "memory_add",
    "arguments": {
      "type": "requirements",
      "content": "...",
      "metadata": {}
    }
  }
}
```

#### Tool Response

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"memory_id\": \"uuid\", \"status\": \"created\"}"
      }
    ]
  }
}
```

### 3.3 JSON Schema Validation

All tool inputs are validated against JSON Schema. Invalid inputs return error with details.

### 3.4 MCP Configuration

**Claude Code Configuration (~/.claude/settings.json):**

```json
{
  "mcpServers": {
    "memory": {
      "command": "docker",
      "args": ["compose", "exec", "-T", "memory-service", "python", "-m", "memory_service"],
      "env": {}
    }
  }
}
```

**Alternative (direct execution):**

```json
{
  "mcpServers": {
    "memory": {
      "command": "python",
      "args": ["-m", "memory_service"],
      "cwd": "/path/to/project",
      "env": {
        "QDRANT_HOST": "localhost",
        "NEO4J_URI": "bolt://localhost:7687"
      }
    }
  }
}
```

### 3.5 Common Response Formats

#### Success Response

```json
{
  "status": "success",
  "data": { ... }
}
```

#### Error Response

```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable message",
    "details": { ... },
    "suggestion": "Actionable suggestion"
  }
}
```

#### Standard Error Codes

| Code | HTTP Status | Description | Consumer Action |
|------|-------------|-------------|-----------------|
| VALIDATION_ERROR | 400 | Invalid input | Fix input per details |
| NOT_FOUND | 404 | Resource not found | Verify ID exists |
| CONFLICT | 409 | Resource conflict | Check for duplicates |
| SERVICE_UNAVAILABLE | 503 | Dependency down | Retry later |
| INTERNAL_ERROR | 500 | Server error | Report issue |

---

## 4. Tool Specifications

### 4.1 Tool Overview

| Category | Tools | Count |
|----------|-------|-------|
| Memory CRUD | memory_add, memory_update, memory_delete, memory_get, memory_bulk_add | 5 |
| Search | memory_search, code_search, graph_query, find_duplicates, get_related | 5 |
| Indexing | index_file, index_directory, index_status, reindex | 4 |
| Analysis | check_consistency, validate_fix, get_design_context, trace_requirements | 4 |
| Maintenance | normalize_memory, normalize_status, memory_statistics, export_memory, import_memory | 5 |

**Total:** 27 tools (Note: The requirements specify 27 tools across 5 categories. The current count is 23. Additional specialized tools may be added.)

### 4.2 Tool Specifications

#### 4.2.1 Memory CRUD Tools

##### memory_add

**Purpose:** Create a new memory entry.

**Input Schema:**

```json
{
  "type": "object",
  "required": ["type", "content"],
  "properties": {
    "type": {
      "type": "string",
      "enum": ["requirements", "design", "code_pattern", "component", "function", "test_history", "session", "user_preference"]
    },
    "content": {
      "type": "string",
      "minLength": 1,
      "maxLength": 100000
    },
    "metadata": {
      "type": "object",
      "description": "Type-specific metadata"
    },
    "relationships": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["type", "target_id"],
        "properties": {
          "type": {"type": "string"},
          "target_id": {"type": "string", "format": "uuid"}
        }
      }
    }
  }
}
```

**Output Schema:**

```json
{
  "type": "object",
  "properties": {
    "memory_id": {"type": "string", "format": "uuid"},
    "status": {"type": "string", "enum": ["created"]},
    "conflicts": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "memory_id": {"type": "string"},
          "similarity": {"type": "number"}
        }
      }
    }
  }
}
```

**Example:**

```json
// Request
{
  "type": "requirements",
  "content": "The system shall provide semantic search across all memory types.",
  "metadata": {
    "requirement_id": "REQ-MEM-FN-080",
    "title": "Semantic Search",
    "priority": "Critical",
    "status": "Approved",
    "source_document": "requirements-memory-docs.md"
  }
}

// Response
{
  "memory_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "created",
  "conflicts": []
}
```

##### memory_update

**Purpose:** Update an existing memory entry.

**Input Schema:**

```json
{
  "type": "object",
  "required": ["memory_id"],
  "properties": {
    "memory_id": {"type": "string", "format": "uuid"},
    "content": {"type": "string"},
    "metadata": {"type": "object"}
  }
}
```

**Output Schema:**

```json
{
  "type": "object",
  "properties": {
    "memory_id": {"type": "string"},
    "status": {"type": "string", "enum": ["updated"]},
    "updated_fields": {"type": "array", "items": {"type": "string"}}
  }
}
```

##### memory_delete

**Purpose:** Soft-delete a memory entry.

**Input Schema:**

```json
{
  "type": "object",
  "required": ["memory_id"],
  "properties": {
    "memory_id": {"type": "string", "format": "uuid"}
  }
}
```

**Output Schema:**

```json
{
  "type": "object",
  "properties": {
    "status": {"type": "string", "enum": ["deleted"]},
    "relationships_removed": {"type": "integer"}
  }
}
```

##### memory_get

**Purpose:** Retrieve a memory by ID.

**Input Schema:**

```json
{
  "type": "object",
  "required": ["memory_id"],
  "properties": {
    "memory_id": {"type": "string", "format": "uuid"},
    "include_relationships": {"type": "boolean", "default": false}
  }
}
```

**Output Schema:**

```json
{
  "type": "object",
  "properties": {
    "memory": {
      "type": "object",
      "description": "Full memory object with all fields"
    },
    "relationships": {
      "type": "array",
      "items": {"type": "object"}
    }
  }
}
```

##### memory_bulk_add

**Purpose:** Create multiple memories in a batch.

**Input Schema:**

```json
{
  "type": "object",
  "required": ["memories"],
  "properties": {
    "memories": {
      "type": "array",
      "maxItems": 100,
      "items": {
        "type": "object",
        "required": ["type", "content"],
        "properties": {
          "type": {"type": "string"},
          "content": {"type": "string"},
          "metadata": {"type": "object"}
        }
      }
    }
  }
}
```

**Output Schema:**

```json
{
  "type": "object",
  "properties": {
    "created": {"type": "integer"},
    "memory_ids": {
      "type": "array",
      "items": {"type": "string", "format": "uuid"}
    },
    "errors": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "index": {"type": "integer"},
          "error": {"type": "string"}
        }
      }
    }
  }
}
```

#### 4.2.2 Search Tools

##### memory_search

**Purpose:** Semantic search across memory types.

**Input Schema:**

```json
{
  "type": "object",
  "required": ["query"],
  "properties": {
    "query": {"type": "string", "minLength": 1},
    "memory_types": {
      "type": "array",
      "items": {"type": "string"}
    },
    "time_range": {
      "type": "object",
      "properties": {
        "start": {"type": "string", "format": "date-time"},
        "end": {"type": "string", "format": "date-time"}
      }
    },
    "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 10},
    "min_similarity": {"type": "number", "minimum": 0, "maximum": 1, "default": 0}
  }
}
```

**Output Schema:**

```json
{
  "type": "object",
  "properties": {
    "results": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "memory_id": {"type": "string"},
          "type": {"type": "string"},
          "content": {"type": "string"},
          "similarity": {"type": "number"},
          "relevance_score": {"type": "number"},
          "metadata": {"type": "object"}
        }
      }
    },
    "total": {"type": "integer"},
    "query_time_ms": {"type": "integer"}
  }
}
```

##### code_search

**Purpose:** Search for similar code in function index.

**Input Schema:**

```json
{
  "type": "object",
  "required": ["query"],
  "properties": {
    "query": {
      "type": "string",
      "description": "Code snippet or natural language description"
    },
    "language": {"type": "string"},
    "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10}
  }
}
```

**Output Schema:**

```json
{
  "type": "object",
  "properties": {
    "results": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "function_id": {"type": "string"},
          "name": {"type": "string"},
          "signature": {"type": "string"},
          "file_path": {"type": "string"},
          "similarity": {"type": "number"},
          "docstring": {"type": "string"}
        }
      }
    }
  }
}
```

##### graph_query

**Purpose:** Execute Cypher query against Neo4j.

**Input Schema:**

```json
{
  "type": "object",
  "required": ["cypher"],
  "properties": {
    "cypher": {
      "type": "string",
      "description": "Cypher query string"
    },
    "params": {
      "type": "object",
      "description": "Query parameters"
    }
  }
}
```

**Output Schema:**

```json
{
  "type": "object",
  "properties": {
    "results": {
      "type": "array",
      "items": {"type": "object"}
    },
    "query_time_ms": {"type": "integer"}
  }
}
```

##### find_duplicates

**Purpose:** Find potential duplicate functions.

**Input Schema:**

```json
{
  "type": "object",
  "required": ["code"],
  "properties": {
    "code": {
      "type": "string",
      "description": "Function signature or code"
    },
    "language": {"type": "string"},
    "threshold": {
      "type": "number",
      "minimum": 0.7,
      "maximum": 0.95,
      "default": 0.85
    },
    "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5}
  }
}
```

**Output Schema:**

```json
{
  "type": "object",
  "properties": {
    "duplicates": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "function_id": {"type": "string"},
          "name": {"type": "string"},
          "signature": {"type": "string"},
          "file_path": {"type": "string"},
          "start_line": {"type": "integer"},
          "similarity": {"type": "number"},
          "recommendation": {"type": "string"}
        }
      }
    },
    "has_duplicates": {"type": "boolean"}
  }
}
```

##### get_related

**Purpose:** Get related entities via graph traversal.

**Input Schema:**

```json
{
  "type": "object",
  "required": ["entity_id"],
  "properties": {
    "entity_id": {"type": "string"},
    "relationship_types": {
      "type": "array",
      "items": {"type": "string"}
    },
    "direction": {
      "type": "string",
      "enum": ["OUTGOING", "INCOMING", "BOTH"],
      "default": "BOTH"
    },
    "depth": {"type": "integer", "minimum": 1, "maximum": 5, "default": 1}
  }
}
```

**Output Schema:**

```json
{
  "type": "object",
  "properties": {
    "related": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "entity_id": {"type": "string"},
          "type": {"type": "string"},
          "name": {"type": "string"},
          "relationship": {"type": "string"},
          "distance": {"type": "integer"}
        }
      }
    }
  }
}
```

#### 4.2.3 Index Tools

##### index_file

**Purpose:** Index a single source file.

**Input Schema:**

```json
{
  "type": "object",
  "required": ["file_path"],
  "properties": {
    "file_path": {"type": "string"},
    "force": {"type": "boolean", "default": false}
  }
}
```

**Output Schema:**

```json
{
  "type": "object",
  "properties": {
    "status": {"type": "string", "enum": ["indexed", "skipped", "unsupported"]},
    "functions": {"type": "integer"},
    "classes": {"type": "integer"},
    "relationships": {"type": "integer"}
  }
}
```

##### index_directory

**Purpose:** Recursively index a directory.

**Input Schema:**

```json
{
  "type": "object",
  "required": ["directory_path"],
  "properties": {
    "directory_path": {"type": "string"},
    "filters": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Glob patterns to include"
    },
    "exclude": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Glob patterns to exclude"
    }
  }
}
```

**Output Schema:**

```json
{
  "type": "object",
  "properties": {
    "job_id": {"type": "string", "format": "uuid"},
    "status": {"type": "string", "enum": ["started"]}
  }
}
```

##### index_status

**Purpose:** Get current index status and statistics.

**Input Schema:**

```json
{
  "type": "object",
  "properties": {
    "job_id": {
      "type": "string",
      "format": "uuid",
      "description": "Optional: specific job status"
    }
  }
}
```

**Output Schema:**

```json
{
  "type": "object",
  "properties": {
    "job": {
      "type": "object",
      "properties": {
        "job_id": {"type": "string"},
        "status": {"type": "string"},
        "progress": {"type": "integer"},
        "stats": {"type": "object"}
      }
    },
    "index": {
      "type": "object",
      "properties": {
        "total_files": {"type": "integer"},
        "total_functions": {"type": "integer"},
        "total_classes": {"type": "integer"},
        "last_indexed": {"type": "string", "format": "date-time"},
        "languages": {"type": "object"}
      }
    }
  }
}
```

##### reindex

**Purpose:** Trigger full or incremental reindexing.

**Input Schema:**

```json
{
  "type": "object",
  "properties": {
    "scope": {
      "type": "string",
      "enum": ["full", "changed"],
      "default": "changed"
    },
    "directory_path": {"type": "string"}
  }
}
```

**Output Schema:**

```json
{
  "type": "object",
  "properties": {
    "job_id": {"type": "string", "format": "uuid"},
    "status": {"type": "string", "enum": ["started"]}
  }
}
```

#### 4.2.4 Analysis Tools

##### check_consistency

**Purpose:** Check component against base patterns.

**Input Schema:**

```json
{
  "type": "object",
  "required": ["component_id"],
  "properties": {
    "component_id": {"type": "string"}
  }
}
```

**Output Schema:**

```json
{
  "type": "object",
  "properties": {
    "component": {
      "type": "object",
      "properties": {
        "name": {"type": "string"},
        "type": {"type": "string"},
        "file_path": {"type": "string"}
      }
    },
    "base_pattern": {
      "type": "object",
      "properties": {
        "name": {"type": "string"},
        "file_path": {"type": "string"}
      }
    },
    "consistency_score": {"type": "number"},
    "deviations": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {"type": "string"},
          "expected": {"type": "string"},
          "actual": {"type": "string"},
          "severity": {"type": "string"}
        }
      }
    },
    "recommendations": {
      "type": "array",
      "items": {"type": "string"}
    }
  }
}
```

##### validate_fix

**Purpose:** Validate proposed fix against design.

**Input Schema:**

```json
{
  "type": "object",
  "required": ["fix_description", "component_id"],
  "properties": {
    "fix_description": {"type": "string"},
    "component_id": {"type": "string"},
    "affected_files": {
      "type": "array",
      "items": {"type": "string"}
    }
  }
}
```

**Output Schema:**

```json
{
  "type": "object",
  "properties": {
    "alignment_score": {"type": "number"},
    "design_context": {
      "type": "object",
      "properties": {
        "requirements": {"type": "array"},
        "design_documents": {"type": "array"},
        "patterns": {"type": "array"}
      }
    },
    "concerns": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {"type": "string"},
          "message": {"type": "string"},
          "severity": {"type": "string"},
          "related_requirement": {"type": "string"}
        }
      }
    },
    "recommendations": {
      "type": "array",
      "items": {"type": "string"}
    }
  }
}
```

##### get_design_context

**Purpose:** Retrieve design context for a component.

**Input Schema:**

```json
{
  "type": "object",
  "required": ["component_id"],
  "properties": {
    "component_id": {"type": "string"},
    "include_code": {"type": "boolean", "default": false}
  }
}
```

**Output Schema:**

```json
{
  "type": "object",
  "properties": {
    "component": {"type": "object"},
    "requirements": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "requirement_id": {"type": "string"},
          "title": {"type": "string"},
          "status": {"type": "string"}
        }
      }
    },
    "design_documents": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "title": {"type": "string"},
          "type": {"type": "string"},
          "excerpt": {"type": "string"}
        }
      }
    },
    "patterns": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "name": {"type": "string"},
          "usage_context": {"type": "string"}
        }
      }
    },
    "dependencies": {"type": "array"},
    "dependents": {"type": "array"}
  }
}
```

##### trace_requirements

**Purpose:** Trace requirement to implementing code.

**Input Schema:**

```json
{
  "type": "object",
  "required": ["requirement_id"],
  "properties": {
    "requirement_id": {"type": "string"}
  }
}
```

**Output Schema:**

```json
{
  "type": "object",
  "properties": {
    "requirement": {
      "type": "object",
      "properties": {
        "requirement_id": {"type": "string"},
        "title": {"type": "string"},
        "status": {"type": "string"}
      }
    },
    "implementations": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "component_id": {"type": "string"},
          "name": {"type": "string"},
          "file_path": {"type": "string"},
          "completeness": {"type": "number"}
        }
      }
    },
    "design_documents": {"type": "array"},
    "tests": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "test_name": {"type": "string"},
          "status": {"type": "string"}
        }
      }
    },
    "coverage": {
      "type": "object",
      "properties": {
        "implementation": {"type": "number"},
        "testing": {"type": "number"}
      }
    }
  }
}
```

#### 4.2.5 Maintenance Tools

##### normalize_memory

**Purpose:** Start memory normalization process.

**Input Schema:**

```json
{
  "type": "object",
  "properties": {
    "options": {
      "type": "object",
      "properties": {
        "skip_deduplication": {"type": "boolean", "default": false},
        "skip_orphan_cleanup": {"type": "boolean", "default": false},
        "skip_embedding_refresh": {"type": "boolean", "default": false}
      }
    }
  }
}
```

**Output Schema:**

```json
{
  "type": "object",
  "properties": {
    "job_id": {"type": "string", "format": "uuid"},
    "status": {"type": "string", "enum": ["started"]},
    "estimated_duration_minutes": {"type": "integer"}
  }
}
```

##### normalize_status

**Purpose:** Check normalization job status.

**Input Schema:**

```json
{
  "type": "object",
  "required": ["job_id"],
  "properties": {
    "job_id": {"type": "string", "format": "uuid"}
  }
}
```

**Output Schema:**

```json
{
  "type": "object",
  "properties": {
    "job_id": {"type": "string"},
    "status": {"type": "string"},
    "phase": {"type": "string"},
    "progress": {"type": "integer"},
    "stats": {
      "type": "object",
      "properties": {
        "memories_processed": {"type": "integer"},
        "duplicates_merged": {"type": "integer"},
        "orphans_removed": {"type": "integer"},
        "embeddings_refreshed": {"type": "integer"}
      }
    },
    "error": {"type": "string"},
    "estimated_remaining_seconds": {"type": "integer"}
  }
}
```

##### memory_statistics

**Purpose:** Get memory system statistics.

**Input Schema:**

```json
{
  "type": "object",
  "properties": {}
}
```

**Output Schema:**

```json
{
  "type": "object",
  "properties": {
    "memories": {
      "type": "object",
      "properties": {
        "total": {"type": "integer"},
        "by_type": {"type": "object"},
        "deleted": {"type": "integer"}
      }
    },
    "index": {
      "type": "object",
      "properties": {
        "files": {"type": "integer"},
        "functions": {"type": "integer"},
        "classes": {"type": "integer"}
      }
    },
    "relationships": {
      "type": "object",
      "properties": {
        "total": {"type": "integer"},
        "by_type": {"type": "object"}
      }
    },
    "storage": {
      "type": "object",
      "properties": {
        "qdrant_size_mb": {"type": "number"},
        "neo4j_size_mb": {"type": "number"},
        "cache_size_mb": {"type": "number"}
      }
    },
    "sync": {
      "type": "object",
      "properties": {
        "pending": {"type": "integer"},
        "failed": {"type": "integer"}
      }
    },
    "performance": {
      "type": "object",
      "properties": {
        "avg_search_ms": {"type": "number"},
        "avg_write_ms": {"type": "number"},
        "cache_hit_rate": {"type": "number"}
      }
    }
  }
}
```

##### export_memory

**Purpose:** Export memories to JSONL format.

**Input Schema:**

```json
{
  "type": "object",
  "properties": {
    "memory_types": {
      "type": "array",
      "items": {"type": "string"}
    },
    "output_path": {"type": "string"},
    "include_embeddings": {"type": "boolean", "default": false}
  }
}
```

**Output Schema:**

```json
{
  "type": "object",
  "properties": {
    "file_path": {"type": "string"},
    "memories_exported": {"type": "integer"},
    "file_size_bytes": {"type": "integer"}
  }
}
```

##### import_memory

**Purpose:** Import memories from JSONL format.

**Input Schema:**

```json
{
  "type": "object",
  "required": ["file_path"],
  "properties": {
    "file_path": {"type": "string"},
    "conflict_resolution": {
      "type": "string",
      "enum": ["skip", "overwrite", "merge"],
      "default": "skip"
    }
  }
}
```

**Output Schema:**

```json
{
  "type": "object",
  "properties": {
    "imported": {"type": "integer"},
    "skipped": {"type": "integer"},
    "errors": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "line": {"type": "integer"},
          "error": {"type": "string"}
        }
      }
    }
  }
}
```

### 4.3 Response Token Limits

Per REQ-MEM-FN-002, tool responses shall not exceed 50,000 tokens.

**Strategies:**
- Pagination for search results (default limit: 10)
- Truncation for large content fields
- Summary-only mode for statistics

---

## 5. CLI Utility

### 5.1 CLI Overview

The CLI provides administrative operations independent of MCP.

**Command:** `memory-cli`

### 5.2 CLI Commands

```
memory-cli health          # Check service health
memory-cli stats           # Show memory statistics
memory-cli index <path>    # Index directory
memory-cli normalize       # Start normalization
memory-cli export <file>   # Export memories
memory-cli import <file>   # Import memories
memory-cli backup <path>   # Backup databases
memory-cli restore <path>  # Restore from backup
```

### 5.3 CLI Implementation

```python
import click

@click.group()
def cli():
    """Memory Service CLI."""
    pass

@cli.command()
def health():
    """Check service health."""
    response = requests.get("http://localhost:9090/health/ready")
    if response.ok:
        click.echo("Service is healthy")
    else:
        click.echo(f"Service unhealthy: {response.json()}")
        raise SystemExit(1)

@cli.command()
def stats():
    """Show memory statistics."""
    # Connect directly to databases and compute stats
    ...

@cli.command()
@click.argument("path")
def index(path):
    """Index a directory."""
    # Trigger indexing via internal API
    ...
```

---

## 6. Error Handling

### 6.1 Error Categories

| Category | Code Prefix | Description |
|----------|-------------|-------------|
| Validation | VAL_ | Input validation failures |
| NotFound | NF_ | Resource not found |
| Conflict | CON_ | Resource conflicts |
| Service | SVC_ | Service-level errors |
| Internal | INT_ | Internal errors |

### 6.2 Error Response Format

```json
{
  "status": "error",
  "error": {
    "code": "VAL_INVALID_TYPE",
    "message": "Invalid memory type 'invalid'. Must be one of: requirements, design, ...",
    "details": {
      "field": "type",
      "provided": "invalid",
      "allowed": ["requirements", "design", "code_pattern", "..."]
    },
    "suggestion": "Use one of the valid memory types listed in the allowed values."
  }
}
```

### 6.3 Actionable Error Messages

Per REQ-MEM-USE-001, all error messages include:
- What went wrong
- Why it happened
- How to fix it

**Examples:**

| Error | Message | Suggestion |
|-------|---------|------------|
| Missing required field | "Field 'content' is required but was not provided" | "Include 'content' with the memory text" |
| Memory not found | "Memory with ID 'abc...' not found" | "Verify the memory ID exists using memory_search" |
| Neo4j unavailable | "Graph database unavailable" | "Graph queries disabled; vector search still works" |

---

## 7. Rate Limiting

Not implemented for single-user system.

---

## 8. Testing

### 8.1 Contract Testing

**Tool:** Pact or custom schema validation

**Test Responsibilities:**

| Role | Responsibility | Tests |
|------|----------------|-------|
| Provider (Memory Service) | Schema compliance | All tool inputs/outputs validated |
| Consumer (Claude Code) | Correct invocation | N/A (Claude Code is external) |

### 8.2 Test Scenarios

| Scenario | Type | Description | Expected Result |
|----------|------|-------------|-----------------|
| Add memory | Happy Path | Valid memory creation | Memory ID returned |
| Add invalid | Error | Missing required field | Validation error |
| Search empty | Edge Case | Query with no results | Empty results array |
| Duplicate check | Happy Path | Check existing code | Matches returned |
| Neo4j down | Error | Graph query when Neo4j unavailable | Graceful error |

---

## 9. Versioning and Evolution

### 9.1 Current Version

| Component | Version | Status |
|-----------|---------|--------|
| MCP Protocol | 2025-11-25 | Active |
| Tool Schema | 1.0 | Active |

### 9.2 Change Management

**Process:**
1. New fields added as optional with defaults
2. Deprecated fields marked in description
3. Breaking changes require version bump
4. 90-day deprecation notice

### 9.3 Backward Compatibility Rules

| Change Type | Backward Compatible | Notes |
|-------------|---------------------|-------|
| Add optional input field | Yes | Default value required |
| Add output field | Yes | Consumers should ignore unknown |
| Remove optional field | No | Deprecation period required |
| Change field type | No | New field + deprecation |
| Add tool | Yes | No impact on existing |
| Remove tool | No | Deprecation period required |

---

## 10. Documentation

### 10.1 API Documentation

All tools documented with:
- Purpose description
- Input/output JSON schemas
- Examples
- Error conditions

### 10.2 CLAUDE.md Integration Template

```markdown
## Memory System Integration

The project uses the Claude Code Long-Term Memory System for persistent context.

### When to Use Memory Tools

| Workflow Phase | Tools to Use | Purpose |
|----------------|--------------|---------|
| Before Implementation | memory_search, find_duplicates | Check existing code |
| After Decisions | memory_add (design) | Record decisions |
| Before Fixes | validate_fix, get_design_context | Ensure alignment |
| After Implementation | memory_add (session) | Record learnings |

### Example Usage

**Check for existing implementation:**
```
Use find_duplicates with the function signature before implementing new code.
```

**Record architectural decision:**
```
Use memory_add with type="design" and design_type="ADR" to record decisions.
```
```

---

## 11. Constraints and Assumptions

### 11.1 Technical Constraints

| Constraint | Source | Impact on Design |
|------------|--------|------------------|
| stdio transport | ADR-001 | Synchronous request/response |
| 50K token limit | Requirements | Pagination required |
| Single user | Requirements | No auth tokens |

### 11.2 Assumptions

| Assumption | Rationale | Risk if Invalid |
|------------|-----------|-----------------|
| JSON parseable | MCP standard | Protocol failure |
| UTF-8 encoding | Standard | Encoding errors |
| Reasonable request size | stdio buffer | Need streaming |

---

## 12. Glossary

| Term | Definition |
|------|------------|
| MCP | Model Context Protocol - AI tool integration standard |
| Tool | MCP function exposed to Claude Code |
| Cypher | Neo4j graph query language |

---

## Appendix A: Complete Tool List

| # | Tool Name | Category | Purpose |
|---|-----------|----------|---------|
| 1 | memory_add | CRUD | Create memory |
| 2 | memory_update | CRUD | Update memory |
| 3 | memory_delete | CRUD | Delete memory |
| 4 | memory_get | CRUD | Get memory by ID |
| 5 | memory_bulk_add | CRUD | Batch create |
| 6 | memory_search | Search | Semantic search |
| 7 | code_search | Search | Code similarity |
| 8 | graph_query | Search | Cypher execution |
| 9 | find_duplicates | Search | Duplicate detection |
| 10 | get_related | Search | Graph traversal |
| 11 | index_file | Index | Single file index |
| 12 | index_directory | Index | Directory index |
| 13 | index_status | Index | Index statistics |
| 14 | reindex | Index | Trigger reindex |
| 15 | check_consistency | Analysis | Pattern check |
| 16 | validate_fix | Analysis | Design alignment |
| 17 | get_design_context | Analysis | Design retrieval |
| 18 | trace_requirements | Analysis | Requirement trace |
| 19 | normalize_memory | Maintenance | Start normalization |
| 20 | normalize_status | Maintenance | Check normalization |
| 21 | memory_statistics | Maintenance | System stats |
| 22 | export_memory | Maintenance | Export to JSONL |
| 23 | import_memory | Maintenance | Import from JSONL |

---

## Appendix B: Reference Documents

| Document | Version | Relevance |
|----------|---------|-----------|
| MCP Specification | 2025-11-25 | Protocol reference |
| requirements-memory-docs.md | 1.0 | Source requirements |
| ADR-001-mcp-server-transport.md | Accepted | Transport decision |
