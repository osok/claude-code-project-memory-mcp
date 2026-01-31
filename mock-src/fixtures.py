"""
Fixtures and utilities for testing the memory system with mock-src.

This module provides easy access to the mock application files and
expected parsing/indexing results for testing the memory system.
"""

from pathlib import Path
from dataclasses import dataclass, field


# Path to the mock-src directory
MOCK_SRC_ROOT = Path(__file__).parent

# Language-specific paths
PYTHON_ROOT = MOCK_SRC_ROOT / "python" / "tasktracker"
TYPESCRIPT_ROOT = MOCK_SRC_ROOT / "typescript" / "src"
GO_ROOT = MOCK_SRC_ROOT / "go" / "pkg"


@dataclass
class ExpectedFunction:
    """Expected function extraction result."""
    name: str
    file_path: str
    has_docstring: bool = True
    is_async: bool = False
    is_method: bool = False
    decorator_count: int = 0
    parameter_count: int = 0


@dataclass
class ExpectedClass:
    """Expected class extraction result."""
    name: str
    file_path: str
    base_classes: list[str] = field(default_factory=list)
    method_count: int = 0
    is_dataclass: bool = False


@dataclass
class ExpectedImport:
    """Expected import extraction result."""
    module: str
    file_path: str
    is_from_import: bool = True
    imported_names: list[str] = field(default_factory=list)


# Expected Python functions
EXPECTED_PYTHON_FUNCTIONS = [
    # models/task.py
    ExpectedFunction("mark_complete", "models/task.py", is_method=True),
    ExpectedFunction("mark_blocked", "models/task.py", is_method=True, parameter_count=1),
    ExpectedFunction("assign_to", "models/task.py", is_method=True, parameter_count=1),
    ExpectedFunction("add_tag", "models/task.py", is_method=True, parameter_count=1),
    ExpectedFunction("remove_tag", "models/task.py", is_method=True, parameter_count=1),

    # models/user.py
    ExpectedFunction("has_permission", "models/user.py", is_method=True, parameter_count=1),
    ExpectedFunction("promote_to", "models/user.py", is_method=True, parameter_count=1),
    ExpectedFunction("deactivate", "models/user.py", is_method=True),
    ExpectedFunction("record_login", "models/user.py", is_method=True),
    ExpectedFunction("create_guest", "models/user.py", is_method=True),  # static
    ExpectedFunction("from_dict", "models/user.py", is_method=True),  # classmethod
    ExpectedFunction("to_dict", "models/user.py", is_method=True),

    # utils/validators.py
    ExpectedFunction("validate_email", "utils/validators.py", parameter_count=1),
    ExpectedFunction("validate_username", "utils/validators.py", parameter_count=1),
    ExpectedFunction("validate_uuid", "utils/validators.py", parameter_count=1),
    ExpectedFunction("validate_task_title", "utils/validators.py", parameter_count=3),
    ExpectedFunction("validate_password", "utils/validators.py", parameter_count=6),
    ExpectedFunction("sanitize_input", "utils/validators.py", parameter_count=2),

    # utils/helpers.py
    ExpectedFunction("generate_id", "utils/helpers.py"),
    ExpectedFunction("format_datetime", "utils/helpers.py", parameter_count=3),
    ExpectedFunction("parse_datetime", "utils/helpers.py", parameter_count=2),
    ExpectedFunction("slugify", "utils/helpers.py", parameter_count=3),
    ExpectedFunction("truncate", "utils/helpers.py", parameter_count=3),
    ExpectedFunction("pluralize", "utils/helpers.py", parameter_count=3),
    ExpectedFunction("merge_dicts", "utils/helpers.py"),
    ExpectedFunction("chunk_list", "utils/helpers.py", parameter_count=2),
    ExpectedFunction("safe_get", "utils/helpers.py", parameter_count=4),

    # services/task_service.py
    ExpectedFunction("create_task", "services/task_service.py", is_method=True, decorator_count=2),
    ExpectedFunction("get_task", "services/task_service.py", is_method=True, decorator_count=1),
    ExpectedFunction("update_task", "services/task_service.py", is_method=True, decorator_count=1),
    ExpectedFunction("delete_task", "services/task_service.py", is_method=True, decorator_count=1),
    ExpectedFunction("create_task_async", "services/task_service.py", is_method=True, is_async=True),
    ExpectedFunction("bulk_create_async", "services/task_service.py", is_method=True, is_async=True),
    ExpectedFunction("assign_task", "services/task_service.py", is_method=True),
    ExpectedFunction("complete_task", "services/task_service.py", is_method=True),
    ExpectedFunction("calculate_priority_score", "services/task_service.py"),  # static

    # services/user_service.py
    ExpectedFunction("create_user", "services/user_service.py", is_method=True, decorator_count=1),
    ExpectedFunction("get_user", "services/user_service.py", is_method=True, decorator_count=1),
    ExpectedFunction("authenticate", "services/user_service.py", is_method=True),
    ExpectedFunction("authenticate_async", "services/user_service.py", is_method=True, is_async=True),
    ExpectedFunction("validate_token", "services/user_service.py", is_method=True),
    ExpectedFunction("logout", "services/user_service.py", is_method=True),
    ExpectedFunction("change_password", "services/user_service.py", is_method=True),

    # repositories/base.py
    ExpectedFunction("get", "repositories/base.py", is_method=True),
    ExpectedFunction("get_all", "repositories/base.py", is_method=True),
    ExpectedFunction("create", "repositories/base.py", is_method=True),
    ExpectedFunction("update", "repositories/base.py", is_method=True),
    ExpectedFunction("delete", "repositories/base.py", is_method=True),
    ExpectedFunction("find_by", "repositories/base.py", is_method=True),
    ExpectedFunction("find_one", "repositories/base.py", is_method=True),
    ExpectedFunction("bulk_create", "repositories/base.py", is_method=True),
]


# Expected Python classes
EXPECTED_PYTHON_CLASSES = [
    # models
    ExpectedClass("Task", "models/task.py", is_dataclass=True, method_count=6),
    ExpectedClass("TaskStatus", "models/task.py"),  # Enum
    ExpectedClass("TaskPriority", "models/task.py"),  # Enum
    ExpectedClass("User", "models/user.py", is_dataclass=True, method_count=8),
    ExpectedClass("UserRole", "models/user.py"),  # Enum
    ExpectedClass("Project", "models/project.py", is_dataclass=True, method_count=10),

    # repositories
    ExpectedClass("BaseRepository", "repositories/base.py", base_classes=["ABC", "Generic"]),
    ExpectedClass("InMemoryRepository", "repositories/base.py", base_classes=["BaseRepository"]),
    ExpectedClass("TaskRepository", "repositories/task_repository.py", base_classes=["InMemoryRepository"]),
    ExpectedClass("UserRepository", "repositories/user_repository.py", base_classes=["InMemoryRepository"]),
    ExpectedClass("ProjectRepository", "repositories/project_repository.py", base_classes=["InMemoryRepository"]),

    # services
    ExpectedClass("BaseService", "services/base.py", base_classes=["ABC"]),
    ExpectedClass("ServiceError", "services/base.py", base_classes=["Exception"]),
    ExpectedClass("NotFoundError", "services/base.py", base_classes=["ServiceError"]),
    ExpectedClass("ValidationError", "services/base.py", base_classes=["ServiceError"]),
    ExpectedClass("AuthorizationError", "services/base.py", base_classes=["ServiceError"]),
    ExpectedClass("TaskService", "services/task_service.py", base_classes=["BaseService"]),
    ExpectedClass("UserService", "services/user_service.py", base_classes=["BaseService"]),
    ExpectedClass("ProjectService", "services/project_service.py", base_classes=["BaseService"]),
    ExpectedClass("NotificationService", "services/notification_service.py", base_classes=["BaseService"]),
]


# Expected relationships
EXPECTED_RELATIONSHIPS = [
    # Service -> Repository dependencies
    ("TaskService", "DEPENDS_ON", "TaskRepository"),
    ("UserService", "DEPENDS_ON", "UserRepository"),
    ("ProjectService", "DEPENDS_ON", "ProjectRepository"),
    ("ProjectService", "DEPENDS_ON", "TaskRepository"),

    # Class inheritance
    ("InMemoryRepository", "EXTENDS", "BaseRepository"),
    ("TaskRepository", "EXTENDS", "InMemoryRepository"),
    ("UserRepository", "EXTENDS", "InMemoryRepository"),
    ("ProjectRepository", "EXTENDS", "InMemoryRepository"),
    ("TaskService", "EXTENDS", "BaseService"),
    ("UserService", "EXTENDS", "BaseService"),
    ("ProjectService", "EXTENDS", "BaseService"),

    # Service method calls
    ("TaskService.create_task", "CALLS", "validate_task_title"),
    ("UserService.create_user", "CALLS", "validate_email"),
    ("UserService.create_user", "CALLS", "validate_username"),
    ("UserService.create_user", "CALLS", "validate_password"),
]


# File counts by language
FILE_COUNTS = {
    "python": 15,
    "typescript": 8,
    "go": 3,
}


def get_python_files() -> list[Path]:
    """Get all Python files in the mock application."""
    return list(PYTHON_ROOT.rglob("*.py"))


def get_typescript_files() -> list[Path]:
    """Get all TypeScript files in the mock application."""
    return list(TYPESCRIPT_ROOT.rglob("*.ts"))


def get_go_files() -> list[Path]:
    """Get all Go files in the mock application."""
    return list(GO_ROOT.rglob("*.go"))


def get_all_files() -> dict[str, list[Path]]:
    """Get all source files grouped by language."""
    return {
        "python": get_python_files(),
        "typescript": get_typescript_files(),
        "go": get_go_files(),
    }


def get_requirements_file() -> Path:
    """Get the path to the requirements document."""
    return MOCK_SRC_ROOT / "requirements" / "requirements.md"


def get_design_file() -> Path:
    """Get the path to the design document."""
    return MOCK_SRC_ROOT / "designs" / "architecture.md"
