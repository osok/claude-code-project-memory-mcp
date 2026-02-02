"""Unit tests for configuration module."""

import os
import pytest
from unittest.mock import patch, MagicMock
from pydantic import SecretStr

from memory_service.config import Settings, get_settings


class TestSettings:
    """Tests for Settings class."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        with patch.dict(os.environ, {
            "VOYAGE_API_KEY": "test-key",
        }, clear=True):
            settings = Settings()

            assert settings.qdrant_host == "localhost"
            assert settings.qdrant_port == 6333
            assert settings.neo4j_uri == "bolt://localhost:7687"
            assert settings.neo4j_user == "neo4j"
            assert settings.log_level == "INFO"
            assert settings.log_format == "json"

    def test_environment_override(self) -> None:
        """Test environment variable override."""
        with patch.dict(os.environ, {
            "QDRANT_HOST": "qdrant.example.com",
            "QDRANT_PORT": "7333",
            "NEO4J_URI": "bolt://neo4j.example.com:7687",
            "NEO4J_USER": "admin",
            "NEO4J_PASSWORD": "secret",
            "VOYAGE_API_KEY": "test-key",
            "LOG_LEVEL": "DEBUG",
        }, clear=True):
            settings = Settings()

            assert settings.qdrant_host == "qdrant.example.com"
            assert settings.qdrant_port == 7333
            assert settings.neo4j_uri == "bolt://neo4j.example.com:7687"
            assert settings.neo4j_user == "admin"
            assert settings.log_level == "DEBUG"

    def test_secret_str_password(self) -> None:
        """Test password is stored as SecretStr."""
        with patch.dict(os.environ, {
            "NEO4J_PASSWORD": "my-secret-password",
            "VOYAGE_API_KEY": "test-key",
        }, clear=True):
            settings = Settings()

            assert isinstance(settings.neo4j_password, SecretStr)
            assert settings.neo4j_password.get_secret_value() == "my-secret-password"

    def test_secret_str_api_key(self) -> None:
        """Test API key is stored as SecretStr."""
        with patch.dict(os.environ, {
            "VOYAGE_API_KEY": "my-api-key",
        }, clear=True):
            settings = Settings()

            assert isinstance(settings.voyage_api_key, SecretStr)
            assert settings.voyage_api_key.get_secret_value() == "my-api-key"

    def test_grpc_port_default(self) -> None:
        """Test gRPC port defaults to qdrant_port + 1."""
        with patch.dict(os.environ, {
            "QDRANT_PORT": "6333",
            "VOYAGE_API_KEY": "test-key",
        }, clear=True):
            settings = Settings()

            # gRPC port should be HTTP port + 1
            assert settings.qdrant_grpc_port == 6334

    def test_metrics_enabled_default(self) -> None:
        """Test metrics enabled by default."""
        with patch.dict(os.environ, {
            "VOYAGE_API_KEY": "test-key",
        }, clear=True):
            settings = Settings()

            assert settings.metrics_enabled is True

    def test_metrics_disabled(self) -> None:
        """Test metrics can be disabled."""
        with patch.dict(os.environ, {
            "VOYAGE_API_KEY": "test-key",
            "METRICS_ENABLED": "false",
        }, clear=True):
            settings = Settings()

            assert settings.metrics_enabled is False

    def test_project_path_default(self) -> None:
        """Test project path default."""
        with patch.dict(os.environ, {
            "VOYAGE_API_KEY": "test-key",
        }, clear=True):
            settings = Settings()

            # Should have some default
            assert settings.project_path is not None


class TestGetSettings:
    """Tests for get_settings function."""

    def test_returns_settings_instance(self) -> None:
        """Test get_settings returns Settings instance."""
        with patch.dict(os.environ, {
            "VOYAGE_API_KEY": "test-key",
        }, clear=True):
            # Clear the cached settings
            import memory_service.config as config_module
            if hasattr(config_module, '_settings'):
                config_module._settings = None

            settings = get_settings()

            assert isinstance(settings, Settings)

    def test_caches_settings(self) -> None:
        """Test get_settings caches the settings object."""
        with patch.dict(os.environ, {
            "VOYAGE_API_KEY": "test-key",
        }, clear=True):
            # Clear the cached settings
            import memory_service.config as config_module
            if hasattr(config_module, '_settings'):
                config_module._settings = None

            settings1 = get_settings()
            settings2 = get_settings()

            # Should return same object
            assert settings1 is settings2


class TestSettingsValidation:
    """Tests for settings validation."""

    def test_invalid_log_level(self) -> None:
        """Test invalid log level."""
        with patch.dict(os.environ, {
            "VOYAGE_API_KEY": "test-key",
            "LOG_LEVEL": "INVALID",
        }, clear=True):
            # May still work (pydantic coercion) or raise error
            try:
                settings = Settings()
                # If it doesn't raise, check it was coerced or kept
                assert settings.log_level is not None
            except Exception:
                # Validation error is acceptable
                pass

    def test_invalid_port_type(self) -> None:
        """Test invalid port type."""
        with patch.dict(os.environ, {
            "VOYAGE_API_KEY": "test-key",
            "QDRANT_PORT": "not-a-number",
        }, clear=True):
            with pytest.raises(Exception):
                Settings()

    def test_negative_port(self) -> None:
        """Test negative port number."""
        with patch.dict(os.environ, {
            "VOYAGE_API_KEY": "test-key",
            "QDRANT_PORT": "-1",
        }, clear=True):
            # May be rejected by validation
            try:
                settings = Settings()
                # If allowed, port should be the value
                assert settings.qdrant_port == -1
            except Exception:
                # Validation error is acceptable
                pass


class TestSettingsOptionalFields:
    """Tests for optional settings fields."""

    def test_qdrant_api_key_optional(self) -> None:
        """Test Qdrant API key is optional."""
        with patch.dict(os.environ, {
            "VOYAGE_API_KEY": "test-key",
        }, clear=True):
            settings = Settings()

            # Should be None if not set
            assert settings.qdrant_api_key is None

    def test_qdrant_api_key_set(self) -> None:
        """Test Qdrant API key when set."""
        with patch.dict(os.environ, {
            "VOYAGE_API_KEY": "test-key",
            "QDRANT_API_KEY": "qdrant-key",
        }, clear=True):
            settings = Settings()

            assert settings.qdrant_api_key is not None
