"""Path validation utilities for secure file operations."""

from pathlib import Path
from typing import Optional

from memory_service.utils.logging import get_logger

logger = get_logger(__name__)


class PathTraversalError(Exception):
    """Raised when a path traversal attempt is detected."""

    def __init__(self, path: str, root: str) -> None:
        self.path = path
        self.root = root
        super().__init__(f"Path traversal detected: '{path}' is outside allowed root '{root}'")


def validate_path(path: str | Path, root: str | Path) -> Path:
    """Validate that a path is within the allowed root directory.

    Canonicalizes both paths using resolve() and verifies containment.

    Args:
        path: The path to validate (can be relative or absolute)
        root: The root directory that path must be within

    Returns:
        The resolved, validated Path object

    Raises:
        PathTraversalError: If the path is outside the root directory
        FileNotFoundError: If the root directory does not exist
    """
    try:
        # Resolve both paths to absolute, canonical forms
        root_resolved = Path(root).resolve()
        path_resolved = Path(path).resolve()

        # Verify the path is within root
        # Use parts comparison to avoid false positives with similar prefixes
        # e.g., /home/user vs /home/user2
        try:
            path_resolved.relative_to(root_resolved)
        except ValueError:
            logger.warning(
                "Path traversal attempt detected",
                path=str(path),
                resolved=str(path_resolved),
                root=str(root_resolved),
            )
            raise PathTraversalError(str(path), str(root_resolved))

        return path_resolved

    except (OSError, RuntimeError) as e:
        logger.error("Path validation error", path=str(path), error=str(e))
        raise


def validate_output_path(
    path: str | Path,
    root: str | Path,
    create_parent: bool = False,
) -> Path:
    """Validate an output path for writing files.

    Similar to validate_path but allows the target file to not exist yet.
    Only validates that the parent directory is within root.

    Args:
        path: The output path to validate
        root: The root directory that path must be within
        create_parent: If True, create parent directories if they don't exist

    Returns:
        The validated Path object

    Raises:
        PathTraversalError: If the path would be outside the root directory
        FileNotFoundError: If parent directory doesn't exist and create_parent is False
    """
    root_resolved = Path(root).resolve()
    path_obj = Path(path)

    # If path is relative, make it relative to root
    if not path_obj.is_absolute():
        path_obj = root_resolved / path_obj

    # Resolve the parent directory (which should exist or be creatable)
    parent = path_obj.parent
    if parent.exists():
        parent_resolved = parent.resolve()
    else:
        # For non-existent parents, we need to resolve what we can
        # Walk up until we find an existing directory
        existing_parent = parent
        while not existing_parent.exists() and existing_parent != existing_parent.parent:
            existing_parent = existing_parent.parent

        if not existing_parent.exists():
            raise FileNotFoundError(f"No valid parent directory found for '{path}'")

        parent_resolved = existing_parent.resolve() / parent.relative_to(existing_parent)

        if create_parent:
            parent_resolved.mkdir(parents=True, exist_ok=True)
            parent_resolved = parent_resolved.resolve()

    # Verify the parent is within root
    try:
        parent_resolved.relative_to(root_resolved)
    except ValueError:
        logger.warning(
            "Output path traversal attempt detected",
            path=str(path),
            parent=str(parent_resolved),
            root=str(root_resolved),
        )
        raise PathTraversalError(str(path), str(root_resolved))

    # Return the full path (file may not exist yet)
    return parent_resolved / path_obj.name


def is_safe_path(path: str | Path, root: str | Path) -> bool:
    """Check if a path is safely within the root directory.

    Non-raising version of validate_path.

    Args:
        path: The path to check
        root: The root directory

    Returns:
        True if path is within root, False otherwise
    """
    try:
        validate_path(path, root)
        return True
    except (PathTraversalError, FileNotFoundError, OSError):
        return False


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename to prevent path traversal via filename.

    Removes or replaces dangerous characters and path components.

    Args:
        filename: The filename to sanitize

    Returns:
        A safe filename
    """
    # Replace path separators
    safe = filename.replace("/", "_").replace("\\", "_")

    # Remove leading dots (hidden files) and special directory names
    while safe.startswith("."):
        safe = safe[1:]

    # Remove any remaining special characters
    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in safe)

    # Ensure we have something left
    if not safe:
        safe = "unnamed"

    return safe
