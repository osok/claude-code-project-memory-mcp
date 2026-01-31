"""Base class for language-specific code extractors."""

from abc import ABC, abstractmethod
from typing import Any

from memory_service.models.code_elements import (
    CallInfo,
    ClassInfo,
    FunctionInfo,
    ImportInfo,
    ParseResult,
)


class LanguageExtractor(ABC):
    """Abstract base class for language-specific code extractors.

    Each language extractor implements methods to extract code elements
    (functions, classes, imports, calls) from source code.
    """

    @property
    @abstractmethod
    def language(self) -> str:
        """Return the language name this extractor handles."""
        ...

    @abstractmethod
    def extract(self, source: str, file_path: str) -> ParseResult:
        """Extract all code elements from source.

        Args:
            source: Source code content
            file_path: Relative file path

        Returns:
            ParseResult with extracted elements
        """
        ...

    @abstractmethod
    def extract_functions(self, source: str, file_path: str) -> list[FunctionInfo]:
        """Extract function definitions from source.

        Args:
            source: Source code content
            file_path: Relative file path

        Returns:
            List of FunctionInfo objects
        """
        ...

    @abstractmethod
    def extract_classes(self, source: str, file_path: str) -> list[ClassInfo]:
        """Extract class definitions from source.

        Args:
            source: Source code content
            file_path: Relative file path

        Returns:
            List of ClassInfo objects
        """
        ...

    @abstractmethod
    def extract_imports(self, source: str) -> list[ImportInfo]:
        """Extract import statements from source.

        Args:
            source: Source code content

        Returns:
            List of ImportInfo objects
        """
        ...

    def extract_calls(self, source: str) -> list[CallInfo]:
        """Extract function/method calls from source.

        Default implementation returns empty list.
        Override in subclass for language-specific call extraction.

        Args:
            source: Source code content

        Returns:
            List of CallInfo objects
        """
        return []

    def extract_docstring(self, source: str) -> str | None:
        """Extract module-level docstring.

        Default implementation returns None.
        Override in subclass for language-specific docstring extraction.

        Args:
            source: Source code content

        Returns:
            Docstring or None
        """
        return None
