"""Code element models for parser output."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ImportInfo:
    """Information about an import statement.

    Frozen dataclass for immutable import information extracted by parsers.
    """

    module: str
    """Module or package being imported."""

    name: str | None = None
    """Specific name imported (for 'from x import y')."""

    alias: str | None = None
    """Import alias (for 'import x as y')."""

    line: int = 0
    """Line number of the import statement."""

    is_relative: bool = False
    """Whether this is a relative import."""

    def __str__(self) -> str:
        """Return string representation of the import."""
        if self.name:
            base = f"from {self.module} import {self.name}"
        else:
            base = f"import {self.module}"
        if self.alias:
            base += f" as {self.alias}"
        return base


@dataclass(frozen=True)
class CallInfo:
    """Information about a function/method call.

    Frozen dataclass for immutable call information extracted by parsers.
    """

    name: str
    """Name of the called function/method."""

    line: int
    """Line number of the call."""

    column: int = 0
    """Column number of the call."""

    receiver: str | None = None
    """Object the method is called on (for method calls)."""

    arguments: tuple[str, ...] = field(default_factory=tuple)
    """String representations of arguments."""

    is_method_call: bool = False
    """Whether this is a method call (has receiver)."""

    def __str__(self) -> str:
        """Return string representation of the call."""
        args = ", ".join(self.arguments)
        if self.receiver:
            return f"{self.receiver}.{self.name}({args})"
        return f"{self.name}({args})"

    @property
    def qualified_name(self) -> str:
        """Return qualified name including receiver if present."""
        if self.receiver:
            return f"{self.receiver}.{self.name}"
        return self.name


@dataclass(frozen=True)
class ParameterInfo:
    """Information about a function parameter."""

    name: str
    """Parameter name."""

    type_annotation: str | None = None
    """Type annotation if present."""

    default_value: str | None = None
    """Default value if present."""

    is_variadic: bool = False
    """Whether this is a variadic parameter (*args, **kwargs)."""

    is_keyword_only: bool = False
    """Whether this is a keyword-only parameter."""


@dataclass(frozen=True)
class FunctionInfo:
    """Information about a function or method definition.

    Frozen dataclass for immutable function information extracted by parsers.
    """

    name: str
    """Function or method name."""

    signature: str
    """Full signature including parameters and return type."""

    file_path: str
    """Source file path (relative to project root)."""

    start_line: int
    """Starting line number (1-indexed)."""

    end_line: int
    """Ending line number (1-indexed)."""

    docstring: str | None = None
    """Documentation string if present."""

    parameters: tuple[ParameterInfo, ...] = field(default_factory=tuple)
    """Function parameters."""

    return_type: str | None = None
    """Return type annotation if present."""

    decorators: tuple[str, ...] = field(default_factory=tuple)
    """Decorator names applied to this function."""

    is_async: bool = False
    """Whether this is an async function."""

    is_method: bool = False
    """Whether this is a class method."""

    is_static: bool = False
    """Whether this is a static method."""

    is_classmethod: bool = False
    """Whether this is a class method (@classmethod)."""

    is_property: bool = False
    """Whether this is a property."""

    containing_class: str | None = None
    """Name of containing class (if method)."""

    calls: tuple[CallInfo, ...] = field(default_factory=tuple)
    """Function calls made within this function."""

    def __str__(self) -> str:
        """Return string representation."""
        prefix = "async " if self.is_async else ""
        return f"{prefix}def {self.signature}"

    @property
    def line_count(self) -> int:
        """Return number of lines in the function."""
        return self.end_line - self.start_line + 1

    @property
    def qualified_name(self) -> str:
        """Return fully qualified name including class if applicable."""
        if self.containing_class:
            return f"{self.containing_class}.{self.name}"
        return self.name


@dataclass(frozen=True)
class ClassInfo:
    """Information about a class definition.

    Frozen dataclass for immutable class information extracted by parsers.
    """

    name: str
    """Class name."""

    file_path: str
    """Source file path (relative to project root)."""

    start_line: int
    """Starting line number (1-indexed)."""

    end_line: int
    """Ending line number (1-indexed)."""

    docstring: str | None = None
    """Documentation string if present."""

    bases: tuple[str, ...] = field(default_factory=tuple)
    """Base class names."""

    decorators: tuple[str, ...] = field(default_factory=tuple)
    """Decorator names applied to this class."""

    methods: tuple[FunctionInfo, ...] = field(default_factory=tuple)
    """Methods defined in this class."""

    class_variables: tuple[tuple[str, str | None], ...] = field(default_factory=tuple)
    """Class variables as (name, type_annotation) tuples."""

    instance_variables: tuple[tuple[str, str | None], ...] = field(default_factory=tuple)
    """Instance variables as (name, type_annotation) tuples."""

    is_dataclass: bool = False
    """Whether this is a dataclass."""

    is_abstract: bool = False
    """Whether this is an abstract base class."""

    def __str__(self) -> str:
        """Return string representation."""
        bases_str = f"({', '.join(self.bases)})" if self.bases else ""
        return f"class {self.name}{bases_str}"

    @property
    def line_count(self) -> int:
        """Return number of lines in the class."""
        return self.end_line - self.start_line + 1

    @property
    def method_names(self) -> list[str]:
        """Return list of method names."""
        return [m.name for m in self.methods]


@dataclass
class ParseResult:
    """Result of parsing a source file.

    Mutable dataclass to allow incremental population during parsing.
    """

    file_path: str
    """Source file path (relative to project root)."""

    language: str
    """Programming language."""

    functions: list[FunctionInfo] = field(default_factory=list)
    """Top-level functions found in the file."""

    classes: list[ClassInfo] = field(default_factory=list)
    """Classes found in the file."""

    imports: list[ImportInfo] = field(default_factory=list)
    """Import statements found in the file."""

    calls: list[CallInfo] = field(default_factory=list)
    """Function/method calls found in the file."""

    module_docstring: str | None = None
    """Module-level docstring if present."""

    errors: list[str] = field(default_factory=list)
    """Parsing errors encountered."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional parser-specific metadata."""

    @property
    def all_functions(self) -> list[FunctionInfo]:
        """Return all functions including methods."""
        result = list(self.functions)
        for cls in self.classes:
            result.extend(cls.methods)
        return result

    @property
    def function_count(self) -> int:
        """Return total number of functions (including methods)."""
        return len(self.all_functions)

    @property
    def class_count(self) -> int:
        """Return number of classes."""
        return len(self.classes)

    @property
    def import_count(self) -> int:
        """Return number of imports."""
        return len(self.imports)

    @property
    def interfaces(self) -> list[ClassInfo]:
        """Return classes that are interfaces (is_abstract=True and no concrete methods)."""
        return [c for c in self.classes if c.is_abstract]

    @property
    def structs(self) -> list[ClassInfo]:
        """Return classes that are structs (not abstract)."""
        return [c for c in self.classes if not c.is_abstract]

    @property
    def traits(self) -> list[ClassInfo]:
        """Return classes that are traits (same as interfaces for Rust)."""
        return self.interfaces
