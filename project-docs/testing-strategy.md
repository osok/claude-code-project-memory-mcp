# Testing Strategy

## Overview

This document defines the testing strategy for the Claude Code Long-Term Memory System. The key principle is **test against real code, not mocks**.

## Core Principle: Use `mock-src/` Instead of Mocking

**DO NOT** mock the infrastructure being tested. Instead, use the `mock-src/` application which provides a known, comprehensive codebase for testing.

### Why?

1. **Known Quantities**: The mock application has defined, expected outputs for validation
2. **Real Code Patterns**: Tests exercise actual code parsing, not simplified toy examples
3. **Multi-Language**: Python, TypeScript, and Go code for cross-language testing
4. **Relationship Testing**: Real inheritance, calls, and imports for graph testing
5. **Reproducible**: Same codebase across all test runs
6. **Comprehensive**: Covers all code patterns the memory system needs to handle

### What to Mock vs. What Not to Mock

| Mock | Don't Mock |
|------|------------|
| External APIs (VoyageAI embeddings) | Code parsing/extraction |
| Database connections (for unit tests) | File system operations on mock-src |
| Network calls | Relationship detection |
| Time-sensitive operations | Indexing workflows |

## Mock Application: `mock-src/`

Location: `/mock-src/`

### Structure

```
mock-src/
├── python/tasktracker/     # Python implementation
│   ├── models/             # Task, User, Project (dataclasses, enums)
│   ├── services/           # Business logic (async, decorators)
│   ├── repositories/       # Data access (abstract base, generics)
│   └── utils/              # Pure functions (validators, helpers)
├── typescript/src/         # TypeScript implementation
│   ├── models/             # Interfaces and classes
│   ├── services/           # Business logic
│   └── utils/              # Helper functions
├── go/pkg/                 # Go implementation
│   ├── models/             # Structs with methods
│   └── handlers/           # HTTP handlers
├── requirements/           # Mock requirements document
└── designs/                # Mock design document
```

### Code Patterns Covered

The mock application intentionally includes these patterns:

- **Classes**: Dataclasses, enums, abstract base classes, inheritance
- **Functions**: Async/await, decorators, static/class methods, properties
- **Patterns**: Service layer, repository pattern, factory pattern
- **Types**: Type hints, generics, protocols
- **Documentation**: Docstrings on all public functions

### Using Mock-Src in Tests

```python
import pytest
from pathlib import Path

# Fixtures are auto-imported via conftest.py

def test_parse_python_files(mock_src_python: Path):
    """Test parsing Python files from mock-src."""
    # mock_src_python points to mock-src/python/tasktracker/
    files = list(mock_src_python.rglob("*.py"))
    assert len(files) >= 15  # Known file count

def test_extract_functions(mock_src_python: Path, expected_python_functions: list):
    """Test function extraction against known results."""
    # Parse files and compare against expected_python_functions
    pass

def test_detect_relationships(mock_src_python: Path, expected_relationships: list):
    """Test relationship detection against known results."""
    # Parse files and compare against expected_relationships
    pass
```

### Available Fixtures

From `src/tests/conftest_mock_src.py`:

| Fixture | Description |
|---------|-------------|
| `mock_src_root` | Path to mock-src/ |
| `mock_src_python` | Path to Python app |
| `mock_src_typescript` | Path to TypeScript app |
| `mock_src_go` | Path to Go app |
| `mock_codebase` | Alias for mock_src_python (replaces temp_codebase) |
| `mock_requirements_file` | Path to requirements.md |
| `mock_design_file` | Path to architecture.md |
| `expected_python_functions` | List of expected function extractions |
| `expected_python_classes` | List of expected class extractions |
| `expected_relationships` | List of expected relationships |

### Expected Results

The fixture files contain expected extraction results:

```python
EXPECTED_PYTHON_FUNCTIONS = [
    {"name": "validate_email", "file": "utils/validators.py", "is_method": False},
    {"name": "create_task", "file": "services/task_service.py", "is_method": True, "has_decorator": True},
    # ... more functions
]

EXPECTED_RELATIONSHIPS = [
    ("TaskService", "EXTENDS", "BaseService"),
    ("TaskService", "DEPENDS_ON", "TaskRepository"),
    ("create_task", "CALLS", "validate_task_title"),
    # ... more relationships
]
```

## Test Categories

### Unit Tests

- Test individual functions in isolation
- Mock external dependencies (APIs, databases)
- Use mock-src for code parsing tests
- Fast execution (<100ms per test)

### Integration Tests

- Test component interactions
- Use testcontainers for databases (Qdrant, Neo4j)
- Use mock-src for indexing tests
- May take longer (<5s per test)

### E2E Tests

- Test complete workflows
- Full stack with containers
- Use mock-src as the codebase to index
- Validate end-to-end memory operations

### Performance Tests

- Benchmark against mock-src (known size)
- Measure indexing throughput
- Measure query latency

## Writing New Tests

### DO

1. Use `mock_src_python` fixture for code parsing tests
2. Add expected results to `conftest_mock_src.py` for new extractions
3. Test against known file counts and patterns
4. Validate relationships are detected correctly

### DON'T

1. Create temporary codebases with `tempfile` for parsing tests
2. Mock the code parser or extractor
3. Use string literals as test code (use real files)
4. Skip validation of expected results

### Example: Adding a New Test

```python
@pytest.mark.asyncio
async def test_index_mock_codebase(
    e2e_indexer_worker: IndexerWorker,
    mock_src_python: Path,
    expected_python_functions: list,
):
    """Index mock-src and validate function extraction."""
    # Index the mock application
    result = await e2e_indexer_worker.index_directory(str(mock_src_python))

    # Validate against known expected results
    for expected in expected_python_functions:
        # Verify function was indexed
        assert any(
            f["name"] == expected["name"]
            for f in result.functions
        ), f"Expected function {expected['name']} not found"
```

## Maintaining Mock-Src

When adding new test scenarios:

1. Add code to `mock-src/` that exercises the pattern
2. Update `mock-src/fixtures.py` with expected results
3. Update `src/tests/conftest_mock_src.py` with new fixtures
4. Document the pattern in mock-src/README.md

### Adding a New Language

1. Create `mock-src/<language>/` directory
2. Implement equivalent Task/User/Project models
3. Add fixture for the new language path
4. Add expected extraction results
