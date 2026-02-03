# Requirements Documents

Place your ISO/IEC/IEEE 29148:2018 compliant requirements documents in this folder.

## File Naming Convention

Requirements documents are named per work sequence:

```
{seq}-requirements-{short_name}.md
```

**Examples:**
- `001-requirements-user-auth.md`
- `002-requirements-payment-processing.md`
- `003-requirements-reporting-dashboard.md`

## Document Structure

Each requirements document should include:

| Section | Content |
|---------|---------|
| Header | Seq, Status, Compliance |
| 1. Introduction | Purpose, Scope, Definitions |
| 2. Stakeholder Requirements | Stakeholder identification, needs, constraints |
| 3. System Requirements | Functional requirements |
| 4. Interface Requirements | UI specifications, API definitions |
| 5. Data Requirements | Entities, retention policies |
| 6. Non-Functional Requirements | Performance, security, accessibility, availability |
| 7. Verification Requirements | Testing requirements |
| 8. Deployment Requirements | Environment strategy, infrastructure |

**Note:** No dates, no fake signatures, no traceability matrix (handled separately).

## Requirement ID Conventions

Requirement IDs include the sequence number to link them to specific work items:

| Pattern | Type | Example |
|---------|------|---------|
| `STK-{SEQ}-NNN` | Stakeholder | `STK-002-001`: Admin users |
| `REQ-{SEQ}-FN-NNN` | Functional | `REQ-002-FN-001`: User auth |
| `REQ-{SEQ}-INT-UI-NNN` | UI Interface | `REQ-002-INT-UI-001`: Dashboard |
| `REQ-{SEQ}-INT-API-NNN` | API Interface | `REQ-002-INT-API-001`: User API |
| `REQ-{SEQ}-DATA-NNN` | Data Entity | `REQ-002-DATA-001`: User entity |
| `REQ-{SEQ}-NFR-PERF-NNN` | Performance | `REQ-002-NFR-PERF-001`: Response time |
| `REQ-{SEQ}-NFR-SEC-NNN` | Security | `REQ-002-NFR-SEC-001`: Password policy |
| `REQ-{SEQ}-NFR-ACC-NNN` | Accessibility | `REQ-002-NFR-ACC-001`: WCAG compliance |
| `REQ-{SEQ}-NFR-AVAIL-NNN` | Availability | `REQ-002-NFR-AVAIL-001`: Uptime |
| `REQ-{SEQ}-VER-NNN` | Verification | `REQ-002-VER-001`: Test coverage |
| `REQ-{SEQ}-DEP-NNN` | Deployment | `REQ-002-DEP-001`: Environment config |

**Note:** `{SEQ}` is the 3-digit sequence number (e.g., 001, 002).

## Requirement Format

```markdown
#### REQ-XXX-FN-NNN: Requirement Title

| Attribute | Value |
|-----------|-------|
| **Priority** | Must Have / Should Have / Could Have |
| **Component** | Target component(s) |
| **Stakeholder** | Related STK-IDs |
| **Traces To** | Related requirement IDs |

Requirement description.

**Acceptance Criteria:**
1. Criterion 1
2. Criterion 2
```

## Sample Document

See `_sample-requirements.md` for a complete example.
