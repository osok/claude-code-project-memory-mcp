"""Fixtures for using mock-src in tests.

This module provides fixtures that use the mock-src application
instead of dynamically created temporary codebases. This provides:
- Known, comprehensive code to parse
- Expected results for validation
- Multi-language support (Python, TypeScript, Go)
- Requirements and design documents for testing those memory types
"""

from pathlib import Path
from typing import Generator

import pytest


# Path to the mock-src directory
MOCK_SRC_ROOT = Path(__file__).parent.parent.parent / "mock-src"


@pytest.fixture(scope="session")
def mock_src_root() -> Path:
    """Get the root path of the mock-src directory.

    Returns:
        Path to mock-src directory.
    """
    assert MOCK_SRC_ROOT.exists(), f"mock-src not found at {MOCK_SRC_ROOT}"
    return MOCK_SRC_ROOT


@pytest.fixture(scope="session")
def mock_src_python() -> Path:
    """Get the path to the Python mock application.

    Returns:
        Path to mock-src/python/tasktracker directory.
    """
    path = MOCK_SRC_ROOT / "python" / "tasktracker"
    assert path.exists(), f"Python mock app not found at {path}"
    return path


@pytest.fixture(scope="session")
def mock_src_typescript() -> Path:
    """Get the path to the TypeScript mock application.

    Returns:
        Path to mock-src/typescript/src directory.
    """
    path = MOCK_SRC_ROOT / "typescript" / "src"
    assert path.exists(), f"TypeScript mock app not found at {path}"
    return path


@pytest.fixture(scope="session")
def mock_src_go() -> Path:
    """Get the path to the Go mock application.

    Returns:
        Path to mock-src/go/pkg directory.
    """
    path = MOCK_SRC_ROOT / "go" / "pkg"
    assert path.exists(), f"Go mock app not found at {path}"
    return path


@pytest.fixture(scope="session")
def mock_requirements_file() -> Path:
    """Get the path to the mock requirements document.

    Returns:
        Path to mock-src/requirements/requirements.md.
    """
    path = MOCK_SRC_ROOT / "requirements" / "requirements.md"
    assert path.exists(), f"Requirements file not found at {path}"
    return path


@pytest.fixture(scope="session")
def mock_design_file() -> Path:
    """Get the path to the mock design document.

    Returns:
        Path to mock-src/designs/architecture.md.
    """
    path = MOCK_SRC_ROOT / "designs" / "architecture.md"
    assert path.exists(), f"Design file not found at {path}"
    return path


# Expected extraction results for validation
EXPECTED_PYTHON_FUNCTIONS = [
    # models/task.py
    {"name": "mark_complete", "file": "models/task.py", "is_method": True},
    {"name": "mark_blocked", "file": "models/task.py", "is_method": True},
    {"name": "assign_to", "file": "models/task.py", "is_method": True},
    {"name": "add_tag", "file": "models/task.py", "is_method": True},
    {"name": "remove_tag", "file": "models/task.py", "is_method": True},

    # utils/validators.py
    {"name": "validate_email", "file": "utils/validators.py", "is_method": False},
    {"name": "validate_username", "file": "utils/validators.py", "is_method": False},
    {"name": "validate_uuid", "file": "utils/validators.py", "is_method": False},
    {"name": "validate_task_title", "file": "utils/validators.py", "is_method": False},
    {"name": "validate_password", "file": "utils/validators.py", "is_method": False},
    {"name": "sanitize_input", "file": "utils/validators.py", "is_method": False},

    # utils/helpers.py
    {"name": "generate_id", "file": "utils/helpers.py", "is_method": False},
    {"name": "format_datetime", "file": "utils/helpers.py", "is_method": False},
    {"name": "parse_datetime", "file": "utils/helpers.py", "is_method": False},
    {"name": "slugify", "file": "utils/helpers.py", "is_method": False},
    {"name": "truncate", "file": "utils/helpers.py", "is_method": False},
    {"name": "pluralize", "file": "utils/helpers.py", "is_method": False},

    # services/task_service.py
    {"name": "create_task", "file": "services/task_service.py", "is_method": True, "has_decorator": True},
    {"name": "get_task", "file": "services/task_service.py", "is_method": True},
    {"name": "update_task", "file": "services/task_service.py", "is_method": True},
    {"name": "delete_task", "file": "services/task_service.py", "is_method": True},
    {"name": "create_task_async", "file": "services/task_service.py", "is_method": True, "is_async": True},
    {"name": "bulk_create_async", "file": "services/task_service.py", "is_method": True, "is_async": True},
    {"name": "assign_task", "file": "services/task_service.py", "is_method": True},
    {"name": "complete_task", "file": "services/task_service.py", "is_method": True},
]

EXPECTED_PYTHON_CLASSES = [
    {"name": "Task", "file": "models/task.py", "is_dataclass": True},
    {"name": "TaskStatus", "file": "models/task.py", "is_enum": True},
    {"name": "TaskPriority", "file": "models/task.py", "is_enum": True},
    {"name": "User", "file": "models/user.py", "is_dataclass": True},
    {"name": "UserRole", "file": "models/user.py", "is_enum": True},
    {"name": "Project", "file": "models/project.py", "is_dataclass": True},

    {"name": "BaseRepository", "file": "repositories/base.py", "bases": ["ABC"]},
    {"name": "InMemoryRepository", "file": "repositories/base.py", "bases": ["BaseRepository"]},
    {"name": "TaskRepository", "file": "repositories/task_repository.py", "bases": ["InMemoryRepository"]},
    {"name": "UserRepository", "file": "repositories/user_repository.py", "bases": ["InMemoryRepository"]},
    {"name": "ProjectRepository", "file": "repositories/project_repository.py", "bases": ["InMemoryRepository"]},

    {"name": "BaseService", "file": "services/base.py", "bases": ["ABC"]},
    {"name": "TaskService", "file": "services/task_service.py", "bases": ["BaseService"]},
    {"name": "UserService", "file": "services/user_service.py", "bases": ["BaseService"]},
    {"name": "ProjectService", "file": "services/project_service.py", "bases": ["BaseService"]},
    {"name": "NotificationService", "file": "services/notification_service.py", "bases": ["BaseService"]},
]

EXPECTED_RELATIONSHIPS = [
    # Inheritance
    ("InMemoryRepository", "EXTENDS", "BaseRepository"),
    ("TaskRepository", "EXTENDS", "InMemoryRepository"),
    ("UserRepository", "EXTENDS", "InMemoryRepository"),
    ("ProjectRepository", "EXTENDS", "InMemoryRepository"),
    ("TaskService", "EXTENDS", "BaseService"),
    ("UserService", "EXTENDS", "BaseService"),
    ("ProjectService", "EXTENDS", "BaseService"),
    ("NotificationService", "EXTENDS", "BaseService"),

    # Dependencies
    ("TaskService", "DEPENDS_ON", "TaskRepository"),
    ("UserService", "DEPENDS_ON", "UserRepository"),
    ("ProjectService", "DEPENDS_ON", "ProjectRepository"),
    ("ProjectService", "DEPENDS_ON", "TaskRepository"),

    # Function calls
    ("create_task", "CALLS", "validate_task_title"),
    ("create_user", "CALLS", "validate_email"),
    ("create_user", "CALLS", "validate_username"),
    ("create_user", "CALLS", "validate_password"),
]


@pytest.fixture(scope="session")
def expected_python_functions() -> list[dict]:
    """Get expected Python function extraction results."""
    return EXPECTED_PYTHON_FUNCTIONS


@pytest.fixture(scope="session")
def expected_python_classes() -> list[dict]:
    """Get expected Python class extraction results."""
    return EXPECTED_PYTHON_CLASSES


@pytest.fixture(scope="session")
def expected_relationships() -> list[tuple[str, str, str]]:
    """Get expected relationship extraction results."""
    return EXPECTED_RELATIONSHIPS


@pytest.fixture
def mock_codebase(mock_src_python: Path) -> Generator[Path, None, None]:
    """Provide the mock codebase for E2E tests.

    This replaces the temp_codebase fixture with the real mock-src
    application, providing a more comprehensive test codebase.

    Yields:
        Path to the mock Python application.
    """
    yield mock_src_python


# File counts for validation
FILE_COUNTS = {
    "python": 15,  # Approximate count of Python files
    "typescript": 8,  # Approximate count of TypeScript files
    "go": 3,  # Approximate count of Go files
}


@pytest.fixture(scope="session")
def expected_file_counts() -> dict[str, int]:
    """Get expected file counts by language."""
    return FILE_COUNTS
