"""Base service class and common decorators."""

import functools
import logging
import time
from abc import ABC
from typing import Callable, TypeVar, ParamSpec

P = ParamSpec("P")
R = TypeVar("R")

logger = logging.getLogger(__name__)


class ServiceError(Exception):
    """Base exception for service layer errors."""

    def __init__(self, message: str, code: str = "SERVICE_ERROR") -> None:
        """
        Initialize the service error.

        Args:
            message: Human-readable error message.
            code: Error code for programmatic handling.
        """
        self.message = message
        self.code = code
        super().__init__(message)


class NotFoundError(ServiceError):
    """Raised when a requested entity is not found."""

    def __init__(self, entity_type: str, entity_id: str) -> None:
        """
        Initialize not found error.

        Args:
            entity_type: Type of entity that was not found.
            entity_id: ID of the entity that was not found.
        """
        super().__init__(
            message=f"{entity_type} with ID {entity_id} not found",
            code="NOT_FOUND",
        )


class ValidationError(ServiceError):
    """Raised when validation fails."""

    def __init__(self, field: str, message: str) -> None:
        """
        Initialize validation error.

        Args:
            field: Field that failed validation.
            message: Description of the validation failure.
        """
        self.field = field
        super().__init__(
            message=f"Validation failed for {field}: {message}",
            code="VALIDATION_ERROR",
        )


class AuthorizationError(ServiceError):
    """Raised when user lacks permission for an operation."""

    def __init__(self, action: str, resource: str) -> None:
        """
        Initialize authorization error.

        Args:
            action: The action that was attempted.
            resource: The resource being accessed.
        """
        super().__init__(
            message=f"Not authorized to {action} {resource}",
            code="AUTHORIZATION_ERROR",
        )


def log_call(func: Callable[P, R]) -> Callable[P, R]:
    """
    Decorator to log method calls.

    Logs the method name and arguments at DEBUG level,
    and any exceptions at ERROR level.
    """

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        logger.debug(
            "Calling %s with args=%s kwargs=%s",
            func.__name__,
            args[1:],  # Skip self
            kwargs,
        )
        try:
            result = func(*args, **kwargs)
            logger.debug("Completed %s", func.__name__)
            return result
        except Exception as e:
            logger.error("Error in %s: %s", func.__name__, str(e))
            raise

    return wrapper


def measure_time(func: Callable[P, R]) -> Callable[P, R]:
    """
    Decorator to measure and log execution time.

    Records the time taken for method execution and logs
    it at DEBUG level.
    """

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed = time.perf_counter() - start
            logger.debug("%s took %.3f seconds", func.__name__, elapsed)

    return wrapper


def validate_not_none(*param_names: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator factory to validate that specified parameters are not None.

    Args:
        *param_names: Names of parameters that must not be None.

    Returns:
        Decorator function.
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Check kwargs
            for name in param_names:
                if name in kwargs and kwargs[name] is None:
                    raise ValidationError(name, "must not be None")
            return func(*args, **kwargs)

        return wrapper

    return decorator


class BaseService(ABC):
    """
    Abstract base class for all services.

    Provides common functionality like logging and error handling.
    All service classes should inherit from this base.

    Attributes:
        logger: Logger instance for the service.
    """

    def __init__(self) -> None:
        """Initialize the base service."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self._initialized = True

    def _log_info(self, message: str, *args) -> None:
        """
        Log an info message.

        Args:
            message: The message format string.
            *args: Arguments for the format string.
        """
        self.logger.info(message, *args)

    def _log_error(self, message: str, *args) -> None:
        """
        Log an error message.

        Args:
            message: The message format string.
            *args: Arguments for the format string.
        """
        self.logger.error(message, *args)

    def _log_debug(self, message: str, *args) -> None:
        """
        Log a debug message.

        Args:
            message: The message format string.
            *args: Arguments for the format string.
        """
        self.logger.debug(message, *args)
