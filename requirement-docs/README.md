# Requirements Documents

Place your ISO/IEC/IEEE 29148:2018 compliant requirements documents in this folder.

## Document Structure

Each requirements document should include:

| Section | Content |
|---------|---------|
| Header | Document ID, Version, Status, Classification, Compliance |
| 1. Introduction | Purpose, Scope, Definitions, References |
| 2. Stakeholder Requirements | Stakeholder identification, needs, goals |
| 3. System Requirements | Context, functional requirements |
| 4. Interface Requirements | UI specifications, API definitions |
| 5. Data Requirements | Entities, retention policies |
| 6. Non-Functional Requirements | Performance, security, accessibility |
| 7. Verification Requirements | Testing requirements |
| 8. Deployment Requirements | Environment strategy, infrastructure |
| 9. Document Control | Revision history, approvals |

## Requirement ID Conventions

| Pattern | Type | Example |
|---------|------|---------|
| `STK-NNN` | Stakeholder | `STK-001`: Admin users |
| `REQ-XXX-FN-NNN` | Functional | `REQ-SYS-FN-001`: User auth |
| `REQ-INT-UI-NNN` | UI Interface | `REQ-INT-UI-001`: Dashboard |
| `REQ-INT-API-NNN` | API Interface | `REQ-INT-API-001`: User API |
| `REQ-DATA-NNN` | Data Entity | `REQ-DATA-001`: User entity |
| `REQ-NFR-PERF-NNN` | Performance | `REQ-NFR-PERF-001`: Response time |
| `REQ-NFR-SEC-NNN` | Security | `REQ-NFR-SEC-001`: Password policy |
| `REQ-NFR-ACC-NNN` | Accessibility | `REQ-NFR-ACC-001`: WCAG compliance |
| `REQ-NFR-AVAIL-NNN` | Availability | `REQ-NFR-AVAIL-001`: Uptime |
| `REQ-VER-NNN` | Verification | `REQ-VER-001`: Test coverage |
| `REQ-DEP-NNN` | Deployment | `REQ-DEP-001`: Environment config |

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
