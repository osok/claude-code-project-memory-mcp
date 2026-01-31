"""Gitignore pattern matching using pathspec."""

from pathlib import Path
from typing import Sequence

import pathspec


class GitignoreFilter:
    """Filter files based on gitignore patterns.

    Uses pathspec library for accurate gitignore-style pattern matching.
    """

    # Default patterns to always ignore
    DEFAULT_IGNORES = [
        ".git/",
        ".git/**",
        "__pycache__/",
        "__pycache__/**",
        "*.pyc",
        "*.pyo",
        ".pytest_cache/",
        ".pytest_cache/**",
        ".mypy_cache/",
        ".mypy_cache/**",
        ".ruff_cache/",
        ".ruff_cache/**",
        "node_modules/",
        "node_modules/**",
        ".venv/",
        ".venv/**",
        "venv/",
        "venv/**",
        ".env",
        ".env.*",
        "*.egg-info/",
        "*.egg-info/**",
        "dist/",
        "dist/**",
        "build/",
        "build/**",
        ".coverage",
        "coverage.xml",
        "htmlcov/",
        "htmlcov/**",
        "*.log",
        "*.lock",
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
    ]

    def __init__(
        self,
        root_path: Path | str,
        extra_patterns: Sequence[str] | None = None,
        use_default_ignores: bool = True,
    ) -> None:
        """Initialize gitignore filter.

        Args:
            root_path: Root directory path
            extra_patterns: Additional patterns to ignore
            use_default_ignores: Whether to include default ignore patterns
        """
        self.root_path = Path(root_path).resolve()
        self._patterns: list[str] = []

        # Add default patterns
        if use_default_ignores:
            self._patterns.extend(self.DEFAULT_IGNORES)

        # Add extra patterns
        if extra_patterns:
            self._patterns.extend(extra_patterns)

        # Load .gitignore from root if exists
        gitignore_path = self.root_path / ".gitignore"
        if gitignore_path.exists():
            self._load_gitignore(gitignore_path)

        # Compile pathspec
        self._spec = pathspec.PathSpec.from_lines(
            pathspec.patterns.GitWildMatchPattern,
            self._patterns,
        )

    def _load_gitignore(self, gitignore_path: Path) -> None:
        """Load patterns from a .gitignore file.

        Args:
            gitignore_path: Path to .gitignore file
        """
        with open(gitignore_path) as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith("#"):
                    self._patterns.append(line)

    def is_ignored(self, path: Path | str) -> bool:
        """Check if a path should be ignored.

        Args:
            path: Path to check (absolute or relative to root)

        Returns:
            True if path matches any ignore pattern
        """
        path = Path(path)

        # Convert to relative path if absolute
        if path.is_absolute():
            try:
                path = path.relative_to(self.root_path)
            except ValueError:
                # Path is not under root, don't ignore
                return False

        # Convert to string with forward slashes
        path_str = str(path).replace("\\", "/")

        return self._spec.match_file(path_str)

    def filter_paths(self, paths: Sequence[Path | str]) -> list[Path]:
        """Filter a list of paths, removing ignored ones.

        Args:
            paths: Sequence of paths to filter

        Returns:
            List of paths that are not ignored
        """
        return [Path(p) for p in paths if not self.is_ignored(p)]

    def iter_files(
        self,
        directory: Path | str | None = None,
        extensions: Sequence[str] | None = None,
    ):
        """Iterate over non-ignored files in a directory.

        Args:
            directory: Directory to iterate (default: root_path)
            extensions: File extensions to include (e.g., ['.py', '.ts'])

        Yields:
            Path objects for non-ignored files
        """
        directory = Path(directory) if directory else self.root_path

        for path in directory.rglob("*"):
            if path.is_file():
                # Check extension filter
                if extensions and path.suffix.lower() not in extensions:
                    continue

                # Check gitignore patterns
                if not self.is_ignored(path):
                    yield path

    def add_pattern(self, pattern: str) -> None:
        """Add a new ignore pattern.

        Args:
            pattern: Gitignore-style pattern to add
        """
        self._patterns.append(pattern)
        self._spec = pathspec.PathSpec.from_lines(
            pathspec.patterns.GitWildMatchPattern,
            self._patterns,
        )

    @property
    def patterns(self) -> list[str]:
        """Get list of all ignore patterns."""
        return self._patterns.copy()
