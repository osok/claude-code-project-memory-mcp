"""Project model for organizing tasks."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from .task import Task, TaskStatus


@dataclass
class Project:
    """
    Represents a project containing tasks.

    Projects organize tasks and have owners and members.
    They track completion progress based on task statuses.

    Attributes:
        id: Unique identifier for the project.
        name: Name of the project.
        description: Detailed description of the project.
        owner_id: ID of the user who owns the project.
        member_ids: List of user IDs who are members.
        created_at: When the project was created.
        updated_at: When the project was last updated.
        is_archived: Whether the project is archived.
    """

    name: str
    owner_id: UUID
    id: UUID = field(default_factory=uuid4)
    description: str = ""
    member_ids: list[UUID] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    is_archived: bool = False
    _tasks: list[Task] = field(default_factory=list, repr=False)

    def add_member(self, user_id: UUID) -> bool:
        """
        Add a member to the project.

        Args:
            user_id: ID of the user to add.

        Returns:
            True if member was added, False if already a member.
        """
        if user_id not in self.member_ids and user_id != self.owner_id:
            self.member_ids.append(user_id)
            self.updated_at = datetime.utcnow()
            return True
        return False

    def remove_member(self, user_id: UUID) -> bool:
        """
        Remove a member from the project.

        Args:
            user_id: ID of the user to remove.

        Returns:
            True if member was removed, False if not a member.
        """
        if user_id in self.member_ids:
            self.member_ids.remove(user_id)
            self.updated_at = datetime.utcnow()
            return True
        return False

    def is_member(self, user_id: UUID) -> bool:
        """
        Check if a user is a member or owner.

        Args:
            user_id: ID of the user to check.

        Returns:
            True if user is a member or owner.
        """
        return user_id == self.owner_id or user_id in self.member_ids

    def add_task(self, task: Task) -> None:
        """
        Add a task to the project.

        Args:
            task: The task to add.
        """
        task.project_id = self.id
        self._tasks.append(task)
        self.updated_at = datetime.utcnow()

    def get_tasks(self, status: Optional[TaskStatus] = None) -> list[Task]:
        """
        Get tasks, optionally filtered by status.

        Args:
            status: Optional status to filter by.

        Returns:
            List of tasks matching the criteria.
        """
        if status is None:
            return list(self._tasks)
        return [t for t in self._tasks if t.status == status]

    def archive(self) -> None:
        """Archive the project."""
        self.is_archived = True
        self.updated_at = datetime.utcnow()

    def unarchive(self) -> None:
        """Unarchive the project."""
        self.is_archived = False
        self.updated_at = datetime.utcnow()

    @property
    def task_count(self) -> int:
        """Get the total number of tasks."""
        return len(self._tasks)

    @property
    def completed_task_count(self) -> int:
        """Get the number of completed tasks."""
        return len([t for t in self._tasks if t.status == TaskStatus.COMPLETED])

    @property
    def completion_percentage(self) -> float:
        """
        Calculate completion percentage.

        Returns:
            Percentage of completed tasks (0-100).
        """
        if not self._tasks:
            return 0.0
        return (self.completed_task_count / self.task_count) * 100

    @property
    def has_overdue_tasks(self) -> bool:
        """Check if the project has any overdue tasks."""
        return any(t.is_overdue for t in self._tasks)

    def get_summary(self) -> dict:
        """
        Get a summary of the project status.

        Returns:
            Dictionary with project statistics.
        """
        status_counts = {}
        for task in self._tasks:
            status_name = task.status.name
            status_counts[status_name] = status_counts.get(status_name, 0) + 1

        return {
            "id": str(self.id),
            "name": self.name,
            "total_tasks": self.task_count,
            "completed_tasks": self.completed_task_count,
            "completion_percentage": self.completion_percentage,
            "status_breakdown": status_counts,
            "has_overdue": self.has_overdue_tasks,
            "member_count": len(self.member_ids) + 1,
        }

    def __str__(self) -> str:
        """Return string representation of the project."""
        return f"Project({self.name}, {self.task_count} tasks)"
