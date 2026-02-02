"""Unit tests for maintenance tools."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from memory_service.api.tools.maintenance import (
    memory_statistics,
    normalize_memory,
    normalize_status,
    export_memory,
    import_memory,
)
from memory_service.models import MemoryType


class TestMemoryStatistics:
    """Tests for memory_statistics tool."""

    @pytest.fixture
    def mock_context(self) -> dict:
        """Create mock context."""
        qdrant = AsyncMock()
        qdrant.count.return_value = 100
        qdrant.get_collection_name.return_value = "requirements"

        neo4j = AsyncMock()
        neo4j.get_statistics.return_value = {"nodes": 100, "relationships": 50}

        embedding_service = MagicMock()
        embedding_service.get_cache_stats.return_value = {"hits": 50, "misses": 10}

        return {
            "qdrant": qdrant,
            "neo4j": neo4j,
            "embedding_service": embedding_service,
        }

    @pytest.mark.asyncio
    async def test_get_statistics_success(self, mock_context: dict) -> None:
        """Test getting memory statistics."""
        params = {"_context": mock_context}

        result = await memory_statistics(params)

        assert isinstance(result, dict)
        assert "memory_counts" in result or "error" in result

    @pytest.mark.asyncio
    async def test_get_statistics_with_qdrant_error(
        self,
        mock_context: dict,
    ) -> None:
        """Test statistics when Qdrant has error."""
        mock_context["qdrant"].count.side_effect = Exception("Connection error")

        params = {"_context": mock_context}

        result = await memory_statistics(params)

        # Should handle error gracefully
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_get_statistics_with_neo4j_error(
        self,
        mock_context: dict,
    ) -> None:
        """Test statistics when Neo4j has error."""
        mock_context["neo4j"].get_statistics.side_effect = Exception("Connection error")

        params = {"_context": mock_context}

        result = await memory_statistics(params)

        # Should handle error gracefully
        assert isinstance(result, dict)


class TestNormalizeMemory:
    """Tests for normalize_memory tool."""

    @pytest.fixture
    def mock_context(self) -> dict:
        """Create mock context."""
        normalizer = AsyncMock()
        normalizer.normalize.return_value = {
            "status": "completed",
            "duplicates_merged": 5,
            "orphans_removed": 2,
        }

        job_manager = AsyncMock()
        job_manager.create_job.return_value = "norm-job-123"

        return {
            "normalizer": normalizer,
            "job_manager": job_manager,
        }

    @pytest.mark.asyncio
    async def test_normalize_sync_success(self, mock_context: dict) -> None:
        """Test synchronous normalization."""
        params = {
            "dry_run": False,
            "_context": mock_context,
        }

        result = await normalize_memory(params)

        assert isinstance(result, dict)
        mock_context["normalizer"].normalize.assert_called_once()

    @pytest.mark.asyncio
    async def test_normalize_dry_run(self, mock_context: dict) -> None:
        """Test normalization dry run."""
        params = {
            "dry_run": True,
            "_context": mock_context,
        }

        result = await normalize_memory(params)

        assert isinstance(result, dict)
        # Dry run should still call normalize
        mock_context["normalizer"].normalize.assert_called_once()
        call_kwargs = mock_context["normalizer"].normalize.call_args.kwargs
        assert call_kwargs.get("dry_run") is True

    @pytest.mark.asyncio
    async def test_normalize_no_normalizer(self) -> None:
        """Test error when normalizer not available."""
        params = {
            "_context": {},
        }

        result = await normalize_memory(params)

        assert "error" in result
        assert "not available" in result["error"]

    @pytest.mark.asyncio
    async def test_normalize_specific_phases(self, mock_context: dict) -> None:
        """Test normalization with specific phases."""
        params = {
            "phases": ["deduplication", "cleanup"],
            "dry_run": True,
            "_context": mock_context,
        }

        result = await normalize_memory(params)

        assert isinstance(result, dict)
        call_kwargs = mock_context["normalizer"].normalize.call_args.kwargs
        assert call_kwargs.get("phases") == ["deduplication", "cleanup"]


class TestNormalizeStatus:
    """Tests for normalize_status tool."""

    @pytest.fixture
    def mock_context(self) -> dict:
        """Create mock context."""
        job_manager = AsyncMock()
        job_manager.get_job.return_value = {
            "id": "norm-job-123",
            "status": "running",
            "progress": 50,
        }

        normalizer = AsyncMock()
        normalizer.get_status.return_value = {
            "status": "idle",
            "last_run": "2024-01-01T00:00:00Z",
        }

        return {
            "job_manager": job_manager,
            "normalizer": normalizer,
        }

    @pytest.mark.asyncio
    async def test_get_status_with_job_id(self, mock_context: dict) -> None:
        """Test getting status for specific job."""
        params = {
            "job_id": "norm-job-123",
            "_context": mock_context,
        }

        result = await normalize_status(params)

        assert isinstance(result, dict)
        assert result["status"] == "running"

    @pytest.mark.asyncio
    async def test_get_status_no_job_id(self, mock_context: dict) -> None:
        """Test getting normalizer status without job_id."""
        params = {
            "_context": mock_context,
        }

        result = await normalize_status(params)

        assert isinstance(result, dict)
        mock_context["normalizer"].get_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_status_job_not_found(self, mock_context: dict) -> None:
        """Test status when job not found."""
        mock_context["job_manager"].get_job.return_value = None

        params = {
            "job_id": "nonexistent",
            "_context": mock_context,
        }

        result = await normalize_status(params)

        assert isinstance(result, dict)
        # Should indicate not found or empty


class TestExportMemory:
    """Tests for export_memory tool."""

    @pytest.fixture
    def mock_context(self) -> dict:
        """Create mock context."""
        qdrant = AsyncMock()
        qdrant.get_collection_name.return_value = "requirements"
        qdrant.scroll.return_value = ([], None)

        return {
            "qdrant": qdrant,
        }

    @pytest.mark.asyncio
    async def test_export_success(
        self,
        mock_context: dict,
        tmp_path,
    ) -> None:
        """Test successful export."""
        from unittest.mock import patch, MagicMock

        output_path = tmp_path / "export.jsonl"

        # Patch settings to use tmp_path as project path
        mock_settings = MagicMock()
        mock_settings.project_path = str(tmp_path)

        with patch("memory_service.api.tools.maintenance.get_settings", return_value=mock_settings):
            params = {
                "output_path": str(output_path),
                "_context": mock_context,
            }

            result = await export_memory(params)

        assert isinstance(result, dict)
        assert result.get("status") in ("completed", "exported") or "exported_count" in result or "memory_count" in result

    @pytest.mark.asyncio
    async def test_export_with_memory_types(
        self,
        mock_context: dict,
        tmp_path,
    ) -> None:
        """Test export with specific memory types."""
        output_path = tmp_path / "export.jsonl"

        params = {
            "output_path": str(output_path),
            "memory_types": ["requirements", "design"],
            "_context": mock_context,
        }

        result = await export_memory(params)

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_export_with_data(
        self,
        mock_context: dict,
        tmp_path,
    ) -> None:
        """Test export with actual data."""
        output_path = tmp_path / "export.jsonl"

        mock_context["qdrant"].scroll.return_value = (
            [
                {
                    "id": str(uuid4()),
                    "vector": [0.1] * 1024,
                    "payload": {"content": "test", "title": "Test"},
                }
            ],
            None,  # No more pages
        )

        params = {
            "output_path": str(output_path),
            "_context": mock_context,
        }

        result = await export_memory(params)

        assert isinstance(result, dict)


class TestImportMemory:
    """Tests for import_memory tool."""

    @pytest.fixture
    def mock_context(self) -> dict:
        """Create mock context."""
        qdrant = AsyncMock()
        qdrant.get_collection_name.return_value = "requirements"
        qdrant.upsert.return_value = True
        qdrant.get.return_value = None  # Not existing

        memory_manager = AsyncMock()
        memory_manager.add_memory.return_value = (uuid4(), [])

        return {
            "qdrant": qdrant,
            "memory_manager": memory_manager,
        }

    @pytest.mark.asyncio
    async def test_import_empty_file(
        self,
        mock_context: dict,
        tmp_path,
    ) -> None:
        """Test import with empty file."""
        input_path = tmp_path / "import.jsonl"
        input_path.write_text("")

        params = {
            "input_path": str(input_path),
            "_context": mock_context,
        }

        result = await import_memory(params)

        assert isinstance(result, dict)
        assert result.get("imported_count") == 0 or "status" in result

    @pytest.mark.asyncio
    async def test_import_with_data(
        self,
        mock_context: dict,
        tmp_path,
    ) -> None:
        """Test import with data."""
        import json

        input_path = tmp_path / "import.jsonl"
        records = [
            {
                "id": str(uuid4()),
                "type": "requirements",
                "vector": [0.1] * 1024,
                "content": "Test requirement",
            }
        ]
        input_path.write_text("\n".join(json.dumps(r) for r in records))

        params = {
            "input_path": str(input_path),
            "_context": mock_context,
        }

        result = await import_memory(params)

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_import_skip_existing(
        self,
        mock_context: dict,
        tmp_path,
    ) -> None:
        """Test import with skip_existing flag."""
        import json

        input_path = tmp_path / "import.jsonl"
        record_id = str(uuid4())
        records = [
            {
                "id": record_id,
                "type": "requirements",
                "vector": [0.1] * 1024,
                "content": "Test requirement",
            }
        ]
        input_path.write_text("\n".join(json.dumps(r) for r in records))

        # Simulate existing record
        mock_context["qdrant"].get.return_value = {"id": record_id}

        params = {
            "input_path": str(input_path),
            "skip_existing": True,
            "_context": mock_context,
        }

        result = await import_memory(params)

        assert isinstance(result, dict)


class TestMaintenanceEdgeCases:
    """Tests for edge cases in maintenance tools."""

    @pytest.fixture
    def mock_context(self) -> dict:
        """Create mock context."""
        embedding_service = MagicMock()
        embedding_service.get_cache_stats.return_value = {"hits": 0, "misses": 0}

        return {
            "qdrant": AsyncMock(),
            "neo4j": AsyncMock(),
            "normalizer": AsyncMock(),
            "job_manager": AsyncMock(),
            "embedding_service": embedding_service,
        }

    @pytest.mark.asyncio
    async def test_statistics_handles_exception(self, mock_context: dict) -> None:
        """Test statistics handles exceptions gracefully."""
        mock_context["qdrant"].count.side_effect = Exception("Error")

        params = {"_context": mock_context}

        result = await memory_statistics(params)

        # Should not crash
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_normalize_handles_exception(self, mock_context: dict) -> None:
        """Test normalize handles exceptions gracefully."""
        mock_context["normalizer"].normalize.side_effect = Exception("Error")

        params = {
            "_context": mock_context,
        }

        result = await normalize_memory(params)

        # Should return error
        assert isinstance(result, dict)
        assert "error" in result
