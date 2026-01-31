"""Task model with status and priority enums."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Optional
from uuid import UUID, uuid4


class TaskStatus(Enum):
    """Status values for tasks."""

    PENDING = auto()
    IN_PROGRESS = auto()
    BLOCKED = auto()
    COMPLETED = auto()
    CANCELLED = auto()


class TaskPriority(Enum):
    """Priority levels for tasks."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Task:
    """
    Represents a task in the system.

    A task belongs to a project and can be assigned to a user.
    Tasks have status and priority tracking with timestamps.

    Attributes:
        id: Unique identifier for the task.
        title: Short description of the task.
        description: Detailed description of what needs to be done.
        project_id: ID of the project this task belongs to.
        assignee_id: ID of the user assigned to this task.
        status: Current status of the task.
        priority: Priority level of the task.
        created_at: When the task was created.
        updated_at: When the task was last updated.
        due_date: Optional deadline for the task.
        tags: List of tags for categorization.
    """

    title: str
    project_id: UUID
    id: UUID = field(default_factory=uuid4)
    description: str = ""
    assignee_id: Optional[UUID] = None
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    due_date: Optional[datetime] = None
    tags: list[str] = field(default_factory=list)

    def mark_complete(self) -> None:
        """Mark the task as completed and update timestamp."""
        self.status = TaskStatus.COMPLETED
        self.updated_at = datetime.utcnow()

    def mark_blocked(self, reason: str = "") -> None:
        """
        Mark the task as blocked.

        Args:
            reason: Optional reason for the block.
        """
        self.status = TaskStatus.BLOCKED
        self.updated_at = datetime.utcnow()
        if reason:
            self.description = f"{self.description}\n\nBlocked: {reason}"

    def assign_to(self, user_id: UUID) -> None:
        """
        Assign the task to a user.

        Args:
            user_id: The ID of the user to assign.
        """
        self.assignee_id = user_id
        self.updated_at = datetime.utcnow()

    def add_tag(self, tag: str) -> bool:
        """
        Add a tag to the task.

        Args:
            tag: The tag to add.

        Returns:
            True if tag was added, False if already exists.
        """
        normalized_tag = tag.lower().strip()
        if normalized_tag not in self.tags:
            self.tags.append(normalized_tag)
            self.updated_at = datetime.utcnow()
            return True
        return False

    def remove_tag(self, tag: str) -> bool:
        """
        Remove a tag from the task.

        Args:
            tag: The tag to remove.

        Returns:
            True if tag was removed, False if not found.
        """
        normalized_tag = tag.lower().strip()
        if normalized_tag in self.tags:
            self.tags.remove(normalized_tag)
            self.updated_at = datetime.utcnow()
            return True
        return False

    @property
    def is_overdue(self) -> bool:
        """Check if the task is past its due date."""
        if self.due_date is None:
            return False
        return datetime.utcnow() > self.due_date and self.status != TaskStatus.COMPLETED

    @property
    def is_active(self) -> bool:
        """Check if the task is in an active state."""
        return self.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS)

    def __str__(self) -> str:
        """Return string representation of the task."""
        return f"Task({self.title}, status={self.status.name})"

    def __repr__(self) -> str:
        """Return detailed representation of the task."""
        return (
            f"Task(id={self.id}, title={self.title!r}, "
            f"status={self.status.name}, priority={self.priority.name})"
        )
