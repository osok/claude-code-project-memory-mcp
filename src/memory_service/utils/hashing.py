"""Content hashing utilities for change detection and cache keys."""

import hashlib
import re
from typing import Any


def normalize_content(content: str) -> str:
    """Normalize content for consistent hashing.

    Normalizes whitespace and removes comments to ensure semantically
    equivalent content produces the same hash.

    Args:
        content: Raw content string

    Returns:
        Normalized content string
    """
    # Normalize line endings
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")

    # Collapse multiple spaces/tabs to single space
    normalized = re.sub(r"[ \t]+", " ", normalized)

    # Collapse multiple newlines to single newline
    normalized = re.sub(r"\n\s*\n", "\n", normalized)

    # Strip leading/trailing whitespace from each line
    lines = [line.strip() for line in normalized.split("\n")]
    normalized = "\n".join(lines)

    # Strip leading/trailing whitespace from entire content
    return normalized.strip()


def content_hash(content: str, normalize: bool = True) -> str:
    """Generate SHA-256 hash of content.

    Args:
        content: Content to hash
        normalize: Whether to normalize content before hashing

    Returns:
        Hexadecimal SHA-256 hash string
    """
    if normalize:
        content = normalize_content(content)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def embedding_cache_key(content: str, model: str) -> str:
    """Generate cache key for an embedding.

    Combines content hash with model name to ensure embeddings
    from different models are cached separately.

    Args:
        content: Content that was embedded
        model: Embedding model name

    Returns:
        Cache key string
    """
    normalized = normalize_content(content)
    combined = f"{model}:{normalized}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def file_content_hash(file_path: str, content: str) -> str:
    """Generate hash for a file's content.

    Includes file path in hash to differentiate identical content
    in different locations.

    Args:
        file_path: Relative file path
        content: File content

    Returns:
        Hexadecimal hash string
    """
    normalized_content = normalize_content(content)
    combined = f"{file_path}:{normalized_content}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def dict_hash(data: dict[str, Any]) -> str:
    """Generate hash for a dictionary.

    Sorts keys to ensure consistent ordering.

    Args:
        data: Dictionary to hash

    Returns:
        Hexadecimal hash string
    """
    import json

    serialized = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
