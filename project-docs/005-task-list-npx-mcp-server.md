# NPX-Based MCP Server Task List

| Field | Value |
|-------|-------|
| **Seq** | 005 |
| **Requirements** | REQ-MEM-005-npx-mcp-server.md |
| **Design** | 005-design-npx-mcp-server.md |
| **ADR** | ADR-010-typescript-mcp-server.md |

## Tasks

| ID | Task | Status | Blocked-By | Agent | Notes |
|----|------|--------|------------|-------|-------|
| T001 | Create project structure (package.json, tsconfig.json) | complete | - | Developer | mcp-server/ directory |
| T002 | Implement config loading (TOML, env vars) | complete | T001 | Developer | src/config.ts |
| T003 | Implement Qdrant adapter | complete | T001 | Developer | src/storage/qdrant.ts |
| T004 | Implement Neo4j adapter | complete | T001 | Developer | src/storage/neo4j.ts |
| T005 | Implement Voyage AI client | complete | T001 | Developer | src/embedding/voyage.ts |
| T006 | Implement MCP server setup | complete | T001 | Developer | src/server.ts with @modelcontextprotocol/sdk |
| T007 | Implement CLI entry point | complete | T002,T006 | Developer | src/index.ts with --project-id |
| T008 | Implement tool context | complete | T003,T004,T005 | Developer | Shared context for all tools |
| T009 | Implement memory_add tool | complete | T008 | Developer | Create memory with embedding |
| T010 | Implement memory_get tool | complete | T008 | Developer | Retrieve by ID |
| T011 | Implement memory_update tool | complete | T008 | Developer | Update memory |
| T012 | Implement memory_delete tool | complete | T008 | Developer | Soft delete |
| T013 | Implement memory_bulk_add tool | complete | T008 | Developer | Batch add |
| T014 | Implement memory_search tool | complete | T008 | Developer | Semantic search |
| T015 | Implement code_search tool | complete | T008 | Developer | Code pattern search |
| T016 | Implement find_duplicates tool | complete | T008 | Developer | Duplicate detection |
| T017 | Implement get_related tool | complete | T008 | Developer | Graph traversal |
| T018 | Implement graph_query tool | complete | T008 | Developer | Read-only Cypher |
| T019 | Implement index_file tool | complete | T008 | Developer | Single file indexing |
| T020 | Implement index_directory tool | complete | T008 | Developer | Directory indexing |
| T021 | Implement index_status tool | complete | T008 | Developer | Job status |
| T022 | Implement reindex tool | complete | T008 | Developer | Trigger reindex |
| T023 | Implement check_consistency tool | complete | T008 | Developer | Pattern compliance |
| T024 | Implement validate_fix tool | complete | T008 | Developer | Design alignment |
| T025 | Implement get_design_context tool | complete | T008 | Developer | ADR/pattern retrieval |
| T026 | Implement trace_requirements tool | complete | T008 | Developer | Requirement tracing |
| T027 | Implement memory_statistics tool | complete | T008 | Developer | Health/counts |
| T028 | Implement normalize_memory tool | complete | T008 | Developer | Normalization |
| T029 | Implement normalize_status tool | complete | T008 | Developer | Job status |
| T030 | Implement export_memory tool | complete | T008 | Developer | JSONL export |
| T031 | Implement import_memory tool | complete | T008 | Developer | JSONL import |
| T032 | Create npx entry point | complete | T007 | Developer | bin/claude-memory-mcp.js |
| T033 | Code Review - Requirements | pending | T032 | Code Reviewer - Requirements | All tools implemented |
| T034 | Code Review - Security | pending | T032 | Code Reviewer - Security | Secret handling, input validation |
| T035 | Code Review - Integration | pending | T032 | Code Reviewer - Integration | No stubs, all wiring complete |
| T036 | Unit tests - Config | pending | T002 | Test Coder | TOML loading, env override |
| T037 | Unit tests - Qdrant adapter | pending | T003 | Test Coder | Collection operations |
| T038 | Unit tests - Neo4j adapter | pending | T004 | Test Coder | Node/relationship operations |
| T039 | Unit tests - Voyage client | pending | T005 | Test Coder | Embedding API |
| T040 | Unit tests - Tool implementations | pending | T031 | Test Coder | All 23 tools |
| T041 | Integration tests - MCP protocol | pending | T032 | Test Coder | stdio transport |
| T042 | Integration tests - Data roundtrip | pending | T032 | Test Coder | Create/Read/Update/Delete |
| T043 | E2E tests - Claude Code integration | pending | T032 | Test Coder | Tools visible/callable |
| T044 | E2E tests - Data compatibility | pending | T032 | Test Coder | Read Python-created data |
| T045 | Run all tests | pending | T044 | Test Runner | Verify all pass |
| T046 | Update .mcp.json example | complete | T032 | Documentation | npx invocation |
| T047 | Update user-docs/quick-reference.md | complete | T032 | Documentation | New setup instructions |
| T048 | Update README.md | complete | T032 | Documentation | TypeScript project info |
| T049 | Delete Python src/memory_service/ | pending | T045 | Developer | After all tests pass |
| T050 | Final verification | pending | T049 | Task Manager | All exit criteria met |

## Summary

| Status | Count |
|--------|-------|
| pending | 15 |
| in-progress | 0 |
| blocked | 0 |
| complete | 35 |
| **Total** | **50** |

## Task Dependencies Graph

```
T001 (project structure)
  |
  +---> T002 (config) ---> T007 (CLI) ---> T032 (npx)
  |                                          |
  +---> T003 (qdrant) ---+                   +---> T033-T035 (code reviews)
  |                      |                   |
  +---> T004 (neo4j) ----+---> T008 (context)--> T009-T031 (23 tools)
  |                      |                   |
  +---> T005 (voyage) ---+                   +---> T036-T044 (tests)
  |                                          |
  +---> T006 (server) ---> T007              +---> T045 (test runner)
                                             |
                                             +---> T046-T048 (docs)
                                             |
                                             +---> T049 (cleanup)
                                             |
                                             +---> T050 (final)
```

## Exit Criteria

### Implementation Phase
- [x] All 23 tools implemented and registered
- [x] Project isolation via --project-id working
- [x] Config loading from TOML working
- [x] Build succeeds without errors
- [x] No TODO/FIXME markers in code

### Testing Phase
- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] E2E tests confirm tools visible in Claude Code
- [ ] E2E tests confirm tools callable from Claude Code
- [ ] Data compatibility verified with existing memories

### Documentation Phase
- [x] .mcp.json updated with npx example
- [x] quick-reference.md updated
- [x] README.md updated

### Cleanup Phase
- [ ] Python src/memory_service/ deleted
- [ ] pyproject.toml removed
- [ ] CLAUDE.md updated
