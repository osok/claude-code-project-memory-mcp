"""Repository for Project entities."""

from typing import Optional
from uuid import UUID

from ..models.project import Project
from .base import InMemoryRepository


class ProjectRepository(InMemoryRepository[Project]):
    """
    Repository for managing Project entities.

    Provides specialized query methods for projects beyond basic CRUD.
    """

    def __init__(self) -> None:
        """Initialize the project repository."""
        super().__init__(id_getter=lambda p: p.id)

    def get_by_owner(self, owner_id: UUID) -> list[Project]:
        """
        Get all projects owned by a specific user.

        Args:
            owner_id: The owner's user ID.

        Returns:
            List of projects owned by the user.
        """
        return self.find_by(lambda p: p.owner_id == owner_id)

    def get_by_member(self, user_id: UUID) -> list[Project]:
        """
        Get all projects where user is a member (including owner).

        Args:
            user_id: The user ID to check membership.

        Returns:
            List of projects the user belongs to.
        """
        return self.find_by(lambda p: p.is_member(user_id))

    def get_active(self) -> list[Project]:
        """
        Get all non-archived projects.

        Returns:
            List of active projects.
        """
        return self.find_by(lambda p: not p.is_archived)

    def get_archived(self) -> list[Project]:
        """
        Get all archived projects.

        Returns:
            List of archived projects.
        """
        return self.find_by(lambda p: p.is_archived)

    def search(self, query: str, include_archived: bool = False) -> list[Project]:
        """
        Search projects by name or description.

        Args:
            query: Text to search for.
            include_archived: Whether to include archived projects.

        Returns:
            List of matching projects.
        """
        query_lower = query.lower()

        def matches(project: Project) -> bool:
            if not include_archived and project.is_archived:
                return False
            return (
                query_lower in project.name.lower()
                or query_lower in project.description.lower()
            )

        return self.find_by(matches)

    def get_with_overdue_tasks(self) -> list[Project]:
        """
        Get projects that have overdue tasks.

        Returns:
            List of projects with overdue tasks.
        """
        return self.find_by(lambda p: p.has_overdue_tasks)

    def get_near_completion(self, threshold: float = 80.0) -> list[Project]:
        """
        Get projects that are near completion.

        Args:
            threshold: Minimum completion percentage.

        Returns:
            List of projects at or above the threshold.
        """
        return self.find_by(
            lambda p: (
                not p.is_archived
                and p.task_count > 0
                and p.completion_percentage >= threshold
            )
        )

    def get_stalled(self, min_tasks: int = 1) -> list[Project]:
        """
        Get projects with no completed tasks.

        Args:
            min_tasks: Minimum total tasks to consider.

        Returns:
            List of stalled projects.
        """
        return self.find_by(
            lambda p: (
                not p.is_archived
                and p.task_count >= min_tasks
                and p.completed_task_count == 0
            )
        )

    def get_summaries(self, include_archived: bool = False) -> list[dict]:
        """
        Get summaries of all projects.

        Args:
            include_archived: Whether to include archived projects.

        Returns:
            List of project summary dictionaries.
        """
        projects = self.get_all() if include_archived else self.get_active()
        return [p.get_summary() for p in projects]
