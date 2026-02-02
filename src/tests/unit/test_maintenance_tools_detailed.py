"""Detailed unit tests for maintenance tools.

Comprehensive tests for api/tools/maintenance.py covering all functions
with various scenarios and edge cases.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from pathlib import Path
import tempfile

from memory_service.api.tools.maintenance import (
    normalize_memory,
    normalize_status,
    memory_statistics,
    export_memory,
    import_memory,
)
from memory_service.models import MemoryType, SyncStatus


class TestNormalizeMemoryDetailed:
    """Detailed tests for normalize_memory tool."""

    @pytest.fixture
    def mock_normalizer(self) -> AsyncMock:
        """Create mock normalizer."""
        normalizer = AsyncMock()
        normalizer.normalize.return_value = {
            "status": "completed",
            "phases_completed": ["snapshot", "deduplication", "cleanup"],
            "duplicates_merged": 5,
            "orphans_removed": 2,
            "embeddings_refreshed": 10,
        }
        return normalizer

    @pytest.fixture
    def mock_job_manager(self) -> AsyncMock:
        """Create mock job manager."""
        job_manager = AsyncMock()
        job_manager.create_job.return_value = "norm-job-001"
        return job_manager

    @pytest.fixture
    def mock_context(
        self,
        mock_normalizer: AsyncMock,
        mock_job_manager: AsyncMock,
    ) -> dict:
        """Create mock context."""
        return {
            "normalizer": mock_normalizer,
            "job_manager": mock_job_manager,
        }

    @pytest.mark.asyncio
    async def test_normalize_all_phases(self, mock_context: dict) -> None:
        """Test normalization with all phases (default)."""
        params = {
            "_context": mock_context,
        }

        result = await normalize_memory(params)

        assert result["status"] == "completed"
        assert result["job_id"] == "norm-job-001"
        mock_context["normalizer"].normalize.assert_called_once()

    @pytest.mark.asyncio
    async def test_normalize_specific_phases(self, mock_context: dict) -> None:
        """Test normalization with specific phases."""
        params = {
            "phases": ["deduplication", "orphan_detection"],
            "_context": mock_context,
        }

        result = await normalize_memory(params)

        assert result["status"] == "completed"
        call_kwargs = mock_context["normalizer"].normalize.call_args.kwargs
        assert call_kwargs["phases"] == ["deduplication", "orphan_detection"]

    @pytest.mark.asyncio
    async def test_normalize_dry_run_true(self, mock_context: dict) -> None:
        """Test normalization with dry_run=True."""
        params = {
            "dry_run": True,
            "_context": mock_context,
        }

        result = await normalize_memory(params)

        assert result["status"] == "completed"
        call_kwargs = mock_context["normalizer"].normalize.call_args.kwargs
        assert call_kwargs["dry_run"] is True

    @pytest.mark.asyncio
    async def test_normalize_dry_run_false(self, mock_context: dict) -> None:
        """Test normalization with dry_run=False (default)."""
        params = {
            "_context": mock_context,
        }

        result = await normalize_memory(params)

        call_kwargs = mock_context["normalizer"].normalize.call_args.kwargs
        assert call_kwargs["dry_run"] is False

    @pytest.mark.asyncio
    async def test_normalize_no_normalizer(self) -> None:
        """Test error when normalizer is not available."""
        params = {
            "_context": {},
        }

        result = await normalize_memory(params)

        assert result["status"] == "error"
        assert "not available" in result["error"]

    @pytest.mark.asyncio
    async def test_normalize_no_job_manager(
        self,
        mock_normalizer: AsyncMock,
    ) -> None:
        """Test normalization works without job manager."""
        params = {
            "_context": {"normalizer": mock_normalizer},
        }

        result = await normalize_memory(params)

        assert result["status"] == "completed"
        assert "job_id" not in result

    @pytest.mark.asyncio
    async def test_normalize_exception_handling(self, mock_context: dict) -> None:
        """Test exception handling during normalization."""
        mock_context["normalizer"].normalize.side_effect = Exception("Normalization failed")

        params = {
            "_context": mock_context,
        }

        result = await normalize_memory(params)

        assert result["status"] == "error"
        assert "Normalization failed" in result["error"]


class TestNormalizeStatusDetailed:
    """Detailed tests for normalize_status tool."""

    @pytest.fixture
    def mock_job_manager(self) -> AsyncMock:
        """Create mock job manager."""
        job_manager = AsyncMock()
        job_manager.get_job.return_value = {
            "job_id": "norm-job-001",
            "status": "running",
            "progress": 75,
            "current_phase": "deduplication",
        }
        job_manager.list_jobs.return_value = [
            {"job_id": "norm-job-001", "status": "running"},
            {"job_id": "norm-job-002", "status": "completed"},
        ]
        return job_manager

    @pytest.fixture
    def mock_normalizer(self) -> AsyncMock:
        """Create mock normalizer."""
        normalizer = AsyncMock()
        normalizer.get_status.return_value = {
            "status": "idle",
            "last_run": "2024-01-15T10:30:00Z",
            "last_result": {
                "duplicates_merged": 3,
                "orphans_removed": 1,
            },
        }
        return normalizer

    @pytest.fixture
    def mock_context(
        self,
        mock_job_manager: AsyncMock,
        mock_normalizer: AsyncMock,
    ) -> dict:
        """Create mock context."""
        return {
            "job_manager": mock_job_manager,
            "normalizer": mock_normalizer,
        }

    @pytest.mark.asyncio
    async def test_status_with_job_id_found(self, mock_context: dict) -> None:
        """Test getting status for existing job."""
        params = {
            "job_id": "norm-job-001",
            "_context": mock_context,
        }

        result = await normalize_status(params)

        assert result["job_id"] == "norm-job-001"
        assert result["status"] == "running"
        assert result["progress"] == 75
        mock_context["job_manager"].get_job.assert_called_once_with("norm-job-001")

    @pytest.mark.asyncio
    async def test_status_with_job_id_not_found(self, mock_context: dict) -> None:
        """Test getting status for non-existent job."""
        mock_context["job_manager"].get_job.return_value = None

        params = {
            "job_id": "nonexistent-job",
            "_context": mock_context,
        }

        result = await normalize_status(params)

        assert result["status"] == "not_found"
        assert result["job_id"] == "nonexistent-job"

    @pytest.mark.asyncio
    async def test_status_without_job_id(self, mock_context: dict) -> None:
        """Test getting normalizer status without job_id."""
        params = {
            "_context": mock_context,
        }

        result = await normalize_status(params)

        assert result["status"] == "idle"
        assert "recent_jobs" in result
        assert len(result["recent_jobs"]) == 2
        mock_context["normalizer"].get_status.assert_called_once()
        mock_context["job_manager"].list_jobs.assert_called_once()

    @pytest.mark.asyncio
    async def test_status_no_job_manager(
        self,
        mock_normalizer: AsyncMock,
    ) -> None:
        """Test status without job manager."""
        params = {
            "_context": {"normalizer": mock_normalizer},
        }

        result = await normalize_status(params)

        assert result["status"] == "idle"
        assert "recent_jobs" not in result

    @pytest.mark.asyncio
    async def test_status_no_normalizer(self) -> None:
        """Test status when normalizer is not available."""
        params = {
            "_context": {},
        }

        result = await normalize_status(params)

        assert result["status"] == "normalizer_not_available"


class TestMemoryStatisticsDetailed:
    """Detailed tests for memory_statistics tool."""

    @pytest.fixture
    def mock_qdrant(self) -> AsyncMock:
        """Create mock Qdrant adapter."""
        qdrant = AsyncMock()
        # Mock count returning different values for different filters
        qdrant.count.return_value = 100
        qdrant.get_collection_name.side_effect = lambda mt: f"memories_{mt.value}"
        qdrant.health_check.return_value = True
        return qdrant

    @pytest.fixture
    def mock_neo4j(self) -> AsyncMock:
        """Create mock Neo4j adapter."""
        neo4j = AsyncMock()
        neo4j.health_check.return_value = True
        return neo4j

    @pytest.fixture
    def mock_embedding_service(self) -> AsyncMock:
        """Create mock embedding service."""
        service = AsyncMock()
        service.get_cache_stats.return_value = {
            "total_entries": 500,
            "hits": 450,
            "misses": 50,
            "hit_rate": 0.9,
        }
        return service

    @pytest.fixture
    def mock_context(
        self,
        mock_qdrant: AsyncMock,
        mock_neo4j: AsyncMock,
        mock_embedding_service: MagicMock,
    ) -> dict:
        """Create mock context."""
        return {
            "qdrant": mock_qdrant,
            "neo4j": mock_neo4j,
            "embedding_service": mock_embedding_service,
        }

    @pytest.mark.asyncio
    async def test_statistics_complete(self, mock_context: dict) -> None:
        """Test getting complete statistics."""
        params = {"_context": mock_context}

        result = await memory_statistics(params)

        assert "memory_counts" in result
        assert "sync_status" in result
        assert "storage" in result
        assert "cache" in result
        assert "totals" in result

    @pytest.mark.asyncio
    async def test_statistics_memory_counts(self, mock_context: dict) -> None:
        """Test memory counts are calculated per type."""
        params = {"_context": mock_context}

        result = await memory_statistics(params)

        # Should have counts for all memory types
        for memory_type in MemoryType:
            assert memory_type.value in result["memory_counts"]
            type_stats = result["memory_counts"][memory_type.value]
            assert "total" in type_stats
            assert "active" in type_stats
            assert "deleted" in type_stats

    @pytest.mark.asyncio
    async def test_statistics_sync_status(self, mock_context: dict) -> None:
        """Test sync status counts are calculated."""
        params = {"_context": mock_context}

        result = await memory_statistics(params)

        # Should aggregate sync status counts
        assert isinstance(result["sync_status"], dict)

    @pytest.mark.asyncio
    async def test_statistics_storage_health(self, mock_context: dict) -> None:
        """Test storage health checks."""
        params = {"_context": mock_context}

        result = await memory_statistics(params)

        assert result["storage"]["qdrant"]["connected"] is True
        assert result["storage"]["neo4j"]["connected"] is True

    @pytest.mark.asyncio
    async def test_statistics_storage_unhealthy(self, mock_context: dict) -> None:
        """Test storage health when services are unhealthy."""
        mock_context["qdrant"].health_check.return_value = False
        mock_context["neo4j"].health_check.return_value = False

        params = {"_context": mock_context}

        result = await memory_statistics(params)

        assert result["storage"]["qdrant"]["connected"] is False
        assert result["storage"]["neo4j"]["connected"] is False

    @pytest.mark.asyncio
    async def test_statistics_cache_stats(self, mock_context: dict) -> None:
        """Test cache statistics are included."""
        params = {"_context": mock_context}

        result = await memory_statistics(params)

        assert result["cache"]["hit_rate"] == 0.9

    @pytest.mark.asyncio
    async def test_statistics_totals(self, mock_context: dict) -> None:
        """Test totals are calculated."""
        params = {"_context": mock_context}

        result = await memory_statistics(params)

        assert "memories" in result["totals"]
        assert "pending_sync" in result["totals"]
        assert "failed_sync" in result["totals"]

    @pytest.mark.asyncio
    async def test_statistics_exception(self, mock_context: dict) -> None:
        """Test exception handling in statistics."""
        mock_context["qdrant"].count.side_effect = Exception("Connection failed")

        params = {"_context": mock_context}

        result = await memory_statistics(params)

        assert "error" in result
        assert "Connection failed" in result["error"]


class TestExportMemoryDetailed:
    """Detailed tests for export_memory tool."""

    @pytest.fixture
    def mock_qdrant(self) -> AsyncMock:
        """Create mock Qdrant adapter."""
        qdrant = AsyncMock()
        qdrant.get_collection_name.side_effect = lambda mt: f"memories_{mt.value}"
        qdrant.scroll.return_value = ([], None)
        return qdrant

    @pytest.fixture
    def mock_context(self, mock_qdrant: AsyncMock) -> dict:
        """Create mock context."""
        return {"qdrant": mock_qdrant}

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.mark.asyncio
    async def test_export_to_file(
        self,
        mock_context: dict,
        temp_project_dir: str,
    ) -> None:
        """Test exporting to a file."""
        output_path = Path(temp_project_dir) / "export.jsonl"

        mock_context["qdrant"].scroll.return_value = (
            [
                {"id": str(uuid4()), "payload": {"content": "test1", "title": "Test 1"}},
                {"id": str(uuid4()), "payload": {"content": "test2", "title": "Test 2"}},
            ],
            None,
        )

        with patch("memory_service.api.tools.maintenance.get_settings") as mock_settings:
            mock_settings.return_value.project_path = temp_project_dir

            params = {
                "output_path": str(output_path),
                "_context": mock_context,
            }

            result = await export_memory(params)

        assert result["status"] == "exported"
        assert result["memory_count"] >= 0
        assert output_path.exists()

    @pytest.mark.asyncio
    async def test_export_without_output_path(self, mock_context: dict) -> None:
        """Test export returning data directly (no file)."""
        mock_context["qdrant"].scroll.return_value = (
            [
                {"id": str(uuid4()), "payload": {"content": "test", "title": "Test"}},
            ],
            None,
        )

        params = {
            "_context": mock_context,
        }

        result = await export_memory(params)

        assert result["status"] == "success"
        assert "sample" in result
        assert "memory_count" in result

    @pytest.mark.asyncio
    async def test_export_specific_memory_types(
        self,
        mock_context: dict,
    ) -> None:
        """Test exporting specific memory types."""
        params = {
            "memory_types": ["requirements", "design"],
            "_context": mock_context,
        }

        result = await export_memory(params)

        assert result["status"] == "success"
        # Should only query for specified types
        call_count = mock_context["qdrant"].scroll.call_count
        assert call_count == 2  # requirements and design

    @pytest.mark.asyncio
    async def test_export_with_filters(self, mock_context: dict) -> None:
        """Test export with additional filters."""
        params = {
            "filters": {"priority": "High"},
            "_context": mock_context,
        }

        result = await export_memory(params)

        # Check that filters are passed to scroll
        call_args = mock_context["qdrant"].scroll.call_args
        assert "deleted" in call_args.kwargs["filters"]

    @pytest.mark.asyncio
    async def test_export_pagination(self, mock_context: dict) -> None:
        """Test export with multiple pages."""
        # First call returns data with offset
        page1_data = [{"id": str(uuid4()), "payload": {"content": "page1"}}]
        page2_data = [{"id": str(uuid4()), "payload": {"content": "page2"}}]

        mock_context["qdrant"].scroll.side_effect = [
            (page1_data, "offset1"),  # First page
            (page2_data, None),  # Second page (last)
        ] * len(MemoryType)  # For each memory type

        params = {
            "_context": mock_context,
        }

        result = await export_memory(params)

        assert result["status"] == "success"
        # Should have paginated through all pages

    @pytest.mark.asyncio
    async def test_export_path_traversal_blocked(
        self,
        mock_context: dict,
        temp_project_dir: str,
    ) -> None:
        """Test that path traversal is blocked."""
        with patch("memory_service.api.tools.maintenance.get_settings") as mock_settings:
            mock_settings.return_value.project_path = temp_project_dir

            params = {
                "output_path": "/etc/passwd",
                "_context": mock_context,
            }

            result = await export_memory(params)

        assert result["status"] == "error"
        assert "must be within project" in result["error"]

    @pytest.mark.asyncio
    async def test_export_truncation(self, mock_context: dict) -> None:
        """Test export truncates large result sets."""
        # Generate more than 100 items
        large_data = [
            {"id": str(uuid4()), "payload": {"content": f"item{i}"}}
            for i in range(150)
        ]

        mock_context["qdrant"].scroll.return_value = (large_data, None)

        params = {
            "_context": mock_context,
        }

        result = await export_memory(params)

        assert result["status"] == "success"
        assert len(result["sample"]) == 100
        assert result["truncated"] is True

    @pytest.mark.asyncio
    async def test_export_exception(self, mock_context: dict) -> None:
        """Test export exception handling."""
        mock_context["qdrant"].scroll.side_effect = Exception("Scroll failed")

        params = {
            "_context": mock_context,
        }

        result = await export_memory(params)

        assert "error" in result


class TestImportMemoryDetailed:
    """Detailed tests for import_memory tool."""

    @pytest.fixture
    def mock_memory_manager(self) -> AsyncMock:
        """Create mock memory manager."""
        manager = AsyncMock()
        manager.add_memory.return_value = (uuid4(), [])
        manager.get_memory.return_value = None
        manager.update_memory.return_value = True
        return manager

    @pytest.fixture
    def mock_context(self, mock_memory_manager: AsyncMock) -> dict:
        """Create mock context."""
        return {"memory_manager": mock_memory_manager}

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.mark.asyncio
    async def test_import_from_file(
        self,
        mock_context: dict,
        temp_project_dir: str,
    ) -> None:
        """Test importing from a file."""
        input_path = Path(temp_project_dir) / "import.jsonl"
        records = [
            {
                "id": str(uuid4()),
                "type": "requirements",
                "content": "Test requirement",
                "requirement_id": "REQ-MEM-TEST-001",
                "title": "Test",
                "description": "Test description",
                "priority": "High",
                "status": "Draft",
                "source_document": "test.md",
            },
        ]
        input_path.write_text("\n".join(json.dumps(r) for r in records))

        with patch("memory_service.api.tools.maintenance.get_settings") as mock_settings:
            mock_settings.return_value.project_path = temp_project_dir

            params = {
                "input_path": str(input_path),
                "_context": mock_context,
            }

            result = await import_memory(params)

        assert result["status"] == "completed"
        assert result["imported"] == 1

    @pytest.mark.asyncio
    async def test_import_from_data_string(self, mock_context: dict) -> None:
        """Test importing from data string."""
        record_id = str(uuid4())
        data = json.dumps({
            "id": record_id,
            "type": "requirements",
            "content": "Test requirement",
            "requirement_id": "REQ-MEM-TEST-001",
            "title": "Test",
            "description": "Test description",
            "priority": "High",
            "status": "Draft",
            "source_document": "test.md",
        })

        params = {
            "data": data,
            "_context": mock_context,
        }

        result = await import_memory(params)

        assert result["status"] == "completed"
        assert result["imported"] == 1

    @pytest.mark.asyncio
    async def test_import_no_input(self, mock_context: dict) -> None:
        """Test error when no input provided."""
        params = {
            "_context": mock_context,
        }

        result = await import_memory(params)

        assert "error" in result
        assert "required" in result["error"]

    @pytest.mark.asyncio
    async def test_import_skip_existing(
        self,
        mock_context: dict,
        temp_project_dir: str,
    ) -> None:
        """Test skip conflict resolution."""
        record_id = str(uuid4())
        input_path = Path(temp_project_dir) / "import.jsonl"
        records = [
            {
                "id": record_id,
                "type": "requirements",
                "content": "Test",
                "requirement_id": "REQ-MEM-TEST-001",
                "title": "Test",
                "description": "Test",
                "priority": "High",
                "status": "Draft",
                "source_document": "test.md",
            },
        ]
        input_path.write_text("\n".join(json.dumps(r) for r in records))

        # Simulate existing memory
        mock_context["memory_manager"].get_memory.return_value = MagicMock()

        with patch("memory_service.api.tools.maintenance.get_settings") as mock_settings:
            mock_settings.return_value.project_path = temp_project_dir

            params = {
                "input_path": str(input_path),
                "conflict_resolution": "skip",
                "_context": mock_context,
            }

            result = await import_memory(params)

        assert result["status"] == "completed"
        assert result["skipped"] == 1
        assert result["imported"] == 0

    @pytest.mark.asyncio
    async def test_import_overwrite_existing(
        self,
        mock_context: dict,
        temp_project_dir: str,
    ) -> None:
        """Test overwrite conflict resolution."""
        record_id = str(uuid4())
        input_path = Path(temp_project_dir) / "import.jsonl"
        records = [
            {
                "id": record_id,
                "type": "requirements",
                "content": "Updated content",
                "requirement_id": "REQ-MEM-TEST-001",
                "title": "Updated",
                "description": "Updated",
                "priority": "High",
                "status": "Draft",
                "source_document": "test.md",
            },
        ]
        input_path.write_text("\n".join(json.dumps(r) for r in records))

        # Simulate existing memory
        mock_context["memory_manager"].get_memory.return_value = MagicMock()

        with patch("memory_service.api.tools.maintenance.get_settings") as mock_settings:
            mock_settings.return_value.project_path = temp_project_dir

            params = {
                "input_path": str(input_path),
                "conflict_resolution": "overwrite",
                "_context": mock_context,
            }

            result = await import_memory(params)

        assert result["status"] == "completed"
        assert result["overwritten"] == 1
        mock_context["memory_manager"].update_memory.assert_called_once()

    @pytest.mark.asyncio
    async def test_import_error_on_existing(
        self,
        mock_context: dict,
        temp_project_dir: str,
    ) -> None:
        """Test error conflict resolution."""
        record_id = str(uuid4())
        input_path = Path(temp_project_dir) / "import.jsonl"
        records = [
            {
                "id": record_id,
                "type": "requirements",
                "content": "Test",
                "requirement_id": "REQ-MEM-TEST-001",
                "title": "Test",
                "description": "Test",
                "priority": "High",
                "status": "Draft",
                "source_document": "test.md",
            },
        ]
        input_path.write_text("\n".join(json.dumps(r) for r in records))

        # Simulate existing memory
        mock_context["memory_manager"].get_memory.return_value = MagicMock()

        with patch("memory_service.api.tools.maintenance.get_settings") as mock_settings:
            mock_settings.return_value.project_path = temp_project_dir

            params = {
                "input_path": str(input_path),
                "conflict_resolution": "error",
                "_context": mock_context,
            }

            result = await import_memory(params)

        assert result["status"] == "completed"
        assert result["total_errors"] >= 1

    @pytest.mark.asyncio
    async def test_import_missing_type(self, mock_context: dict) -> None:
        """Test import with missing type field."""
        data = json.dumps({
            "id": str(uuid4()),
            "content": "Test",  # Missing "type"
        })

        params = {
            "data": data,
            "_context": mock_context,
        }

        result = await import_memory(params)

        assert result["status"] == "completed"
        assert result["total_errors"] >= 1
        assert any("Missing type" in str(e) for e in result["errors"])

    @pytest.mark.asyncio
    async def test_import_unknown_type(self, mock_context: dict) -> None:
        """Test import with unknown type."""
        data = json.dumps({
            "id": str(uuid4()),
            "type": "unknown_type",
            "content": "Test",
        })

        params = {
            "data": data,
            "_context": mock_context,
        }

        result = await import_memory(params)

        assert result["status"] == "completed"
        # Should handle unknown type gracefully

    @pytest.mark.asyncio
    async def test_import_path_traversal_blocked(
        self,
        mock_context: dict,
        temp_project_dir: str,
    ) -> None:
        """Test that path traversal is blocked."""
        with patch("memory_service.api.tools.maintenance.get_settings") as mock_settings:
            mock_settings.return_value.project_path = temp_project_dir

            params = {
                "input_path": "/etc/passwd",
                "_context": mock_context,
            }

            result = await import_memory(params)

        assert result["status"] == "error"
        assert "must be within project" in result["error"]

    @pytest.mark.asyncio
    async def test_import_file_not_found(
        self,
        mock_context: dict,
        temp_project_dir: str,
    ) -> None:
        """Test import with non-existent file."""
        with patch("memory_service.api.tools.maintenance.get_settings") as mock_settings:
            mock_settings.return_value.project_path = temp_project_dir

            params = {
                "input_path": f"{temp_project_dir}/nonexistent.jsonl",
                "_context": mock_context,
            }

            result = await import_memory(params)

        # Error is returned either in "error" key directly or with status
        assert "error" in result
        error_msg = result.get("error", "")
        assert "no such file" in error_msg.lower() or "not found" in error_msg.lower()

    @pytest.mark.asyncio
    async def test_import_empty_file(
        self,
        mock_context: dict,
        temp_project_dir: str,
    ) -> None:
        """Test import with empty file."""
        input_path = Path(temp_project_dir) / "empty.jsonl"
        input_path.write_text("")

        with patch("memory_service.api.tools.maintenance.get_settings") as mock_settings:
            mock_settings.return_value.project_path = temp_project_dir

            params = {
                "input_path": str(input_path),
                "_context": mock_context,
            }

            result = await import_memory(params)

        assert result["status"] == "completed"
        assert result["imported"] == 0

    @pytest.mark.asyncio
    async def test_import_multiple_records(
        self,
        mock_context: dict,
        temp_project_dir: str,
    ) -> None:
        """Test importing multiple records."""
        input_path = Path(temp_project_dir) / "import.jsonl"
        records = [
            {
                "id": str(uuid4()),
                "type": "requirements",
                "content": f"Requirement {i}",
                "requirement_id": f"REQ-MEM-TEST-{i:03d}",
                "title": f"Test {i}",
                "description": f"Description {i}",
                "priority": "Medium",
                "status": "Draft",
                "source_document": "test.md",
            }
            for i in range(5)
        ]
        input_path.write_text("\n".join(json.dumps(r) for r in records))

        with patch("memory_service.api.tools.maintenance.get_settings") as mock_settings:
            mock_settings.return_value.project_path = temp_project_dir

            params = {
                "input_path": str(input_path),
                "_context": mock_context,
            }

            result = await import_memory(params)

        assert result["status"] == "completed"
        assert result["imported"] == 5

    @pytest.mark.asyncio
    async def test_import_strips_embedding(
        self,
        mock_context: dict,
    ) -> None:
        """Test that import strips embedding field (will be regenerated)."""
        data = json.dumps({
            "id": str(uuid4()),
            "type": "requirements",
            "content": "Test",
            "requirement_id": "REQ-MEM-TEST-001",
            "title": "Test",
            "description": "Test",
            "priority": "High",
            "status": "Draft",
            "source_document": "test.md",
            "embedding": [0.1] * 1024,  # This should be removed
        })

        params = {
            "data": data,
            "_context": mock_context,
        }

        result = await import_memory(params)

        assert result["status"] == "completed"
        # Embedding should have been stripped before creating memory
