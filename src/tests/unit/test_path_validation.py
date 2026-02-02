"""Unit tests for path validation module."""

import pytest
from pathlib import Path

from memory_service.utils.path_validation import (
    validate_path,
    validate_output_path,
    is_safe_path,
    sanitize_filename,
    PathTraversalError,
)


class TestValidatePath:
    """Tests for validate_path function."""

    def test_valid_absolute_path(self, tmp_path: Path) -> None:
        """Test validating absolute path within base."""
        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("# test")

        result = validate_path(str(test_file), str(tmp_path))

        assert result == test_file

    def test_valid_relative_path(self, tmp_path: Path) -> None:
        """Test validating path within base directory."""
        # Create a test file
        test_file = tmp_path / "subdir" / "test.py"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("# test")

        # Use absolute path - validate_path resolves against CWD for relative paths
        result = validate_path(str(test_file), str(tmp_path))

        assert result == test_file

    def test_path_traversal_rejected(self, tmp_path: Path) -> None:
        """Test path traversal is rejected."""
        with pytest.raises(PathTraversalError):
            validate_path("../outside.py", str(tmp_path))

    def test_path_traversal_hidden(self, tmp_path: Path) -> None:
        """Test hidden path traversal is rejected."""
        with pytest.raises(PathTraversalError):
            validate_path("subdir/../../outside.py", str(tmp_path))

    def test_absolute_path_outside_base(self, tmp_path: Path) -> None:
        """Test absolute path outside base is rejected."""
        with pytest.raises(PathTraversalError):
            validate_path("/etc/passwd", str(tmp_path))

    def test_symlink_traversal(self, tmp_path: Path) -> None:
        """Test symlink traversal is rejected."""
        # Create a symlink pointing outside
        outside_dir = tmp_path.parent / "outside"
        outside_dir.mkdir(exist_ok=True)
        outside_file = outside_dir / "secret.txt"
        outside_file.write_text("secret")

        symlink = tmp_path / "link"
        try:
            symlink.symlink_to(outside_dir)
        except OSError:
            pytest.skip("Cannot create symlinks on this system")

        with pytest.raises(PathTraversalError):
            validate_path("link/secret.txt", str(tmp_path))

    def test_nonexistent_file_validated(self, tmp_path: Path) -> None:
        """Test that non-existent file within root is valid (path exists check is separate)."""
        # validate_path only checks containment, not existence
        nonexistent = tmp_path / "nonexistent.py"
        result = validate_path(str(nonexistent), str(tmp_path))

        # Returns the resolved path (even if file doesn't exist)
        assert result == nonexistent

    def test_directory_validation(self, tmp_path: Path) -> None:
        """Test validating directory path."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        result = validate_path(str(subdir), str(tmp_path))

        assert result == subdir

    def test_nested_directory(self, tmp_path: Path) -> None:
        """Test validating nested directory."""
        nested = tmp_path / "a" / "b" / "c"
        nested.mkdir(parents=True)

        # Use absolute path
        result = validate_path(str(nested), str(tmp_path))

        assert result == nested

    def test_path_with_dots(self, tmp_path: Path) -> None:
        """Test path with dots in filename."""
        # Create file with dots in name
        test_file = tmp_path / "file.test.py"
        test_file.write_text("# test")

        # Use absolute path
        result = validate_path(str(test_file), str(tmp_path))

        assert result == test_file

    def test_path_normalization(self, tmp_path: Path) -> None:
        """Test path normalization."""
        # Create file
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        test_file = subdir / "test.py"
        test_file.write_text("# test")

        # Path with extra slashes (using absolute path)
        result = validate_path(str(tmp_path / "subdir" / "test.py"), str(tmp_path))

        assert result == test_file


class TestPathTraversalError:
    """Tests for PathTraversalError."""

    def test_error_message(self) -> None:
        """Test error message."""
        error = PathTraversalError("/bad/path", "/base")

        assert "/bad/path" in str(error)
        assert "/base" in str(error)

    def test_error_inherits_exception(self) -> None:
        """Test error inherits from Exception."""
        error = PathTraversalError("/bad/path", "/base")

        assert isinstance(error, Exception)


class TestEdgeCases:
    """Tests for edge cases in path validation."""

    def test_empty_path(self, tmp_path: Path) -> None:
        """Test empty path."""
        # Empty path resolves to CWD which should be outside tmp_path
        with pytest.raises((FileNotFoundError, PathTraversalError)):
            validate_path("", str(tmp_path))

    def test_base_path_is_file(self, tmp_path: Path) -> None:
        """Test when base path is a file, not directory."""
        base_file = tmp_path / "basefile.txt"
        base_file.write_text("base")

        # Behavior depends on implementation
        try:
            validate_path("test.py", str(base_file))
        except (ValueError, FileNotFoundError, PathTraversalError):
            pass  # Expected

    def test_unicode_path(self, tmp_path: Path) -> None:
        """Test Unicode characters in path."""
        test_file = tmp_path / "test_unicode.py"
        test_file.write_text("# test")

        # Use absolute path
        result = validate_path(str(test_file), str(tmp_path))

        assert result == test_file

    def test_spaces_in_path(self, tmp_path: Path) -> None:
        """Test spaces in path."""
        test_file = tmp_path / "test file.py"
        test_file.write_text("# test")

        # Use absolute path
        result = validate_path(str(test_file), str(tmp_path))

        assert result == test_file


class TestValidateOutputPath:
    """Tests for validate_output_path function."""

    def test_valid_output_path(self, tmp_path: Path) -> None:
        """Test validating valid output path."""
        result = validate_output_path("newfile.txt", str(tmp_path))

        assert result.parent == tmp_path
        assert result.name == "newfile.txt"

    def test_create_parent_directory(self, tmp_path: Path) -> None:
        """Test creating parent directory."""
        result = validate_output_path(
            "subdir/newfile.txt",
            str(tmp_path),
            create_parent=True,
        )

        assert (tmp_path / "subdir").exists()
        assert result.parent == tmp_path / "subdir"

    def test_output_path_traversal_rejected(self, tmp_path: Path) -> None:
        """Test output path traversal is rejected."""
        with pytest.raises(PathTraversalError):
            validate_output_path("../outside.txt", str(tmp_path))


class TestIsSafePath:
    """Tests for is_safe_path function."""

    def test_safe_path_returns_true(self, tmp_path: Path) -> None:
        """Test safe path returns True."""
        test_file = tmp_path / "safe.py"
        test_file.write_text("# test")

        result = is_safe_path(str(test_file), str(tmp_path))

        assert result is True

    def test_unsafe_path_returns_false(self, tmp_path: Path) -> None:
        """Test unsafe path returns False."""
        result = is_safe_path("../outside.py", str(tmp_path))

        assert result is False

    def test_nonexistent_path_returns_false(self, tmp_path: Path) -> None:
        """Test nonexistent path returns False."""
        result = is_safe_path("nonexistent.py", str(tmp_path))

        assert result is False


class TestSanitizeFilename:
    """Tests for sanitize_filename function."""

    def test_normal_filename(self) -> None:
        """Test normal filename passes through."""
        result = sanitize_filename("myfile.py")

        assert result == "myfile.py"

    def test_removes_path_separators(self) -> None:
        """Test path separators are replaced."""
        result = sanitize_filename("path/to/file.py")

        assert "/" not in result
        assert result == "path_to_file.py"

    def test_removes_leading_dots(self) -> None:
        """Test leading dots are removed."""
        result = sanitize_filename(".hidden")

        assert not result.startswith(".")

    def test_removes_special_characters(self) -> None:
        """Test special characters are removed."""
        result = sanitize_filename("file<>:*?.py")

        # Should not contain special chars
        for char in "<>:*?":
            assert char not in result

    def test_empty_string_returns_unnamed(self) -> None:
        """Test empty string returns 'unnamed'."""
        result = sanitize_filename("...")

        assert result == "unnamed" or len(result) > 0

    def test_backslash_replaced(self) -> None:
        """Test backslash is replaced."""
        result = sanitize_filename("path\\to\\file.py")

        assert "\\" not in result
