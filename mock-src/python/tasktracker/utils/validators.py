"""Validation functions for user input."""

import re
from typing import Optional
from uuid import UUID


EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
)

USERNAME_PATTERN = re.compile(
    r"^[a-zA-Z][a-zA-Z0-9_]{2,29}$"
)


def validate_email(email: str) -> bool:
    """
    Validate an email address format.

    Args:
        email: The email address to validate.

    Returns:
        True if the email is valid, False otherwise.

    Examples:
        >>> validate_email("user@example.com")
        True
        >>> validate_email("invalid-email")
        False
    """
    if not email or not isinstance(email, str):
        return False
    return bool(EMAIL_PATTERN.match(email.strip()))


def validate_username(username: str) -> bool:
    """
    Validate a username.

    Username must:
    - Start with a letter
    - Be 3-30 characters long
    - Contain only letters, numbers, and underscores

    Args:
        username: The username to validate.

    Returns:
        True if the username is valid, False otherwise.

    Examples:
        >>> validate_username("john_doe")
        True
        >>> validate_username("123invalid")
        False
    """
    if not username or not isinstance(username, str):
        return False
    return bool(USERNAME_PATTERN.match(username))


def validate_uuid(value: str) -> bool:
    """
    Validate a UUID string.

    Args:
        value: The string to validate as UUID.

    Returns:
        True if the string is a valid UUID, False otherwise.

    Examples:
        >>> validate_uuid("550e8400-e29b-41d4-a716-446655440000")
        True
        >>> validate_uuid("not-a-uuid")
        False
    """
    if not value or not isinstance(value, str):
        return False
    try:
        UUID(value)
        return True
    except (ValueError, AttributeError):
        return False


def validate_task_title(title: str, min_length: int = 3, max_length: int = 200) -> tuple[bool, Optional[str]]:
    """
    Validate a task title.

    Args:
        title: The title to validate.
        min_length: Minimum allowed length.
        max_length: Maximum allowed length.

    Returns:
        Tuple of (is_valid, error_message).

    Examples:
        >>> validate_task_title("Fix bug")
        (True, None)
        >>> validate_task_title("Ab")
        (False, 'Title must be at least 3 characters')
    """
    if not title or not isinstance(title, str):
        return False, "Title is required"

    title = title.strip()
    if len(title) < min_length:
        return False, f"Title must be at least {min_length} characters"
    if len(title) > max_length:
        return False, f"Title must be at most {max_length} characters"

    return True, None


def validate_password(
    password: str,
    min_length: int = 8,
    require_uppercase: bool = True,
    require_lowercase: bool = True,
    require_digit: bool = True,
    require_special: bool = False,
) -> tuple[bool, list[str]]:
    """
    Validate a password against security requirements.

    Args:
        password: The password to validate.
        min_length: Minimum length required.
        require_uppercase: Require at least one uppercase letter.
        require_lowercase: Require at least one lowercase letter.
        require_digit: Require at least one digit.
        require_special: Require at least one special character.

    Returns:
        Tuple of (is_valid, list_of_errors).

    Examples:
        >>> validate_password("SecurePass1")
        (True, [])
        >>> validate_password("weak")
        (False, ['Password must be at least 8 characters', ...])
    """
    errors = []

    if not password:
        return False, ["Password is required"]

    if len(password) < min_length:
        errors.append(f"Password must be at least {min_length} characters")

    if require_uppercase and not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")

    if require_lowercase and not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")

    if require_digit and not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one digit")

    if require_special and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        errors.append("Password must contain at least one special character")

    return len(errors) == 0, errors


def sanitize_input(value: str, max_length: int = 1000) -> str:
    """
    Sanitize user input by stripping whitespace and limiting length.

    Args:
        value: The input to sanitize.
        max_length: Maximum allowed length.

    Returns:
        Sanitized string.
    """
    if not value:
        return ""
    return value.strip()[:max_length]
