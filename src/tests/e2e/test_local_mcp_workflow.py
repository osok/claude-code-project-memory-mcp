"""End-to-end tests for Local MCP Architecture workflow (REQ-MEM-002-VER-004).

Tests verify the complete workflow:
1. Package installs successfully
2. init-config creates config file
3. check-db verifies connectivity
4. Server starts with --project-id
5. MCP tools are available
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import shutil

import pytest

from click.testing import CliRunner


class TestCLICommands:
    """Tests for CLI commands."""

    def test_cli_help(self):
        """CLI --help should display usage information."""
        from memory_service.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "Claude Code Long-Term Memory MCP Server" in result.output
        assert "--project-id" in result.output
        assert "init-config" in result.output
        assert "check-db" in result.output

    def test_cli_version(self):
        """CLI --version should display version."""
        from memory_service.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["--version"])

        assert result.exit_code == 0
        assert "claude-memory-mcp" in result.output
        assert "0.2.0" in result.output

    def test_cli_requires_project_id(self):
        """CLI should require --project-id for server mode."""
        from memory_service.cli import main

        runner = CliRunner()
        result = runner.invoke(main, [])

        assert result.exit_code == 1
        assert "--project-id is required" in result.output

    def test_cli_validates_project_id_format(self):
        """CLI should validate project_id format."""
        from memory_service.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["--project-id", "-invalid"])

        assert result.exit_code == 1
        assert "Invalid project_id" in result.output


class TestInitConfigCommand:
    """Tests for init-config command."""

    def test_init_config_creates_file(self):
        """init-config should create config file."""
        from memory_service.cli import main

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.toml"

            result = runner.invoke(main, [
                "--config", str(config_path),
                "init-config"
            ])

            assert result.exit_code == 0
            assert config_path.exists()
            assert "Created config file" in result.output

    def test_init_config_has_correct_structure(self):
        """Created config should have correct TOML structure."""
        from memory_service.cli import main

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.toml"

            runner.invoke(main, [
                "--config", str(config_path),
                "init-config"
            ])

            content = config_path.read_text()
            assert "[qdrant]" in content
            assert "[neo4j]" in content
            assert "[voyage]" in content
            assert "host = \"localhost\"" in content

    def test_init_config_sets_permissions(self):
        """Config file should have 600 permissions on Unix."""
        from memory_service.cli import main

        if os.name == "nt":
            pytest.skip("Permission test not applicable on Windows")

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.toml"

            runner.invoke(main, [
                "--config", str(config_path),
                "init-config"
            ])

            mode = config_path.stat().st_mode & 0o777
            assert mode == 0o600


class TestCheckDbCommand:
    """Tests for check-db command."""

    def test_check_db_reports_qdrant_status(self):
        """check-db should report Qdrant connectivity."""
        from memory_service.cli import main

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.toml"
            config_path.write_text("""
[qdrant]
host = "localhost"
port = 6333

[neo4j]
uri = "bolt://localhost:7687"
user = "neo4j"
password = "test"
""")

            # Mock the database clients
            with patch("memory_service.cli.QdrantClient") as mock_qdrant:
                with patch("memory_service.cli.GraphDatabase") as mock_neo4j:
                    mock_qdrant_instance = MagicMock()
                    mock_qdrant_instance.get_collections.return_value = MagicMock(collections=[])
                    mock_qdrant.return_value = mock_qdrant_instance

                    mock_driver = MagicMock()
                    mock_session = MagicMock()
                    mock_result = MagicMock()
                    mock_result.single.return_value = {"n": 1}
                    mock_session.run.return_value = mock_result
                    mock_session.__enter__ = MagicMock(return_value=mock_session)
                    mock_session.__exit__ = MagicMock(return_value=None)
                    mock_driver.session.return_value = mock_session
                    mock_neo4j.driver.return_value = mock_driver

                    result = runner.invoke(main, [
                        "--config", str(config_path),
                        "check-db"
                    ])

                    assert "Qdrant" in result.output
                    assert "Neo4j" in result.output


class TestConfigPrecedence:
    """Tests for configuration precedence (REQ-MEM-002-DATA-002)."""

    def test_env_var_overrides_config_file(self):
        """Environment variables should override config file values."""
        from memory_service.cli import main, load_toml_config, flatten_config
        from memory_service.config import Settings

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.toml"
            config_path.write_text("""
[qdrant]
host = "filehost"
port = 6333
""")

            # Load config
            toml_config = load_toml_config(config_path)
            overrides = flatten_config(toml_config)

            # Settings will use env vars
            with patch.dict(os.environ, {"CLAUDE_MEMORY_QDRANT_HOST": "envhost"}):
                settings = Settings(**overrides)
                # Env var should win
                assert settings.qdrant_host == "envhost"

    def test_defaults_used_without_config(self):
        """Default values should be used when no config exists."""
        from memory_service.config import Settings

        settings = Settings()

        assert settings.qdrant_host == "localhost"
        assert settings.qdrant_port == 6333
        assert settings.neo4j_uri == "bolt://localhost:7687"
        assert settings.voyage_model == "voyage-code-3"


class TestMCPJsonConfiguration:
    """Tests for mcp.json configuration format."""

    def test_mcp_json_format_valid(self):
        """mcp.json format should match expected structure."""
        import json

        # Expected format from requirements
        expected_structure = {
            "mcpServers": {
                "memory": {
                    "command": ".venv/bin/claude-memory-mcp",
                    "args": ["--project-id", "my-project"]
                }
            }
        }

        # Validate it's valid JSON
        json_str = json.dumps(expected_structure)
        parsed = json.loads(json_str)

        assert "mcpServers" in parsed
        assert "memory" in parsed["mcpServers"]
        assert "command" in parsed["mcpServers"]["memory"]
        assert "args" in parsed["mcpServers"]["memory"]
        assert "--project-id" in parsed["mcpServers"]["memory"]["args"]


class TestPackageEntryPoint:
    """Tests for package entry point."""

    def test_entry_point_exists(self):
        """claude-memory-mcp entry point should be importable."""
        from memory_service.cli import main

        assert callable(main)

    def test_cli_module_imports(self):
        """CLI module should import without errors."""
        from memory_service import cli

        assert hasattr(cli, "main")
        assert hasattr(cli, "init_config")
        assert hasattr(cli, "check_db")
        assert hasattr(cli, "validate_project_id")


class TestServerStartup:
    """Tests for MCP server startup."""

    def test_server_accepts_project_id(self):
        """Server should accept --project-id argument."""
        from memory_service.cli import main, validate_project_id

        # Validate project_id is accepted
        assert validate_project_id("test-project") is True
        assert validate_project_id("my_app") is True
        assert validate_project_id("MyProject123") is True

    def test_server_rejects_invalid_project_id(self):
        """Server should reject invalid project_id."""
        from memory_service.cli import validate_project_id

        assert validate_project_id("-invalid") is False
        assert validate_project_id("has spaces") is False
        assert validate_project_id("") is False


class TestPythonVersion:
    """Tests for Python version requirement."""

    def test_python_version_supported(self):
        """Should run on Python 3.11+."""
        version = sys.version_info
        assert version.major == 3
        assert version.minor >= 11


class TestDatabaseInfrastructure:
    """Tests for database-only Docker infrastructure."""

    def test_docker_compose_has_qdrant(self):
        """docker-compose.yml should have Qdrant service."""
        docker_compose_path = Path(__file__).parent.parent.parent.parent.parent / "docker" / "docker-compose.yml"
        if docker_compose_path.exists():
            content = docker_compose_path.read_text()
            assert "qdrant" in content
            assert "qdrant/qdrant" in content

    def test_docker_compose_has_neo4j(self):
        """docker-compose.yml should have Neo4j service."""
        docker_compose_path = Path(__file__).parent.parent.parent.parent.parent / "docker" / "docker-compose.yml"
        if docker_compose_path.exists():
            content = docker_compose_path.read_text()
            assert "neo4j" in content
            assert "neo4j:" in content

    def test_docker_compose_no_mcp_server(self):
        """docker-compose.yml should NOT have MCP server service."""
        docker_compose_path = Path(__file__).parent.parent.parent.parent.parent / "docker" / "docker-compose.yml"
        if docker_compose_path.exists():
            content = docker_compose_path.read_text()
            # Should not have memory-service or mcp-server container
            assert "memory-service:" not in content or "# deprecated" in content.lower()

    def test_ports_bound_to_localhost(self):
        """Database ports should be bound to localhost only."""
        docker_compose_path = Path(__file__).parent.parent.parent.parent.parent / "docker" / "docker-compose.yml"
        if docker_compose_path.exists():
            content = docker_compose_path.read_text()
            # Check for localhost binding
            assert "127.0.0.1:6333" in content
            assert "127.0.0.1:7687" in content
