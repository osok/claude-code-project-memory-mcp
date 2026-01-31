# Security Review Report
Seq: 002
Reviewer: Code-Reviewer-Security

## Summary
- Critical: 0
- High: 3
- Medium: 5
- Low: 4
- Info: 3

## Executive Summary

The Claude Code Long-Term Memory System demonstrates generally good security practices including SecretStr for credentials, structured logging with sanitization, parameterized Neo4j queries, and Docker container hardening. However, several high-severity issues require attention before production deployment, particularly around file path handling, Cypher query validation bypass, and network exposure.

---

## High Findings

### SEC-001: Cypher Injection via Pattern Bypass
- **File:** `/ai/work/claude-code/claude-code-project-memory-mcp/src/memory_service/core/query_engine.py:606-629`
- **Category:** A03: Injection
- **Description:** The `_validate_cypher` method uses simple string matching to block dangerous Cypher operations. This approach can be bypassed using case variations, unicode characters, or comment injection.
- **Evidence:**
```python
def _validate_cypher(self, cypher: str) -> None:
    dangerous_patterns = [
        "CREATE", "DELETE", "DETACH", "SET", "REMOVE", "MERGE", "DROP", "CALL",
    ]
    upper_cypher = cypher.upper()
    for pattern in dangerous_patterns:
        if pattern in upper_cypher:
            raise ValueError(f"Query contains forbidden operation: {pattern}")
```
- **Attack Vectors:**
  - Unicode lookalikes: `CREAT\u0395` (Greek Epsilon)
  - Comment injection: `/**/CREATE/**/`
  - Although `upper()` handles basic case, more sophisticated bypasses exist
- **Recommendation:**
  1. Use Neo4j's query parsing capabilities to analyze query structure
  2. Implement allowlist-based validation instead of blocklist
  3. Use read-only database connections/roles for query endpoint
  4. Add query execution timeout limits
- **References:** CWE-89, OWASP A03:2021

### SEC-002: Path Traversal in File Indexing Operations
- **File:** `/ai/work/claude-code/claude-code-project-memory-mcp/src/memory_service/api/tools/indexing.py:10-49`
- **Category:** A01: Broken Access Control
- **Description:** The `index_file` and `index_directory` tools accept user-provided file paths without validating they are within the allowed project directory. An attacker could potentially index files outside the mounted project directory.
- **Evidence:**
```python
async def index_file(params: dict[str, Any]) -> dict[str, Any]:
    file_path = params.get("file_path")
    # ... no path validation
    result = await indexer.index_file(file_path, force=force)
```
- **Attack Scenarios:**
  - `index_file("/etc/passwd")` - index system files
  - `index_file("../../sensitive/config.py")` - traverse outside project
- **Recommendation:**
  1. Validate all file paths are within `settings.project_path`
  2. Use `Path.resolve()` to canonicalize paths and check containment
  3. Implement path validation utility function:
  ```python
  def validate_path(path: str, root: str) -> Path:
      resolved = Path(path).resolve()
      root_resolved = Path(root).resolve()
      if not str(resolved).startswith(str(root_resolved)):
          raise ValueError("Path traversal detected")
      return resolved
  ```
- **References:** CWE-22, OWASP A01:2021

### SEC-003: Arbitrary File Write via Export Function
- **File:** `/ai/work/claude-code/claude-code-project-memory-mcp/src/memory_service/api/tools/maintenance.py:252-262`
- **Category:** A01: Broken Access Control
- **Description:** The `export_memory` function accepts an arbitrary `output_path` and writes to it without validation, enabling writes to arbitrary filesystem locations.
- **Evidence:**
```python
if output_path:
    # Write to file
    with open(output_path, "w") as f:
        for item in export_data:
            f.write(json.dumps(item, default=str) + "\n")
```
- **Attack Scenarios:**
  - Overwrite system files: `output_path="/etc/cron.d/malicious"`
  - Write to sensitive locations: `output_path="~/.ssh/authorized_keys"`
- **Recommendation:**
  1. Validate `output_path` is within an allowed export directory
  2. Restrict output to a specific export folder within project path
  3. Never allow absolute paths starting with `/` or containing `..`
- **References:** CWE-22, CWE-73, OWASP A01:2021

---

## Medium Findings

### SEC-004: HTTP Server Binds to All Interfaces
- **File:** `/ai/work/claude-code/claude-code-project-memory-mcp/src/memory_service/__main__.py:73-78`
- **Category:** A05: Security Misconfiguration
- **Description:** The HTTP server binds to `0.0.0.0` which exposes health, metrics, and status endpoints to all network interfaces, potentially exposing internal information.
- **Evidence:**
```python
http_config = uvicorn.Config(
    http_app,
    host="0.0.0.0",
    port=settings.metrics_port,
    log_level="warning",
)
```
- **Recommendation:**
  1. Make the bind address configurable via settings
  2. Default to `127.0.0.1` for local deployments
  3. Use `0.0.0.0` only when explicitly configured for container environments
  4. Add authentication to status endpoint which reveals internal counts
- **References:** CWE-668, OWASP A05:2021

### SEC-005: Arbitrary File Read via Import Function
- **File:** `/ai/work/claude-code/claude-code-project-memory-mcp/src/memory_service/api/tools/maintenance.py:297-304`
- **Category:** A01: Broken Access Control
- **Description:** The `import_memory` function reads from arbitrary file paths without validation.
- **Evidence:**
```python
if input_path:
    with open(input_path) as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))
```
- **Recommendation:** Same as SEC-003 - validate paths are within allowed directories
- **References:** CWE-22, OWASP A01:2021

### SEC-006: Neo4j Default Password Fallback
- **File:** `/ai/work/claude-code/claude-code-project-memory-mcp/docker/docker-compose.yml:19,72`
- **Category:** A07: Authentication Failures
- **Description:** Docker Compose uses a default password fallback which could lead to weak credentials in development/test environments being accidentally used in production.
- **Evidence:**
```yaml
- NEO4J_PASSWORD=${NEO4J_PASSWORD:-password}
- NEO4J_AUTH=neo4j/${NEO4J_PASSWORD:-password}
```
- **Recommendation:**
  1. Remove default password fallback
  2. Require explicit password configuration
  3. Add validation to fail startup if password is weak or default
  4. Document strong password requirements
- **References:** CWE-521, OWASP A07:2021

### SEC-007: Qdrant and Neo4j Ports Exposed to Host
- **File:** `/ai/work/claude-code/claude-code-project-memory-mcp/docker/docker-compose.yml:48-49,69-70`
- **Category:** A05: Security Misconfiguration
- **Description:** Database ports are mapped to the host, potentially exposing them to the network. While useful for development, production deployments should not expose these ports.
- **Evidence:**
```yaml
qdrant:
  ports:
    - "6333:6333"
    - "6334:6334"

neo4j:
  ports:
    - "7474:7474"
    - "7687:7687"
```
- **Recommendation:**
  1. Create a production compose file without port mappings
  2. Or bind to localhost: `127.0.0.1:6333:6333`
  3. Document that these ports should not be exposed in production
  4. Use network policies to restrict access
- **References:** CWE-668, OWASP A05:2021

### SEC-008: Information Disclosure in Status Endpoint
- **File:** `/ai/work/claude-code/claude-code-project-memory-mcp/src/memory_service/api/http_server.py:90-132`
- **Category:** A05: Security Misconfiguration
- **Description:** The `/status` endpoint exposes detailed internal information including collection counts, node counts, and error details without authentication.
- **Evidence:**
```python
@app.get("/status")
async def status() -> JSONResponse:
    # Returns detailed storage info, collection counts, node counts
    status_data["storage"]["qdrant"]["error"] = str(e)  # Exposes error details
```
- **Recommendation:**
  1. Remove or protect the `/status` endpoint with authentication
  2. Don't expose internal error messages
  3. Consider making this endpoint optional/disabled by default
- **References:** CWE-200, OWASP A05:2021

---

## Low Findings

### SEC-009: Weak Input Validation in MCP Server
- **File:** `/ai/work/claude-code/claude-code-project-memory-mcp/src/memory_service/api/mcp_server.py:644-659`
- **Category:** A03: Injection
- **Description:** Input validation only checks for required fields but doesn't validate types, ranges, or format constraints defined in the schema.
- **Evidence:**
```python
def _validate_input(self, tool_name: str, args: dict[str, Any]) -> None:
    schema = self._tool_schemas.get(tool_name, {})
    required = schema.get("required", [])
    for field in required:
        if field not in args:
            raise ValidationError(f"Missing required field: {field}")
```
- **Recommendation:** Use pydantic or jsonschema for full schema validation
- **References:** CWE-20, OWASP A03:2021

### SEC-010: Development Password in dev Compose File
- **File:** `/ai/work/claude-code/claude-code-project-memory-mcp/docker/docker-compose.dev.yml:32`
- **Category:** A07: Authentication Failures
- **Description:** Hardcoded weak password in development configuration.
- **Evidence:**
```yaml
- NEO4J_AUTH=neo4j/devpassword
```
- **Recommendation:**
  1. Use environment variable even in dev
  2. Add comment warning not to use in production
  3. Consider using secrets management even for dev
- **References:** CWE-798, OWASP A07:2021

### SEC-011: Embedding Cache in Persistent Volume
- **File:** `/ai/work/claude-code/claude-code-project-memory-mcp/src/memory_service/storage/cache.py`
- **Category:** A02: Cryptographic Failures
- **Description:** The embedding cache stores data in SQLite without encryption. While embeddings are not directly sensitive, they could potentially be used to infer information about indexed content.
- **Evidence:** Cache stores embeddings as raw binary blobs without encryption
- **Recommendation:** Consider encrypting cache if it may contain embeddings of sensitive code
- **References:** CWE-311, OWASP A02:2021

### SEC-012: Graph Query Results Not Limited
- **File:** `/ai/work/claude-code/claude-code-project-memory-mcp/src/memory_service/core/query_engine.py:167-196`
- **Category:** A04: Insecure Design
- **Description:** The `graph_query` function executes arbitrary Cypher queries without enforcing result limits, potentially enabling DoS through expensive queries.
- **Evidence:**
```python
async def graph_query(self, cypher: str, parameters: dict[str, Any] | None = None):
    self._validate_cypher(cypher)
    results = await self.neo4j.execute_cypher(cypher, parameters)
    # No LIMIT enforcement
```
- **Recommendation:**
  1. Enforce maximum LIMIT clause in all queries
  2. Add query timeout at database connection level
  3. Monitor and alert on slow queries
- **References:** CWE-400, OWASP A04:2021

---

## Informational

### SEC-013: Good Practice - SecretStr for Credentials
- **File:** `/ai/work/claude-code/claude-code-project-memory-mcp/src/memory_service/config.py`
- **Category:** A02: Cryptographic Failures (Positive)
- **Description:** Proper use of `pydantic.SecretStr` for sensitive configuration values prevents accidental logging of secrets.
- **Evidence:**
```python
neo4j_password: SecretStr = Field(default=SecretStr(""), description="Neo4j password")
voyage_api_key: SecretStr = Field(default=SecretStr(""), description="Voyage AI API key")
qdrant_api_key: SecretStr | None = Field(default=None, description="Qdrant API key")
```

### SEC-014: Good Practice - Structured Logging with Sanitization
- **File:** `/ai/work/claude-code/claude-code-project-memory-mcp/src/memory_service/utils/logging.py:31-73`
- **Category:** A09: Logging Failures (Positive)
- **Description:** Logging implementation includes sanitization to redact sensitive fields.
- **Evidence:**
```python
sensitive_keys = {
    "api_key", "apikey", "password", "passwd", "token", "secret",
    "authorization", "auth", "credential", "private_key",
    "voyage_api_key", "neo4j_password", "qdrant_api_key",
}
```

### SEC-015: Good Practice - Docker Non-Root User
- **File:** `/ai/work/claude-code/claude-code-project-memory-mcp/docker/Dockerfile:26-42`
- **Category:** A05: Security Misconfiguration (Positive)
- **Description:** Dockerfile creates and uses a non-root user for running the application.
- **Evidence:**
```dockerfile
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser
# ...
USER appuser
```

---

## Checklist Results

| Category | Pass | Fail | N/A |
|----------|------|------|-----|
| A01: Access Control | 2 | 3 | 0 |
| A02: Cryptography | 3 | 1 | 0 |
| A03: Injection | 3 | 2 | 0 |
| A04: Insecure Design | 4 | 1 | 0 |
| A05: Security Misconfiguration | 5 | 3 | 0 |
| A06: Vulnerable Components | 4 | 0 | 0 |
| A07: Authentication Failures | 3 | 2 | 0 |
| A08: Data Integrity | 4 | 0 | 0 |
| A09: Logging & Monitoring | 5 | 0 | 0 |
| A10: SSRF | 3 | 0 | 0 |

### Detailed Checklist

#### A01: Broken Access Control
- [x] Authorization checks on all protected routes/endpoints - N/A (local service)
- [ ] **FAIL** - No validation of file paths against project root
- [ ] **FAIL** - Export/import allow arbitrary file access
- [x] CORS configuration is restrictive - Not enabled
- [ ] **FAIL** - Directory traversal possible via file path parameters

#### A02: Cryptographic Failures
- [x] Sensitive data (secrets) use SecretStr
- [x] TLS/HTTPS - Expected to use container networking
- [x] No hardcoded secrets in source code (only .env.example placeholders)
- [ ] **WARN** - Embedding cache not encrypted at rest

#### A03: Injection
- [x] Parameterized queries for Neo4j (uses parameters)
- [x] Input validation exists but incomplete
- [ ] **FAIL** - Cypher validation can be bypassed
- [x] ORM-style usage with Qdrant client

#### A04: Insecure Design
- [x] Rate limiting - Not required for local MCP service
- [x] Soft delete with retention period
- [x] Defense in depth patterns in sync worker
- [ ] **WARN** - No query result limits enforced

#### A05: Security Misconfiguration
- [x] Debug mode controllable via LOG_LEVEL
- [ ] **FAIL** - Default password fallback in compose
- [ ] **FAIL** - Database ports exposed to host
- [x] Security-relevant response codes
- [ ] **FAIL** - Status endpoint exposes internal info

#### A06: Vulnerable Components
- [x] Dependencies specified with minimum versions
- [x] Using maintained libraries (qdrant-client, neo4j)
- [x] Lock files would be generated by pip
- [x] Reasonable dependency count

#### A07: Authentication Failures
- [x] Session management via MCP stdio (inherently limited)
- [ ] **FAIL** - Default password in docker-compose
- [ ] **FAIL** - Weak password in dev compose
- [x] No brute force concern (local service)

#### A08: Data Integrity
- [x] Input validation via pydantic models
- [x] Deserialization via JSON (safe)
- [x] No unsafe pickle or eval usage
- [x] Content hashing for deduplication

#### A09: Logging & Monitoring
- [x] Security events logged (errors, operations)
- [x] Logs sanitized for sensitive data
- [x] Log injection prevented (structured logging)
- [x] Audit trail via sync status
- [x] Prometheus metrics available

#### A10: Server-Side Request Forgery (SSRF)
- [x] Voyage API URL is hardcoded (not user-controllable)
- [x] Database connections use configured hosts only
- [x] No user-provided URLs for external requests

---

## Recommendations Summary

### Must Fix Before Deployment (High)
1. **SEC-002, SEC-003, SEC-005**: Implement path validation for all file operations
2. **SEC-001**: Replace Cypher blocklist with allowlist or use read-only database role

### Should Fix Before Testing Complete
3. **SEC-006, SEC-010**: Remove default password fallbacks
4. **SEC-004, SEC-007**: Document network exposure and provide production-safe configs
5. **SEC-008**: Add authentication or disable detailed status endpoint

### Fix When Convenient (Low/Info)
6. **SEC-009**: Implement full JSON schema validation
7. **SEC-011**: Consider encrypting embedding cache
8. **SEC-012**: Add query timeout and result limits

---

## Files Reviewed

| File | Status |
|------|--------|
| src/memory_service/config.py | Reviewed |
| src/memory_service/__main__.py | Reviewed |
| src/memory_service/api/http_server.py | Reviewed |
| src/memory_service/api/mcp_server.py | Reviewed |
| src/memory_service/api/tools/indexing.py | Reviewed |
| src/memory_service/api/tools/search.py | Reviewed |
| src/memory_service/api/tools/maintenance.py | Reviewed |
| src/memory_service/api/tools/memory_crud.py | Reviewed |
| src/memory_service/core/query_engine.py | Reviewed |
| src/memory_service/core/workers.py | Reviewed |
| src/memory_service/storage/neo4j_adapter.py | Reviewed |
| src/memory_service/storage/qdrant_adapter.py | Reviewed |
| src/memory_service/storage/cache.py | Reviewed |
| src/memory_service/embedding/voyage_client.py | Reviewed |
| src/memory_service/parsing/parser.py | Reviewed |
| src/memory_service/utils/logging.py | Reviewed |
| src/memory_service/utils/gitignore.py | Reviewed |
| docker/Dockerfile | Reviewed |
| docker/docker-compose.yml | Reviewed |
| docker/docker-compose.dev.yml | Reviewed |
| docker/.env.example | Reviewed |
| pyproject.toml | Reviewed |

---

<log-entry>
  <agent>code-reviewer-security</agent>
  <action>COMPLETE</action>
  <details>Security review of Claude Code Long-Term Memory System completed. Found 3 high, 5 medium, 4 low, 3 informational issues. Key concerns: path traversal in file operations, Cypher injection via validation bypass, network exposure in Docker config. Good practices noted: SecretStr usage, log sanitization, non-root Docker user.</details>
  <files>22 source files and Docker configs reviewed</files>
  <decisions>Classified path traversal as HIGH due to file system access. Classified Cypher injection as HIGH due to potential data manipulation. Classified network exposure as MEDIUM for development-focused service.</decisions>
  <errors>None</errors>
</log-entry>

---

## Task Result
status: complete
vulnerabilities_found: true
critical_count: 0
high_count: 3
medium_count: 5
findings: Path traversal in file indexing, Cypher injection bypass, arbitrary file write in export, network exposure, default passwords
notes: No critical vulnerabilities found. Three high-severity issues (SEC-001, SEC-002, SEC-003) require remediation before production deployment. The codebase shows good security awareness with proper credential handling and log sanitization. Primary recommendation is implementing path validation utility and replacing Cypher blocklist with more robust validation or read-only database access.
