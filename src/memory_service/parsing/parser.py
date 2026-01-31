"""Parser orchestration for code analysis."""

from pathlib import Path
from typing import Any

from memory_service.models.code_elements import ParseResult
from memory_service.parsing.extractors import get_extractor, get_language_for_extension
from memory_service.utils.logging import get_logger

logger = get_logger(__name__)


class ParserOrchestrator:
    """Orchestrates code parsing across multiple languages.

    Provides:
    - Language detection from file extension
    - Delegation to language-specific extractors
    - Unified parse result format
    """

    def __init__(self) -> None:
        """Initialize parser orchestrator."""
        logger.info("parser_orchestrator_initialized")

    def detect_language(self, file_path: str | Path) -> str | None:
        """Detect programming language from file extension.

        Args:
            file_path: Path to source file

        Returns:
            Language name or None if not supported
        """
        path = Path(file_path)
        return get_language_for_extension(path.suffix)

    async def parse_file(
        self,
        file_path: str | Path,
        content: str | None = None,
    ) -> ParseResult:
        """Parse a source file.

        Args:
            file_path: Path to source file
            content: File content (read from disk if not provided)

        Returns:
            Parse result with extracted code elements
        """
        import asyncio

        path = Path(file_path)
        relative_path = str(path)

        # Detect language
        language = self.detect_language(path)
        if not language:
            return ParseResult(
                file_path=relative_path,
                language="unknown",
                errors=[f"Unsupported file type: {path.suffix}"],
            )

        # Read content if not provided
        if content is None:
            try:
                content = path.read_text(encoding="utf-8")
            except Exception as e:
                return ParseResult(
                    file_path=relative_path,
                    language=language,
                    errors=[f"Failed to read file: {e}"],
                )

        # Get extractor
        extractor = get_extractor(language)
        if not extractor:
            return ParseResult(
                file_path=relative_path,
                language=language,
                errors=[f"No extractor available for {language}"],
            )

        # Parse with extractor
        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                lambda: extractor.extract(content, relative_path),
            )
            return result

        except Exception as e:
            logger.error("parse_file_failed", file_path=relative_path, error=str(e))
            return ParseResult(
                file_path=relative_path,
                language=language,
                errors=[f"Parse error: {e}"],
            )

    async def parse_directory(
        self,
        directory: str | Path,
        extensions: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
    ) -> list[ParseResult]:
        """Parse all supported files in a directory.

        Args:
            directory: Directory to parse
            extensions: File extensions to include (default: all supported)
            exclude_patterns: Patterns to exclude

        Returns:
            List of parse results
        """
        from memory_service.utils.gitignore import GitignoreFilter

        directory = Path(directory)
        gitignore = GitignoreFilter(
            root_path=directory,
            extra_patterns=exclude_patterns,
        )

        results = []

        # Determine extensions to process
        if extensions:
            ext_set = set(extensions)
        else:
            from memory_service.parsing.extractors import EXTENSION_MAP

            ext_set = set(EXTENSION_MAP.keys())

        # Iterate through files
        for file_path in gitignore.iter_files(extensions=list(ext_set)):
            result = await self.parse_file(file_path)
            results.append(result)

        logger.info(
            "directory_parsed",
            directory=str(directory),
            file_count=len(results),
            error_count=sum(1 for r in results if r.errors),
        )

        return results
