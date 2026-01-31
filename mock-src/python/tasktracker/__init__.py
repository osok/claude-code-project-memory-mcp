"""
TaskTracker - A simple task management application.

This mock application is designed to exercise the memory system's
code parsing, indexing, and relationship detection capabilities.
"""

from .models.task import Task, TaskStatus, TaskPriority
from .models.user import User, UserRole
from .models.project import Project
from .services.task_service import TaskService
from .services.user_service import UserService
from .services.project_service import ProjectService

__version__ = "1.0.0"
__all__ = [
    "Task",
    "TaskStatus",
    "TaskPriority",
    "User",
    "UserRole",
    "Project",
    "TaskService",
    "UserService",
    "ProjectService",
]
