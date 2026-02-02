# Claude Code Memory Service - Deployment Guide

This guide covers deploying the Memory Service with Docker and configuring it for use with Claude Code.

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 8GB RAM minimum (16GB recommended for large codebases)
- Voyage AI API key (for embeddings)

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd claude-code-memory-service
```

### 2. Configure Environment

Copy the example environment file and configure it:

```bash
cp docker/.env.example docker/.env
```

Edit `docker/.env` with your settings:

```env
# Required
VOYAGE_API_KEY=your-voyage-api-key-here
NEO4J_PASSWORD=your-secure-password

# Project Isolation (required)
PROJECT_ID=my-project             # Unique identifier for this project
PROJECT_PATH=/path/to/your/project  # Path to project directory

# Optional overrides
QDRANT_HOST=qdrant
QDRANT_PORT=6333
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Metrics/Health HTTP server
METRICS_HOST=127.0.0.1   # Use 0.0.0.0 for Docker
METRICS_PORT=9090
```

### 3. Start Services

```bash
cd docker
docker-compose up -d
```

This starts:
- **memory-service**: The MCP server and HTTP API
- **qdrant**: Vector database for semantic search
- **neo4j**: Graph database for relationships

### 4. Verify Deployment

Check service health:

```bash
# HTTP health endpoint
curl http://localhost:9090/health

# Readiness check (verifies database connections)
curl http://localhost:9090/health/ready
```

---

## Docker Compose Configuration

### Production Configuration

For production deployments, use the following `docker-compose.yml`:

```yaml
version: '3.8'

services:
  memory-service:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    ports:
      - "127.0.0.1:9090:9090"
    volumes:
      - ${PROJECT_PATH:-/path/to/project}:/project:ro
      - memory-cache:/app/cache
    environment:
      - QDRANT_HOST=qdrant
      - QDRANT_PORT=6333
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=${NEO4J_PASSWORD}
      - VOYAGE_API_KEY=${VOYAGE_API_KEY}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - LOG_FORMAT=json
      - METRICS_HOST=0.0.0.0
      - METRICS_PORT=9090
      - PROJECT_PATH=/project
    depends_on:
      qdrant:
        condition: service_healthy
      neo4j:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9090/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    user: "1000:1000"  # Non-root user

  qdrant:
    image: qdrant/qdrant:v1.7.0
    volumes:
      - qdrant-data:/qdrant/storage
    environment:
      - QDRANT__SERVICE__GRPC_PORT=6334
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  neo4j:
    image: neo4j:5.15.0
    volumes:
      - neo4j-data:/data
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}
      - NEO4J_PLUGINS=["apoc"]
    healthcheck:
      test: ["CMD", "wget", "-q", "-O", "-", "http://localhost:7474/"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

volumes:
  qdrant-data:
  neo4j-data:
  memory-cache:
```

### Development Configuration

For development, expose additional ports:

```yaml
services:
  qdrant:
    ports:
      - "127.0.0.1:6333:6333"  # HTTP API
      - "127.0.0.1:6334:6334"  # gRPC

  neo4j:
    ports:
      - "127.0.0.1:7474:7474"  # Browser UI
      - "127.0.0.1:7687:7687"  # Bolt
```

---

## Claude Code Integration

### MCP Server Configuration

Add the Memory Service to your Claude Code MCP configuration (`~/.claude/mcp.json` or project-level):

```json
{
  "mcpServers": {
    "memory": {
      "command": "docker",
      "args": [
        "exec", "-i", "memory-service",
        "python", "-m", "memory_service", "mcp"
      ],
      "env": {}
    }
  }
}
```

Or for stdio transport directly:

```json
{
  "mcpServers": {
    "memory": {
      "command": "docker",
      "args": [
        "compose", "-f", "/path/to/docker/docker-compose.yml",
        "exec", "-T", "memory-service",
        "python", "-m", "memory_service", "mcp"
      ]
    }
  }
}
```

### Verify Integration

In Claude Code, verify the tools are available:

```
You: What memory tools are available?

Claude: I have access to 23 memory tools:
- memory_add, memory_update, memory_delete, memory_get, memory_bulk_add
- memory_search, code_search, graph_query, find_duplicates, get_related
...
```

---

## Environment Variables

### Required

| Variable | Description |
|----------|-------------|
| `VOYAGE_API_KEY` | Voyage AI API key for embeddings |
| `NEO4J_PASSWORD` | Neo4j database password |
| `PROJECT_ID` | Unique identifier for project data isolation (e.g., `my-project`) |
| `PROJECT_PATH` | Path to the project directory to mount |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `QDRANT_HOST` | `localhost` | Qdrant host |
| `QDRANT_PORT` | `6333` | Qdrant HTTP port |
| `QDRANT_GRPC_PORT` | `6334` | Qdrant gRPC port |
| `NEO4J_URI` | `bolt://localhost:7687` | Neo4j connection URI |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FORMAT` | `json` | Log format (json, console) |
| `METRICS_HOST` | `127.0.0.1` | HTTP server bind address (use 0.0.0.0 for Docker) |
| `METRICS_PORT` | `9090` | HTTP server port |
| `PROJECT_PATH` | `/project` | Project mount path in container |
| `CACHE_DIR` | `/app/cache` | Embedding cache directory |
| `METRICS_ENABLED` | `true` | Enable Prometheus metrics |

---

## Data Persistence

### Volume Mounts

| Volume | Purpose | Backup Priority |
|--------|---------|-----------------|
| `qdrant-data` | Vector embeddings and metadata | High |
| `neo4j-data` | Graph relationships | High |
| `memory-cache` | Embedding cache (can be rebuilt) | Low |

### Backup Procedure

```bash
# Stop services
docker-compose stop

# Backup volumes
docker run --rm \
  -v qdrant-data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar cvf /backup/qdrant-backup.tar /data

docker run --rm \
  -v neo4j-data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar cvf /backup/neo4j-backup.tar /data

# Restart services
docker-compose start
```

### Restore Procedure

```bash
# Stop services
docker-compose down

# Remove existing data
docker volume rm qdrant-data neo4j-data

# Restore from backup
docker run --rm \
  -v qdrant-data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar xvf /backup/qdrant-backup.tar -C /

docker run --rm \
  -v neo4j-data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar xvf /backup/neo4j-backup.tar -C /

# Start services
docker-compose up -d
```

---

## Monitoring

### Health Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Basic liveness check |
| `GET /health/ready` | Full readiness check (includes DB connections) |
| `GET /metrics` | Prometheus metrics |
| `GET /status` | Detailed system status |

### Prometheus Metrics

Key metrics to monitor:

```
# Memory operations
memory_add_total
memory_search_latency_seconds
memory_search_total

# Database health
qdrant_connection_errors_total
neo4j_connection_errors_total

# Embedding service
embedding_cache_hits_total
embedding_cache_misses_total
embedding_api_latency_seconds
```

---

## Security Considerations

### Network Binding

- HTTP server binds to `127.0.0.1` by default
- MCP server uses stdio transport (no network exposure)
- Database ports should not be exposed externally

### Secrets Management

- Store `VOYAGE_API_KEY` and `NEO4J_PASSWORD` securely
- Use Docker secrets or external secret management in production
- Never commit `.env` files to version control

### Container Security

- Service runs as non-root user (UID 1000)
- Project directory is mounted read-only
- No privileged capabilities required

---

## Troubleshooting

### Common Issues

**Service won't start:**
```bash
# Check logs
docker-compose logs memory-service

# Verify environment
docker-compose config
```

**Database connection errors:**
```bash
# Check Qdrant
curl http://localhost:6333/health

# Check Neo4j
curl http://localhost:7474/
```

**Embedding failures:**
- Verify `VOYAGE_API_KEY` is set correctly
- Check Voyage AI API status
- Review embedding service logs

**Memory issues with large codebases:**
- Increase Docker memory limit
- Use incremental indexing
- Consider increasing batch sizes

### Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f memory-service

# Last 100 lines
docker-compose logs --tail=100 memory-service
```

---

## Scaling Considerations

### Single-Node Performance

The default configuration handles:
- Up to 1M memories
- 100K source files
- 500K indexed functions

### Horizontal Scaling

For larger deployments:
- Use Qdrant cluster mode
- Deploy Neo4j cluster
- Run multiple memory-service instances behind load balancer

---

## CLI Usage

The service includes a CLI for administrative tasks:

```bash
# Initialize database schemas
docker exec memory-service python -m memory_service init-schema

# Check health
docker exec memory-service python -m memory_service health

# Get statistics
docker exec memory-service python -m memory_service stats

# Index a directory
docker exec memory-service python -m memory_service index /project/src

# Run normalization
docker exec memory-service python -m memory_service normalize

# Backup data
docker exec memory-service python -m memory_service backup /backup/memories.jsonl

# Restore data
docker exec memory-service python -m memory_service restore /backup/memories.jsonl
```
