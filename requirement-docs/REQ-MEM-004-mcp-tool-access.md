# REQ-MEM-004: MCP Tool Access Fix and Full Test Validation

## 1. Overview

### 1.1 Purpose

1. Investigate and resolve the issue where Claude Code shows the MCP server as "connected" but does not expose the 23 memory tools to the Claude assistant.
2. Comprehensively update and run ALL tests to validate the entire system works correctly.

### 1.2 Problem Statement

The memory MCP server correctly exposes 23 tools via the JSON-RPC protocol. When tested directly via bash/stdio, all tools are returned with proper schemas. However, when Claude Code connects to the server:
- `/mcp` shows "connected" status
- The tools (`memory_add`, `index_directory`, etc.) are NOT available in Claude's tool list
- Other MCP servers (e.g., chrome-devtools) work correctly in the same environment

### 1.3 Scope

- Diagnose why Claude Code isn't loading tools from the memory MCP server
- Identify root cause (protocol issue, configuration issue, or Claude Code behavior)
- Implement fixes to ensure tools are accessible
- Document any Claude Code-specific requirements for MCP servers

## 2. Current State Analysis

### 2.1 What Works

| Component | Status | Evidence |
|-----------|--------|----------|
| MCP Server startup | OK | Server starts, connects to databases |
| JSON-RPC protocol | OK | Responds correctly to initialize/tools/list |
| Tool schemas | OK | All 23 tools have valid inputSchema |
| Logging to stderr | OK | Logs go to stderr, stdout clean for JSON-RPC |
| Protocol version | OK | Uses "2024-11-05" |

### 2.2 What Doesn't Work

| Issue | Description |
|-------|-------------|
| Tools not loaded | Claude Code shows "connected" but tools unavailable |
| No error messages | No visible errors in Claude Code when tools fail to load |
| Session persistence | Issue persists across conversation restarts |

### 2.3 Configuration

Current `.mcp.json`:
```json
{
  "mcpServers": {
    "memory": {
      "type": "stdio",
      "command": "bash",
      "args": ["-c", "source .../venv/bin/activate && claude-memory-mcp --project-id claude-memory-mcp"]
    }
  }
}
```

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| REQ-MEM-004-FN-001 | Tools SHALL be accessible to Claude after MCP connection | P0 |
| REQ-MEM-004-FN-002 | MCP server SHALL respond to all standard MCP protocol messages | P0 |
| REQ-MEM-004-FN-003 | Tool calls SHALL execute and return results to Claude | P0 |
| REQ-MEM-004-FN-004 | Connection status SHALL accurately reflect tool availability | P1 |

### 3.2 Investigation Areas

| ID | Area | Description |
|----|------|-------------|
| REQ-MEM-004-INV-001 | Protocol compliance | Verify full MCP 2024-11-05 protocol compliance |
| REQ-MEM-004-INV-002 | Response format | Verify JSON-RPC response format matches Claude Code expectations |
| REQ-MEM-004-INV-003 | Startup timing | Check if tools list is requested before server is fully ready |
| REQ-MEM-004-INV-004 | stderr interference | Verify no stderr output corrupts stdout JSON-RPC |
| REQ-MEM-004-INV-005 | Configuration format | Verify `.mcp.json` format matches Claude Code requirements |
| REQ-MEM-004-INV-006 | Venv activation | Check if bash wrapper causes issues |

### 3.3 Potential Solutions to Evaluate

| ID | Solution | Description |
|----|----------|-------------|
| REQ-MEM-004-SOL-001 | Direct Python execution | Use `python -m memory_service` instead of bash wrapper |
| REQ-MEM-004-SOL-002 | Suppress all logging | Set log level to CRITICAL to eliminate stderr output |
| REQ-MEM-004-SOL-003 | Protocol adjustments | Add any missing MCP protocol messages |
| REQ-MEM-004-SOL-004 | Response buffering | Ensure complete responses before newline |
| REQ-MEM-004-SOL-005 | MCP SDK usage | Use official mcp Python SDK instead of custom implementation |

## 4. Success Criteria

| Criteria | Measurement |
|----------|-------------|
| Tools visible | All 23 tools appear in Claude's available tools |
| Tools callable | Can successfully call `memory_statistics` from Claude |
| Tool results | Tool call results are returned to Claude |
| All unit tests pass | `pytest src/tests/unit/ -v` passes 100% |
| All integration tests pass | `pytest src/tests/integration/ -v` passes 100% |
| All E2E tests pass | `pytest src/tests/e2e/ -v` passes 100% |
| All security tests pass | `pytest src/tests/security/ -v` passes 100% |
| Linting passes | `ruff check src/` passes with no errors |

## 4.1 Test Validation Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| REQ-MEM-004-TEST-001 | ALL existing tests SHALL pass without modification or with justified fixes | P0 |
| REQ-MEM-004-TEST-002 | Tests SHALL actually test the real implementation, not mocks | P0 |
| REQ-MEM-004-TEST-003 | Integration tests SHALL verify MCP protocol end-to-end | P0 |
| REQ-MEM-004-TEST-004 | Any test changes SHALL be documented with justification | P1 |
| REQ-MEM-004-TEST-005 | Test coverage SHALL be reported | P1 |

## 5. Testing Approach

### 5.1 Manual Testing

1. Start fresh Claude Code conversation
2. Verify `/mcp` shows "connected"
3. Verify tools are listed (can ask Claude to list available tools)
4. Call `memory_statistics` tool
5. Verify result is returned

### 5.2 Automated Testing

| Test | Description |
|------|-------------|
| Protocol test | Send all MCP protocol messages, verify responses |
| Tool list test | Verify all 23 tools in tools/list response |
| Tool call test | Call each tool, verify response format |
| Stderr isolation | Verify no stderr output on stdout channel |

## 6. Dependencies

- Claude Code version: Current
- MCP Protocol version: 2024-11-05
- Python: 3.12+
- Databases: Qdrant, Neo4j (running in Docker)

## 7. Timeline

This is an investigation task - timeline depends on root cause discovery.

## 8. References

- [MCP Protocol Specification](https://modelcontextprotocol.io/docs)
- Previous conversation screenshot showing issue
- Working MCP server (chrome-devtools) for comparison
