"""Helper functions for common operations."""

import re
from datetime import datetime
from typing import Optional, Union
from uuid import UUID, uuid4


def generate_id() -> UUID:
    """
    Generate a new unique identifier.

    Returns:
        A new UUID4.

    Examples:
        >>> id = generate_id()
        >>> isinstance(id, UUID)
        True
    """
    return uuid4()


def format_datetime(
    dt: datetime,
    fmt: str = "%Y-%m-%d %H:%M:%S",
    include_tz: bool = False,
) -> str:
    """
    Format a datetime object as a string.

    Args:
        dt: The datetime to format.
        fmt: The format string to use.
        include_tz: Whether to include timezone info.

    Returns:
        Formatted datetime string.

    Examples:
        >>> from datetime import datetime
        >>> dt = datetime(2024, 1, 15, 10, 30, 0)
        >>> format_datetime(dt)
        '2024-01-15 10:30:00'
    """
    result = dt.strftime(fmt)
    if include_tz and dt.tzinfo:
        result += f" {dt.tzinfo}"
    return result


def parse_datetime(
    value: str,
    formats: Optional[list[str]] = None,
) -> Optional[datetime]:
    """
    Parse a string into a datetime object.

    Tries multiple formats until one succeeds.

    Args:
        value: The string to parse.
        formats: List of format strings to try.

    Returns:
        Parsed datetime or None if parsing fails.

    Examples:
        >>> parse_datetime("2024-01-15")
        datetime.datetime(2024, 1, 15, 0, 0)
        >>> parse_datetime("invalid") is None
        True
    """
    if not value:
        return None

    if formats is None:
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
        ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    return None


def slugify(text: str, separator: str = "-", max_length: int = 100) -> str:
    """
    Convert text to a URL-friendly slug.

    Args:
        text: The text to slugify.
        separator: Character to use between words.
        max_length: Maximum length of the result.

    Returns:
        URL-friendly slug.

    Examples:
        >>> slugify("Hello World!")
        'hello-world'
        >>> slugify("My Project Name", separator="_")
        'my_project_name'
    """
    if not text:
        return ""

    # Convert to lowercase and replace spaces
    slug = text.lower().strip()

    # Remove special characters
    slug = re.sub(r"[^\w\s-]", "", slug)

    # Replace spaces and repeated separators
    slug = re.sub(r"[\s_-]+", separator, slug)

    # Remove leading/trailing separators
    slug = slug.strip(separator)

    return slug[:max_length]


def truncate(
    text: str,
    max_length: int = 100,
    suffix: str = "...",
) -> str:
    """
    Truncate text to a maximum length.

    Args:
        text: The text to truncate.
        max_length: Maximum length including suffix.
        suffix: String to append when truncated.

    Returns:
        Truncated text.

    Examples:
        >>> truncate("Hello World", max_length=8)
        'Hello...'
    """
    if not text or len(text) <= max_length:
        return text or ""

    return text[: max_length - len(suffix)] + suffix


def pluralize(count: int, singular: str, plural: Optional[str] = None) -> str:
    """
    Return singular or plural form based on count.

    Args:
        count: The count to check.
        singular: Singular form of the word.
        plural: Plural form (defaults to singular + 's').

    Returns:
        Appropriate form with count.

    Examples:
        >>> pluralize(1, "task")
        '1 task'
        >>> pluralize(5, "task")
        '5 tasks'
    """
    if plural is None:
        plural = singular + "s"

    return f"{count} {singular if count == 1 else plural}"


def merge_dicts(*dicts: dict, deep: bool = False) -> dict:
    """
    Merge multiple dictionaries.

    Args:
        *dicts: Dictionaries to merge.
        deep: Whether to perform deep merge of nested dicts.

    Returns:
        Merged dictionary.

    Examples:
        >>> merge_dicts({'a': 1}, {'b': 2})
        {'a': 1, 'b': 2}
    """
    result = {}

    for d in dicts:
        if not d:
            continue

        for key, value in d.items():
            if deep and isinstance(value, dict) and isinstance(result.get(key), dict):
                result[key] = merge_dicts(result[key], value, deep=True)
            else:
                result[key] = value

    return result


def chunk_list(items: list, chunk_size: int) -> list[list]:
    """
    Split a list into chunks of specified size.

    Args:
        items: The list to split.
        chunk_size: Maximum size of each chunk.

    Returns:
        List of chunks.

    Examples:
        >>> chunk_list([1, 2, 3, 4, 5], 2)
        [[1, 2], [3, 4], [5]]
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    return [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]


def safe_get(
    data: Union[dict, list],
    path: str,
    default: Optional[any] = None,
    separator: str = ".",
) -> any:
    """
    Safely get a nested value from a dict or list.

    Args:
        data: The data structure to traverse.
        path: Dot-separated path to the value.
        default: Default value if path not found.
        separator: Path separator character.

    Returns:
        The value at path or default.

    Examples:
        >>> safe_get({'a': {'b': 1}}, 'a.b')
        1
        >>> safe_get({'a': 1}, 'a.b.c', default='missing')
        'missing'
    """
    keys = path.split(separator)
    result = data

    for key in keys:
        try:
            if isinstance(result, dict):
                result = result[key]
            elif isinstance(result, (list, tuple)):
                result = result[int(key)]
            else:
                return default
        except (KeyError, IndexError, ValueError, TypeError):
            return default

    return result
