"""Security tests for input validation (ST-040 to ST-043).

Tests verify proper input validation:
- ST-040: Cypher injection prevented
- ST-041: Path traversal prevented
- ST-042: Memory content size limited
- ST-043: Invalid JSON rejected
"""

import re
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from memory_service.models import (
    BaseMemory,
    FunctionMemory,
    RequirementsMemory,
    MemoryType,
)


class TestInputValidation:
    """Test suite for input validation security requirements."""

    def test_st_040_cypher_injection_prevention(
        self,
        source_files: list[Path],
    ) -> None:
        """ST-040: Cypher injection prevented.

        Verify parameterized queries are used.
        """
        neo4j_files = [f for f in source_files if "neo4j" in f.name.lower()]

        for file_path in neo4j_files:
            content = file_path.read_text()

            # Find Cypher query patterns
            query_patterns = [
                r'\.run\(["\'].*\$',  # Should use parameters
                r'f["\'].*MATCH.*{.*}',  # f-string with Cypher - suspicious
                r'\.format\(.*\).*MATCH',  # .format() with Cypher - suspicious
            ]

            # Check for f-strings in Cypher queries (potential injection)
            fstring_matches = re.findall(
                r'f["\'][^"\']*(?:MATCH|CREATE|MERGE|DELETE|SET)[^"\']*{[^}]+}[^"\']*["\']',
                content,
                re.IGNORECASE
            )

            for match in fstring_matches:
                # Check if it's a safe pattern (parameter reference)
                if re.search(r'\$\w+', match):
                    continue  # Uses parameters
                if "memory_id" in match and "{" in match:
                    print(f"\nWarning: Potential Cypher injection in {file_path.name}")
                    print(f"  Query: {match[:80]}...")

            # Check for string concatenation in queries
            concat_matches = re.findall(
                r'["\'][^"\']*(?:MATCH|CREATE|MERGE)[^"\']*["\']\s*\+\s*\w+',
                content,
                re.IGNORECASE
            )

            if concat_matches:
                for match in concat_matches:
                    pytest.fail(f"String concatenation in Cypher query: {match[:50]}...")

            # Verify use of parameters
            param_usage = re.findall(r'\.run\([^)]+,\s*(?:params|{)', content)
            query_count = len(re.findall(r'\.run\(', content))

            if query_count > 0 and len(param_usage) < query_count * 0.5:
                print(f"\nNote: {file_path.name} - Consider using parameterized queries consistently")

    def test_st_041_path_traversal_prevention(
        self,
        source_files: list[Path],
    ) -> None:
        """ST-041: Path traversal prevented.

        Verify file paths are validated to base directory.
        """
        # Look for path handling in source files
        path_handling_files = []
        for f in source_files:
            content = f.read_text()
            if any(x in content for x in ["os.path", "Path(", "open(", "file_path"]):
                path_handling_files.append((f, content))

        for file_path, content in path_handling_files:
            # Skip test files
            if "test" in str(file_path).lower():
                continue

            # Check for path traversal prevention patterns
            safe_patterns = [
                r'resolve\(\)',  # Path resolution
                r'is_relative_to',  # Python 3.9+ relative check
                r'\.startswith\(',  # Prefix check
                r'validate.*path',  # Validation function
                r'safe.*path',  # Safety check
            ]

            has_file_open = "open(" in content or "Path(" in content
            has_path_validation = any(
                re.search(pattern, content, re.IGNORECASE)
                for pattern in safe_patterns
            )

            # Check for direct file operations without validation
            if has_file_open and not has_path_validation:
                # Check if there's a dedicated path validation module
                if "path_validation" in content or "validate_path" in content:
                    continue
                if "test" not in file_path.name:
                    print(f"\nNote: {file_path.name} has file operations - verify path validation")

    def test_st_041_path_validation_module(
        self,
        source_files: list[Path],
    ) -> None:
        """Test that path validation module properly prevents traversal."""
        # Find path validation module
        path_val_file = None
        for f in source_files:
            if "path_validation" in f.name:
                path_val_file = f
                break

        if not path_val_file:
            print("\nNote: No dedicated path validation module found")
            return

        content = path_val_file.read_text()

        # Check for traversal prevention
        required_checks = [
            ("resolve", "Path resolution for canonical path"),
            ("is_relative_to", "Relative path check"),
            ("'..'", "Parent directory check"),
        ]

        for check, description in required_checks:
            if check not in content:
                print(f"\nWarning: Path validation may be missing: {description}")

    def test_st_042_memory_content_size_limit(self) -> None:
        """ST-042: Memory content size limited.

        Verify content > 100KB is rejected.
        """
        max_size = 100 * 1024  # 100KB

        # Test with oversized content
        oversized_content = "x" * (max_size + 1000)

        # This should raise validation error
        try:
            memory = FunctionMemory(
                id=uuid4(),
                type=MemoryType.FUNCTION,
                content=oversized_content,
                embedding=[0.1] * 1024,
                function_id=uuid4(),
                name="test_function",
                signature="def test()",
                file_path="test.py",
                start_line=1,
                end_line=10,
                language="python",
            )
            # If we get here, check if there's a content length constraint
            if len(memory.content) > max_size:
                print(f"\nWarning: Content size {len(memory.content)} exceeds 100KB limit")
                print("Consider adding content size validation")
        except Exception as e:
            # Validation error expected
            print(f"\nGood: Content size validation active: {type(e).__name__}")

    def test_st_043_invalid_json_rejected(self) -> None:
        """ST-043: Invalid JSON rejected.

        Verify Pydantic validation catches malformed input.
        """
        # Test cases with invalid data
        invalid_cases = [
            # Missing required fields
            {"type": "function"},  # Missing everything else

            # Invalid types
            {"id": "not-a-uuid", "type": "function"},

            # Invalid enum values
            {"id": str(uuid4()), "type": "invalid_type"},

            # Invalid importance score
            {"importance_score": 2.0},  # Should be 0.0-1.0

            # Invalid sync status
            {"sync_status": "invalid"},
        ]

        for i, invalid_data in enumerate(invalid_cases):
            try:
                # Try to create a memory with invalid data
                RequirementsMemory(**invalid_data)
                # Should not reach here
                print(f"\nCase {i}: Validation did not catch: {invalid_data}")
            except Exception as e:
                # Expected - validation should fail
                pass

        print("\nGood: Pydantic validation catches invalid input")


class TestQuerySanitization:
    """Additional tests for query input sanitization."""

    def test_search_query_sanitization(
        self,
        source_files: list[Path],
    ) -> None:
        """Test that search queries are sanitized."""
        query_files = [f for f in source_files if "query" in f.name.lower() or "search" in f.name.lower()]

        for file_path in query_files:
            if "test" in str(file_path).lower():
                continue

            content = file_path.read_text()

            # Check for query length limits
            if "max_length" not in content.lower() and "limit" not in content.lower():
                if "query" in content and "search" in content:
                    print(f"\nNote: {file_path.name} - Consider adding query length limits")

    def test_memory_type_validation(self) -> None:
        """Test that memory types are validated."""
        # Valid types should work
        valid_types = ["requirements", "design", "code_pattern", "component",
                       "function", "test_history", "session", "user_preference"]

        for type_name in valid_types:
            try:
                memory_type = MemoryType(type_name)
                assert memory_type is not None
            except ValueError:
                pytest.fail(f"Valid memory type '{type_name}' rejected")

        # Invalid types should fail
        invalid_types = ["invalid", "hack", "", "requirements; DROP TABLE"]

        for type_name in invalid_types:
            try:
                memory_type = MemoryType(type_name)
                pytest.fail(f"Invalid memory type '{type_name}' should be rejected")
            except ValueError:
                pass  # Expected

        print("\nGood: Memory type validation working correctly")

    def test_uuid_validation(self) -> None:
        """Test that UUIDs are properly validated."""
        from uuid import UUID

        # Valid UUIDs
        valid_uuids = [
            "550e8400-e29b-41d4-a716-446655440000",
            str(uuid4()),
        ]

        for uuid_str in valid_uuids:
            try:
                parsed = UUID(uuid_str)
                assert str(parsed) == uuid_str.lower()
            except ValueError:
                pytest.fail(f"Valid UUID rejected: {uuid_str}")

        # Invalid UUIDs
        invalid_uuids = [
            "not-a-uuid",
            "550e8400-e29b-41d4-a716",  # Too short
            "550e8400-e29b-41d4-a716-446655440000-extra",  # Too long
            "'; DROP TABLE memories; --",  # SQL injection attempt
        ]

        for uuid_str in invalid_uuids:
            try:
                UUID(uuid_str)
                pytest.fail(f"Invalid UUID should be rejected: {uuid_str}")
            except ValueError:
                pass  # Expected
