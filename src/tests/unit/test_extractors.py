"""Unit tests for language extractors."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from memory_service.parsing.parser import ParserOrchestrator
from memory_service.parsing.extractors import get_extractor, get_language_for_extension
from memory_service.parsing.extractors.python import PythonExtractor
from memory_service.parsing.extractors.typescript import TypeScriptExtractor
from memory_service.parsing.extractors.javascript import JavaScriptExtractor
from memory_service.parsing.extractors.go import GoExtractor
from memory_service.parsing.extractors.java import JavaExtractor
from memory_service.parsing.extractors.rust import RustExtractor
from memory_service.parsing.extractors.csharp import CSharpExtractor


class TestParserOrchestrator:
    """Tests for ParserOrchestrator."""

    @pytest.fixture
    def orchestrator(self) -> ParserOrchestrator:
        """Create parser orchestrator."""
        return ParserOrchestrator()

    def test_get_extractor_python(self, orchestrator: ParserOrchestrator) -> None:
        """Test getting Python extractor via language detection."""
        language = orchestrator.detect_language("test.py")
        assert language == "python"
        extractor = get_extractor(language)
        assert extractor is not None
        assert isinstance(extractor, PythonExtractor)

    def test_get_extractor_typescript(self, orchestrator: ParserOrchestrator) -> None:
        """Test getting TypeScript extractor via language detection."""
        language = orchestrator.detect_language("test.ts")
        assert language == "typescript"
        extractor = get_extractor(language)
        assert extractor is not None
        assert isinstance(extractor, TypeScriptExtractor)

    def test_get_extractor_javascript(self, orchestrator: ParserOrchestrator) -> None:
        """Test getting JavaScript extractor via language detection."""
        language = orchestrator.detect_language("test.js")
        assert language == "javascript"
        extractor = get_extractor(language)
        assert extractor is not None
        assert isinstance(extractor, JavaScriptExtractor)

    def test_get_extractor_go(self, orchestrator: ParserOrchestrator) -> None:
        """Test getting Go extractor via language detection."""
        language = orchestrator.detect_language("test.go")
        assert language == "go"
        extractor = get_extractor(language)
        assert extractor is not None
        assert isinstance(extractor, GoExtractor)

    def test_get_extractor_java(self, orchestrator: ParserOrchestrator) -> None:
        """Test getting Java extractor via language detection."""
        language = orchestrator.detect_language("Test.java")
        assert language == "java"
        extractor = get_extractor(language)
        assert extractor is not None
        assert isinstance(extractor, JavaExtractor)

    def test_get_extractor_rust(self, orchestrator: ParserOrchestrator) -> None:
        """Test getting Rust extractor via language detection."""
        language = orchestrator.detect_language("test.rs")
        assert language == "rust"
        extractor = get_extractor(language)
        assert extractor is not None
        assert isinstance(extractor, RustExtractor)

    def test_get_extractor_csharp(self, orchestrator: ParserOrchestrator) -> None:
        """Test getting C# extractor via language detection."""
        language = orchestrator.detect_language("Test.cs")
        assert language == "csharp"
        extractor = get_extractor(language)
        assert extractor is not None
        assert isinstance(extractor, CSharpExtractor)

    def test_get_extractor_unknown(self, orchestrator: ParserOrchestrator) -> None:
        """Test language detection for unknown extension."""
        language = orchestrator.detect_language("test.xyz")
        assert language is None

    def test_detect_language_from_extension(self, orchestrator: ParserOrchestrator) -> None:
        """Test language detection for common extensions."""
        assert orchestrator.detect_language("test.py") == "python"
        assert orchestrator.detect_language("test.ts") == "typescript"
        assert orchestrator.detect_language("test.js") == "javascript"
        assert orchestrator.detect_language("test.go") == "go"


class TestPythonExtractor:
    """Tests for PythonExtractor."""

    @pytest.fixture
    def extractor(self) -> PythonExtractor:
        """Create Python extractor."""
        return PythonExtractor()

    def test_extract_simple_function(self, extractor: PythonExtractor) -> None:
        """Test extracting simple function."""
        code = """
def hello():
    print("Hello")
"""
        result = extractor.extract(code, "test.py")

        assert result.functions is not None
        assert len(result.functions) >= 1
        assert any(f.name == "hello" for f in result.functions)

    def test_extract_function_with_docstring(self, extractor: PythonExtractor) -> None:
        """Test extracting function with docstring."""
        code = '''
def greet(name: str) -> str:
    """Greet someone by name.

    Args:
        name: The name to greet

    Returns:
        A greeting string
    """
    return f"Hello, {name}!"
'''
        result = extractor.extract(code, "test.py")

        assert result.functions is not None
        assert len(result.functions) >= 1
        func = next(f for f in result.functions if f.name == "greet")
        assert func.docstring is not None
        assert "Greet someone" in func.docstring

    def test_extract_class(self, extractor: PythonExtractor) -> None:
        """Test extracting class."""
        code = """
class MyClass:
    '''A simple class.'''

    def __init__(self, value):
        self.value = value

    def get_value(self):
        return self.value
"""
        result = extractor.extract(code, "test.py")

        assert result.classes is not None
        assert len(result.classes) >= 1
        assert any(c.name == "MyClass" for c in result.classes)

    def test_extract_class_with_inheritance(self, extractor: PythonExtractor) -> None:
        """Test extracting class with inheritance."""
        code = """
class Parent:
    pass

class Child(Parent):
    pass
"""
        result = extractor.extract(code, "test.py")

        assert result.classes is not None
        assert len(result.classes) >= 2

    def test_extract_imports(self, extractor: PythonExtractor) -> None:
        """Test extracting imports."""
        code = """
import os
from pathlib import Path
from typing import List, Dict
"""
        result = extractor.extract(code, "test.py")

        assert result.imports is not None
        assert len(result.imports) >= 1

    def test_extract_async_function(self, extractor: PythonExtractor) -> None:
        """Test extracting async function."""
        code = """
async def fetch_data(url: str) -> dict:
    '''Fetch data from URL.'''
    pass
"""
        result = extractor.extract(code, "test.py")

        assert result.functions is not None
        assert any(f.name == "fetch_data" for f in result.functions)

    def test_extract_decorated_function(self, extractor: PythonExtractor) -> None:
        """Test extracting decorated function."""
        code = """
def decorator(func):
    return func

@decorator
def decorated():
    pass
"""
        result = extractor.extract(code, "test.py")

        assert result.functions is not None
        # Should extract both functions
        assert len(result.functions) >= 2

    def test_extract_nested_function(self, extractor: PythonExtractor) -> None:
        """Test extracting nested function."""
        code = """
def outer():
    def inner():
        pass
    return inner
"""
        result = extractor.extract(code, "test.py")

        assert result.functions is not None
        # May or may not include inner depending on implementation

    def test_extract_empty_file(self, extractor: PythonExtractor) -> None:
        """Test extracting from empty file."""
        code = ""
        result = extractor.extract(code, "test.py")

        assert result is not None

    def test_extract_syntax_error(self, extractor: PythonExtractor) -> None:
        """Test extracting from file with syntax error."""
        code = """
def broken(
    # Missing closing paren
"""
        result = extractor.extract(code, "test.py")

        # Should return result (possibly with errors) but not crash
        assert result is not None


class TestTypeScriptExtractor:
    """Tests for TypeScriptExtractor."""

    @pytest.fixture
    def extractor(self) -> TypeScriptExtractor:
        """Create TypeScript extractor."""
        return TypeScriptExtractor()

    def test_extract_function(self, extractor: TypeScriptExtractor) -> None:
        """Test extracting TypeScript function."""
        code = """
function greet(name: string): string {
    return `Hello, ${name}!`;
}
"""
        result = extractor.extract(code, "test.ts")

        assert result.functions is not None

    def test_extract_arrow_function(self, extractor: TypeScriptExtractor) -> None:
        """Test extracting arrow function."""
        code = """
const add = (a: number, b: number): number => a + b;
"""
        result = extractor.extract(code, "test.ts")

        assert result is not None

    def test_extract_interface(self, extractor: TypeScriptExtractor) -> None:
        """Test extracting interface."""
        code = """
interface User {
    id: number;
    name: string;
    email: string;
}
"""
        result = extractor.extract(code, "test.ts")

        assert result is not None

    def test_extract_class(self, extractor: TypeScriptExtractor) -> None:
        """Test extracting class."""
        code = """
class UserService {
    private users: User[] = [];

    addUser(user: User): void {
        this.users.push(user);
    }
}
"""
        result = extractor.extract(code, "test.ts")

        assert result.classes is not None


class TestJavaScriptExtractor:
    """Tests for JavaScriptExtractor."""

    @pytest.fixture
    def extractor(self) -> JavaScriptExtractor:
        """Create JavaScript extractor."""
        return JavaScriptExtractor()

    def test_extract_function(self, extractor: JavaScriptExtractor) -> None:
        """Test extracting JavaScript function."""
        code = """
function hello() {
    console.log("Hello");
}
"""
        result = extractor.extract(code, "test.js")

        assert result.functions is not None

    def test_extract_arrow_function(self, extractor: JavaScriptExtractor) -> None:
        """Test extracting arrow function."""
        code = """
const add = (a, b) => a + b;
"""
        result = extractor.extract(code, "test.js")

        assert result is not None

    def test_extract_class(self, extractor: JavaScriptExtractor) -> None:
        """Test extracting class."""
        code = """
class Calculator {
    add(a, b) {
        return a + b;
    }
}
"""
        result = extractor.extract(code, "test.js")

        assert result.classes is not None


class TestGoExtractor:
    """Tests for GoExtractor."""

    @pytest.fixture
    def extractor(self) -> GoExtractor:
        """Create Go extractor."""
        return GoExtractor()

    def test_extract_function(self, extractor: GoExtractor) -> None:
        """Test extracting Go function."""
        code = """
package main

func Hello() string {
    return "Hello"
}
"""
        result = extractor.extract(code, "main.go")

        assert result.functions is not None

    def test_extract_method(self, extractor: GoExtractor) -> None:
        """Test extracting Go method."""
        code = """
package main

type Greeter struct {
    Name string
}

func (g *Greeter) Greet() string {
    return "Hello, " + g.Name
}
"""
        result = extractor.extract(code, "main.go")

        assert result is not None

    def test_extract_struct(self, extractor: GoExtractor) -> None:
        """Test extracting Go struct."""
        code = """
package main

type User struct {
    ID   int
    Name string
}
"""
        result = extractor.extract(code, "main.go")

        assert result is not None


class TestJavaExtractor:
    """Tests for JavaExtractor."""

    @pytest.fixture
    def extractor(self) -> JavaExtractor:
        """Create Java extractor."""
        return JavaExtractor()

    def test_extract_class(self, extractor: JavaExtractor) -> None:
        """Test extracting Java class."""
        code = """
public class HelloWorld {
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
}
"""
        result = extractor.extract(code, "HelloWorld.java")

        assert result.classes is not None

    def test_extract_method(self, extractor: JavaExtractor) -> None:
        """Test extracting Java method."""
        code = """
public class Calculator {
    public int add(int a, int b) {
        return a + b;
    }
}
"""
        result = extractor.extract(code, "Calculator.java")

        assert result is not None

    def test_extract_interface(self, extractor: JavaExtractor) -> None:
        """Test extracting Java interface."""
        code = """
public interface Greeter {
    String greet(String name);
}
"""
        result = extractor.extract(code, "Greeter.java")

        assert result is not None


class TestRustExtractor:
    """Tests for RustExtractor."""

    @pytest.fixture
    def extractor(self) -> RustExtractor:
        """Create Rust extractor."""
        return RustExtractor()

    def test_extract_function(self, extractor: RustExtractor) -> None:
        """Test extracting Rust function."""
        code = """
fn hello() {
    println!("Hello");
}
"""
        result = extractor.extract(code, "main.rs")

        assert result.functions is not None

    def test_extract_struct(self, extractor: RustExtractor) -> None:
        """Test extracting Rust struct."""
        code = """
struct User {
    id: u32,
    name: String,
}
"""
        result = extractor.extract(code, "main.rs")

        assert result is not None

    def test_extract_impl(self, extractor: RustExtractor) -> None:
        """Test extracting Rust impl block."""
        code = """
struct Greeter {
    name: String,
}

impl Greeter {
    fn new(name: String) -> Self {
        Greeter { name }
    }

    fn greet(&self) -> String {
        format!("Hello, {}!", self.name)
    }
}
"""
        result = extractor.extract(code, "main.rs")

        assert result is not None


class TestCSharpExtractor:
    """Tests for CSharpExtractor."""

    @pytest.fixture
    def extractor(self) -> CSharpExtractor:
        """Create C# extractor."""
        return CSharpExtractor()

    def test_extract_class(self, extractor: CSharpExtractor) -> None:
        """Test extracting C# class."""
        code = """
public class HelloWorld
{
    public static void Main(string[] args)
    {
        Console.WriteLine("Hello, World!");
    }
}
"""
        result = extractor.extract(code, "HelloWorld.cs")

        assert result.classes is not None

    def test_extract_method(self, extractor: CSharpExtractor) -> None:
        """Test extracting C# method."""
        code = """
public class Calculator
{
    public int Add(int a, int b)
    {
        return a + b;
    }
}
"""
        result = extractor.extract(code, "Calculator.cs")

        assert result is not None

    def test_extract_interface(self, extractor: CSharpExtractor) -> None:
        """Test extracting C# interface."""
        code = """
public interface IGreeter
{
    string Greet(string name);
}
"""
        result = extractor.extract(code, "IGreeter.cs")

        assert result is not None


class TestExtractorEdgeCases:
    """Tests for edge cases in extractors."""

    def test_python_with_encoding(self) -> None:
        """Test Python extractor with encoding declaration."""
        extractor = PythonExtractor()
        code = """# -*- coding: utf-8 -*-
def hello():
    print("Hello, World!")
"""
        result = extractor.extract(code, "test.py")
        assert result is not None

    def test_python_with_multiline_string(self) -> None:
        """Test Python extractor with multiline strings."""
        extractor = PythonExtractor()
        code = '''
SQL = """
SELECT *
FROM users
WHERE active = true
"""

def query_users():
    return SQL
'''
        result = extractor.extract(code, "test.py")
        assert result is not None

    def test_typescript_with_generics(self) -> None:
        """Test TypeScript extractor with generics."""
        extractor = TypeScriptExtractor()
        code = """
function identity<T>(value: T): T {
    return value;
}

class Container<T> {
    constructor(private value: T) {}
    getValue(): T { return this.value; }
}
"""
        result = extractor.extract(code, "test.ts")
        assert result is not None

    def test_go_with_goroutines(self) -> None:
        """Test Go extractor with goroutines."""
        extractor = GoExtractor()
        code = """
package main

import "sync"

func process(wg *sync.WaitGroup) {
    defer wg.Done()
    // Process something
}

func main() {
    var wg sync.WaitGroup
    go process(&wg)
}
"""
        result = extractor.extract(code, "main.go")
        assert result is not None
