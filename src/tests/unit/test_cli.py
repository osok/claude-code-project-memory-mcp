"""Unit tests for CLI commands."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from click.testing import CliRunner

from memory_service.api.cli import cli, main


class TestCliGroup:
    """Tests for main CLI group."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    def test_cli_help(self, runner: CliRunner) -> None:
        """Test CLI shows help."""
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "Memory Service CLI" in result.output

    def test_cli_verbose_flag(self, runner: CliRunner) -> None:
        """Test verbose flag is accepted."""
        result = runner.invoke(cli, ["-v", "--help"])

        assert result.exit_code == 0


class TestHealthCommand:
    """Tests for health command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    @patch("memory_service.api.cli.get_settings")
    @patch("memory_service.api.cli.setup_logging")
    def test_health_all_healthy(
        self,
        mock_setup: MagicMock,
        mock_settings: MagicMock,
        runner: CliRunner,
    ) -> None:
        """Test health command when all services are healthy."""
        with patch("memory_service.storage.qdrant_adapter.QdrantAdapter") as mock_qdrant_cls, \
             patch("memory_service.storage.neo4j_adapter.Neo4jAdapter") as mock_neo4j_cls:

            # Setup mock instances
            mock_qdrant = AsyncMock()
            mock_qdrant.health_check.return_value = True
            mock_qdrant.close = AsyncMock()
            mock_qdrant_cls.return_value = mock_qdrant

            mock_neo4j = AsyncMock()
            mock_neo4j.health_check.return_value = True
            mock_neo4j.close = AsyncMock()
            mock_neo4j_cls.return_value = mock_neo4j

            mock_settings.return_value = MagicMock(
                qdrant_host="localhost",
                qdrant_port=6333,
                qdrant_api_key=None,
                neo4j_uri="bolt://localhost:7687",
                neo4j_user="neo4j",
                neo4j_password="password",
            )

            result = runner.invoke(cli, ["health"])

            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["qdrant"]["status"] == "healthy"
            assert data["neo4j"]["status"] == "healthy"

    @patch("memory_service.api.cli.get_settings")
    @patch("memory_service.api.cli.setup_logging")
    def test_health_qdrant_unhealthy(
        self,
        mock_setup: MagicMock,
        mock_settings: MagicMock,
        runner: CliRunner,
    ) -> None:
        """Test health command when Qdrant is unhealthy."""
        with patch("memory_service.storage.qdrant_adapter.QdrantAdapter") as mock_qdrant_cls, \
             patch("memory_service.storage.neo4j_adapter.Neo4jAdapter") as mock_neo4j_cls:

            mock_qdrant = AsyncMock()
            mock_qdrant.health_check.return_value = False
            mock_qdrant.close = AsyncMock()
            mock_qdrant_cls.return_value = mock_qdrant

            mock_neo4j = AsyncMock()
            mock_neo4j.health_check.return_value = True
            mock_neo4j.close = AsyncMock()
            mock_neo4j_cls.return_value = mock_neo4j

            mock_settings.return_value = MagicMock(
                qdrant_host="localhost",
                qdrant_port=6333,
                qdrant_api_key=None,
                neo4j_uri="bolt://localhost:7687",
                neo4j_user="neo4j",
                neo4j_password="password",
            )

            result = runner.invoke(cli, ["health"])

            assert result.exit_code == 1
            data = json.loads(result.output)
            assert data["qdrant"]["status"] == "unhealthy"

    @patch("memory_service.api.cli.get_settings")
    @patch("memory_service.api.cli.setup_logging")
    def test_health_qdrant_error(
        self,
        mock_setup: MagicMock,
        mock_settings: MagicMock,
        runner: CliRunner,
    ) -> None:
        """Test health command when Qdrant raises error."""
        with patch("memory_service.storage.qdrant_adapter.QdrantAdapter") as mock_qdrant_cls, \
             patch("memory_service.storage.neo4j_adapter.Neo4jAdapter") as mock_neo4j_cls:

            mock_qdrant_cls.side_effect = Exception("Connection failed")

            mock_neo4j = AsyncMock()
            mock_neo4j.health_check.return_value = True
            mock_neo4j.close = AsyncMock()
            mock_neo4j_cls.return_value = mock_neo4j

            mock_settings.return_value = MagicMock(
                qdrant_host="localhost",
                qdrant_port=6333,
                qdrant_api_key=None,
                neo4j_uri="bolt://localhost:7687",
                neo4j_user="neo4j",
                neo4j_password="password",
            )

            result = runner.invoke(cli, ["health"])

            assert result.exit_code == 1
            data = json.loads(result.output)
            assert data["qdrant"]["status"] == "error"


class TestStatsCommand:
    """Tests for stats command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    @patch("memory_service.api.cli.get_settings")
    @patch("memory_service.api.cli.setup_logging")
    def test_stats_success(
        self,
        mock_setup: MagicMock,
        mock_settings: MagicMock,
        runner: CliRunner,
    ) -> None:
        """Test stats command shows memory counts."""
        with patch("memory_service.storage.qdrant_adapter.QdrantAdapter") as mock_qdrant_cls:
            mock_qdrant = AsyncMock()
            mock_qdrant.get_collection_name.return_value = "requirements"
            mock_qdrant.count.return_value = 10
            mock_qdrant.close = AsyncMock()
            mock_qdrant_cls.return_value = mock_qdrant

            mock_settings.return_value = MagicMock(
                qdrant_host="localhost",
                qdrant_port=6333,
                qdrant_api_key=None,
            )

            result = runner.invoke(cli, ["stats"])

            assert result.exit_code == 0
            data = json.loads(result.output)
            assert "memory_counts" in data
            assert "total" in data


class TestIndexCommand:
    """Tests for index command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    @patch("memory_service.api.cli.setup_logging")
    def test_index_dry_run(
        self,
        mock_setup: MagicMock,
        runner: CliRunner,
        tmp_path,
    ) -> None:
        """Test index command in dry run mode."""
        # Create a test directory with a file
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass")

        result = runner.invoke(cli, ["index", str(tmp_path), "--dry-run"])

        assert result.exit_code == 0
        # Output may contain log lines before JSON, find the JSON object
        output_lines = result.output.strip().split("\n")
        # Find line starting with { that's followed by mode or contains "mode"
        json_output = None
        for i, line in enumerate(output_lines):
            if line.strip() == "{":
                # Multi-line JSON - join remaining lines
                json_output = "\n".join(output_lines[i:])
                break
            elif '"mode":' in line:
                json_output = line
                break
        assert json_output is not None, f"No JSON found in output: {result.output}"
        data = json.loads(json_output)
        assert data["mode"] == "dry_run"
        assert "file_count" in data


class TestNormalizeCommand:
    """Tests for normalize command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    @patch("memory_service.api.cli.get_settings")
    @patch("memory_service.api.cli.setup_logging")
    def test_normalize_success(
        self,
        mock_setup: MagicMock,
        mock_settings: MagicMock,
        runner: CliRunner,
    ) -> None:
        """Test normalize command succeeds."""
        with patch("memory_service.storage.qdrant_adapter.QdrantAdapter") as mock_qdrant_cls, \
             patch("memory_service.storage.neo4j_adapter.Neo4jAdapter") as mock_neo4j_cls, \
             patch("memory_service.core.workers.NormalizerWorker") as mock_normalizer_cls, \
             patch("memory_service.core.workers.JobManager"):

            mock_qdrant = AsyncMock()
            mock_qdrant.close = AsyncMock()
            mock_qdrant_cls.return_value = mock_qdrant

            mock_neo4j = AsyncMock()
            mock_neo4j.close = AsyncMock()
            mock_neo4j_cls.return_value = mock_neo4j

            mock_normalizer = AsyncMock()
            mock_normalizer.normalize.return_value = {
                "status": "success",
                "duplicates_merged": 0,
            }
            mock_normalizer_cls.return_value = mock_normalizer

            mock_settings.return_value = MagicMock(
                qdrant_host="localhost",
                qdrant_port=6333,
                qdrant_api_key=None,
                neo4j_uri="bolt://localhost:7687",
                neo4j_user="neo4j",
                neo4j_password="password",
            )

            result = runner.invoke(cli, ["normalize", "--dry-run"])

            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["status"] == "success"


class TestBackupCommand:
    """Tests for backup command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    @patch("memory_service.api.cli.get_settings")
    @patch("memory_service.api.cli.setup_logging")
    def test_backup_success(
        self,
        mock_setup: MagicMock,
        mock_settings: MagicMock,
        runner: CliRunner,
        tmp_path,
    ) -> None:
        """Test backup command creates file."""
        output_file = tmp_path / "backup.jsonl"

        with patch("memory_service.storage.qdrant_adapter.QdrantAdapter") as mock_qdrant_cls:
            mock_qdrant = AsyncMock()
            mock_qdrant.get_collection_name.return_value = "requirements"
            mock_qdrant.scroll.return_value = ([], None)  # Empty result
            mock_qdrant.close = AsyncMock()
            mock_qdrant_cls.return_value = mock_qdrant

            mock_settings.return_value = MagicMock(
                qdrant_host="localhost",
                qdrant_port=6333,
                qdrant_api_key=None,
            )

            result = runner.invoke(cli, ["backup", str(output_file)])

            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["status"] == "completed"
            assert data["exported_count"] == 0


class TestRestoreCommand:
    """Tests for restore command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    @patch("memory_service.api.cli.get_settings")
    @patch("memory_service.api.cli.setup_logging")
    def test_restore_empty_file(
        self,
        mock_setup: MagicMock,
        mock_settings: MagicMock,
        runner: CliRunner,
        tmp_path,
    ) -> None:
        """Test restore command with empty file."""
        input_file = tmp_path / "backup.jsonl"
        input_file.write_text("")

        with patch("memory_service.storage.qdrant_adapter.QdrantAdapter") as mock_qdrant_cls:
            mock_qdrant = AsyncMock()
            mock_qdrant.close = AsyncMock()
            mock_qdrant_cls.return_value = mock_qdrant

            mock_settings.return_value = MagicMock(
                qdrant_host="localhost",
                qdrant_port=6333,
                qdrant_api_key=None,
            )

            result = runner.invoke(cli, ["restore", str(input_file)])

            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["status"] == "completed"
            assert data["imported_count"] == 0


class TestInitSchemaCommand:
    """Tests for init-schema command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    @patch("memory_service.api.cli.get_settings")
    @patch("memory_service.api.cli.setup_logging")
    def test_init_schema_success(
        self,
        mock_setup: MagicMock,
        mock_settings: MagicMock,
        runner: CliRunner,
    ) -> None:
        """Test init-schema command initializes databases."""
        with patch("memory_service.storage.qdrant_adapter.QdrantAdapter") as mock_qdrant_cls, \
             patch("memory_service.storage.neo4j_adapter.Neo4jAdapter") as mock_neo4j_cls:

            mock_qdrant = AsyncMock()
            mock_qdrant.initialize_collections = AsyncMock()
            mock_qdrant.close = AsyncMock()
            mock_qdrant_cls.return_value = mock_qdrant

            mock_neo4j = AsyncMock()
            mock_neo4j.initialize_schema = AsyncMock()
            mock_neo4j.close = AsyncMock()
            mock_neo4j_cls.return_value = mock_neo4j

            mock_settings.return_value = MagicMock(
                qdrant_host="localhost",
                qdrant_port=6333,
                qdrant_api_key=None,
                neo4j_uri="bolt://localhost:7687",
                neo4j_user="neo4j",
                neo4j_password="password",
            )

            result = runner.invoke(cli, ["init-schema"])

            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["qdrant"] == "initialized"
            assert data["neo4j"] == "initialized"

    @patch("memory_service.api.cli.get_settings")
    @patch("memory_service.api.cli.setup_logging")
    def test_init_schema_qdrant_error(
        self,
        mock_setup: MagicMock,
        mock_settings: MagicMock,
        runner: CliRunner,
    ) -> None:
        """Test init-schema command handles Qdrant error."""
        with patch("memory_service.storage.qdrant_adapter.QdrantAdapter") as mock_qdrant_cls, \
             patch("memory_service.storage.neo4j_adapter.Neo4jAdapter") as mock_neo4j_cls:

            mock_qdrant_cls.side_effect = Exception("Connection failed")

            mock_neo4j = AsyncMock()
            mock_neo4j.initialize_schema = AsyncMock()
            mock_neo4j.close = AsyncMock()
            mock_neo4j_cls.return_value = mock_neo4j

            mock_settings.return_value = MagicMock(
                qdrant_host="localhost",
                qdrant_port=6333,
                qdrant_api_key=None,
                neo4j_uri="bolt://localhost:7687",
                neo4j_user="neo4j",
                neo4j_password="password",
            )

            result = runner.invoke(cli, ["init-schema"])

            assert result.exit_code == 0  # CLI still runs
            data = json.loads(result.output)
            assert "error" in data["qdrant"]


class TestMainEntryPoint:
    """Tests for main entry point."""

    def test_main_exists(self) -> None:
        """Test main function exists."""
        assert callable(main)
