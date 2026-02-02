# DEPRECATED: MCP server no longer runs in Docker
# ===============================================
#
# As of v0.2.0, the MCP server runs as a local native process, not in Docker.
# See REQ-MEM-002 and ADR-009 for the architectural decision rationale.
#
# The MCP server should be installed via pip:
#   pip install claude-memory-mcp
#
# And run locally:
#   claude-memory-mcp --project-id my-project
#
# Databases (Qdrant, Neo4j) continue to run in Docker via docker-compose.yml.
#
# This Dockerfile is kept for reference only and may be removed in a future release.

# syntax=docker/dockerfile:1.4
FROM python:3.12-slim

# This file is deprecated - see comments above
RUN echo "DEPRECATED: MCP server should run locally, not in Docker." && \
    echo "Install via: pip install claude-memory-mcp" && \
    echo "Run via: claude-memory-mcp --project-id <project>" && \
    exit 1
