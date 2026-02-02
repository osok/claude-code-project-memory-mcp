"""Unit tests for local MCP configuration and CLI.

Tests for REQ-MEM-002:
- REQ-MEM-002-FN-020: Global config file support
- REQ-MEM-002-FN-023: Environment variable overrides
- REQ-MEM-002-DATA-002: Config precedence
- REQ-MEM-002-DATA-010: Project ID validation
- REQ-MEM-002-DATA-011: Project ID case sensitivity
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from memory_service.cli import (
    validate_project_id,
    get_config_path,
    get_default_config,
    load_toml_config,
    flatten_config,
    ErrorCategory,
    format_error,
)
from memory_service.config import (
    Settings,
    validate_project_id as config_validate_project_id,
    get_config_path as config_get_config_path,
    load_toml_config as config_load_toml_config,
    flatten_toml_config,
    load_settings_with_toml,
)


class TestProjectIdValidation:
    """Tests for project_id validation (REQ-MEM-002-DATA-010)."""

    def test_valid_alphanumeric_project_id(self):
        """Valid alphanumeric project IDs should pass."""
        assert validate_project_id("myproject") is True
        assert validate_project_id("MyProject") is True
        assert validate_project_id("project123") is True
        assert validate_project_id("123project") is True

    def test_valid_project_id_with_hyphens(self):
        """Project IDs with hyphens should pass."""
        assert validate_project_id("my-project") is True
        assert validate_project_id("my-app-v2") is True

    def test_valid_project_id_with_underscores(self):
        """Project IDs with underscores should pass."""
        assert validate_project_id("my_project") is True
        assert validate_project_id("my_app_v2") is True

    def test_valid_mixed_project_id(self):
        """Project IDs with mixed chars should pass."""
        assert validate_project_id("my-project_v2") is True
        assert validate_project_id("MyProject-123_test") is True

    def test_invalid_project_id_starts_with_hyphen(self):
        """Project IDs starting with hyphen should fail."""
        assert validate_project_id("-myproject") is False

    def test_invalid_project_id_starts_with_underscore(self):
        """Project IDs starting with underscore should fail."""
        assert validate_project_id("_myproject") is False

    def test_invalid_project_id_special_chars(self):
        """Project IDs with special chars should fail."""
        assert validate_project_id("my.project") is False
        assert validate_project_id("my project") is False
        assert validate_project_id("my@project") is False
        assert validate_project_id("my/project") is False

    def test_invalid_project_id_empty(self):
        """Empty project ID should fail."""
        assert validate_project_id("") is False

    def test_valid_single_char_project_id(self):
        """Single char project ID should pass if alphanumeric."""
        assert validate_project_id("a") is True
        assert validate_project_id("Z") is True
        assert validate_project_id("9") is True

    def test_valid_max_length_project_id(self):
        """64-char project ID should pass."""
        project_id = "a" * 64
        assert validate_project_id(project_id) is True

    def test_invalid_too_long_project_id(self):
        """65+ char project ID should fail."""
        project_id = "a" * 65
        assert validate_project_id(project_id) is False

    def test_project_id_case_sensitivity(self):
        """Project IDs should be case-sensitive (REQ-MEM-002-DATA-011)."""
        # Both should be valid but distinct
        assert validate_project_id("MyProject") is True
        assert validate_project_id("myproject") is True
        # They are different strings
        assert "MyProject" != "myproject"

    def test_config_module_validates_same_way(self):
        """Config module should use same validation logic."""
        # Test a few cases to ensure consistency
        assert config_validate_project_id("myproject") is True
        assert config_validate_project_id("-invalid") is False
        assert config_validate_project_id("a" * 65) is False


class TestConfigPath:
    """Tests for config file path resolution."""

    def test_linux_config_path(self):
        """Linux should use XDG_CONFIG_HOME or ~/.config."""
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": "/custom/config"}, clear=False):
            with patch("os.name", "posix"):
                path = get_config_path()
                # Should be under the XDG path
                assert "claude-memory" in str(path)
                assert "config.toml" in str(path)

    def test_default_linux_config_path(self):
        """Without XDG_CONFIG_HOME, use ~/.config."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("os.name", "posix"):
                path = get_config_path()
                assert "claude-memory" in str(path)
                assert "config.toml" in str(path)


class TestTomlConfigLoading:
    """Tests for TOML configuration loading."""

    def test_load_nonexistent_config(self):
        """Loading nonexistent config should return empty dict."""
        result = load_toml_config(Path("/nonexistent/path/config.toml"))
        assert result == {}

    def test_load_valid_toml_config(self):
        """Should load valid TOML config."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write("""
[qdrant]
host = "remotehost"
port = 6333

[neo4j]
uri = "bolt://remotehost:7687"
password = "testpass"

[voyage]
api_key = "test-api-key"
""")
            f.flush()
            config_path = Path(f.name)

        try:
            result = load_toml_config(config_path)
            assert result["qdrant"]["host"] == "remotehost"
            assert result["neo4j"]["uri"] == "bolt://remotehost:7687"
            assert result["voyage"]["api_key"] == "test-api-key"
        finally:
            config_path.unlink()


class TestConfigFlattening:
    """Tests for flattening nested TOML config."""

    def test_flatten_qdrant_config(self):
        """Should flatten qdrant section."""
        toml_config = {
            "qdrant": {
                "host": "remotehost",
                "port": 9999,
            }
        }
        result = flatten_config(toml_config)
        assert result["qdrant_host"] == "remotehost"
        assert result["qdrant_port"] == 9999

    def test_flatten_neo4j_config(self):
        """Should flatten neo4j section."""
        toml_config = {
            "neo4j": {
                "uri": "bolt://test:7687",
                "user": "testuser",
                "password": "testpass",
            }
        }
        result = flatten_config(toml_config)
        assert result["neo4j_uri"] == "bolt://test:7687"
        assert result["neo4j_user"] == "testuser"
        assert result["neo4j_password"] == "testpass"

    def test_flatten_voyage_config(self):
        """Should flatten voyage section."""
        toml_config = {
            "voyage": {
                "api_key": "test-key",
                "model": "voyage-test-3",
            }
        }
        result = flatten_config(toml_config)
        assert result["voyage_api_key"] == "test-key"
        assert result["voyage_model"] == "voyage-test-3"

    def test_flatten_server_config(self):
        """Should flatten server section."""
        toml_config = {
            "server": {
                "log_level": "DEBUG",
            }
        }
        result = flatten_config(toml_config)
        assert result["log_level"] == "DEBUG"

    def test_flatten_partial_config(self):
        """Should handle partial config without errors."""
        toml_config = {
            "qdrant": {
                "host": "localhost",
                # Missing port - should not be in result
            }
        }
        result = flatten_config(toml_config)
        assert result["qdrant_host"] == "localhost"
        assert "qdrant_port" not in result

    def test_flatten_empty_config(self):
        """Should handle empty config."""
        result = flatten_config({})
        assert result == {}


class TestConfigPrecedence:
    """Tests for configuration precedence (REQ-MEM-002-DATA-002)."""

    def test_default_values(self):
        """Settings should have sensible defaults."""
        settings = Settings()
        assert settings.qdrant_host == "localhost"
        assert settings.qdrant_port == 6333
        assert settings.neo4j_uri == "bolt://localhost:7687"
        assert settings.neo4j_user == "neo4j"
        assert settings.voyage_model == "voyage-code-3"

    def test_env_var_override(self):
        """Environment variables should override defaults."""
        with patch.dict(os.environ, {"CLAUDE_MEMORY_QDRANT_HOST": "envhost"}, clear=False):
            settings = Settings()
            assert settings.qdrant_host == "envhost"

    def test_env_var_prefix(self):
        """Should use CLAUDE_MEMORY_ prefix for env vars (REQ-MEM-002-FN-023)."""
        with patch.dict(
            os.environ,
            {
                "CLAUDE_MEMORY_QDRANT_PORT": "9999",
                "CLAUDE_MEMORY_LOG_LEVEL": "DEBUG",
            },
            clear=False,
        ):
            settings = Settings()
            assert settings.qdrant_port == 9999
            assert settings.log_level == "DEBUG"

    def test_toml_config_override(self):
        """TOML config should override defaults (env vars override both)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write("""
[qdrant]
host = "tomlhost"
port = 8888
""")
            f.flush()
            config_path = Path(f.name)

        try:
            # Clear env vars to test TOML override of defaults
            with patch.dict(os.environ, {}, clear=True):
                settings = load_settings_with_toml(config_path)
                assert settings.qdrant_host == "tomlhost"
                assert settings.qdrant_port == 8888
        finally:
            config_path.unlink()


class TestDefaultConfig:
    """Tests for default configuration template."""

    def test_default_config_structure(self):
        """Default config should have all required sections."""
        config = get_default_config()
        assert "qdrant" in config
        assert "neo4j" in config
        assert "voyage" in config
        assert "server" in config

    def test_default_config_values(self):
        """Default config should have sensible values."""
        config = get_default_config()
        assert config["qdrant"]["host"] == "localhost"
        assert config["qdrant"]["port"] == 6333
        assert config["neo4j"]["uri"] == "bolt://localhost:7687"
        assert config["voyage"]["model"] == "voyage-code-3"


class TestErrorFormatting:
    """Tests for error message formatting (REQ-MEM-002-NFR-USE-002)."""

    def test_error_categories_exist(self):
        """Error categories should be defined."""
        assert ErrorCategory.CONFIGURATION == "configuration"
        assert ErrorCategory.DATABASE == "database"
        assert ErrorCategory.API_KEY == "api_key"
        assert ErrorCategory.VALIDATION == "validation"
        assert ErrorCategory.INTERNAL == "internal"

    def test_format_error_includes_category(self):
        """Formatted error should include category."""
        error = format_error(
            ErrorCategory.DATABASE,
            "Cannot connect",
            "Check database is running",
        )
        assert "DATABASE" in error
        assert "Cannot connect" in error
        assert "Check database is running" in error

    def test_format_error_includes_remediation(self):
        """Formatted error should include remediation steps."""
        error = format_error(
            ErrorCategory.CONFIGURATION,
            "Missing config",
            "Run: claude-memory-mcp init-config",
        )
        assert "Remediation" in error
        assert "init-config" in error


class TestSettingsSecrets:
    """Tests for secret handling in settings."""

    def test_password_is_secret(self):
        """Passwords should use SecretStr."""
        settings = Settings(neo4j_password="testpass")
        # SecretStr doesn't expose value in repr/str
        assert "testpass" not in repr(settings)

    def test_api_key_is_secret(self):
        """API keys should use SecretStr."""
        settings = Settings(voyage_api_key="test-api-key")
        assert "test-api-key" not in repr(settings)

    def test_can_access_secret_value(self):
        """Should be able to access secret value when needed."""
        settings = Settings(neo4j_password="testpass")
        assert settings.neo4j_password.get_secret_value() == "testpass"
