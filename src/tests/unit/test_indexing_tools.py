"""Unit tests for indexing tools.

Tests for api/tools/indexing.py covering index_file, index_directory,
index_status, and reindex tools.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from pathlib import Path
import tempfile
import os

from memory_service.api.tools.indexing import (
    index_file,
    index_directory,
    index_status,
    reindex,
)


class TestIndexFile:
    """Tests for index_file tool."""

    @pytest.fixture
    def mock_indexer(self) -> AsyncMock:
        """Create mock indexer worker."""
        indexer = AsyncMock()
        indexer.index_file.return_value = {
            "status": "success",
            "functions": 5,
            "classes": 2,
            "relationships": 3,
        }
        return indexer

    @pytest.fixture
    def mock_context(self, mock_indexer: AsyncMock) -> dict:
        """Create mock context with indexer."""
        return {"indexer": mock_indexer}

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary project directory with test file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def hello(): pass")
            yield tmpdir

    @pytest.mark.asyncio
    async def test_index_file_success(
        self,
        mock_context: dict,
        temp_project_dir: str,
    ) -> None:
        """Test successful file indexing."""
        test_file = os.path.join(temp_project_dir, "test.py")

        with patch("memory_service.api.tools.indexing.get_settings") as mock_settings:
            mock_settings.return_value.project_path = temp_project_dir

            params = {
                "file_path": test_file,
                "_context": mock_context,
            }

            result = await index_file(params)

            assert result["status"] == "success"
            assert result["functions"] == 5
            mock_context["indexer"].index_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_index_file_with_force(
        self,
        mock_context: dict,
        temp_project_dir: str,
    ) -> None:
        """Test file indexing with force flag."""
        test_file = os.path.join(temp_project_dir, "test.py")

        with patch("memory_service.api.tools.indexing.get_settings") as mock_settings:
            mock_settings.return_value.project_path = temp_project_dir

            params = {
                "file_path": test_file,
                "force": True,
                "_context": mock_context,
            }

            result = await index_file(params)

            assert result["status"] == "success"
            call_args = mock_context["indexer"].index_file.call_args
            assert call_args.kwargs.get("force") is True

    @pytest.mark.asyncio
    async def test_index_file_no_path(self, mock_context: dict) -> None:
        """Test error when file_path not provided."""
        params = {
            "_context": mock_context,
        }

        result = await index_file(params)

        assert "error" in result
        assert "required" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_index_file_no_indexer(self) -> None:
        """Test error when indexer not available."""
        params = {
            "file_path": "/some/path.py",
            "_context": {},
        }

        result = await index_file(params)

        assert result["status"] == "error"
        assert "not available" in result["error"]

    @pytest.mark.asyncio
    async def test_index_file_path_traversal(
        self,
        mock_context: dict,
        temp_project_dir: str,
    ) -> None:
        """Test path traversal is blocked."""
        with patch("memory_service.api.tools.indexing.get_settings") as mock_settings:
            mock_settings.return_value.project_path = temp_project_dir

            params = {
                "file_path": "/etc/passwd",
                "_context": mock_context,
            }

            result = await index_file(params)

            assert result["status"] == "error"
            assert "Path must be within project" in result["error"]

    @pytest.mark.asyncio
    async def test_index_file_indexer_exception(
        self,
        mock_context: dict,
        temp_project_dir: str,
    ) -> None:
        """Test error handling when indexer raises exception."""
        test_file = os.path.join(temp_project_dir, "test.py")
        mock_context["indexer"].index_file.side_effect = Exception("Parse error")

        with patch("memory_service.api.tools.indexing.get_settings") as mock_settings:
            mock_settings.return_value.project_path = temp_project_dir

            params = {
                "file_path": test_file,
                "_context": mock_context,
            }

            result = await index_file(params)

            assert result["status"] == "error"
            assert "Parse error" in result["error"]


class TestIndexDirectory:
    """Tests for index_directory tool."""

    @pytest.fixture
    def mock_indexer(self) -> AsyncMock:
        """Create mock indexer worker."""
        indexer = AsyncMock()
        indexer.index_directory.return_value = {
            "status": "success",
            "files_indexed": 10,
            "functions": 50,
            "classes": 20,
        }
        return indexer

    @pytest.fixture
    def mock_job_manager(self) -> AsyncMock:
        """Create mock job manager."""
        job_manager = AsyncMock()
        job_manager.create_job.return_value = "job-123"
        return job_manager

    @pytest.fixture
    def mock_context(
        self,
        mock_indexer: AsyncMock,
        mock_job_manager: AsyncMock,
    ) -> dict:
        """Create mock context."""
        return {
            "indexer": mock_indexer,
            "job_manager": mock_job_manager,
        }

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary project directory with test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            Path(tmpdir, "test1.py").write_text("def hello(): pass")
            Path(tmpdir, "test2.py").write_text("def world(): pass")
            subdir = Path(tmpdir, "subdir")
            subdir.mkdir()
            Path(subdir, "test3.py").write_text("def nested(): pass")
            yield tmpdir

    @pytest.mark.asyncio
    async def test_index_directory_success(
        self,
        mock_context: dict,
        temp_project_dir: str,
    ) -> None:
        """Test successful directory indexing."""
        with patch("memory_service.api.tools.indexing.get_settings") as mock_settings:
            mock_settings.return_value.project_path = temp_project_dir

            params = {
                "directory_path": temp_project_dir,
                "_context": mock_context,
            }

            result = await index_directory(params)

            assert result["status"] == "success"
            assert result["files_indexed"] == 10
            assert result["job_id"] == "job-123"
            mock_context["indexer"].index_directory.assert_called_once()

    @pytest.mark.asyncio
    async def test_index_directory_with_extensions(
        self,
        mock_context: dict,
        temp_project_dir: str,
    ) -> None:
        """Test directory indexing with file extensions filter."""
        with patch("memory_service.api.tools.indexing.get_settings") as mock_settings:
            mock_settings.return_value.project_path = temp_project_dir

            params = {
                "directory_path": temp_project_dir,
                "extensions": [".py", ".ts"],
                "_context": mock_context,
            }

            result = await index_directory(params)

            assert result["status"] == "success"
            call_args = mock_context["indexer"].index_directory.call_args
            assert call_args.kwargs.get("extensions") == [".py", ".ts"]

    @pytest.mark.asyncio
    async def test_index_directory_with_exclude(
        self,
        mock_context: dict,
        temp_project_dir: str,
    ) -> None:
        """Test directory indexing with exclude patterns."""
        with patch("memory_service.api.tools.indexing.get_settings") as mock_settings:
            mock_settings.return_value.project_path = temp_project_dir

            params = {
                "directory_path": temp_project_dir,
                "exclude": ["**/test_*", "**/node_modules/**"],
                "_context": mock_context,
            }

            result = await index_directory(params)

            assert result["status"] == "success"
            call_args = mock_context["indexer"].index_directory.call_args
            assert call_args.kwargs.get("exclude_patterns") == ["**/test_*", "**/node_modules/**"]

    @pytest.mark.asyncio
    async def test_index_directory_with_force(
        self,
        mock_context: dict,
        temp_project_dir: str,
    ) -> None:
        """Test directory indexing with force flag."""
        with patch("memory_service.api.tools.indexing.get_settings") as mock_settings:
            mock_settings.return_value.project_path = temp_project_dir

            params = {
                "directory_path": temp_project_dir,
                "force": True,
                "_context": mock_context,
            }

            result = await index_directory(params)

            assert result["status"] == "success"
            call_args = mock_context["indexer"].index_directory.call_args
            assert call_args.kwargs.get("force") is True

    @pytest.mark.asyncio
    async def test_index_directory_no_path(self, mock_context: dict) -> None:
        """Test error when directory_path not provided."""
        params = {
            "_context": mock_context,
        }

        result = await index_directory(params)

        assert "error" in result
        assert "required" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_index_directory_no_indexer(self) -> None:
        """Test error when indexer not available."""
        params = {
            "directory_path": "/some/path",
            "_context": {},
        }

        result = await index_directory(params)

        assert result["status"] == "error"
        assert "not available" in result["error"]

    @pytest.mark.asyncio
    async def test_index_directory_path_traversal(
        self,
        mock_context: dict,
        temp_project_dir: str,
    ) -> None:
        """Test path traversal is blocked."""
        with patch("memory_service.api.tools.indexing.get_settings") as mock_settings:
            mock_settings.return_value.project_path = temp_project_dir

            params = {
                "directory_path": "/etc",
                "_context": mock_context,
            }

            result = await index_directory(params)

            assert result["status"] == "error"
            assert "Path must be within project" in result["error"]

    @pytest.mark.asyncio
    async def test_index_directory_without_job_manager(
        self,
        mock_indexer: AsyncMock,
        temp_project_dir: str,
    ) -> None:
        """Test indexing without job manager."""
        with patch("memory_service.api.tools.indexing.get_settings") as mock_settings:
            mock_settings.return_value.project_path = temp_project_dir

            params = {
                "directory_path": temp_project_dir,
                "_context": {"indexer": mock_indexer},
            }

            result = await index_directory(params)

            assert result["status"] == "success"
            assert "job_id" not in result

    @pytest.mark.asyncio
    async def test_index_directory_exception(
        self,
        mock_context: dict,
        temp_project_dir: str,
    ) -> None:
        """Test error handling when indexer raises exception."""
        mock_context["indexer"].index_directory.side_effect = Exception("IO error")

        with patch("memory_service.api.tools.indexing.get_settings") as mock_settings:
            mock_settings.return_value.project_path = temp_project_dir

            params = {
                "directory_path": temp_project_dir,
                "_context": mock_context,
            }

            result = await index_directory(params)

            assert result["status"] == "error"
            assert "IO error" in result["error"]


class TestIndexStatus:
    """Tests for index_status tool."""

    @pytest.fixture
    def mock_job_manager(self) -> AsyncMock:
        """Create mock job manager."""
        job_manager = AsyncMock()
        job_manager.get_job.return_value = {
            "job_id": "job-123",
            "status": "running",
            "progress": 50,
        }
        job_manager.list_jobs.return_value = [
            {"job_id": "job-1", "status": "completed"},
            {"job_id": "job-2", "status": "running"},
        ]
        return job_manager

    @pytest.fixture
    def mock_qdrant(self) -> AsyncMock:
        """Create mock Qdrant adapter."""
        qdrant = AsyncMock()
        qdrant.count.return_value = 100
        qdrant.get_collection_name.return_value = "memories_function"
        return qdrant

    @pytest.fixture
    def mock_context(
        self,
        mock_job_manager: AsyncMock,
        mock_qdrant: AsyncMock,
    ) -> dict:
        """Create mock context."""
        return {
            "job_manager": mock_job_manager,
            "qdrant": mock_qdrant,
        }

    @pytest.mark.asyncio
    async def test_get_status_with_job_id(self, mock_context: dict) -> None:
        """Test getting status for specific job."""
        params = {
            "job_id": "job-123",
            "_context": mock_context,
        }

        result = await index_status(params)

        assert result["job_id"] == "job-123"
        assert result["status"] == "running"
        assert result["progress"] == 50

    @pytest.mark.asyncio
    async def test_get_status_job_not_found(self, mock_context: dict) -> None:
        """Test status when job not found."""
        mock_context["job_manager"].get_job.return_value = None

        params = {
            "job_id": "nonexistent-job",
            "_context": mock_context,
        }

        result = await index_status(params)

        assert result["status"] == "not_found"

    @pytest.mark.asyncio
    async def test_get_overall_stats(self, mock_context: dict) -> None:
        """Test getting overall indexing stats."""
        params = {
            "_context": mock_context,
        }

        result = await index_status(params)

        assert "function_count" in result
        assert "component_count" in result
        assert "total_indexed" in result
        assert result["function_count"] == 100

    @pytest.mark.asyncio
    async def test_get_overall_stats_with_recent_jobs(self, mock_context: dict) -> None:
        """Test overall stats include recent jobs list."""
        params = {
            "_context": mock_context,
        }

        result = await index_status(params)

        assert "recent_jobs" in result
        mock_context["job_manager"].list_jobs.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_overall_stats_without_job_manager(
        self,
        mock_qdrant: AsyncMock,
    ) -> None:
        """Test overall stats without job manager."""
        params = {
            "_context": {"qdrant": mock_qdrant},
        }

        result = await index_status(params)

        assert "function_count" in result
        assert "recent_jobs" not in result

    @pytest.mark.asyncio
    async def test_get_status_exception(self, mock_context: dict) -> None:
        """Test error handling when getting stats fails."""
        mock_context["qdrant"].count.side_effect = Exception("Connection error")

        params = {
            "_context": mock_context,
        }

        result = await index_status(params)

        assert "error" in result


class TestReindex:
    """Tests for reindex tool."""

    @pytest.fixture
    def mock_indexer(self) -> AsyncMock:
        """Create mock indexer worker."""
        indexer = AsyncMock()
        indexer.index_directory.return_value = {
            "status": "success",
            "files_indexed": 15,
            "functions": 75,
        }
        indexer.clear_index.return_value = 100
        return indexer

    @pytest.fixture
    def mock_job_manager(self) -> AsyncMock:
        """Create mock job manager."""
        job_manager = AsyncMock()
        job_manager.create_job.return_value = "reindex-job-456"
        return job_manager

    @pytest.fixture
    def mock_context(
        self,
        mock_indexer: AsyncMock,
        mock_job_manager: AsyncMock,
    ) -> dict:
        """Create mock context."""
        return {
            "indexer": mock_indexer,
            "job_manager": mock_job_manager,
        }

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "test.py").write_text("def hello(): pass")
            yield tmpdir

    @pytest.mark.asyncio
    async def test_reindex_changed_scope(
        self,
        mock_context: dict,
        temp_project_dir: str,
    ) -> None:
        """Test reindex with changed scope (incremental)."""
        with patch("memory_service.api.tools.indexing.get_settings") as mock_settings:
            mock_settings.return_value.project_path = temp_project_dir

            params = {
                "directory_path": temp_project_dir,
                "scope": "changed",
                "_context": mock_context,
            }

            result = await reindex(params)

            assert result["status"] == "success"
            assert result["scope"] == "changed"
            # clear_index should NOT be called for changed scope
            mock_context["indexer"].clear_index.assert_not_called()

    @pytest.mark.asyncio
    async def test_reindex_full_scope(
        self,
        mock_context: dict,
        temp_project_dir: str,
    ) -> None:
        """Test reindex with full scope (clear and rebuild)."""
        with patch("memory_service.api.tools.indexing.get_settings") as mock_settings:
            mock_settings.return_value.project_path = temp_project_dir

            params = {
                "directory_path": temp_project_dir,
                "scope": "full",
                "_context": mock_context,
            }

            result = await reindex(params)

            assert result["status"] == "success"
            assert result["scope"] == "full"
            # clear_index SHOULD be called for full scope
            mock_context["indexer"].clear_index.assert_called_once()

    @pytest.mark.asyncio
    async def test_reindex_default_scope(
        self,
        mock_context: dict,
        temp_project_dir: str,
    ) -> None:
        """Test reindex with default scope (should be changed)."""
        with patch("memory_service.api.tools.indexing.get_settings") as mock_settings:
            mock_settings.return_value.project_path = temp_project_dir

            params = {
                "directory_path": temp_project_dir,
                "_context": mock_context,
            }

            result = await reindex(params)

            assert result["status"] == "success"
            assert result["scope"] == "changed"

    @pytest.mark.asyncio
    async def test_reindex_with_extensions(
        self,
        mock_context: dict,
        temp_project_dir: str,
    ) -> None:
        """Test reindex with extensions filter."""
        with patch("memory_service.api.tools.indexing.get_settings") as mock_settings:
            mock_settings.return_value.project_path = temp_project_dir

            params = {
                "directory_path": temp_project_dir,
                "extensions": [".py"],
                "_context": mock_context,
            }

            result = await reindex(params)

            assert result["status"] == "success"
            call_args = mock_context["indexer"].index_directory.call_args
            assert call_args.kwargs.get("extensions") == [".py"]

    @pytest.mark.asyncio
    async def test_reindex_with_exclude(
        self,
        mock_context: dict,
        temp_project_dir: str,
    ) -> None:
        """Test reindex with exclude patterns."""
        with patch("memory_service.api.tools.indexing.get_settings") as mock_settings:
            mock_settings.return_value.project_path = temp_project_dir

            params = {
                "directory_path": temp_project_dir,
                "exclude": ["**/test_*"],
                "_context": mock_context,
            }

            result = await reindex(params)

            assert result["status"] == "success"
            call_args = mock_context["indexer"].index_directory.call_args
            assert call_args.kwargs.get("exclude_patterns") == ["**/test_*"]

    @pytest.mark.asyncio
    async def test_reindex_no_path(self, mock_context: dict) -> None:
        """Test error when directory_path not provided."""
        params = {
            "_context": mock_context,
        }

        result = await reindex(params)

        assert "error" in result
        assert "required" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_reindex_no_indexer(self) -> None:
        """Test error when indexer not available."""
        params = {
            "directory_path": "/some/path",
            "_context": {},
        }

        result = await reindex(params)

        assert result["status"] == "error"
        assert "not available" in result["error"]

    @pytest.mark.asyncio
    async def test_reindex_path_traversal(
        self,
        mock_context: dict,
        temp_project_dir: str,
    ) -> None:
        """Test path traversal is blocked."""
        with patch("memory_service.api.tools.indexing.get_settings") as mock_settings:
            mock_settings.return_value.project_path = temp_project_dir

            params = {
                "directory_path": "/etc",
                "_context": mock_context,
            }

            result = await reindex(params)

            assert result["status"] == "error"
            assert "Path must be within project" in result["error"]

    @pytest.mark.asyncio
    async def test_reindex_job_tracking(
        self,
        mock_context: dict,
        temp_project_dir: str,
    ) -> None:
        """Test reindex creates tracking job."""
        with patch("memory_service.api.tools.indexing.get_settings") as mock_settings:
            mock_settings.return_value.project_path = temp_project_dir

            params = {
                "directory_path": temp_project_dir,
                "_context": mock_context,
            }

            result = await reindex(params)

            assert result["job_id"] == "reindex-job-456"
            mock_context["job_manager"].create_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_reindex_exception(
        self,
        mock_context: dict,
        temp_project_dir: str,
    ) -> None:
        """Test error handling when reindex fails."""
        mock_context["indexer"].index_directory.side_effect = Exception("Reindex failed")

        with patch("memory_service.api.tools.indexing.get_settings") as mock_settings:
            mock_settings.return_value.project_path = temp_project_dir

            params = {
                "directory_path": temp_project_dir,
                "_context": mock_context,
            }

            result = await reindex(params)

            assert result["status"] == "error"
            assert "Reindex failed" in result["error"]
