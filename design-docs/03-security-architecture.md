# Design Document: Security Architecture

## Document Control

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Status | Draft |
| Sequence | 002 |
| Component | Security Layer |

---

## 1. Introduction

### 1.1 Purpose

This document defines the security architecture for the Claude Code Long-Term Memory System. It covers authentication, authorization, secrets management, network security, data protection, and security monitoring appropriate for a single-developer workstation deployment.

### 1.2 Scope

**Included:**
- Authentication for database connections
- Secrets management for API keys
- Network isolation and binding
- Container security hardening
- Data protection in transit and at rest
- Audit logging

**Excluded:**
- Multi-user access control (single user system)
- Enterprise IAM integration
- Compliance certifications (SOC2, HIPAA)
- Production-grade security operations

### 1.3 Requirements Traceability

| Requirement ID | Requirement Summary | Design Section |
|----------------|---------------------|----------------|
| REQ-MEM-SEC-001 | API keys in environment variables | 10.2 |
| REQ-MEM-SEC-002 | Localhost binding | 6.2 |
| REQ-MEM-SEC-003 | Non-root containers | 9.2 |
| REQ-MEM-SEC-004 | Database authentication | 5.3 |
| REQ-MEM-SEC-005 | External transmission limits | 8.1 |

---

## 2. Security Context

### 2.1 System Overview

The Claude Code Long-Term Memory System runs on a single developer's workstation as a Docker Compose deployment. All services communicate over a Docker network with no external exposure except for Voyage AI API calls.

### 2.2 Security Objectives

| Objective | Description | Priority |
|-----------|-------------|----------|
| Confidentiality | Protect source code and memories from unauthorized access | High |
| Integrity | Ensure memory data is not corrupted or tampered | High |
| Availability | Maintain system availability during development | Medium |
| Non-repudiation | N/A (single user) | N/A |
| Privacy | Protect developer's code from external exposure | High |

### 2.3 Data Classification

| Data Type | Classification | Examples | Handling Requirements |
|-----------|----------------|----------|----------------------|
| Source Code | Confidential | Indexed functions, patterns | No external transmission except Voyage |
| Memory Content | Internal | Decisions, requirements | Docker volume storage |
| Embeddings | Internal | Vector representations | Sent to Voyage API |
| Credentials | Secret | API keys, DB passwords | Environment variables only |
| Logs | Internal | Operational logs | Sanitize before output |

### 2.4 Trust Boundaries

| Boundary | Description | What Crosses | Trust Change |
|----------|-------------|--------------|--------------|
| Host <-> Container | Docker isolation | Named volumes, ports | Host trusted, container untrusted |
| Container <-> Container | Docker network | Database connections | Mutual trust within network |
| Container <-> Voyage | Internet egress | Embeddings | Voyage API trusted for embedding only |
| Claude Code <-> MCP | stdio | Tool invocations | Claude Code trusted |

---

## 3. Threat Model

### 3.1 Threat Modeling Methodology

STRIDE methodology applied to single-developer workstation context.

### 3.2 Assets

| Asset | Description | Value | Impact if Compromised |
|-------|-------------|-------|----------------------|
| Source Code | Indexed codebase | High | IP theft, competitive disadvantage |
| Memory Content | Development decisions | Medium | Knowledge loss |
| Voyage API Key | Embedding service access | Medium | Unauthorized API usage, billing |
| Database Contents | Memories and relationships | High | Data loss, manipulation |

### 3.3 Threat Actors

| Actor | Motivation | Capability | Likelihood |
|-------|------------|------------|------------|
| Malicious Local Process | Data exfiltration | Medium | Low |
| Network Attacker | API key theft | High | Low (localhost only) |
| Container Escape | Host compromise | High | Very Low |

### 3.4 Threats

#### T1: API Key Exposure

**Category:** Information Disclosure

**Description:** Voyage API key exposed in logs, code, or configuration files.

**Impact:** Unauthorized API usage, potential billing impact.

**Likelihood:** Medium

**Risk Rating:** Medium

**Mitigations:** 10.2 (Secrets Management), 10.6 (Secrets in Code Prevention)

#### T2: Unauthorized Network Access

**Category:** Tampering / Information Disclosure

**Description:** External network access to MCP or HTTP server.

**Impact:** Memory manipulation or extraction.

**Likelihood:** Low (localhost binding)

**Risk Rating:** Low

**Mitigations:** 6.2 (Network Segmentation)

#### T3: Container Privilege Escalation

**Category:** Elevation of Privilege

**Description:** Attacker escapes container to host.

**Impact:** Full system compromise.

**Likelihood:** Very Low

**Risk Rating:** Low

**Mitigations:** 9.2 (Container Security)

#### T4: Data Exfiltration via Logs

**Category:** Information Disclosure

**Description:** Sensitive data (code, secrets) exposed in logs.

**Impact:** Code or credential exposure.

**Likelihood:** Medium

**Risk Rating:** Medium

**Mitigations:** 11.2 (Log Collection), 8.4 (Audit Logging)

### 3.5 Threat Summary

| Threat | Category | Risk Rating | Primary Mitigation |
|--------|----------|-------------|-------------------|
| API Key Exposure | Disclosure | Medium | Secrets management |
| Unauthorized Network | Tampering | Low | Localhost binding |
| Container Escape | Elevation | Low | Non-root containers |
| Log Exfiltration | Disclosure | Medium | Log sanitization |

---

## 4. Security Architecture Overview

### 4.1 Security Architecture Principles

#### Principle: Defense in Depth

**Definition:** Multiple layers of security controls.

**Application:** Network isolation + container hardening + secrets management.

#### Principle: Least Privilege

**Definition:** Minimal permissions for each component.

**Application:** Non-root containers, read-only file systems where possible.

#### Principle: Fail Secure

**Definition:** System fails to a secure state.

**Application:** Missing secrets prevent startup rather than defaulting.

#### Principle: Security by Default

**Definition:** Secure configuration out of the box.

**Application:** Localhost binding, non-root user, minimal capabilities.

### 4.2 Defense in Depth

| Layer | Controls | Purpose |
|-------|----------|---------|
| Perimeter | Localhost binding | No external network access |
| Network | Docker network isolation | Service-to-service only |
| Host | Non-root containers | Limit container privileges |
| Application | Input validation | Prevent injection attacks |
| Data | Volume encryption (optional) | Protect at rest |

### 4.3 Security Zones

| Zone | Description | Trust Level | Controls |
|------|-------------|-------------|----------|
| Host | Developer workstation | Full trust | OS security |
| Memory Network | Docker bridge network | Service trust | Network isolation |
| External | Internet (Voyage only) | Partial trust | HTTPS only |

---

## 5. Identity and Access Management

### 5.1 IAM Strategy

Single-user system with service-level authentication for database connections. No user authentication required for MCP interface (inherently local via stdio).

### 5.2 Identity Management

#### Service Identities

| Service | Identity Type | Provisioning | Rotation |
|---------|---------------|--------------|----------|
| Memory Service | Environment credentials | Manual | Annual |
| Qdrant | API key (optional) | Manual | Annual |
| Neo4j | Username/password | Manual | Annual |

### 5.3 Authentication Design

#### Service Authentication

| Pattern | Use Case | Implementation |
|---------|----------|----------------|
| API Key | Qdrant connection | QDRANT_API_KEY env var |
| Username/Password | Neo4j connection | NEO4J_USER, NEO4J_PASSWORD env vars |
| API Key | Voyage AI | VOYAGE_API_KEY env var |

**Session Management:** N/A (stateless service connections with connection pooling).

### 5.4 Authorization Design

**Authorization Model:** Service accounts with full access to respective databases.

No fine-grained authorization required for single-user system.

---

## 6. Network Security

### 6.1 Network Security Strategy

All services bind to localhost or Docker internal network. No external ports exposed.

### 6.2 Network Segmentation

| Segment | Purpose | Access Restrictions |
|---------|---------|---------------------|
| memory-network | Inter-service communication | Docker-internal only |
| Host localhost | MCP and HTTP endpoints | 127.0.0.1 only |

### 6.3 Firewall Rules (Docker Network)

| Rule | Source | Destination | Port/Protocol | Action |
|------|--------|-------------|---------------|--------|
| MCP | Host (stdio) | memory-service | N/A (stdio) | Allow |
| HTTP Health | Host | memory-service | 9090/TCP | Allow |
| Qdrant | memory-service | qdrant | 6333/TCP | Allow |
| Neo4j | memory-service | neo4j | 7687/TCP | Allow |
| Voyage | memory-service | api.voyageai.com | 443/TCP | Allow |
| Default | Any | Any | Any | Deny |

### 6.4 Service Binding

| Service | Bind Address | Port | Exposure |
|---------|--------------|------|----------|
| MCP Server | N/A (stdio) | N/A | Local process only |
| HTTP Server | 127.0.0.1 | 9090 | Localhost only |
| Qdrant | 0.0.0.0 | 6333 | Docker network only |
| Neo4j | 0.0.0.0 | 7474, 7687 | Docker network only |

---

## 7. Application Security

### 7.1 Secure Development Practices

| Practice | Implementation | Enforcement |
|----------|----------------|-------------|
| Secure Coding Standards | Google Python Style Guide | Code review |
| Type Safety | Python type hints + mypy | CI checks |
| Dependency Scanning | pip-audit, safety | CI pipeline |

### 7.2 Input Validation

| Input Type | Validation Approach | Implementation |
|------------|---------------------|----------------|
| MCP Tool Parameters | Pydantic schema validation | JSON Schema |
| File Paths | Whitelist base directory | Path validation |
| Cypher Queries | Parameterized queries only | Neo4j driver |
| Memory Content | Size limits, encoding validation | Application layer |

### 7.3 Output Encoding

| Context | Encoding | Implementation |
|---------|----------|----------------|
| JSON Responses | UTF-8, escape special chars | Pydantic serialization |
| Log Output | Sanitize secrets | structlog processors |
| Database Queries | Parameterization | Driver-level |

### 7.4 API Security

| Control | Implementation | Endpoints |
|---------|----------------|-----------|
| Rate Limiting | N/A (single user) | - |
| Request Validation | Pydantic schemas | All MCP tools |
| Response Filtering | No sensitive data in responses | All endpoints |

### 7.5 Dependency Security

**Vulnerability Scanning:** pip-audit in CI pipeline.

**Update Policy:** Security patches applied within 7 days of disclosure.

**Approved Sources:** PyPI (public), no private registries.

---

## 8. Data Security

### 8.1 Data Security Strategy

Minimize data exposure by:
- Storing all data locally in Docker volumes
- Only transmitting content to Voyage AI for embedding
- No telemetry or analytics data collection

### 8.2 Encryption at Rest

| Data Store | Encryption | Key Type | Key Management |
|------------|------------|----------|----------------|
| Qdrant | Volume-level (optional) | Host-managed | Docker volume encryption |
| Neo4j | Volume-level (optional) | Host-managed | Docker volume encryption |
| SQLite Cache | Volume-level (optional) | Host-managed | Docker volume encryption |

**Note:** At-rest encryption is optional for workstation deployment. Enable via Docker volume encryption if required.

### 8.3 Encryption in Transit

| Connection | Protocol | Minimum Version | Certificate |
|------------|----------|-----------------|-------------|
| Voyage AI | TLS | 1.2 | Voyage CA |
| Qdrant (internal) | Plaintext | N/A | N/A (Docker network) |
| Neo4j (internal) | Plaintext | N/A | N/A (Docker network) |

**Rationale:** Internal Docker network traffic is isolated. External (Voyage) uses TLS.

### 8.4 Audit Logging

| Event | Data Logged | Retention |
|-------|-------------|-----------|
| Memory CRUD | Operation type, memory ID, timestamp | 30 days |
| Search Queries | Query text (truncated), result count | 7 days |
| Tool Invocations | Tool name, execution time, status | 30 days |
| Errors | Error type, context (no secrets) | 30 days |

---

## 9. Infrastructure Security

### 9.1 Cloud Security

N/A - Local Docker deployment only.

### 9.2 Container Security

| Control | Implementation |
|---------|----------------|
| Base Image Security | python:3.12-slim (official image) |
| Image Scanning | trivy in CI pipeline |
| Runtime Security | Read-only root filesystem (where possible) |
| Non-root User | USER directive in Dockerfile |
| Minimal Capabilities | Drop all, add only required |
| Secrets Management | Environment variables, not baked in |

**Dockerfile Security Directives:**

```dockerfile
# Non-root user
RUN useradd -m -u 1000 memuser
USER memuser

# Read-only where possible
# (Note: Qdrant and Neo4j require writable volumes)
```

### 9.3 Host Security

| Control | Implementation |
|---------|----------------|
| OS Hardening | Developer responsibility |
| Patch Management | Developer responsibility |
| File Permissions | Docker volumes owned by container user |

---

## 10. Secrets Management

### 10.1 Secrets Management Strategy

All secrets stored as environment variables, provided via .env file (git-ignored) or Docker Compose environment section. No secrets in code or committed files.

### 10.2 Secrets Inventory

| Secret | Classification | Type | Storage | Rotation |
|--------|----------------|------|---------|----------|
| VOYAGE_API_KEY | High | API Key | Environment variable | Manual/Annual |
| NEO4J_PASSWORD | Medium | Password | Environment variable | Manual/Annual |
| QDRANT_API_KEY | Medium | API Key | Environment variable | Manual/Annual (if enabled) |

### 10.3 Secrets Storage Architecture

```
.env (git-ignored)
    |
    v
Docker Compose
    |
    +-- memory-service (env vars)
    +-- qdrant (env vars)
    +-- neo4j (env vars)
```

**Access Control:** File permissions on .env (600), owned by developer.

### 10.4 Secrets Rotation

| Secret Type | Rotation Frequency | Automation | Procedure |
|-------------|-------------------|------------|-----------|
| VOYAGE_API_KEY | Annual or on compromise | Manual | Generate new key in Voyage console, update .env |
| NEO4J_PASSWORD | Annual | Manual | Update .env, restart containers |

### 10.5 Emergency Secret Rotation

**Trigger Conditions:**

| Trigger | Severity | Response Time | Procedure |
|---------|----------|---------------|-----------|
| Suspected compromise | Critical | Immediate | Revoke key, generate new, restart services |
| Key exposure in logs | High | 24 hours | Rotate affected key |

### 10.6 Secrets in Code Prevention

| Control | Implementation | Enforcement |
|---------|----------------|-------------|
| Pre-commit hooks | detect-secrets | Developer setup |
| .gitignore | .env, *.key | Repository |
| Code review | Manual check | Pull request |

**Secret Detection Patterns:**

| Pattern | Examples | Tool |
|---------|----------|------|
| API keys | VOYAGE_*, voyage_api_key | detect-secrets |
| Passwords | password=, NEO4J_PASSWORD | detect-secrets |
| Private keys | -----BEGIN RSA | detect-secrets |

### 10.7 Local Development Secrets

| Approach | Security Level | Setup Complexity | Recommended For |
|----------|----------------|------------------|-----------------|
| .env file (git-ignored) | Medium | Easy | All local development |

**Local Development Policy:**

- Never commit .env to version control
- Use .env.example with placeholder values
- Separate development and production API keys (if applicable)

### 10.8 Secret Injection Patterns

| Pattern | Use Case | Security | Implementation |
|---------|----------|----------|----------------|
| Environment variables | All secrets | Medium | Docker Compose env_file |

---

## 11. Security Monitoring and Detection

### 11.1 Security Monitoring Strategy

Lightweight monitoring appropriate for developer workstation:
- Structured logging with security context
- No dedicated SIEM (not cost-effective for single user)
- Manual review of logs as needed

### 11.2 Log Collection

| Log Source | Events Collected | Retention | Storage |
|------------|------------------|-----------|---------|
| memory-service | All operations | 30 days | Docker logs |
| qdrant | Errors only | 30 days | Docker logs |
| neo4j | Errors only | 30 days | Docker logs |

**Log Format:** JSON structured logging with fields:
- timestamp
- level
- service
- operation
- request_id (for correlation)
- error (if applicable)

**Sensitive Data:** API keys and passwords redacted before logging.

### 11.3 Security Alerting

Not implemented for single-user workstation deployment.

---

## 12. Incident Response

### 12.1 Incident Response Plan

For single-developer deployment, incident response is simplified:

| Severity | Criteria | Response |
|----------|----------|----------|
| High | API key compromised | Immediate rotation |
| Medium | Service compromise suspected | Stop containers, investigate |
| Low | Minor security issue | Address in next update |

### 12.2 Incident Response Process

1. **Detection:** Developer notices unusual behavior
2. **Containment:** Stop Docker containers
3. **Investigation:** Review logs, check for data access
4. **Recovery:** Rotate secrets, restart services
5. **Lessons Learned:** Update security controls if needed

---

## 13. Security Testing

### 13.1 Security Testing Strategy

| Test Type | Frequency | Scope | Tools |
|-----------|-----------|-------|-------|
| Dependency Scanning | Every build | Python dependencies | pip-audit, safety |
| Container Scanning | Every build | Docker images | trivy |
| Secret Scanning | Pre-commit | All files | detect-secrets |

### 13.2 Vulnerability Management

**Remediation SLAs:**

| Severity | Remediation Timeline |
|----------|---------------------|
| Critical | Immediate |
| High | 7 days |
| Medium | 30 days |
| Low | 90 days |

---

## 14. Dependency Security Policies

### 14.1 License Policies

**License Allowlist:**

| License | Status | Rationale |
|---------|--------|-----------|
| MIT | Approved | Permissive |
| Apache 2.0 | Approved | Permissive, patent grant |
| BSD 2/3-Clause | Approved | Permissive |
| ISC | Approved | Permissive |

**License Blocklist:**

| License | Status | Rationale |
|---------|--------|-----------|
| GPL v2/v3 | Review Required | Copyleft considerations |
| AGPL | Prohibited | Network copyleft |

### 14.2 Vulnerability Policies

| Severity | CVSS Score | Deployment Policy | Remediation SLA |
|----------|------------|-------------------|-----------------|
| Critical | 9.0 - 10.0 | Block deployment | Immediate |
| High | 7.0 - 8.9 | Block deployment | 7 days |
| Medium | 4.0 - 6.9 | Warning | 30 days |
| Low | 0.1 - 3.9 | Track | 90 days |

### 14.3 Dependency Update Policy

| Update Type | Frequency | Automation | Review |
|-------------|-----------|------------|--------|
| Security patches | Immediate | Dependabot alerts | Required |
| Minor versions | Monthly | Manual | Optional |
| Major versions | Quarterly | Manual | Required |

---

## 15. Constraints and Assumptions

### 15.1 Security Constraints

| Constraint | Source | Impact on Design |
|------------|--------|------------------|
| Single user | Requirements | No multi-user auth needed |
| Workstation deployment | Requirements | No network-level security controls |
| External Voyage API | Requirements | Must transmit embeddings externally |
| Docker deployment | Requirements | Container-based isolation |

### 15.2 Assumptions

| Assumption | Rationale | Risk if Invalid |
|------------|-----------|-----------------|
| Developer workstation is trusted | Single user system | Compromised host = full access |
| Voyage AI is trustworthy | Established vendor | Embedding data exposure |
| Docker network is isolated | Docker default behavior | Container escape = network access |

---

## 16. Risks and Open Questions

### 16.1 Residual Risks

| Risk | Likelihood | Impact | Residual Risk | Acceptance |
|------|------------|--------|---------------|------------|
| API key exposure via logs | Low | Medium | Low | Accepted with log sanitization |
| Container escape | Very Low | High | Low | Accepted with hardening |
| Voyage API compromise | Very Low | Medium | Low | Accepted (vendor risk) |

### 16.2 Open Questions

| Question | Owner | Target Resolution Date |
|----------|-------|------------------------|
| Enable Qdrant authentication? | Developer | At deployment |
| Enable volume encryption? | Developer | Based on data sensitivity |

---

## 17. Glossary

| Term | Definition |
|------|------------|
| Container Escape | Breaking out of container isolation to host |
| STRIDE | Spoofing, Tampering, Repudiation, Information Disclosure, DoS, Elevation |
| Defense in Depth | Multiple overlapping security controls |
| Least Privilege | Minimal permissions required for function |

---

## Appendix A: Security Checklist

### Pre-Deployment Checklist

- [ ] .env file created with all required secrets
- [ ] .env file permissions set to 600
- [ ] .gitignore includes .env
- [ ] Docker images pulled from official sources
- [ ] No secrets in docker-compose.yml (use env_file)
- [ ] Containers run as non-root
- [ ] detect-secrets pre-commit hook installed

### Operational Checklist

- [ ] Rotate Voyage API key annually
- [ ] Review Docker logs periodically
- [ ] Keep base images updated
- [ ] Run dependency vulnerability scans

---

## Appendix B: Reference Documents

| Document | Version | Relevance |
|----------|---------|-----------|
| requirements-memory-docs.md | 1.0 | Security requirements |
| OWASP Docker Security | Current | Container hardening |
| CIS Docker Benchmark | Current | Security baseline |
