"""Task service for managing tasks."""

import asyncio
from datetime import datetime
from typing import Optional
from uuid import UUID

from ..models.task import Task, TaskStatus, TaskPriority
from ..repositories.task_repository import TaskRepository
from ..utils.validators import validate_task_title
from .base import (
    BaseService,
    NotFoundError,
    ValidationError,
    log_call,
    measure_time,
)


class TaskService(BaseService):
    """
    Service for task management operations.

    Handles business logic for creating, updating, and querying tasks.
    Uses TaskRepository for data persistence.

    Attributes:
        repository: The task repository for data access.
        _cache: Simple cache for frequently accessed tasks.
    """

    def __init__(self, repository: Optional[TaskRepository] = None) -> None:
        """
        Initialize the task service.

        Args:
            repository: Optional repository instance. Creates new one if not provided.
        """
        super().__init__()
        self.repository = repository or TaskRepository()
        self._cache: dict[UUID, Task] = {}
        self._cache_ttl = 300  # 5 minutes

    @log_call
    @measure_time
    def create_task(
        self,
        title: str,
        project_id: UUID,
        description: str = "",
        assignee_id: Optional[UUID] = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        due_date: Optional[datetime] = None,
        tags: Optional[list[str]] = None,
    ) -> Task:
        """
        Create a new task.

        Args:
            title: Task title.
            project_id: ID of the project the task belongs to.
            description: Detailed description.
            assignee_id: Optional user to assign.
            priority: Task priority level.
            due_date: Optional deadline.
            tags: Optional list of tags.

        Returns:
            The created task.

        Raises:
            ValidationError: If title is invalid.
        """
        is_valid, error_msg = validate_task_title(title)
        if not is_valid:
            raise ValidationError("title", error_msg)

        task = Task(
            title=title,
            project_id=project_id,
            description=description,
            assignee_id=assignee_id,
            priority=priority,
            due_date=due_date,
            tags=tags or [],
        )

        created = self.repository.create(task)
        self._log_info("Created task: %s", created.id)
        return created

    @log_call
    def get_task(self, task_id: UUID) -> Task:
        """
        Get a task by ID.

        Args:
            task_id: The task's unique identifier.

        Returns:
            The task.

        Raises:
            NotFoundError: If task doesn't exist.
        """
        task = self.repository.get(task_id)
        if not task:
            raise NotFoundError("Task", str(task_id))
        return task

    @log_call
    def update_task(
        self,
        task_id: UUID,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
        assignee_id: Optional[UUID] = None,
        due_date: Optional[datetime] = None,
    ) -> Task:
        """
        Update a task's properties.

        Args:
            task_id: The task to update.
            title: New title (if provided).
            description: New description (if provided).
            status: New status (if provided).
            priority: New priority (if provided).
            assignee_id: New assignee (if provided).
            due_date: New due date (if provided).

        Returns:
            The updated task.

        Raises:
            NotFoundError: If task doesn't exist.
            ValidationError: If new values are invalid.
        """
        task = self.get_task(task_id)

        if title is not None:
            is_valid, error_msg = validate_task_title(title)
            if not is_valid:
                raise ValidationError("title", error_msg)
            task.title = title

        if description is not None:
            task.description = description

        if status is not None:
            task.status = status

        if priority is not None:
            task.priority = priority

        if assignee_id is not None:
            task.assignee_id = assignee_id

        if due_date is not None:
            task.due_date = due_date

        task.updated_at = datetime.utcnow()
        self.repository.update(task)
        self._invalidate_cache(task_id)
        return task

    @log_call
    def delete_task(self, task_id: UUID) -> bool:
        """
        Delete a task.

        Args:
            task_id: The task to delete.

        Returns:
            True if deleted.

        Raises:
            NotFoundError: If task doesn't exist.
        """
        if not self.repository.exists(task_id):
            raise NotFoundError("Task", str(task_id))

        self.repository.delete(task_id)
        self._invalidate_cache(task_id)
        self._log_info("Deleted task: %s", task_id)
        return True

    async def create_task_async(
        self,
        title: str,
        project_id: UUID,
        **kwargs,
    ) -> Task:
        """
        Create a task asynchronously.

        Useful when creating tasks as part of a larger async workflow.

        Args:
            title: Task title.
            project_id: Project ID.
            **kwargs: Additional task properties.

        Returns:
            The created task.
        """
        # Simulate async operation
        await asyncio.sleep(0.01)
        return self.create_task(title, project_id, **kwargs)

    async def bulk_create_async(
        self,
        tasks_data: list[dict],
    ) -> list[Task]:
        """
        Create multiple tasks asynchronously.

        Args:
            tasks_data: List of task data dictionaries.

        Returns:
            List of created tasks.
        """
        tasks = []
        for data in tasks_data:
            task = await self.create_task_async(**data)
            tasks.append(task)
        return tasks

    async def get_tasks_with_refresh(
        self,
        project_id: UUID,
        force_refresh: bool = False,
    ) -> list[Task]:
        """
        Get tasks for a project with optional cache refresh.

        Args:
            project_id: Project to get tasks for.
            force_refresh: Whether to bypass cache.

        Returns:
            List of tasks.
        """
        if force_refresh:
            self._cache.clear()
            await asyncio.sleep(0.01)  # Simulate refresh delay

        return self.repository.get_by_project(project_id)

    def assign_task(self, task_id: UUID, user_id: UUID) -> Task:
        """
        Assign a task to a user.

        Args:
            task_id: The task to assign.
            user_id: The user to assign to.

        Returns:
            The updated task.
        """
        task = self.get_task(task_id)
        task.assign_to(user_id)
        self.repository.update(task)
        return task

    def complete_task(self, task_id: UUID) -> Task:
        """
        Mark a task as completed.

        Args:
            task_id: The task to complete.

        Returns:
            The updated task.
        """
        task = self.get_task(task_id)
        task.mark_complete()
        self.repository.update(task)
        return task

    def get_overdue_tasks(self) -> list[Task]:
        """Get all overdue tasks."""
        return self.repository.get_overdue()

    def get_tasks_by_status(self, status: TaskStatus) -> list[Task]:
        """Get tasks filtered by status."""
        return self.repository.get_by_status(status)

    def search_tasks(
        self,
        query: str,
        project_id: Optional[UUID] = None,
        status: Optional[TaskStatus] = None,
    ) -> list[Task]:
        """
        Search tasks with filters.

        Args:
            query: Search text.
            project_id: Optional project filter.
            status: Optional status filter.

        Returns:
            Matching tasks.
        """
        return self.repository.search(query, project_id, status)

    def _invalidate_cache(self, task_id: UUID) -> None:
        """Remove a task from cache."""
        self._cache.pop(task_id, None)

    @property
    def task_count(self) -> int:
        """Get total number of tasks."""
        return self.repository.count()

    @staticmethod
    def calculate_priority_score(task: Task) -> int:
        """
        Calculate a priority score for sorting.

        Args:
            task: The task to score.

        Returns:
            Priority score (higher = more important).
        """
        score = task.priority.value * 10

        if task.is_overdue:
            score += 50

        if task.status == TaskStatus.BLOCKED:
            score -= 20

        return score
