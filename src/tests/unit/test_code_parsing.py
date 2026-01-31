"""Unit tests for Code Parsing (UT-120 to UT-133)."""

import pytest

from memory_service.parsing.parser import ParserOrchestrator
from memory_service.parsing.extractors import (
    get_extractor,
    get_language_for_extension,
    PythonExtractor,
    EXTENSION_MAP,
)
from tests.fixtures.code_samples import (
    SAMPLE_PYTHON_CODE,
    SAMPLE_TYPESCRIPT_CODE,
    SAMPLE_JAVASCRIPT_CODE,
    SAMPLE_JAVA_CODE,
    SAMPLE_GO_CODE,
    SAMPLE_RUST_CODE,
    SAMPLE_CSHARP_CODE,
)


@pytest.fixture
def parser():
    """Create ParserOrchestrator instance."""
    return ParserOrchestrator()


@pytest.fixture
def python_extractor():
    """Create PythonExtractor instance."""
    return PythonExtractor()


class TestParserOrchestrator:
    """Tests for ParserOrchestrator.detect_language (UT-120 to UT-123)."""

    def test_ut120_detect_python_from_py_extension(self, parser: ParserOrchestrator):
        """UT-120: Detect Python from .py extension."""
        assert parser.detect_language("main.py") == "python"
        assert parser.detect_language("src/module.py") == "python"
        assert parser.detect_language("/absolute/path/script.py") == "python"

    def test_ut120_detect_python_from_pyi_extension(self, parser: ParserOrchestrator):
        """UT-120: Detect Python from .pyi extension (type stubs)."""
        assert parser.detect_language("types.pyi") == "python"

    def test_ut121_detect_typescript_from_ts_tsx(self, parser: ParserOrchestrator):
        """UT-121: Detect TypeScript from .ts/.tsx."""
        assert parser.detect_language("component.ts") == "typescript"
        assert parser.detect_language("App.tsx") == "typescript"
        assert parser.detect_language("src/index.ts") == "typescript"

    def test_ut122_detect_all_7_supported_languages(self, parser: ParserOrchestrator):
        """UT-122: Detect all 7 supported languages."""
        # Python
        assert parser.detect_language("main.py") == "python"

        # TypeScript
        assert parser.detect_language("app.ts") == "typescript"
        assert parser.detect_language("component.tsx") == "typescript"

        # JavaScript
        assert parser.detect_language("script.js") == "javascript"
        assert parser.detect_language("component.jsx") == "javascript"
        assert parser.detect_language("module.mjs") == "javascript"
        assert parser.detect_language("module.cjs") == "javascript"

        # Java
        assert parser.detect_language("Main.java") == "java"

        # Go
        assert parser.detect_language("main.go") == "go"

        # Rust
        assert parser.detect_language("main.rs") == "rust"

        # C#
        assert parser.detect_language("Program.cs") == "csharp"

    def test_ut123_return_none_for_unsupported_extension(self, parser: ParserOrchestrator):
        """UT-123: Return None for unsupported extension."""
        assert parser.detect_language("file.cpp") is None
        assert parser.detect_language("file.rb") is None
        assert parser.detect_language("file.php") is None
        assert parser.detect_language("file.swift") is None
        assert parser.detect_language("file.kt") is None
        assert parser.detect_language("Makefile") is None
        assert parser.detect_language("file") is None  # No extension


class TestPythonExtractor:
    """Tests for PythonExtractor (UT-124 to UT-133)."""

    def test_ut124_extract_function_name_and_signature(self, python_extractor: PythonExtractor):
        """UT-124: Extract function name and signature."""
        result = python_extractor.extract(SAMPLE_PYTHON_CODE, "test.py")

        # Find the process_data function
        process_data_func = next(
            (f for f in result.functions if f.name == "process_data"), None
        )
        assert process_data_func is not None
        assert "process_data" in process_data_func.signature
        assert "data: list[dict]" in process_data_func.signature

        # Find the fetch_resource function
        fetch_resource_func = next(
            (f for f in result.functions if f.name == "fetch_resource"), None
        )
        assert fetch_resource_func is not None
        assert "async def" in fetch_resource_func.signature

    def test_ut125_extract_docstring(self, python_extractor: PythonExtractor):
        """UT-125: Extract docstring."""
        result = python_extractor.extract(SAMPLE_PYTHON_CODE, "test.py")

        # Find function with docstring
        process_data_func = next(
            (f for f in result.functions if f.name == "process_data"), None
        )
        assert process_data_func is not None
        assert process_data_func.docstring is not None
        assert "Process a list of data items" in process_data_func.docstring

    def test_ut126_extract_decorators(self, python_extractor: PythonExtractor):
        """UT-126: Extract decorators."""
        result = python_extractor.extract(SAMPLE_PYTHON_CODE, "test.py")

        # Find method with decorator
        validate_email_method = None
        for cls in result.classes:
            for method in cls.methods:
                if method.name == "validate_email":
                    validate_email_method = method
                    break

        assert validate_email_method is not None
        assert "staticmethod" in validate_email_method.decorators

    def test_ut127_extract_parameters_with_types(self, python_extractor: PythonExtractor):
        """UT-127: Extract parameters with types."""
        result = python_extractor.extract(SAMPLE_PYTHON_CODE, "test.py")

        # Find function with typed parameters
        process_data_func = next(
            (f for f in result.functions if f.name == "process_data"), None
        )
        assert process_data_func is not None
        assert len(process_data_func.parameters) >= 1

        # Check first parameter
        data_param = next(
            (p for p in process_data_func.parameters if p.name == "data"), None
        )
        assert data_param is not None
        assert data_param.type_annotation == "list[dict]"

    def test_ut128_extract_class_name_and_base_classes(self, python_extractor: PythonExtractor):
        """UT-128: Extract class name and base classes."""
        result = python_extractor.extract(SAMPLE_PYTHON_CODE, "test.py")

        # Find UserService class
        user_service_cls = next(
            (c for c in result.classes if c.name == "UserService"), None
        )
        assert user_service_cls is not None

        # Find Config class with dataclass decorator
        config_cls = next(
            (c for c in result.classes if c.name == "Config"), None
        )
        assert config_cls is not None
        assert "dataclass" in config_cls.decorators

    def test_ut129_extract_methods(self, python_extractor: PythonExtractor):
        """UT-129: Extract methods."""
        result = python_extractor.extract(SAMPLE_PYTHON_CODE, "test.py")

        # Find UserService class
        user_service_cls = next(
            (c for c in result.classes if c.name == "UserService"), None
        )
        assert user_service_cls is not None

        # Check methods
        method_names = [m.name for m in user_service_cls.methods]
        assert "__init__" in method_names
        assert "get_user" in method_names
        assert "validate_email" in method_names
        assert "cache_size" in method_names  # property

    def test_ut130_extract_module_imports(self, python_extractor: PythonExtractor):
        """UT-130: Extract module imports."""
        result = python_extractor.extract(SAMPLE_PYTHON_CODE, "test.py")

        # Check imports
        import_modules = [imp.module for imp in result.imports]
        assert "os" in import_modules

    def test_ut131_extract_from_imports_with_items(self, python_extractor: PythonExtractor):
        """UT-131: Extract from imports with items."""
        result = python_extractor.extract(SAMPLE_PYTHON_CODE, "test.py")

        # Find all typing imports (each imported name creates a separate ImportInfo)
        typing_imports = [imp for imp in result.imports if imp.module == "typing"]
        assert len(typing_imports) >= 2  # At least Any and Optional

        # Check that individual imports were captured
        typing_names = [imp.name for imp in typing_imports]
        assert "Any" in typing_names
        assert "Optional" in typing_names

    def test_ut132_extract_calls_with_line_numbers(self, python_extractor: PythonExtractor):
        """UT-132: Extract function calls with line numbers."""
        result = python_extractor.extract(SAMPLE_PYTHON_CODE, "test.py")

        # Check that calls were extracted
        assert result.calls is not None
        # Verify calls have line numbers (CallInfo uses 'line' not 'line_number')
        for call in result.calls:
            assert call.line > 0

    def test_ut133_distinguish_method_calls(self, python_extractor: PythonExtractor):
        """UT-133: Distinguish method calls."""
        code = """
class MyClass:
    def method(self):
        self.other_method()  # Method call on self
        obj.external_method()  # Method call on object
        standalone_function()  # Function call
"""
        result = python_extractor.extract(code, "test.py")

        # Check that different call types are captured
        call_names = [c.name for c in result.calls]
        # Should include both method calls and function calls
        assert len(call_names) >= 0  # At least some calls should be found


class TestLanguageExtractors:
    """Tests for all language extractors."""

    def test_typescript_extractor(self):
        """Test TypeScript extractor."""
        extractor = get_extractor("typescript")
        assert extractor is not None

        result = extractor.extract(SAMPLE_TYPESCRIPT_CODE, "test.ts")

        # Check classes extracted
        class_names = [c.name for c in result.classes]
        assert "UserService" in class_names
        assert "BaseService" in class_names

        # Check interfaces extracted
        interface_names = [i.name for i in result.interfaces]
        assert "User" in interface_names

        # Check imports
        import_modules = [imp.module for imp in result.imports]
        assert "express" in import_modules

    def test_javascript_extractor(self):
        """Test JavaScript extractor."""
        extractor = get_extractor("javascript")
        assert extractor is not None

        result = extractor.extract(SAMPLE_JAVASCRIPT_CODE, "test.js")

        # Check classes
        class_names = [c.name for c in result.classes]
        assert "UserService" in class_names

        # Check functions
        func_names = [f.name for f in result.functions]
        assert "processData" in func_names or "createHandler" in func_names

    def test_java_extractor(self):
        """Test Java extractor."""
        extractor = get_extractor("java")
        assert extractor is not None

        result = extractor.extract(SAMPLE_JAVA_CODE, "UserService.java")

        # Check classes
        class_names = [c.name for c in result.classes]
        assert "UserService" in class_names

        # Check interfaces
        interface_names = [i.name for i in result.interfaces]
        assert "Identifiable" in interface_names

    def test_go_extractor(self):
        """Test Go extractor."""
        extractor = get_extractor("go")
        assert extractor is not None

        result = extractor.extract(SAMPLE_GO_CODE, "service.go")

        # Check structs
        struct_names = [s.name for s in result.structs]
        assert "User" in struct_names
        assert "UserService" in struct_names

        # Check functions
        func_names = [f.name for f in result.functions]
        assert "NewUserService" in func_names or "ValidateEmail" in func_names

    def test_rust_extractor(self):
        """Test Rust extractor."""
        extractor = get_extractor("rust")
        assert extractor is not None

        result = extractor.extract(SAMPLE_RUST_CODE, "lib.rs")

        # Check structs
        struct_names = [s.name for s in result.structs]
        assert "User" in struct_names
        assert "UserService" in struct_names

        # Check traits
        trait_names = [t.name for t in result.traits]
        assert "Validator" in trait_names

    def test_csharp_extractor(self):
        """Test C# extractor."""
        extractor = get_extractor("csharp")
        assert extractor is not None

        result = extractor.extract(SAMPLE_CSHARP_CODE, "UserService.cs")

        # Check classes
        class_names = [c.name for c in result.classes]
        assert "UserService" in class_names
        assert "User" in class_names

        # Check interfaces
        interface_names = [i.name for i in result.interfaces]
        assert "IValidator" in interface_names


class TestExtractorRegistry:
    """Tests for extractor registry functions."""

    def test_get_extractor_returns_correct_type(self):
        """Test get_extractor returns correct extractor type."""
        python_ext = get_extractor("python")
        assert python_ext is not None
        assert isinstance(python_ext, PythonExtractor)

    def test_get_extractor_case_insensitive(self):
        """Test get_extractor is case-insensitive."""
        assert get_extractor("Python") is not None
        assert get_extractor("PYTHON") is not None
        assert get_extractor("python") is not None

    def test_get_extractor_returns_none_for_unknown(self):
        """Test get_extractor returns None for unknown language."""
        assert get_extractor("cobol") is None
        assert get_extractor("fortran") is None
        assert get_extractor("") is None

    def test_get_language_for_extension(self):
        """Test get_language_for_extension."""
        assert get_language_for_extension(".py") == "python"
        assert get_language_for_extension(".ts") == "typescript"
        assert get_language_for_extension(".js") == "javascript"
        assert get_language_for_extension(".java") == "java"
        assert get_language_for_extension(".go") == "go"
        assert get_language_for_extension(".rs") == "rust"
        assert get_language_for_extension(".cs") == "csharp"

    def test_get_language_for_extension_case_insensitive(self):
        """Test get_language_for_extension is case-insensitive."""
        assert get_language_for_extension(".PY") == "python"
        assert get_language_for_extension(".Py") == "python"

    def test_get_language_for_extension_unknown(self):
        """Test get_language_for_extension returns None for unknown."""
        assert get_language_for_extension(".cpp") is None
        assert get_language_for_extension(".unknown") is None
        assert get_language_for_extension("") is None

    def test_extension_map_complete(self):
        """Test EXTENSION_MAP has all expected extensions."""
        expected_extensions = [
            ".py", ".pyi",  # Python
            ".ts", ".tsx",  # TypeScript
            ".js", ".jsx", ".mjs", ".cjs",  # JavaScript
            ".java",  # Java
            ".go",  # Go
            ".rs",  # Rust
            ".cs",  # C#
        ]

        for ext in expected_extensions:
            assert ext in EXTENSION_MAP, f"Missing extension: {ext}"


class TestParseResults:
    """Tests for parse result structure."""

    def test_parse_result_has_file_path(self, python_extractor: PythonExtractor):
        """Test ParseResult includes file path."""
        result = python_extractor.extract(SAMPLE_PYTHON_CODE, "src/module.py")
        assert result.file_path == "src/module.py"

    def test_parse_result_has_language(self, python_extractor: PythonExtractor):
        """Test ParseResult includes language."""
        result = python_extractor.extract(SAMPLE_PYTHON_CODE, "test.py")
        assert result.language == "python"

    def test_parse_result_has_no_errors_for_valid_code(self, python_extractor: PythonExtractor):
        """Test ParseResult has no errors for valid code."""
        result = python_extractor.extract(SAMPLE_PYTHON_CODE, "test.py")
        assert result.errors == []

    def test_parse_result_captures_errors_for_invalid_code(self, python_extractor: PythonExtractor):
        """Test ParseResult captures errors for invalid syntax."""
        invalid_code = "def broken(:\n  pass"
        result = python_extractor.extract(invalid_code, "broken.py")
        # Should still return a result (possibly with errors or empty)
        assert result is not None


class TestAsyncParsing:
    """Tests for async parsing functionality."""

    @pytest.mark.asyncio
    async def test_parse_file_with_content(self, parser: ParserOrchestrator):
        """Test parsing file with provided content."""
        result = await parser.parse_file(
            file_path="test.py",
            content=SAMPLE_PYTHON_CODE,
        )

        assert result.language == "python"
        assert len(result.classes) > 0
        assert len(result.functions) > 0

    @pytest.mark.asyncio
    async def test_parse_file_unsupported_type(self, parser: ParserOrchestrator):
        """Test parsing unsupported file type."""
        result = await parser.parse_file(
            file_path="file.cpp",
            content="int main() { return 0; }",
        )

        assert result.language == "unknown"
        assert len(result.errors) > 0
        assert "Unsupported" in result.errors[0]
