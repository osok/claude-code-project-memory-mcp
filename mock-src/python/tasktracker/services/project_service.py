"""Project service for managing projects."""

import asyncio
from typing import Optional
from uuid import UUID

from ..models.project import Project
from ..models.task import Task, TaskStatus
from ..repositories.project_repository import ProjectRepository
from ..repositories.task_repository import TaskRepository
from .base import (
    BaseService,
    NotFoundError,
    ValidationError,
    AuthorizationError,
    log_call,
    measure_time,
)


class ProjectService(BaseService):
    """
    Service for project management operations.

    Handles creating and managing projects, including membership
    and task aggregation.

    Attributes:
        project_repo: Repository for project data.
        task_repo: Repository for task data.
    """

    def __init__(
        self,
        project_repo: Optional[ProjectRepository] = None,
        task_repo: Optional[TaskRepository] = None,
    ) -> None:
        """
        Initialize the project service.

        Args:
            project_repo: Optional project repository.
            task_repo: Optional task repository.
        """
        super().__init__()
        self.project_repo = project_repo or ProjectRepository()
        self.task_repo = task_repo or TaskRepository()

    @log_call
    @measure_time
    def create_project(
        self,
        name: str,
        owner_id: UUID,
        description: str = "",
        member_ids: Optional[list[UUID]] = None,
    ) -> Project:
        """
        Create a new project.

        Args:
            name: Project name.
            owner_id: ID of the project owner.
            description: Project description.
            member_ids: Optional list of initial member IDs.

        Returns:
            The created project.

        Raises:
            ValidationError: If name is invalid.
        """
        if not name or len(name.strip()) < 3:
            raise ValidationError("name", "Project name must be at least 3 characters")

        if len(name) > 100:
            raise ValidationError("name", "Project name must be at most 100 characters")

        project = Project(
            name=name.strip(),
            owner_id=owner_id,
            description=description,
            member_ids=member_ids or [],
        )

        created = self.project_repo.create(project)
        self._log_info("Created project: %s", created.name)
        return created

    @log_call
    def get_project(self, project_id: UUID) -> Project:
        """
        Get a project by ID.

        Args:
            project_id: The project's unique identifier.

        Returns:
            The project.

        Raises:
            NotFoundError: If project doesn't exist.
        """
        project = self.project_repo.get(project_id)
        if not project:
            raise NotFoundError("Project", str(project_id))
        return project

    @log_call
    def update_project(
        self,
        project_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        actor_id: Optional[UUID] = None,
    ) -> Project:
        """
        Update a project's properties.

        Args:
            project_id: The project to update.
            name: New name (if provided).
            description: New description (if provided).
            actor_id: User performing the update.

        Returns:
            The updated project.

        Raises:
            AuthorizationError: If actor is not the owner.
        """
        project = self.get_project(project_id)

        if actor_id and project.owner_id != actor_id:
            raise AuthorizationError("update", "this project")

        if name is not None:
            if len(name.strip()) < 3:
                raise ValidationError("name", "Name must be at least 3 characters")
            project.name = name.strip()

        if description is not None:
            project.description = description

        self.project_repo.update(project)
        return project

    @log_call
    def delete_project(self, project_id: UUID, actor_id: UUID) -> bool:
        """
        Delete a project.

        Args:
            project_id: The project to delete.
            actor_id: User performing the deletion.

        Returns:
            True if deleted.

        Raises:
            AuthorizationError: If actor is not the owner.
        """
        project = self.get_project(project_id)

        if project.owner_id != actor_id:
            raise AuthorizationError("delete", "this project")

        # Delete all tasks in the project
        tasks = self.task_repo.get_by_project(project_id)
        for task in tasks:
            self.task_repo.delete(task.id)

        self.project_repo.delete(project_id)
        self._log_info("Deleted project: %s", project.name)
        return True

    def add_member(
        self,
        project_id: UUID,
        user_id: UUID,
        actor_id: UUID,
    ) -> Project:
        """
        Add a member to a project.

        Args:
            project_id: The project to modify.
            user_id: The user to add.
            actor_id: User performing the action.

        Returns:
            The updated project.
        """
        project = self.get_project(project_id)

        if project.owner_id != actor_id:
            raise AuthorizationError("add members to", "this project")

        project.add_member(user_id)
        self.project_repo.update(project)
        return project

    def remove_member(
        self,
        project_id: UUID,
        user_id: UUID,
        actor_id: UUID,
    ) -> Project:
        """
        Remove a member from a project.

        Args:
            project_id: The project to modify.
            user_id: The user to remove.
            actor_id: User performing the action.

        Returns:
            The updated project.
        """
        project = self.get_project(project_id)

        if project.owner_id != actor_id:
            raise AuthorizationError("remove members from", "this project")

        project.remove_member(user_id)
        self.project_repo.update(project)
        return project

    def get_user_projects(self, user_id: UUID) -> list[Project]:
        """
        Get all projects a user is a member of.

        Args:
            user_id: The user's ID.

        Returns:
            List of projects.
        """
        return self.project_repo.get_by_member(user_id)

    def get_owned_projects(self, user_id: UUID) -> list[Project]:
        """
        Get all projects owned by a user.

        Args:
            user_id: The user's ID.

        Returns:
            List of owned projects.
        """
        return self.project_repo.get_by_owner(user_id)

    async def get_project_summary_async(
        self,
        project_id: UUID,
    ) -> dict:
        """
        Get a comprehensive project summary asynchronously.

        Args:
            project_id: The project's ID.

        Returns:
            Dictionary with project details and statistics.
        """
        project = self.get_project(project_id)

        # Simulate async task loading
        await asyncio.sleep(0.01)
        tasks = self.task_repo.get_by_project(project_id)

        # Load tasks into project
        for task in tasks:
            if task not in project._tasks:
                project._tasks.append(task)

        return project.get_summary()

    async def bulk_archive_async(
        self,
        project_ids: list[UUID],
        actor_id: UUID,
    ) -> list[Project]:
        """
        Archive multiple projects asynchronously.

        Args:
            project_ids: List of project IDs to archive.
            actor_id: User performing the action.

        Returns:
            List of archived projects.
        """
        archived = []
        for project_id in project_ids:
            project = await self._archive_project_async(project_id, actor_id)
            if project:
                archived.append(project)
        return archived

    async def _archive_project_async(
        self,
        project_id: UUID,
        actor_id: UUID,
    ) -> Optional[Project]:
        """Archive a single project asynchronously."""
        try:
            project = self.get_project(project_id)
            if project.owner_id != actor_id:
                return None
            await asyncio.sleep(0.01)
            project.archive()
            self.project_repo.update(project)
            return project
        except NotFoundError:
            return None

    def get_project_tasks(
        self,
        project_id: UUID,
        status: Optional[TaskStatus] = None,
    ) -> list[Task]:
        """
        Get tasks for a project, optionally filtered by status.

        Args:
            project_id: The project's ID.
            status: Optional status filter.

        Returns:
            List of tasks.
        """
        self.get_project(project_id)  # Verify project exists
        tasks = self.task_repo.get_by_project(project_id)

        if status:
            tasks = [t for t in tasks if t.status == status]

        return tasks

    def search_projects(
        self,
        query: str,
        include_archived: bool = False,
    ) -> list[Project]:
        """
        Search projects by name or description.

        Args:
            query: Search text.
            include_archived: Whether to include archived projects.

        Returns:
            Matching projects.
        """
        return self.project_repo.search(query, include_archived)

    def get_stalled_projects(self) -> list[Project]:
        """Get projects with no completed tasks."""
        return self.project_repo.get_stalled()

    def get_projects_near_completion(
        self,
        threshold: float = 80.0,
    ) -> list[Project]:
        """
        Get projects that are near completion.

        Args:
            threshold: Minimum completion percentage.

        Returns:
            Projects at or above the threshold.
        """
        return self.project_repo.get_near_completion(threshold)

    @property
    def active_project_count(self) -> int:
        """Get count of active projects."""
        return len(self.project_repo.get_active())
