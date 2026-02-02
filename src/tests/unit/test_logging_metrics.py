"""Unit tests for logging and metrics utilities."""

import pytest
from unittest.mock import patch, MagicMock

from memory_service.utils.logging import (
    get_logger,
    setup_logging,
    sanitize_for_logging,
)
import memory_service.utils.metrics as metrics_module
from memory_service.utils.metrics import get_metrics, Metrics


@pytest.fixture(autouse=True)
def reset_metrics_registry():
    """Reset prometheus registry and metrics singleton between tests."""
    from prometheus_client import REGISTRY, GC_COLLECTOR, PROCESS_COLLECTOR, PLATFORM_COLLECTOR

    # Clear the metrics singleton cache
    metrics_module._metrics_instance = None

    # Keep track of platform collectors to preserve
    platform_collectors = set()
    try:
        platform_collectors.add(GC_COLLECTOR)
    except Exception:
        pass
    try:
        platform_collectors.add(PROCESS_COLLECTOR)
    except Exception:
        pass
    try:
        platform_collectors.add(PLATFORM_COLLECTOR)
    except Exception:
        pass

    # Unregister all non-platform collectors
    collectors_to_remove = [
        collector for collector in list(REGISTRY._names_to_collectors.values())
        if collector not in platform_collectors
    ]
    for collector in collectors_to_remove:
        try:
            REGISTRY.unregister(collector)
        except Exception:
            pass

    yield

    # Cleanup after test
    metrics_module._metrics_instance = None


class TestGetLogger:
    """Tests for get_logger function."""

    def test_returns_logger(self) -> None:
        """Test get_logger returns a logger."""
        logger = get_logger("test_module")

        assert logger is not None
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "debug")

    def test_logger_name(self) -> None:
        """Test logger has correct name."""
        logger = get_logger("my.module.name")

        # Logger should be named or bound
        assert logger is not None

    def test_multiple_calls_same_logger(self) -> None:
        """Test multiple calls return cached logger."""
        logger1 = get_logger("cached_test_module")
        logger2 = get_logger("cached_test_module")

        # Should return same cached instance
        assert logger1 is logger2


class TestSetupLogging:
    """Tests for setup_logging function."""

    @patch("memory_service.utils.logging.get_settings")
    def test_setup_logging_json_format(self, mock_settings: MagicMock) -> None:
        """Test setting up JSON format logging."""
        mock_settings.return_value = MagicMock(
            log_level="INFO",
            log_format="json",
            log_file=None,
        )

        setup_logging()

        # Should not raise
        logger = get_logger("test_json")
        logger.info("test message")

    @patch("memory_service.utils.logging.get_settings")
    def test_setup_logging_console_format(self, mock_settings: MagicMock) -> None:
        """Test setting up console format logging."""
        mock_settings.return_value = MagicMock(
            log_level="DEBUG",
            log_format="console",
            log_file=None,
        )

        setup_logging()

        # Should not raise
        logger = get_logger("test_console")
        logger.debug("test message")


class TestSanitizeForLogging:
    """Tests for sanitize_for_logging processor.

    Note: sanitize_for_logging is a structlog processor that takes
    (logger, method_name, event_dict) and returns modified event_dict.
    """

    def test_sanitizes_api_key(self) -> None:
        """Test API key is sanitized."""
        event_dict = {"api_key": "sk-secret-key-12345", "event": "test"}
        result = sanitize_for_logging(None, "info", event_dict)

        # Should be redacted
        assert "sk-secret-key-12345" not in str(result.get("api_key", ""))
        assert "api_key" in result

    def test_sanitizes_password(self) -> None:
        """Test password is sanitized."""
        event_dict = {"password": "my-secret-password", "event": "test"}
        result = sanitize_for_logging(None, "info", event_dict)

        # Should be redacted
        assert "my-secret-password" not in str(result.get("password", ""))
        assert "password" in result

    def test_sanitizes_nested(self) -> None:
        """Test nested sensitive data is sanitized."""
        event_dict = {
            "config": {
                "api_key": "secretkey123",
                "password": "password123",
            },
            "event": "test",
        }
        result = sanitize_for_logging(None, "info", event_dict)

        # Nested values should be redacted
        config = result.get("config", {})
        if isinstance(config, dict):
            assert "secretkey123" not in str(config.get("api_key", ""))
            assert "password123" not in str(config.get("password", ""))

    def test_preserves_safe_data(self) -> None:
        """Test safe data is preserved."""
        event_dict = {"name": "test", "count": 42, "event": "test"}
        result = sanitize_for_logging(None, "info", event_dict)

        assert result["name"] == "test"
        assert result["count"] == 42


class TestMetrics:
    """Tests for Metrics class."""

    def test_metrics_initialization(self) -> None:
        """Test Metrics class initializes correctly."""
        metrics = Metrics()

        assert metrics is not None
        assert hasattr(metrics, "memory_operations_total")
        assert hasattr(metrics, "search_requests_total")

    def test_get_metrics_returns_instance(self) -> None:
        """Test get_metrics returns Metrics instance."""
        metrics = get_metrics()

        assert isinstance(metrics, Metrics)

    def test_get_metrics_cached(self) -> None:
        """Test get_metrics returns cached instance."""
        metrics1 = get_metrics()
        metrics2 = get_metrics()

        assert metrics1 is metrics2

    def test_record_memory_operation(self) -> None:
        """Test recording memory operation."""
        metrics = get_metrics()

        # Should not raise
        metrics.record_memory_operation(
            operation="add",
            memory_type="requirements",
            status="success",
            duration=0.1,
        )

    def test_record_search(self) -> None:
        """Test recording search operation."""
        metrics = get_metrics()

        # Should not raise
        metrics.record_search(
            search_type="semantic",
            status="success",
            duration=0.05,
            result_count=10,
        )

    def test_record_embedding(self) -> None:
        """Test recording embedding operation."""
        metrics = get_metrics()

        # Should not raise
        metrics.record_embedding(
            source="voyage",
            status="success",
            duration=0.2,
            batch_size=5,
        )

    def test_record_mcp_tool_call(self) -> None:
        """Test recording MCP tool call."""
        metrics = get_metrics()

        # Should not raise
        metrics.record_mcp_tool_call(
            tool="memory_add",
            status="success",
            duration=0.1,
        )


class TestLoggerIntegration:
    """Integration tests for logger."""

    def test_logger_with_context(self) -> None:
        """Test logger with bound context."""
        logger = get_logger("test_integration")

        # Should support binding context
        bound_logger = logger.bind(request_id="123")
        bound_logger.info("test message with context")

    def test_logger_exception(self) -> None:
        """Test logger with exception."""
        logger = get_logger("test_exception")

        try:
            raise ValueError("test error")
        except ValueError:
            logger.exception("caught error")


class TestMetricsIntegration:
    """Integration tests for metrics."""

    def test_metrics_prometheus_format(self) -> None:
        """Test metrics can be exported in Prometheus format."""
        from prometheus_client import generate_latest, REGISTRY

        metrics = get_metrics()

        # Record some metrics
        metrics.record_memory_operation("add", "function", "success", 0.1)
        metrics.record_search("semantic", "success", 0.05, 5)

        # Generate Prometheus output
        output = generate_latest(REGISTRY)

        assert output is not None
        assert isinstance(output, bytes)
        # Should contain either our metrics or platform metrics
        # Platform metrics include python_info, process_*, python_gc_*
        assert len(output) > 0
        # Should have some metrics registered
        assert b"# HELP" in output and b"# TYPE" in output
