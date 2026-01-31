"""Structured logging configuration using structlog."""

import logging
import sys
from functools import lru_cache
from typing import Any

import structlog
from structlog.types import Processor

from memory_service.config import get_settings


def add_request_id(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Add request ID to log events if available in context."""
    import contextvars

    request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
        "request_id", default=None
    )
    request_id = request_id_var.get()
    if request_id:
        event_dict["request_id"] = request_id
    return event_dict


def sanitize_for_logging(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Redact sensitive information from log events.

    Redacts:
    - API keys
    - Passwords
    - Tokens
    - Authorization headers
    """
    sensitive_keys = {
        "api_key",
        "apikey",
        "password",
        "passwd",
        "token",
        "secret",
        "authorization",
        "auth",
        "credential",
        "private_key",
        "voyage_api_key",
        "neo4j_password",
        "qdrant_api_key",
    }

    def redact_value(key: str, value: Any) -> Any:
        key_lower = key.lower()
        for sensitive in sensitive_keys:
            if sensitive in key_lower:
                if isinstance(value, str):
                    if len(value) > 8:
                        return f"{value[:4]}...{value[-4:]}"
                    return "***REDACTED***"
                return "***REDACTED***"
        if isinstance(value, dict):
            return {k: redact_value(k, v) for k, v in value.items()}
        return value

    return {k: redact_value(k, v) for k, v in event_dict.items()}


def setup_logging() -> None:
    """Configure structured logging based on settings."""
    settings = get_settings()

    # Shared processors for all outputs
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        add_request_id,
        sanitize_for_logging,
    ]

    if settings.log_format == "json":
        # JSON format for production
        renderer: Processor = structlog.processors.JSONRenderer()
    else:
        # Console format for development
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=renderer,
            foreign_pre_chain=shared_processors,
        )
    )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, settings.log_level))

    # Configure file handler if specified
    if settings.log_file:
        file_handler = logging.FileHandler(settings.log_file)
        file_handler.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                processor=structlog.processors.JSONRenderer(),
                foreign_pre_chain=shared_processors,
            )
        )
        root_logger.addHandler(file_handler)

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("neo4j").setLevel(logging.WARNING)


@lru_cache(maxsize=128)
def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a cached structured logger by name.

    Args:
        name: Logger name, typically __name__

    Returns:
        Bound structured logger
    """
    return structlog.get_logger(name)
