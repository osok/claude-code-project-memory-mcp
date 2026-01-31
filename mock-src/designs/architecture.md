# TaskTracker Architecture

## Overview

TaskTracker follows a layered architecture with clear separation of concerns:

```
┌─────────────────────────────────────────┐
│            Presentation Layer           │
│         (Handlers / Controllers)        │
├─────────────────────────────────────────┤
│            Service Layer                │
│      (Business Logic / Use Cases)       │
├─────────────────────────────────────────┤
│           Repository Layer              │
│          (Data Access / Persistence)    │
├─────────────────────────────────────────┤
│             Domain Layer                │
│       (Models / Entities / Values)      │
└─────────────────────────────────────────┘
```

## Design Decisions

### ADR-001: Service Layer Pattern
**Decision:** Use a service layer to encapsulate business logic.
**Rationale:** Separates concerns, enables unit testing, provides clear API boundaries.
**Consequences:** Additional abstraction layer, but improved maintainability.

### ADR-002: Repository Pattern
**Decision:** Use repositories to abstract data access.
**Rationale:** Enables swapping storage backends, improves testability.
**Consequences:** More code, but storage-agnostic business logic.

### ADR-003: In-Memory Storage for Testing
**Decision:** Use in-memory repositories for testing.
**Rationale:** Fast, no external dependencies, deterministic behavior.
**Consequences:** Data lost on restart, not suitable for production.

### ADR-004: Async Operations
**Decision:** Provide async versions of I/O-bound operations.
**Rationale:** Enables concurrent processing, improves throughput.
**Consequences:** More complex code, but better scalability.

## Component Dependencies

```
TaskService ──────┬──▶ TaskRepository
                  │
                  └──▶ validators

UserService ──────┬──▶ UserRepository
                  │
                  └──▶ validators

ProjectService ───┬──▶ ProjectRepository
                  │
                  └──▶ TaskRepository

NotificationService ──▶ (external senders)
```

## Code Patterns

### Decorator Pattern (Python)
- `@log_call` - Logs method entry/exit
- `@measure_time` - Records execution time

### Options Pattern (Go)
- Functional options for flexible object construction
- Example: `NewTaskWithOptions(title, projectId, WithPriority(High))`

### Factory Pattern
- Static factory methods: `User.create_guest()`
- Class methods: `User.from_dict(data)`

## Security Considerations

1. **Input Validation**: All user input validated at service boundary
2. **Password Hashing**: Passwords hashed with secure algorithm
3. **Authorization**: Role-based access control on all operations
4. **Session Management**: Secure token generation and validation
