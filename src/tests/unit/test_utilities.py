"""Unit tests for Utility Functions (UT-140 to UT-149)."""

import tempfile
from pathlib import Path

import pytest

from memory_service.utils.hashing import (
    content_hash,
    normalize_content,
    embedding_cache_key,
    file_content_hash,
    dict_hash,
)
from memory_service.utils.gitignore import GitignoreFilter


class TestContentHashing:
    """Tests for content hashing functions (UT-140 to UT-143)."""

    def test_ut140_generate_sha256_hash(self):
        """UT-140: Generate SHA-256 hash for string."""
        test_content = "Hello, World!"
        hash_result = content_hash(test_content, normalize=False)

        # SHA-256 produces 64 character hex string
        assert len(hash_result) == 64
        # Should be valid hex
        assert all(c in "0123456789abcdef" for c in hash_result)

    def test_ut141_same_hash_for_same_content(self):
        """UT-141: Generate same hash for same content."""
        content = "This is test content for hashing."

        hash1 = content_hash(content)
        hash2 = content_hash(content)

        assert hash1 == hash2

    def test_ut141_different_hash_for_different_content(self):
        """UT-141: Generate different hash for different content."""
        content1 = "First piece of content"
        content2 = "Second piece of content"

        hash1 = content_hash(content1)
        hash2 = content_hash(content2)

        assert hash1 != hash2

    def test_ut142_normalize_line_endings_to_lf(self):
        """UT-142: Normalize line endings to LF."""
        # Content with CRLF (Windows)
        windows_content = "line1\r\nline2\r\nline3"

        # Content with LF (Unix)
        unix_content = "line1\nline2\nline3"

        # Content with CR (old Mac)
        mac_content = "line1\rline2\rline3"

        # After normalization, all should have same hash
        hash_windows = content_hash(windows_content)
        hash_unix = content_hash(unix_content)
        hash_mac = content_hash(mac_content)

        assert hash_windows == hash_unix == hash_mac

    def test_ut143_strip_trailing_whitespace(self):
        """UT-143: Strip trailing whitespace."""
        # Content with trailing whitespace
        content_with_whitespace = "line1  \nline2   \nline3    "

        # Content without trailing whitespace
        content_clean = "line1\nline2\nline3"

        # After normalization, should have same hash
        hash_whitespace = content_hash(content_with_whitespace)
        hash_clean = content_hash(content_clean)

        assert hash_whitespace == hash_clean

    def test_normalize_content_collapses_spaces(self):
        """Test that multiple spaces are collapsed."""
        content_spaces = "word1    word2     word3"
        normalized = normalize_content(content_spaces)

        assert "    " not in normalized
        assert "word1 word2 word3" == normalized

    def test_normalize_content_collapses_blank_lines(self):
        """Test that multiple blank lines are collapsed."""
        content_blanks = "line1\n\n\n\nline2"
        normalized = normalize_content(content_blanks)

        # Multiple newlines should collapse
        assert "\n\n" not in normalized


class TestGitignoreFilter:
    """Tests for GitignoreFilter (UT-144 to UT-146)."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create some files
            (root / "src").mkdir()
            (root / "src" / "main.py").write_text("# Main module")
            (root / "src" / "utils.py").write_text("# Utils module")

            (root / "tests").mkdir()
            (root / "tests" / "test_main.py").write_text("# Tests")

            (root / "node_modules").mkdir()
            (root / "node_modules" / "package").mkdir()
            (root / "node_modules" / "package" / "index.js").write_text("// JS")

            (root / ".git").mkdir()
            (root / ".git" / "config").write_text("[core]")

            (root / "__pycache__").mkdir()
            (root / "__pycache__" / "main.cpython-311.pyc").write_text("")

            yield root

    def test_ut144_match_gitignore_patterns(self, temp_project):
        """UT-144: Match gitignore patterns."""
        filter = GitignoreFilter(temp_project)

        # node_modules should be ignored
        assert filter.is_ignored(temp_project / "node_modules" / "package" / "index.js")

        # __pycache__ should be ignored
        assert filter.is_ignored(temp_project / "__pycache__" / "main.cpython-311.pyc")

        # .git should be ignored
        assert filter.is_ignored(temp_project / ".git" / "config")

        # Regular source files should not be ignored
        assert not filter.is_ignored(temp_project / "src" / "main.py")
        assert not filter.is_ignored(temp_project / "tests" / "test_main.py")

    def test_ut145_handle_missing_gitignore(self):
        """UT-145: Handle missing .gitignore."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # No .gitignore file
            filter = GitignoreFilter(root)

            # Should still use default patterns
            assert filter.is_ignored("node_modules/package.json")
            assert filter.is_ignored("__pycache__/module.pyc")

    def test_ut146_filter_list_of_paths(self, temp_project):
        """UT-146: Filter list of paths."""
        filter = GitignoreFilter(temp_project)

        paths = [
            temp_project / "src" / "main.py",
            temp_project / "src" / "utils.py",
            temp_project / "node_modules" / "package" / "index.js",
            temp_project / "__pycache__" / "main.cpython-311.pyc",
            temp_project / "tests" / "test_main.py",
        ]

        filtered = filter.filter_paths(paths)

        # Should only include non-ignored paths
        assert len(filtered) == 3
        assert temp_project / "src" / "main.py" in filtered
        assert temp_project / "src" / "utils.py" in filtered
        assert temp_project / "tests" / "test_main.py" in filtered
        assert temp_project / "node_modules" / "package" / "index.js" not in filtered

    def test_gitignore_custom_patterns(self, temp_project):
        """Test GitignoreFilter with custom patterns."""
        # Create a custom file to ignore
        (temp_project / "config.local.json").write_text("{}")

        filter = GitignoreFilter(
            temp_project,
            extra_patterns=["*.local.json"],
        )

        assert filter.is_ignored("config.local.json")
        assert not filter.is_ignored("config.json")

    def test_gitignore_loads_file(self, temp_project):
        """Test GitignoreFilter loads .gitignore file."""
        # Create a .gitignore file
        (temp_project / ".gitignore").write_text("*.secret\ncredentials/\n")
        (temp_project / "password.secret").write_text("secret")
        (temp_project / "credentials").mkdir()
        (temp_project / "credentials" / "api.key").write_text("key")

        filter = GitignoreFilter(temp_project)

        assert filter.is_ignored("password.secret")
        assert filter.is_ignored("credentials/api.key")

    def test_gitignore_relative_paths(self, temp_project):
        """Test is_ignored works with relative paths."""
        filter = GitignoreFilter(temp_project)

        # Test with relative path strings
        assert filter.is_ignored("node_modules/package.json")
        assert not filter.is_ignored("src/main.py")

    def test_gitignore_iter_files(self, temp_project):
        """Test iter_files returns non-ignored files."""
        filter = GitignoreFilter(temp_project)

        files = list(filter.iter_files())

        # Should not include ignored files
        file_names = [f.name for f in files]
        assert "index.js" not in file_names  # In node_modules
        assert "config" not in file_names  # In .git
        assert "main.cpython-311.pyc" not in file_names  # In __pycache__

        # Should include non-ignored files
        assert "main.py" in file_names
        assert "utils.py" in file_names
        assert "test_main.py" in file_names

    def test_gitignore_iter_files_with_extension_filter(self, temp_project):
        """Test iter_files with extension filter."""
        # Add a non-Python file
        (temp_project / "readme.md").write_text("# README")

        filter = GitignoreFilter(temp_project)
        py_files = list(filter.iter_files(extensions=[".py"]))

        # Should only include Python files
        assert all(f.suffix == ".py" for f in py_files)


class TestEmbeddingCacheKey:
    """Tests for embedding cache key generation."""

    def test_same_content_same_model_same_key(self):
        """Test same content and model produce same key."""
        content = "test content for embedding"
        model = "voyage-code-3"

        key1 = embedding_cache_key(content, model)
        key2 = embedding_cache_key(content, model)

        assert key1 == key2

    def test_same_content_different_model_different_key(self):
        """Test same content with different model produces different key."""
        content = "test content"

        key1 = embedding_cache_key(content, "voyage-code-3")
        key2 = embedding_cache_key(content, "text-embedding-ada-002")

        assert key1 != key2

    def test_different_content_same_model_different_key(self):
        """Test different content with same model produces different key."""
        model = "voyage-code-3"

        key1 = embedding_cache_key("content A", model)
        key2 = embedding_cache_key("content B", model)

        assert key1 != key2

    def test_cache_key_is_hex_string(self):
        """Test cache key is valid hex string."""
        key = embedding_cache_key("test", "model")

        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)


class TestFileContentHash:
    """Tests for file content hashing."""

    def test_same_content_same_path_same_hash(self):
        """Test same content and path produce same hash."""
        content = "file content"
        path = "src/module.py"

        hash1 = file_content_hash(path, content)
        hash2 = file_content_hash(path, content)

        assert hash1 == hash2

    def test_same_content_different_path_different_hash(self):
        """Test same content with different path produces different hash."""
        content = "identical content"

        hash1 = file_content_hash("src/a.py", content)
        hash2 = file_content_hash("src/b.py", content)

        assert hash1 != hash2

    def test_different_content_same_path_different_hash(self):
        """Test different content with same path produces different hash."""
        path = "module.py"

        hash1 = file_content_hash(path, "version 1")
        hash2 = file_content_hash(path, "version 2")

        assert hash1 != hash2


class TestDictHash:
    """Tests for dictionary hashing."""

    def test_same_dict_same_hash(self):
        """Test same dictionary produces same hash."""
        data = {"key": "value", "number": 42}

        hash1 = dict_hash(data)
        hash2 = dict_hash(data)

        assert hash1 == hash2

    def test_key_order_independent(self):
        """Test hash is independent of key order."""
        data1 = {"a": 1, "b": 2, "c": 3}
        data2 = {"c": 3, "a": 1, "b": 2}

        hash1 = dict_hash(data1)
        hash2 = dict_hash(data2)

        assert hash1 == hash2

    def test_different_dict_different_hash(self):
        """Test different dictionaries produce different hashes."""
        data1 = {"key": "value1"}
        data2 = {"key": "value2"}

        hash1 = dict_hash(data1)
        hash2 = dict_hash(data2)

        assert hash1 != hash2

    def test_nested_dict_hashing(self):
        """Test nested dictionaries can be hashed."""
        data = {
            "outer": {
                "inner": {
                    "value": 123
                }
            }
        }

        hash_result = dict_hash(data)

        assert len(hash_result) == 64
        assert all(c in "0123456789abcdef" for c in hash_result)


class TestDefaultIgnorePatterns:
    """Tests for default ignore patterns."""

    def test_default_patterns_include_common_ignores(self):
        """Test DEFAULT_IGNORES includes common patterns."""
        defaults = GitignoreFilter.DEFAULT_IGNORES

        # Should include .git
        assert ".git/" in defaults or ".git/**" in defaults

        # Should include node_modules
        assert "node_modules/" in defaults or "node_modules/**" in defaults

        # Should include __pycache__
        assert "__pycache__/" in defaults or "__pycache__/**" in defaults

        # Should include .env files
        assert ".env" in defaults or ".env.*" in defaults

        # Should include virtual environments
        assert ".venv/" in defaults or ".venv/**" in defaults
        assert "venv/" in defaults or "venv/**" in defaults

    def test_can_disable_default_patterns(self):
        """Test default patterns can be disabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            filter = GitignoreFilter(root, use_default_ignores=False)

            # Without defaults, these patterns won't be ignored
            # unless explicitly added
            assert "node_modules" not in filter.patterns or not filter.is_ignored("node_modules/x")


class TestAddPattern:
    """Tests for dynamically adding patterns."""

    def test_add_pattern_updates_filter(self):
        """Test add_pattern updates the filter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            filter = GitignoreFilter(root)

            # Initially not ignored
            assert not filter.is_ignored("custom.ignore")

            # Add pattern
            filter.add_pattern("*.ignore")

            # Now should be ignored
            assert filter.is_ignored("custom.ignore")

    def test_patterns_property_returns_copy(self):
        """Test patterns property returns a copy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            filter = GitignoreFilter(root)

            patterns1 = filter.patterns
            patterns2 = filter.patterns

            # Should be different lists (copies)
            patterns1.append("new_pattern")
            assert "new_pattern" not in patterns2
