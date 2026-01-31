"""Tests for TaskService."""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from tasktracker.models.task import Task, TaskStatus, TaskPriority
from tasktracker.services.task_service import TaskService
from tasktracker.services.base import ValidationError, NotFoundError


@pytest.fixture
def task_service():
    """Create a TaskService instance for testing."""
    return TaskService()


@pytest.fixture
def project_id():
    """Create a project ID for testing."""
    return uuid4()


class TestCreateTask:
    """Tests for task creation."""

    def test_create_task_with_valid_title(self, task_service, project_id):
        """Test creating a task with a valid title."""
        task = task_service.create_task("Test Task", project_id)

        assert task.title == "Test Task"
        assert task.project_id == project_id
        assert task.status == TaskStatus.PENDING
        assert task.priority == TaskPriority.MEDIUM

    def test_create_task_with_all_options(self, task_service, project_id):
        """Test creating a task with all options."""
        assignee_id = uuid4()
        due_date = datetime.utcnow() + timedelta(days=7)

        task = task_service.create_task(
            "Complete Task",
            project_id,
            description="Full description",
            assignee_id=assignee_id,
            priority=TaskPriority.HIGH,
            due_date=due_date,
            tags=["urgent", "backend"],
        )

        assert task.description == "Full description"
        assert task.assignee_id == assignee_id
        assert task.priority == TaskPriority.HIGH
        assert task.due_date == due_date
        assert "urgent" in task.tags
        assert "backend" in task.tags

    def test_create_task_with_short_title_raises_error(self, task_service, project_id):
        """Test that creating a task with a short title raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            task_service.create_task("Ab", project_id)

        assert "title" in str(exc_info.value)


class TestGetTask:
    """Tests for retrieving tasks."""

    def test_get_existing_task(self, task_service, project_id):
        """Test getting an existing task."""
        created = task_service.create_task("Test Task", project_id)
        retrieved = task_service.get_task(created.id)

        assert retrieved.id == created.id
        assert retrieved.title == created.title

    def test_get_nonexistent_task_raises_error(self, task_service):
        """Test that getting a nonexistent task raises NotFoundError."""
        with pytest.raises(NotFoundError):
            task_service.get_task(uuid4())


class TestUpdateTask:
    """Tests for updating tasks."""

    def test_update_task_title(self, task_service, project_id):
        """Test updating a task's title."""
        task = task_service.create_task("Original Title", project_id)
        updated = task_service.update_task(task.id, title="New Title")

        assert updated.title == "New Title"

    def test_update_task_status(self, task_service, project_id):
        """Test updating a task's status."""
        task = task_service.create_task("Test Task", project_id)
        updated = task_service.update_task(task.id, status=TaskStatus.IN_PROGRESS)

        assert updated.status == TaskStatus.IN_PROGRESS


class TestDeleteTask:
    """Tests for deleting tasks."""

    def test_delete_existing_task(self, task_service, project_id):
        """Test deleting an existing task."""
        task = task_service.create_task("To Delete", project_id)
        result = task_service.delete_task(task.id)

        assert result is True
        with pytest.raises(NotFoundError):
            task_service.get_task(task.id)

    def test_delete_nonexistent_task_raises_error(self, task_service):
        """Test that deleting a nonexistent task raises NotFoundError."""
        with pytest.raises(NotFoundError):
            task_service.delete_task(uuid4())


class TestCompleteTask:
    """Tests for completing tasks."""

    def test_complete_task(self, task_service, project_id):
        """Test marking a task as completed."""
        task = task_service.create_task("To Complete", project_id)
        completed = task_service.complete_task(task.id)

        assert completed.status == TaskStatus.COMPLETED


class TestSearchTasks:
    """Tests for searching tasks."""

    def test_search_by_title(self, task_service, project_id):
        """Test searching tasks by title."""
        task_service.create_task("Find Me", project_id)
        task_service.create_task("Other Task", project_id)

        results = task_service.search_tasks("Find")

        assert len(results) == 1
        assert results[0].title == "Find Me"

    def test_search_with_status_filter(self, task_service, project_id):
        """Test searching tasks with status filter."""
        task1 = task_service.create_task("Task One", project_id)
        task2 = task_service.create_task("Task Two", project_id)
        task_service.complete_task(task2.id)

        results = task_service.search_tasks(
            "Task",
            status=TaskStatus.COMPLETED
        )

        assert len(results) == 1
        assert results[0].id == task2.id
