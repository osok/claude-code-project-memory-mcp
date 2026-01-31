# TaskTracker Mock Application

A mock application designed for testing the Claude Code Long-Term Memory System.

## Purpose

This mock application provides a known, well-defined codebase that exercises all of the memory system's capabilities:

- **Code Parsing**: Multiple languages (Python, TypeScript, Go)
- **Element Extraction**: Classes, functions, imports, method calls
- **Relationship Detection**: CALLS, IMPORTS, EXTENDS, CONTAINS, etc.
- **Memory Types**: Function, Component, Requirements, Design, CodePattern

## Structure

```
mock-src/
├── python/               # Python implementation
│   └── tasktracker/
│       ├── models/       # Data models (Task, User, Project)
│       ├── services/     # Business logic layer
│       ├── repositories/ # Data access layer
│       ├── utils/        # Utility functions
│       └── tests/        # Unit tests
├── typescript/           # TypeScript implementation
│   └── src/
│       ├── models/       # Data models
│       ├── services/     # Business logic
│       └── utils/        # Utility functions
├── go/                   # Go implementation
│   └── pkg/
│       ├── models/       # Data models
│       └── handlers/     # HTTP handlers
├── requirements/         # Mock requirements documents
└── designs/              # Mock design documents
```

## Code Coverage

### Python (Primary Language)
- 3 models with dataclasses and enums
- 4 services with async methods
- 3 repositories with abstract base classes
- 2 utility modules with pure functions
- 25+ functions total

### TypeScript
- 3 models with interfaces and classes
- 2 services
- 2 utility modules
- 20+ functions

### Go
- 2 models with structs and methods
- 1 handler package
- 10+ functions

## Testing Capabilities

### Code Parsing Tests
- Parse each file and extract functions, classes, imports
- Validate language detection
- Verify AST extraction accuracy

### Indexing Tests
- Create FunctionMemory for each function
- Create ComponentMemory for each service
- Build relationship graph from call analysis

### Relationship Tests
- CALLS: Function-to-function calls
- IMPORTS: Module imports
- EXTENDS: Class inheritance
- CONTAINS: Module contains function/class
- DEPENDS_ON: Service dependencies

### Duplicate Detection Tests
- Similar functions across files
- Semantic similarity detection

## Usage

```python
from memory_system.parsing import parse_codebase
from memory_system.indexing import index_codebase

# Parse the mock application
results = parse_codebase("mock-src/python/tasktracker")

# Index to memory
await index_codebase(results, memory_service)
```

## Known Patterns

The mock application intentionally includes these patterns for testing:

1. **Service Layer Pattern**: Services depend on repositories
2. **Repository Pattern**: Abstract base with concrete implementations
3. **Decorator Pattern**: Python decorators on methods
4. **Factory Pattern**: Static factory methods for object creation
5. **Async/Await**: Async methods for I/O simulation
