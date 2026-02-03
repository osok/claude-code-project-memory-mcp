# Design Document: Infrastructure - Claude Code Long-Term Memory System

## Document Control

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Status | Draft |
| Sequence | 002 |
| Requirements | requirements-memory-docs.md |
| Architecture | 002-architecture-memory-mcp.md |

---

## 1. Introduction

### 1.1 Purpose

This document specifies the infrastructure design for the Claude Code Long-Term Memory System. It defines the Docker containerization, volume management, networking, observability, and operational procedures for deploying and running the memory system on a developer workstation.

### 1.2 Scope

**Included:**
- Docker container configuration for all services
- Docker Compose orchestration
- Volume management for data persistence
- Network architecture and port allocation
- Environment variable configuration
- Health checks and monitoring endpoints
- Logging and metrics infrastructure
- Operational procedures

**Excluded:**
- Cloud deployment (system is designed for local workstation)
- Kubernetes orchestration
- Multi-node clustering
- CI/CD pipelines (out of scope for MCP server)
- Load balancing beyond single instance

### 1.3 Requirements Traceability

| Requirement ID | Requirement Summary | Design Section |
|----------------|---------------------|----------------|
| REQ-MEM-DEP-001 | docker-compose.yml configuration | 4.1 |
| REQ-MEM-DEP-002 | Named Docker volumes | 5.2 |
| REQ-MEM-DEP-003 | Health checks and restart policies | 4.2 |
| REQ-MEM-DEP-004 | .env.example documentation | 6.2 |
| REQ-MEM-REL-001 | Data persistence across restarts | 5.2 |
| REQ-MEM-REL-004 | Health checks for dependencies | 4.2, 8.4 |
| REQ-MEM-SEC-001 | Environment variable secrets | 6.2 |
| REQ-MEM-SEC-002 | Localhost binding | 7.2 |
| REQ-MEM-SEC-003 | Non-root containers | 4.2 |
| REQ-MEM-SCAL-001 | Support 100K source files | 14.3 |
| REQ-MEM-SCAL-002 | Support 1M memories | 14.3 |
| REQ-MEM-SCAL-003 | Support 500K function index | 14.3 |
| REQ-MEM-SCAL-004 | Configurable resource limits | 4.2 |
| REQ-MEM-MAINT-002 | Structured JSON logging | 8.2 |
| REQ-MEM-MAINT-003 | Externalized configuration | 6.2 |
| REQ-MEM-OBS-001 | Prometheus metrics endpoint | 8.3 |
| REQ-MEM-OBS-002 | Tool invocation logging | 8.2 |
| REQ-MEM-OBS-004 | Error context logging | 8.2 |
| REQ-MEM-FN-033 | Configurable duplicate threshold | 6.2 |

---

## 2. Infrastructure Context

### 2.1 Infrastructure Overview

The Claude Code Long-Term Memory System runs entirely on a single developer workstation using Docker containers. The architecture consists of three containerized services orchestrated via Docker Compose:

1. **memory-service** - Python application providing MCP server and HTTP endpoints
2. **qdrant** - Vector database for embeddings and semantic search
3. **neo4j** - Graph database for relationship tracking

All services communicate over a dedicated Docker bridge network with no external network exposure except the Voyage AI embedding API.

### 2.2 Applications Supported

| Application | Type | Resource Requirements | Criticality |
|-------------|------|----------------------|-------------|
| Memory Service | MCP Server + HTTP API | 2GB RAM, 1 CPU | High |
| Qdrant | Vector Database | 4GB RAM, 2 CPU | High |
| Neo4j | Graph Database | 2GB RAM, 1 CPU | Medium |

### 2.3 Environment Strategy

| Environment | Purpose | Configuration | Access |
|-------------|---------|---------------|--------|
| Development | Local development and testing | docker-compose.dev.yml | Developer |
| Production | Developer workstation deployment | docker-compose.yml | Developer |

**Note:** This system is designed for single-developer workstation deployment. There is no staging or multi-environment pipeline.

### 2.4 Platform Selection

| Platform | Services Used | Rationale |
|----------|---------------|-----------|
| Docker | Container runtime | Standard containerization, reproducible builds |
| Docker Compose | Service orchestration | Simple multi-container management |

---

## 3. Network Architecture

### 3.1 Network Topology

All services run on a single Docker bridge network with isolated internal communication. External access is restricted to:
- Localhost ports for developer access
- Outbound HTTPS to Voyage AI for embeddings

### 3.2 Docker Network

**Network Name:** `memory-network`

**Type:** Bridge network (default driver)

**Purpose:** Isolated communication between memory system services

**Internal DNS:** Docker's embedded DNS enables service discovery by container name

### 3.3 Port Allocation

| Service | Internal Port | External Port | Protocol | Purpose |
|---------|---------------|---------------|----------|---------|
| memory-service | 9090 | 9090 | HTTP | Health/metrics endpoints |
| memory-service | 8765 | 8765 | HTTP | HTTP MCP transport (optional) |
| qdrant | 6333 | 6333 | HTTP | Qdrant REST API |
| qdrant | 6334 | 6334 | gRPC | Qdrant gRPC API |
| neo4j | 7474 | 7474 | HTTP | Neo4j Browser/REST |
| neo4j | 7687 | 7687 | Bolt | Neo4j Bolt protocol |

**Note:** All external ports bind to `127.0.0.1` only, preventing external network access.

### 3.4 Service Communication

```
+------------------+
|   Claude Code    |
+--------+---------+
         | stdio (primary)
         | HTTP 8765 (optional)
         v
+------------------+        +------------------+
|  memory-service  |------->|   Voyage AI      |
|    (Python)      |        |   (External)     |
+--------+---------+        +------------------+
         |
    +----+----+
    |         |
    v         v
+-------+  +-------+
| qdrant|  | neo4j |
| :6333 |  | :7687 |
+-------+  +-------+
```

### 3.5 Network Security

| Rule | Source | Destination | Ports | Purpose |
|------|--------|-------------|-------|---------|
| Allow | memory-service | qdrant | 6333, 6334 | Database access |
| Allow | memory-service | neo4j | 7687 | Database access |
| Allow | localhost | memory-service | 9090, 8765 | Developer access |
| Allow | localhost | qdrant | 6333 | Direct database access |
| Allow | localhost | neo4j | 7474, 7687 | Direct database access |
| Allow | memory-service | api.voyageai.com | 443 | Embedding generation |
| Deny | external | all | all | No external access |

---

## 4. Container Architecture

### 4.1 Docker Compose Configuration

**File:** `docker-compose.yml`

```yaml
version: "3.8"

services:
  memory-service:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: memory-service
    restart: unless-stopped
    user: "1000:1000"
    ports:
      - "127.0.0.1:9090:9090"
      - "127.0.0.1:8765:8765"
    volumes:
      - memory-service-cache:/app/cache
      - ${PROJECT_PATH}:/project:ro
    environment:
      - QDRANT_HOST=qdrant
      - QDRANT_PORT=6333
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=${NEO4J_USER:-neo4j}
      - NEO4J_PASSWORD=${NEO4J_PASSWORD}
      - VOYAGE_API_KEY=${VOYAGE_API_KEY}
      - VOYAGE_MODEL=${VOYAGE_MODEL:-voyage-code-3}
      - EMBEDDING_CACHE_SIZE=${EMBEDDING_CACHE_SIZE:-10000}
      - DUPLICATE_THRESHOLD=${DUPLICATE_THRESHOLD:-0.85}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - LOG_FORMAT=${LOG_FORMAT:-json}
      - METRICS_ENABLED=${METRICS_ENABLED:-true}
      - METRICS_PORT=9090
      - PROJECT_PATH=/project
    depends_on:
      qdrant:
        condition: service_healthy
      neo4j:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9090/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    networks:
      - memory-network
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: "1.0"
        reservations:
          memory: 1G
          cpus: "0.5"

  qdrant:
    image: qdrant/qdrant:v1.7.4
    container_name: memory-qdrant
    restart: unless-stopped
    ports:
      - "127.0.0.1:6333:6333"
      - "127.0.0.1:6334:6334"
    volumes:
      - memory-qdrant-data:/qdrant/storage
    environment:
      - QDRANT__SERVICE__GRPC_PORT=6334
      - QDRANT__SERVICE__HTTP_PORT=6333
      - QDRANT__STORAGE__STORAGE_PATH=/qdrant/storage
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    networks:
      - memory-network
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: "2.0"
        reservations:
          memory: 2G
          cpus: "1.0"

  neo4j:
    image: neo4j:5.15-community
    container_name: memory-neo4j
    restart: unless-stopped
    ports:
      - "127.0.0.1:7474:7474"
      - "127.0.0.1:7687:7687"
    volumes:
      - memory-neo4j-data:/data
      - memory-neo4j-logs:/logs
    environment:
      - NEO4J_AUTH=${NEO4J_USER:-neo4j}/${NEO4J_PASSWORD}
      - NEO4J_PLUGINS=["apoc"]
      - NEO4J_dbms_memory_heap_initial__size=512m
      - NEO4J_dbms_memory_heap_max__size=1G
      - NEO4J_dbms_memory_pagecache_size=512m
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7474"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    networks:
      - memory-network
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: "1.0"
        reservations:
          memory: 1G
          cpus: "0.5"

networks:
  memory-network:
    driver: bridge
    name: memory-network

volumes:
  memory-service-cache:
    name: memory-service-cache
  memory-qdrant-data:
    name: memory-qdrant-data
  memory-neo4j-data:
    name: memory-neo4j-data
  memory-neo4j-logs:
    name: memory-neo4j-logs
```

### 4.2 Container Specifications

#### Memory Service Container

**Base Image:** `python:3.12-slim`

**Dockerfile:**

```dockerfile
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r memoryuser && useradd -r -g memoryuser memoryuser

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=memoryuser:memoryuser src/ ./src/
COPY --chown=memoryuser:memoryuser pyproject.toml ./

# Create cache directory
RUN mkdir -p /app/cache && chown memoryuser:memoryuser /app/cache

USER memoryuser

# Health check endpoint
EXPOSE 9090

# MCP HTTP transport (optional)
EXPOSE 8765

ENTRYPOINT ["python", "-m", "memory_service"]
```

**Resource Limits:**
- Memory: 2GB (recommended), 1GB (minimum)
- CPU: 1 core (recommended), 0.5 core (minimum)

**Security:**
- Runs as non-root user (UID 1000)
- Read-only project mount
- Minimal base image

#### Qdrant Container

**Image:** `qdrant/qdrant:v1.7.4`

**Resource Limits:**
- Memory: 4GB (recommended), 2GB (minimum)
- CPU: 2 cores (recommended), 1 core (minimum)

**Configuration:**
- HNSW index parameters: ef_construct=200, m=16
- Storage path: `/qdrant/storage`

#### Neo4j Container

**Image:** `neo4j:5.15-community`

**Resource Limits:**
- Memory: 2GB (recommended), 1GB (minimum)
- CPU: 1 core (recommended), 0.5 core (minimum)

**Configuration:**
- Heap: 512MB initial, 1GB max
- Page cache: 512MB
- APOC plugin enabled

---

## 5. Storage Architecture

### 5.1 Storage Strategy

All persistent data is stored in Docker named volumes, ensuring:
- Data survives container restarts
- Data survives container recreation
- Simple backup via volume export
- Isolation from host filesystem

### 5.2 Volume Configuration

| Volume Name | Container | Mount Path | Purpose | Estimated Size |
|-------------|-----------|------------|---------|----------------|
| memory-service-cache | memory-service | /app/cache | Embedding cache, SQLite | 1-5 GB |
| memory-qdrant-data | qdrant | /qdrant/storage | Vector collections | 10-50 GB |
| memory-neo4j-data | neo4j | /data | Graph database | 5-20 GB |
| memory-neo4j-logs | neo4j | /logs | Neo4j logs | 1-2 GB |

### 5.3 Project Mount

The project directory is mounted read-only into the memory-service container:

| Host Path | Container Path | Mode | Purpose |
|-----------|----------------|------|---------|
| ${PROJECT_PATH} | /project | ro | Codebase indexing |

### 5.4 Backup Strategy

**Manual Backup:**

```bash
# Stop services
docker-compose stop

# Backup volumes
docker run --rm -v memory-qdrant-data:/data -v $(pwd)/backup:/backup \
    alpine tar czf /backup/qdrant-backup.tar.gz -C /data .

docker run --rm -v memory-neo4j-data:/data -v $(pwd)/backup:/backup \
    alpine tar czf /backup/neo4j-backup.tar.gz -C /data .

docker run --rm -v memory-service-cache:/data -v $(pwd)/backup:/backup \
    alpine tar czf /backup/cache-backup.tar.gz -C /data .

# Restart services
docker-compose start
```

**Restore:**

```bash
# Stop services
docker-compose down

# Restore volumes
docker run --rm -v memory-qdrant-data:/data -v $(pwd)/backup:/backup \
    alpine sh -c "rm -rf /data/* && tar xzf /backup/qdrant-backup.tar.gz -C /data"

# Repeat for other volumes...

# Start services
docker-compose up -d
```

---

## 6. Configuration Management

### 6.1 Configuration Hierarchy

1. **Default values** - Hardcoded in application
2. **Environment variables** - Override defaults
3. **.env file** - Loaded by Docker Compose

### 6.2 Environment Variables

**File:** `.env.example`

```bash
# =============================================================================
# Claude Code Long-Term Memory System - Environment Configuration
# =============================================================================
# Copy this file to .env and configure values for your environment.
# DO NOT commit .env to version control.
# =============================================================================

# -----------------------------------------------------------------------------
# Project Configuration
# -----------------------------------------------------------------------------

# Path to project directory for codebase indexing (required)
PROJECT_PATH=/path/to/your/project

# -----------------------------------------------------------------------------
# Voyage AI Configuration
# -----------------------------------------------------------------------------

# Voyage AI API key for embeddings (required)
# Get your API key from: https://dash.voyageai.com/
VOYAGE_API_KEY=your-voyage-api-key-here

# Voyage embedding model (optional, default: voyage-code-3)
VOYAGE_MODEL=voyage-code-3

# -----------------------------------------------------------------------------
# Neo4j Configuration
# -----------------------------------------------------------------------------

# Neo4j username (optional, default: neo4j)
NEO4J_USER=neo4j

# Neo4j password (required)
NEO4J_PASSWORD=your-secure-password-here

# -----------------------------------------------------------------------------
# Memory Service Configuration
# -----------------------------------------------------------------------------

# Embedding cache size - max embeddings to cache (optional, default: 10000)
EMBEDDING_CACHE_SIZE=10000

# Duplicate detection threshold - cosine similarity 0.70-0.95 (optional, default: 0.85)
DUPLICATE_THRESHOLD=0.85

# Logging level - DEBUG, INFO, WARNING, ERROR (optional, default: INFO)
LOG_LEVEL=INFO

# Log format - json or text (optional, default: json)
LOG_FORMAT=json

# Enable Prometheus metrics (optional, default: true)
METRICS_ENABLED=true

# -----------------------------------------------------------------------------
# Qdrant Configuration (Optional)
# -----------------------------------------------------------------------------

# Qdrant API key if authentication is enabled (optional)
# QDRANT_API_KEY=your-qdrant-api-key
```

### 6.3 Configuration Validation

The memory service validates configuration at startup:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Required
    project_path: str
    voyage_api_key: str
    neo4j_password: str

    # Optional with defaults
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    qdrant_api_key: str | None = None
    neo4j_uri: str = "bolt://neo4j:7687"
    neo4j_user: str = "neo4j"
    voyage_model: str = "voyage-code-3"
    embedding_cache_size: int = 10000
    duplicate_threshold: float = 0.85
    log_level: str = "INFO"
    log_format: str = "json"
    metrics_enabled: bool = True
    metrics_port: int = 9090

    class Config:
        env_file = ".env"
        case_sensitive = False
```

---

## 7. Security Infrastructure

### 7.1 Container Security

| Control | Implementation | Purpose |
|---------|----------------|---------|
| Non-root user | USER 1000:1000 | Principle of least privilege |
| Read-only project mount | :ro flag | Prevent accidental modification |
| Minimal base image | python:3.12-slim | Reduce attack surface |
| No privileged mode | Default | Container isolation |
| No extra capabilities | Default | Minimal permissions |

### 7.2 Network Security

| Control | Implementation | Purpose |
|---------|----------------|---------|
| Localhost binding | 127.0.0.1:port | Prevent external access |
| Internal network | Bridge network | Service isolation |
| No external ports | Only localhost | Workstation-only access |

### 7.3 Secrets Management

| Secret | Storage | Access Pattern |
|--------|---------|----------------|
| VOYAGE_API_KEY | .env file (gitignored) | Memory service only |
| NEO4J_PASSWORD | .env file (gitignored) | Memory service, Neo4j |
| QDRANT_API_KEY | .env file (gitignored) | Memory service, Qdrant |

**Security Requirements:**
- `.env` file must be in `.gitignore`
- Secrets never logged (redacted in logs)
- No secrets in Dockerfile or docker-compose.yml

### 7.4 File Permissions

| Path | Permissions | Owner | Purpose |
|------|-------------|-------|---------|
| /app | 755 | memoryuser | Application code |
| /app/cache | 755 | memoryuser | Writable cache |
| /project | 555 | root | Read-only project access |

---

## 8. Observability Infrastructure

### 8.1 Observability Strategy

| Component | Solution | Purpose |
|-----------|----------|---------|
| Logging | structlog (JSON) | Structured application logs |
| Metrics | prometheus-client | Performance metrics |
| Health | HTTP endpoints | Service health status |
| Tracing | Request IDs | Request correlation |

### 8.2 Logging Architecture

**Log Format:** JSON structured logging

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "logger": "memory_service.query_engine",
  "message": "Query executed successfully",
  "request_id": "abc123-def456",
  "query_type": "semantic_search",
  "duration_ms": 125,
  "result_count": 10,
  "context": {
    "memory_type": "code_pattern",
    "limit": 10
  }
}
```

**Log Levels:**

| Level | Use Case | Volume |
|-------|----------|--------|
| DEBUG | Detailed diagnostics | High (dev only) |
| INFO | Normal operations | Medium |
| WARNING | Potential issues | Low |
| ERROR | Failures with context | Low |

**Log Destinations:**

| Source | Destination | Retention |
|--------|-------------|-----------|
| memory-service | stdout | Docker logs |
| qdrant | stdout | Docker logs |
| neo4j | /logs volume | 7 days |

**View Logs:**

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f memory-service

# Filter by level (requires jq)
docker-compose logs memory-service | jq 'select(.level == "ERROR")'
```

### 8.3 Metrics Infrastructure

**Endpoint:** `http://localhost:9090/metrics`

**Format:** Prometheus exposition format

**Metrics Categories:**

| Category | Metrics | Labels |
|----------|---------|--------|
| Operations | `memory_operations_total` | operation, memory_type, status |
| Latency | `memory_operation_duration_seconds` | operation, memory_type |
| Cache | `embedding_cache_hits_total`, `embedding_cache_misses_total` | - |
| Database | `qdrant_operations_total`, `neo4j_operations_total` | operation, status |
| Errors | `memory_errors_total` | operation, error_type |
| Index | `index_files_total`, `index_functions_total` | language |

**Example Metrics:**

```
# HELP memory_operations_total Total memory operations
# TYPE memory_operations_total counter
memory_operations_total{operation="add",memory_type="code_pattern",status="success"} 1234
memory_operations_total{operation="search",memory_type="function_index",status="success"} 5678

# HELP memory_operation_duration_seconds Operation duration in seconds
# TYPE memory_operation_duration_seconds histogram
memory_operation_duration_seconds_bucket{operation="search",memory_type="semantic",le="0.1"} 850
memory_operation_duration_seconds_bucket{operation="search",memory_type="semantic",le="0.5"} 990
memory_operation_duration_seconds_bucket{operation="search",memory_type="semantic",le="1.0"} 999

# HELP embedding_cache_hits_total Embedding cache hits
# TYPE embedding_cache_hits_total counter
embedding_cache_hits_total 45678

# HELP embedding_cache_misses_total Embedding cache misses
# TYPE embedding_cache_misses_total counter
embedding_cache_misses_total 1234
```

### 8.4 Health Checks

**Memory Service Health Endpoint:** `GET http://localhost:9090/health`

**Response (Healthy):**

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "checks": {
    "qdrant": {
      "status": "healthy",
      "latency_ms": 5
    },
    "neo4j": {
      "status": "healthy",
      "latency_ms": 12
    },
    "embedding_cache": {
      "status": "healthy",
      "size": 5432,
      "max_size": 10000
    }
  }
}
```

**Response (Unhealthy):**

```json
{
  "status": "unhealthy",
  "version": "1.0.0",
  "checks": {
    "qdrant": {
      "status": "healthy",
      "latency_ms": 5
    },
    "neo4j": {
      "status": "unhealthy",
      "error": "Connection refused"
    },
    "embedding_cache": {
      "status": "healthy",
      "size": 5432,
      "max_size": 10000
    }
  }
}
```

**Container Health Checks:**

| Service | Endpoint | Interval | Timeout | Retries |
|---------|----------|----------|---------|---------|
| memory-service | http://localhost:9090/health | 30s | 10s | 3 |
| qdrant | http://localhost:6333/health | 30s | 10s | 3 |
| neo4j | http://localhost:7474 | 30s | 10s | 3 |

### 8.5 Status Endpoint

**Endpoint:** `GET http://localhost:9090/status`

**Response:**

```json
{
  "service": "memory-service",
  "version": "1.0.0",
  "uptime_seconds": 86400,
  "statistics": {
    "memories": {
      "total": 15234,
      "by_type": {
        "requirements": 156,
        "design": 89,
        "code_pattern": 234,
        "component_registry": 67,
        "function_index": 12456,
        "test_history": 890,
        "session_history": 45,
        "user_preferences": 12
      }
    },
    "index": {
      "files_indexed": 2345,
      "functions_indexed": 12456,
      "last_index_time": "2024-01-15T08:00:00Z"
    },
    "cache": {
      "embedding_cache_size": 5432,
      "embedding_cache_hit_rate": 0.87
    },
    "performance": {
      "avg_search_latency_ms": 125,
      "avg_write_latency_ms": 45
    }
  }
}
```

---

## 9. Operations

### 9.1 Deployment Commands

**Start Services:**

```bash
# Start all services in background
docker-compose up -d

# Start with build
docker-compose up -d --build

# View logs
docker-compose logs -f
```

**Stop Services:**

```bash
# Stop services (preserves data)
docker-compose stop

# Stop and remove containers (preserves volumes)
docker-compose down

# Stop and remove everything including volumes (DATA LOSS)
docker-compose down -v
```

**Restart Services:**

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart memory-service
```

### 9.2 MCP Configuration

**Claude Code MCP Configuration:**

Add to Claude Code's MCP configuration file:

```json
{
  "mcpServers": {
    "memory": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "memory-service",
        "python",
        "-m",
        "memory_service.mcp"
      ]
    }
  }
}
```

**Alternative (HTTP Transport):**

```json
{
  "mcpServers": {
    "memory": {
      "url": "http://localhost:8765/mcp"
    }
  }
}
```

### 9.3 Administrative Operations

**View Statistics:**

```bash
curl http://localhost:9090/status | jq
```

**Check Health:**

```bash
curl http://localhost:9090/health | jq
```

**View Metrics:**

```bash
curl http://localhost:9090/metrics
```

**Access Qdrant Dashboard:**

Open `http://localhost:6333/dashboard` in browser.

**Access Neo4j Browser:**

Open `http://localhost:7474` in browser. Login with configured credentials.

### 9.4 Troubleshooting

**Service Not Starting:**

```bash
# Check container logs
docker-compose logs memory-service

# Check container status
docker-compose ps

# Inspect container
docker inspect memory-service
```

**Database Connection Issues:**

```bash
# Test Qdrant connectivity
curl http://localhost:6333/health

# Test Neo4j connectivity
curl http://localhost:7474

# Check network
docker network inspect memory-network
```

**Memory Issues:**

```bash
# Check resource usage
docker stats

# Increase limits in docker-compose.yml if needed
```

---

## 10. Maintenance

### 10.1 Routine Maintenance

| Task | Frequency | Procedure |
|------|-----------|-----------|
| Log rotation | Weekly | Docker handles via json-file driver |
| Backup | Weekly | See Section 5.4 |
| Update images | Monthly | Pull new images, recreate containers |
| Memory normalization | As needed | Via MCP tool `normalize_memory` |

### 10.2 Image Updates

```bash
# Pull latest images
docker-compose pull

# Recreate containers with new images
docker-compose up -d --force-recreate

# Verify health
curl http://localhost:9090/health
```

### 10.3 Volume Management

**List Volumes:**

```bash
docker volume ls | grep memory
```

**Inspect Volume:**

```bash
docker volume inspect memory-qdrant-data
```

**Clean Unused Volumes:**

```bash
# Remove only unused volumes (safe)
docker volume prune
```

---

## 11. Disaster Recovery

### 11.1 Recovery Scenarios

| Scenario | RTO | RPO | Procedure |
|----------|-----|-----|-----------|
| Container crash | < 1 min | 0 | Automatic restart |
| Service corruption | < 5 min | Last backup | Restore from volume backup |
| Volume loss | < 30 min | Last backup | Restore from backup |
| Complete failure | < 1 hour | Last backup | Full restore procedure |

### 11.2 Recovery Procedure

**From Container Crash:**
Automatic via `restart: unless-stopped` policy.

**From Volume Corruption:**

```bash
# Stop services
docker-compose down

# Remove corrupted volume
docker volume rm memory-qdrant-data

# Restore from backup
docker volume create memory-qdrant-data
docker run --rm -v memory-qdrant-data:/data -v $(pwd)/backup:/backup \
    alpine tar xzf /backup/qdrant-backup.tar.gz -C /data

# Restart
docker-compose up -d
```

**From Complete Failure:**

1. Install Docker and Docker Compose
2. Clone repository
3. Copy `.env` from backup
4. Restore all volumes from backup
5. Start services: `docker-compose up -d`

---

## 12. Development Environment

### 12.1 Development Compose Override

**File:** `docker-compose.dev.yml`

```yaml
version: "3.8"

services:
  memory-service:
    build:
      context: .
      dockerfile: Dockerfile.dev
    volumes:
      - ./src:/app/src:ro
      - memory-service-cache:/app/cache
      - ${PROJECT_PATH}:/project:ro
    environment:
      - LOG_LEVEL=DEBUG
      - LOG_FORMAT=text
    command: ["python", "-m", "memory_service", "--reload"]
```

**Usage:**

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### 12.2 Development Dockerfile

**File:** `Dockerfile.dev`

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dev dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

# Dev user
RUN useradd -m devuser
USER devuser

EXPOSE 9090 8765

CMD ["python", "-m", "memory_service"]
```

---

## 13. Scaling Considerations

### 13.1 Vertical Scaling

| Resource | Current | Maximum Tested | Notes |
|----------|---------|----------------|-------|
| Memory Service RAM | 2GB | 4GB | Increase for larger caches |
| Qdrant RAM | 4GB | 16GB | Scale with vector count |
| Neo4j RAM | 2GB | 8GB | Scale with graph size |

### 13.2 Scale Triggers

| Metric | Threshold | Action |
|--------|-----------|--------|
| Qdrant memory > 80% | 3.2GB | Increase limit to 8GB |
| Neo4j heap > 90% | 900MB | Increase max heap to 2GB |
| Search latency > 500ms | P95 | Review index configuration |

### 13.3 Capacity Limits

Per requirements:

| Resource | Target Capacity | Infrastructure Needed |
|----------|-----------------|----------------------|
| Source files | 100,000 | Default configuration |
| Total memories | 1,000,000 | Qdrant: 8GB RAM |
| Function index | 500,000 | Qdrant: 8GB RAM |

---

## 14. Constraints and Assumptions

### 14.1 Technical Constraints

| Constraint | Source | Impact |
|------------|--------|--------|
| Single workstation | Requirements | No distributed deployment |
| Docker required | Architecture | Must have Docker installed |
| 8GB minimum RAM | Resource requirements | Sum of all containers |
| Voyage API access | Embedding requirement | Internet connectivity needed |

### 14.2 Assumptions

| Assumption | Rationale | Risk if Invalid |
|------------|-----------|-----------------|
| Developer has Docker | Standard dev tooling | Cannot deploy |
| 8GB+ RAM available | Workstation standard | Performance issues |
| Stable internet | Voyage API calls | Embedding failures (fallback available) |
| Single user | Requirements scope | No multi-user issues |

---

## 15. Glossary

| Term | Definition |
|------|------------|
| Docker Compose | Tool for defining multi-container Docker applications |
| Named Volume | Docker volume with explicit name for persistence |
| Bridge Network | Default Docker network type for container communication |
| Health Check | Periodic check to verify service availability |
| MCP | Model Context Protocol - AI tool integration standard |

---

## Appendix A: Quick Reference

### A.1 Common Commands

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Logs
docker-compose logs -f

# Status
docker-compose ps

# Health
curl http://localhost:9090/health

# Metrics
curl http://localhost:9090/metrics

# Rebuild
docker-compose up -d --build
```

### A.2 Port Reference

| Port | Service | Protocol |
|------|---------|----------|
| 9090 | memory-service (health/metrics) | HTTP |
| 8765 | memory-service (MCP HTTP) | HTTP |
| 6333 | Qdrant REST | HTTP |
| 6334 | Qdrant gRPC | gRPC |
| 7474 | Neo4j Browser | HTTP |
| 7687 | Neo4j Bolt | Bolt |

### A.3 Volume Reference

| Volume | Path | Purpose |
|--------|------|---------|
| memory-service-cache | /app/cache | Embedding cache |
| memory-qdrant-data | /qdrant/storage | Vector data |
| memory-neo4j-data | /data | Graph data |
| memory-neo4j-logs | /logs | Neo4j logs |

---

## Appendix B: Reference Documents

| Document | Location | Purpose |
|----------|----------|---------|
| Requirements | requirement-docs/requirements-memory-docs.md | Source requirements |
| Architecture | project-docs/002-architecture-memory-mcp.md | System architecture |
| Backend Design | design-docs/20-backend-design.md | Service implementation |
| Integration Design | design-docs/50-integration-design.md | MCP API contracts |
| Security Design | design-docs/03-security-architecture.md | Security controls |
