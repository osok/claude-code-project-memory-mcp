"""Repository for Task entities."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from ..models.task import Task, TaskStatus, TaskPriority
from .base import InMemoryRepository


class TaskRepository(InMemoryRepository[Task]):
    """
    Repository for managing Task entities.

    Provides specialized query methods for tasks beyond basic CRUD.
    """

    def __init__(self) -> None:
        """Initialize the task repository."""
        super().__init__(id_getter=lambda t: t.id)

    def get_by_project(self, project_id: UUID) -> list[Task]:
        """
        Get all tasks for a specific project.

        Args:
            project_id: The project ID to filter by.

        Returns:
            List of tasks belonging to the project.
        """
        return self.find_by(lambda t: t.project_id == project_id)

    def get_by_assignee(self, user_id: UUID) -> list[Task]:
        """
        Get all tasks assigned to a specific user.

        Args:
            user_id: The user ID to filter by.

        Returns:
            List of tasks assigned to the user.
        """
        return self.find_by(lambda t: t.assignee_id == user_id)

    def get_by_status(self, status: TaskStatus) -> list[Task]:
        """
        Get all tasks with a specific status.

        Args:
            status: The status to filter by.

        Returns:
            List of tasks with the given status.
        """
        return self.find_by(lambda t: t.status == status)

    def get_overdue(self) -> list[Task]:
        """
        Get all overdue tasks.

        Returns:
            List of tasks past their due date.
        """
        return self.find_by(lambda t: t.is_overdue)

    def get_by_priority(
        self,
        min_priority: TaskPriority = TaskPriority.LOW,
    ) -> list[Task]:
        """
        Get tasks at or above a minimum priority level.

        Args:
            min_priority: Minimum priority to include.

        Returns:
            List of tasks meeting the priority threshold.
        """
        return self.find_by(lambda t: t.priority.value >= min_priority.value)

    def get_by_tag(self, tag: str) -> list[Task]:
        """
        Get all tasks with a specific tag.

        Args:
            tag: The tag to search for.

        Returns:
            List of tasks with the tag.
        """
        normalized_tag = tag.lower().strip()
        return self.find_by(lambda t: normalized_tag in t.tags)

    def search(
        self,
        query: str,
        project_id: Optional[UUID] = None,
        status: Optional[TaskStatus] = None,
        assignee_id: Optional[UUID] = None,
    ) -> list[Task]:
        """
        Search tasks with multiple filters.

        Args:
            query: Text to search in title and description.
            project_id: Optional project filter.
            status: Optional status filter.
            assignee_id: Optional assignee filter.

        Returns:
            List of matching tasks.
        """
        query_lower = query.lower()

        def matches(task: Task) -> bool:
            if query_lower not in task.title.lower():
                if query_lower not in task.description.lower():
                    return False

            if project_id and task.project_id != project_id:
                return False

            if status and task.status != status:
                return False

            if assignee_id and task.assignee_id != assignee_id:
                return False

            return True

        return self.find_by(matches)

    def get_due_soon(self, within_days: int = 7) -> list[Task]:
        """
        Get tasks due within a specified number of days.

        Args:
            within_days: Number of days to look ahead.

        Returns:
            List of tasks due within the specified period.
        """
        from datetime import timedelta

        cutoff = datetime.utcnow() + timedelta(days=within_days)

        return self.find_by(
            lambda t: (
                t.due_date is not None
                and t.due_date <= cutoff
                and t.status != TaskStatus.COMPLETED
            )
        )

    def get_recent(self, limit: int = 10) -> list[Task]:
        """
        Get the most recently updated tasks.

        Args:
            limit: Maximum number of tasks to return.

        Returns:
            List of recently updated tasks.
        """
        tasks = self.get_all()
        tasks.sort(key=lambda t: t.updated_at, reverse=True)
        return tasks[:limit]

    def count_by_status(self) -> dict[TaskStatus, int]:
        """
        Get count of tasks grouped by status.

        Returns:
            Dictionary mapping status to count.
        """
        counts = {status: 0 for status in TaskStatus}
        for task in self:
            counts[task.status] += 1
        return counts
