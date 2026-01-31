"""Language-specific code extractors."""

from memory_service.parsing.extractors.base import LanguageExtractor
from memory_service.parsing.extractors.python import PythonExtractor
from memory_service.parsing.extractors.typescript import TypeScriptExtractor
from memory_service.parsing.extractors.javascript import JavaScriptExtractor
from memory_service.parsing.extractors.java import JavaExtractor
from memory_service.parsing.extractors.go import GoExtractor
from memory_service.parsing.extractors.rust import RustExtractor
from memory_service.parsing.extractors.csharp import CSharpExtractor

EXTRACTORS: dict[str, type[LanguageExtractor]] = {
    "python": PythonExtractor,
    "typescript": TypeScriptExtractor,
    "javascript": JavaScriptExtractor,
    "java": JavaExtractor,
    "go": GoExtractor,
    "rust": RustExtractor,
    "csharp": CSharpExtractor,
}

EXTENSION_MAP: dict[str, str] = {
    ".py": "python",
    ".pyi": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".cs": "csharp",
}


def get_extractor(language: str) -> LanguageExtractor | None:
    """Get extractor for the specified language.

    Args:
        language: Programming language name (e.g., 'python', 'typescript')

    Returns:
        Extractor instance or None if language not supported
    """
    extractor_class = EXTRACTORS.get(language.lower())
    if extractor_class:
        return extractor_class()
    return None


def get_language_for_extension(extension: str) -> str | None:
    """Get language name for a file extension.

    Args:
        extension: File extension including dot (e.g., '.py')

    Returns:
        Language name or None if extension not recognized
    """
    return EXTENSION_MAP.get(extension.lower())


__all__ = [
    "LanguageExtractor",
    "PythonExtractor",
    "TypeScriptExtractor",
    "JavaScriptExtractor",
    "JavaExtractor",
    "GoExtractor",
    "RustExtractor",
    "CSharpExtractor",
    "get_extractor",
    "get_language_for_extension",
    "EXTRACTORS",
    "EXTENSION_MAP",
]
