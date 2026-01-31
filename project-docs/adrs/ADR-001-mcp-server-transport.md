# ADR-001: MCP Server Transport Mechanism

## Status

Accepted

## Context

The Claude Code Long-Term Memory System must expose its capabilities to Claude Code via the Model Context Protocol (MCP). MCP supports multiple transport mechanisms:

1. **stdio** - Communication via standard input/output streams
2. **HTTP/SSE** - Communication via HTTP with Server-Sent Events for streaming

The choice of transport affects:
- How Claude Code connects to the memory service
- Deployment complexity
- Debugging and observability
- Performance characteristics
- Session management

Requirements addressed:
- REQ-MEM-INT-001: MCP server compliant with protocol specification
- REQ-MEM-INT-004: Support concurrent tool invocations
- REQ-MEM-DEP-010: Provide MCP server configuration for Claude Code

## Options Considered

### Option 1: stdio Transport Only

- **Pros**:
  - Native Claude Code support (standard MCP pattern)
  - No network configuration required
  - Simple deployment - single process spawned by Claude Code
  - Inherently secure (no network exposure)
- **Cons**:
  - Limited observability (no easy way to inspect messages)
  - Process lifecycle tied to Claude Code session
  - Harder to debug in isolation
  - No HTTP endpoints for health checks

### Option 2: HTTP Transport Only

- **Pros**:
  - Independent service lifecycle
  - Easy observability via HTTP logs
  - Health check endpoints (/health, /metrics)
  - Can run as standalone daemon
- **Cons**:
  - Requires network configuration
  - Additional security considerations (localhost binding)
  - More complex deployment
  - Not the native Claude Code pattern

### Option 3: Dual Transport (stdio primary, HTTP for metrics/health)

- **Pros**:
  - Best of both worlds - native stdio for MCP
  - Separate HTTP server for observability endpoints
  - Health checks and metrics accessible independently
  - No compromise on MCP protocol compliance
- **Cons**:
  - Two server components to manage
  - Slightly more complex codebase

## Decision

**Option 3: Dual Transport** - Use stdio for MCP protocol communication with a separate HTTP server for observability.

The MCP server will use stdio transport as the primary communication channel with Claude Code. A lightweight HTTP server will run alongside to expose:
- `/health` - Health check endpoint
- `/metrics` - Prometheus metrics endpoint
- `/status` - Detailed system status (memory statistics)

This approach:
1. Follows the standard MCP pattern expected by Claude Code
2. Enables proper observability without compromising protocol compliance
3. Allows health checks from Docker orchestration
4. Supports Prometheus scraping for metrics

## Consequences

### Positive
- Native integration with Claude Code via stdio
- Full observability via HTTP endpoints
- Health checks enable container orchestration (docker-compose health_check)
- Metrics endpoint supports monitoring dashboards
- Security maintained - stdio is inherently local-only

### Negative
- Two server components in the memory service
- Slightly increased memory footprint
- Need to manage two ports (stdio implicit, HTTP configurable)

### Risks
- **Risk**: HTTP server could introduce security vulnerabilities
- **Mitigation**: Bind HTTP server to localhost only (127.0.0.1), no authentication required for local-only access

## Requirements Addressed

- REQ-MEM-INT-001 (MCP compliance)
- REQ-MEM-INT-004 (concurrent invocations)
- REQ-MEM-DEP-010 (MCP configuration)
- REQ-MEM-REL-004 (health checks)
- REQ-MEM-OBS-001 (metrics endpoint)
- REQ-MEM-SEC-002 (localhost binding)

## References

- Model Context Protocol Specification: https://modelcontextprotocol.io
- Claude Code MCP Configuration Documentation
