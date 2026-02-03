# Design Document: Shared Libraries

## Document Control

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Status | Draft |
| Sequence | 002 |
| Component | Library Layer |

---

## 1. Introduction

### 1.1 Purpose

This document defines the shared libraries for the Claude Code Long-Term Memory System. These libraries provide common models, utilities, parsing capabilities, and interfaces used across all components of the system.

### 1.2 Scope

**Included:**
- Data models (Pydantic schemas for all memory types)
- Utility functions (hashing, gitignore, logging)
- Code parsing (Tree-sitter orchestration, language extractors)
- Common interfaces and protocols

**Excluded:**
- Business logic (see 20-backend-design.md)
- API handlers (see 50-integration-design.md)
- Storage adapters (see 20-backend-design.md)

### 1.3 Requirements Traceability

| Requirement ID | Requirement Summary | Design Section |
|----------------|---------------------|----------------|
| REQ-MEM-FN-061 | Tree-sitter parsing | 5.2 |
| REQ-MEM-FN-063 | Multi-language support (7 languages) | 5.2 |
| REQ-MEM-FN-064 | Relationship extraction | 5.2.3 |
| REQ-MEM-INT-090 | File system reading | 4.4 |
| REQ-MEM-INT-091 | Gitignore respect | 4.3 |
| REQ-MEM-INT-092 | Change detection (SHA-256) | 4.2 |
| REQ-MEM-MAINT-001 | Type hints and docstrings | 13.1 |
| REQ-MEM-MAINT-005 | 80% test coverage | 12.1 |

---

## 2. Library Context

### 2.1 Library Overview

The shared libraries provide foundational capabilities used by all other layers:

```
+------------------+
|   API Layer      |  Uses: models, schemas
+------------------+
         |
+------------------+
|   Core Layer     |  Uses: models, utils, parsing
+------------------+
         |
+------------------+
|  Storage Layer   |  Uses: models
+------------------+
         |
+------------------+
|  Library Layer   |  models/, utils/, parsing/
+------------------+
```

### 2.2 Target Consumers

| Consumer Type | Use Cases | Integration Pattern |
|---------------|-----------|---------------------|
| MCP Tools | Input/output schema validation | Import Pydantic models |
| Memory Manager | Memory lifecycle operations | Import memory models |
| Indexer | Code parsing for indexing | Import parsing module |
| Query Engine | Result formatting | Import models |

### 2.3 External Dependencies

| Dependency | Version | Purpose | Optional |
|------------|---------|---------|----------|
| pydantic | >=2.0.0 | Data validation and serialization | No |
| tree-sitter | >=0.20.0 | Code parsing | No |
| tree-sitter-languages | >=1.8.0 | Pre-built language grammars | No |
| structlog | >=23.0.0 | Structured logging | No |
| pathspec | >=0.11.0 | Gitignore pattern matching | No |

---

## 3. Architectural Design

### 3.1 Architectural Overview

The library layer is organized into three modules:

```
memory_service/
    models/           # Data models and schemas
    utils/            # Shared utilities
    parsing/          # Code parsing
```

Each module is independently importable with no circular dependencies.

### 3.2 Design Principles

#### Immutability

**Definition:** Data models are immutable after creation where possible.

**Application:** Pydantic models use frozen=True for value objects.

#### Type Safety

**Definition:** All public interfaces have complete type annotations.

**Application:** mypy strict mode enforced, no Any types in public API.

#### Single Responsibility

**Definition:** Each module handles one concern.

**Application:** models = data, utils = helpers, parsing = code analysis.

### 3.3 Module Dependencies

```
models/
    base.py           # No internal dependencies
    memories.py       # Depends on base.py
    code_elements.py  # Depends on base.py
    relationships.py  # No internal dependencies
    schemas.py        # Depends on memories.py

utils/
    hashing.py        # No internal dependencies
    gitignore.py      # External: pathspec
    logging.py        # External: structlog

parsing/
    parser.py         # External: tree-sitter
    extractors/
        base.py       # Depends on models/code_elements.py
        python.py     # Depends on base.py
        ...           # Each extractor depends on base.py
```

---

## 4. Models Module

### 4.1 Module Structure

```
models/
    __init__.py       # Public exports
    base.py           # BaseMemory and common types
    memories.py       # Memory type models
    code_elements.py  # Function, Class, Import definitions
    relationships.py  # Relationship type definitions
    schemas.py        # Request/response schemas
```

### 4.2 Base Memory Model

```python
# models/base.py
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    """Memory type discriminator."""
    REQUIREMENTS = "requirements"
    DESIGN = "design"
    CODE_PATTERN = "code_pattern"
    COMPONENT = "component"
    FUNCTION = "function"
    TEST_HISTORY = "test_history"
    SESSION = "session"
    USER_PREFERENCE = "user_preference"


class SyncStatus(str, Enum):
    """Cross-store sync status."""
    SYNCED = "synced"
    PENDING = "pending"
    FAILED = "failed"


class BaseMemory(BaseModel):
    """Base memory model with common fields."""

    id: UUID = Field(default_factory=uuid4)
    type: MemoryType
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    access_count: int = 0
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    neo4j_node_id: Optional[str] = None
    sync_status: SyncStatus = SyncStatus.PENDING
    deleted: bool = False
    deleted_at: Optional[datetime] = None
    metadata: dict = Field(default_factory=dict)

    class Config:
        use_enum_values = True
```

### 4.3 Memory Type Models

```python
# models/memories.py
from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .base import BaseMemory, MemoryType


class Priority(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class RequirementStatus(str, Enum):
    DRAFT = "Draft"
    APPROVED = "Approved"
    IMPLEMENTED = "Implemented"
    VERIFIED = "Verified"


class RequirementsMemory(BaseMemory):
    """Requirements memory model."""

    type: MemoryType = MemoryType.REQUIREMENTS
    requirement_id: str  # Pattern: REQ-XXX-NNN
    title: str
    description: str
    priority: Priority
    status: RequirementStatus
    source_document: str
    implementing_components: List[UUID] = Field(default_factory=list)


class DesignType(str, Enum):
    ADR = "ADR"
    SPECIFICATION = "Specification"
    ARCHITECTURE = "Architecture"
    INTERFACE = "Interface"


class DesignStatus(str, Enum):
    PROPOSED = "Proposed"
    ACCEPTED = "Accepted"
    DEPRECATED = "Deprecated"
    SUPERSEDED = "Superseded"


class DesignMemory(BaseMemory):
    """Design memory model."""

    type: MemoryType = MemoryType.DESIGN
    design_type: DesignType
    title: str
    decision: Optional[str] = None
    rationale: Optional[str] = None
    consequences: Optional[str] = None
    related_requirements: List[str] = Field(default_factory=list)
    affected_components: List[UUID] = Field(default_factory=list)
    status: DesignStatus


class PatternType(str, Enum):
    TEMPLATE = "Template"
    CONVENTION = "Convention"
    IDIOM = "Idiom"
    ARCHITECTURE = "Architecture"


class CodePatternMemory(BaseMemory):
    """Code pattern memory model."""

    type: MemoryType = MemoryType.CODE_PATTERN
    pattern_name: str
    pattern_type: PatternType
    language: str
    code_template: str
    usage_context: str
    applicable_components: List[str] = Field(default_factory=list)
    example_implementations: List[str] = Field(default_factory=list)


class ComponentType(str, Enum):
    FRONTEND = "Frontend"
    BACKEND = "Backend"
    AGENT = "Agent"
    LIBRARY = "Library"
    SERVICE = "Service"
    DATABASE = "Database"


class ComponentMemory(BaseMemory):
    """Component registry memory model."""

    type: MemoryType = MemoryType.COMPONENT
    component_id: str
    component_type: ComponentType
    name: str
    file_path: str
    public_interface: Optional[dict] = None
    dependencies: List[str] = Field(default_factory=list)
    dependents: List[str] = Field(default_factory=list)
    base_pattern: Optional[UUID] = None
    version: Optional[str] = None


class FunctionMemory(BaseMemory):
    """Function index memory model."""

    type: MemoryType = MemoryType.FUNCTION
    function_id: UUID = Field(default_factory=uuid4)
    name: str
    signature: str
    file_path: str
    start_line: int
    end_line: int
    language: str
    docstring: Optional[str] = None
    containing_class: Optional[UUID] = None
    calls: List[UUID] = Field(default_factory=list)
    called_by: List[UUID] = Field(default_factory=list)


class TestStatus(str, Enum):
    PASSED = "Passed"
    FAILED = "Failed"
    SKIPPED = "Skipped"
    ERROR = "Error"


class TestHistoryMemory(BaseMemory):
    """Test history memory model."""

    type: MemoryType = MemoryType.TEST_HISTORY
    test_id: UUID = Field(default_factory=uuid4)
    test_name: str
    test_file: str
    execution_time: datetime
    status: TestStatus
    failure_message: Optional[str] = None
    affected_component: Optional[UUID] = None
    related_requirements: List[str] = Field(default_factory=list)
    fix_applied: Optional[str] = None
    fix_commit: Optional[str] = None
    design_alignment_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class SessionMemory(BaseMemory):
    """Session history memory model."""

    type: MemoryType = MemoryType.SESSION
    session_id: UUID = Field(default_factory=uuid4)
    start_time: datetime
    end_time: Optional[datetime] = None
    summary: str
    key_decisions: List[str] = Field(default_factory=list)
    components_modified: List[UUID] = Field(default_factory=list)
    memories_created: List[UUID] = Field(default_factory=list)
    outcome: Optional[str] = None


class PreferenceCategory(str, Enum):
    CODING_STYLE = "CodingStyle"
    NAMING = "Naming"
    FRAMEWORK = "Framework"
    TOOL = "Tool"
    CONVENTION = "Convention"


class PreferenceScope(str, Enum):
    GLOBAL = "Global"
    LANGUAGE = "Language"
    PROJECT = "Project"
    COMPONENT = "Component"


class UserPreferenceMemory(BaseMemory):
    """User preference memory model."""

    type: MemoryType = MemoryType.USER_PREFERENCE
    preference_id: UUID = Field(default_factory=uuid4)
    category: PreferenceCategory
    key: str
    value: dict
    scope: PreferenceScope
    examples: List[str] = Field(default_factory=list)
```

### 4.4 Code Element Models

```python
# models/code_elements.py
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class ParameterInfo:
    """Function parameter information."""
    name: str
    type_hint: Optional[str] = None
    default: Optional[str] = None


@dataclass(frozen=True)
class FunctionInfo:
    """Extracted function information."""
    name: str
    signature: str
    docstring: Optional[str]
    start_line: int
    end_line: int
    body: str
    containing_class: Optional[str]
    decorators: List[str]
    parameters: List[ParameterInfo]


@dataclass(frozen=True)
class ClassInfo:
    """Extracted class information."""
    name: str
    docstring: Optional[str]
    start_line: int
    end_line: int
    base_classes: List[str]
    interfaces: List[str]
    methods: List[str]
    attributes: List[str]


@dataclass(frozen=True)
class ImportInfo:
    """Extracted import information."""
    module: str
    items: List[str]  # Specific imports, empty for module import
    alias: Optional[str]
    is_relative: bool


@dataclass(frozen=True)
class CallInfo:
    """Extracted call information."""
    caller: str  # Function/method name
    callee: str  # Called function/method
    line: int
    is_method_call: bool
```

### 4.5 Relationship Models

```python
# models/relationships.py
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RelationshipType(str, Enum):
    CALLS = "CALLS"
    IMPORTS = "IMPORTS"
    EXTENDS = "EXTENDS"
    IMPLEMENTS = "IMPLEMENTS"
    CONTAINS = "CONTAINS"
    DEPENDS_ON = "DEPENDS_ON"
    IMPLEMENTS_REQ = "IMPLEMENTS_REQ"
    FOLLOWS_DESIGN = "FOLLOWS_DESIGN"
    USES_PATTERN = "USES_PATTERN"
    TESTS = "TESTS"


class Relationship(BaseModel):
    """Graph relationship model."""

    type: RelationshipType
    from_id: str
    to_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)
```

---

## 5. Parsing Module

### 5.1 Module Structure

```
parsing/
    __init__.py
    parser.py           # ParserOrchestrator
    extractors/
        __init__.py
        base.py         # LanguageExtractor protocol
        python.py
        typescript.py
        javascript.py
        java.py
        go.py
        rust.py
        csharp.py
```

### 5.2 Parser Orchestrator

```python
# parsing/parser.py
from pathlib import Path
from typing import Optional, Tuple

import tree_sitter_languages

from ..models.code_elements import FunctionInfo, ClassInfo, ImportInfo, CallInfo
from .extractors import get_extractor


# File extension to language mapping
EXTENSION_MAP = {
    '.py': 'python',
    '.ts': 'typescript',
    '.tsx': 'typescript',
    '.js': 'javascript',
    '.jsx': 'javascript',
    '.java': 'java',
    '.go': 'go',
    '.rs': 'rust',
    '.cs': 'csharp',
}


class ParserOrchestrator:
    """Orchestrates code parsing across languages."""

    def __init__(self):
        self._parsers = {}  # Lazy-loaded parsers

    def detect_language(self, file_path: str) -> Optional[str]:
        """Detect language from file extension."""
        ext = Path(file_path).suffix.lower()
        return EXTENSION_MAP.get(ext)

    def _get_parser(self, language: str):
        """Get or create parser for language."""
        if language not in self._parsers:
            self._parsers[language] = tree_sitter_languages.get_parser(language)
        return self._parsers[language]

    def parse_file(self, file_path: str, content: str) -> Optional[Tuple[
        list[FunctionInfo],
        list[ClassInfo],
        list[ImportInfo],
        list[CallInfo]
    ]]:
        """Parse file and extract code elements."""
        language = self.detect_language(file_path)
        if not language:
            return None

        parser = self._get_parser(language)
        tree = parser.parse(content.encode('utf-8'))

        extractor = get_extractor(language)
        if not extractor:
            return None

        functions = extractor.extract_functions(tree, content)
        classes = extractor.extract_classes(tree, content)
        imports = extractor.extract_imports(tree, content)
        calls = extractor.extract_calls(tree, content)

        return functions, classes, imports, calls

    def supports_language(self, language: str) -> bool:
        """Check if language is supported."""
        return language in EXTENSION_MAP.values()
```

### 5.2.1 Language Extractor Protocol

```python
# parsing/extractors/base.py
from typing import List, Protocol

from tree_sitter import Tree

from ...models.code_elements import FunctionInfo, ClassInfo, ImportInfo, CallInfo


class LanguageExtractor(Protocol):
    """Protocol for language-specific extractors."""

    def extract_functions(self, tree: Tree, source: str) -> List[FunctionInfo]:
        """Extract function definitions from AST."""
        ...

    def extract_classes(self, tree: Tree, source: str) -> List[ClassInfo]:
        """Extract class definitions from AST."""
        ...

    def extract_imports(self, tree: Tree, source: str) -> List[ImportInfo]:
        """Extract import statements from AST."""
        ...

    def extract_calls(self, tree: Tree, source: str) -> List[CallInfo]:
        """Extract function calls from AST."""
        ...
```

### 5.2.2 Python Extractor

```python
# parsing/extractors/python.py
from typing import List, Optional

from tree_sitter import Node, Tree

from ...models.code_elements import (
    FunctionInfo, ClassInfo, ImportInfo, CallInfo, ParameterInfo
)


class PythonExtractor:
    """Python-specific code extractor."""

    def extract_functions(self, tree: Tree, source: str) -> List[FunctionInfo]:
        """Extract function definitions."""
        functions = []

        def visit(node: Node, containing_class: Optional[str] = None):
            if node.type == 'function_definition':
                functions.append(self._extract_function(node, source, containing_class))
            elif node.type == 'class_definition':
                class_name = self._get_name(node)
                for child in node.children:
                    visit(child, class_name)
            else:
                for child in node.children:
                    visit(child, containing_class)

        visit(tree.root_node)
        return functions

    def _extract_function(
        self,
        node: Node,
        source: str,
        containing_class: Optional[str]
    ) -> FunctionInfo:
        """Extract function information from node."""
        name = self._get_name(node)
        signature = self._get_signature(node, source)
        docstring = self._get_docstring(node, source)
        decorators = self._get_decorators(node, source)
        parameters = self._get_parameters(node, source)
        body = source[node.start_byte:node.end_byte]

        return FunctionInfo(
            name=name,
            signature=signature,
            docstring=docstring,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            body=body,
            containing_class=containing_class,
            decorators=decorators,
            parameters=parameters,
        )

    def _get_name(self, node: Node) -> str:
        """Get function or class name."""
        for child in node.children:
            if child.type == 'identifier':
                return child.text.decode('utf-8')
        return ""

    def _get_signature(self, node: Node, source: str) -> str:
        """Get function signature."""
        for child in node.children:
            if child.type == 'parameters':
                params = source[child.start_byte:child.end_byte]
                return f"def {self._get_name(node)}{params}"
        return f"def {self._get_name(node)}()"

    def _get_docstring(self, node: Node, source: str) -> Optional[str]:
        """Extract docstring if present."""
        for child in node.children:
            if child.type == 'block':
                for block_child in child.children:
                    if block_child.type == 'expression_statement':
                        expr = block_child.children[0] if block_child.children else None
                        if expr and expr.type == 'string':
                            return expr.text.decode('utf-8').strip('"""\'\'\'')
        return None

    def _get_decorators(self, node: Node, source: str) -> List[str]:
        """Extract decorator names."""
        decorators = []
        # Find decorators in siblings before the function
        parent = node.parent
        if parent:
            for sibling in parent.children:
                if sibling.type == 'decorator' and sibling.end_point[0] < node.start_point[0]:
                    decorators.append(source[sibling.start_byte:sibling.end_byte])
        return decorators

    def _get_parameters(self, node: Node, source: str) -> List[ParameterInfo]:
        """Extract parameter information."""
        parameters = []
        for child in node.children:
            if child.type == 'parameters':
                for param in child.children:
                    if param.type in ('identifier', 'typed_parameter', 'default_parameter'):
                        parameters.append(self._extract_parameter(param, source))
        return parameters

    def _extract_parameter(self, node: Node, source: str) -> ParameterInfo:
        """Extract single parameter information."""
        name = ""
        type_hint = None
        default = None

        if node.type == 'identifier':
            name = node.text.decode('utf-8')
        elif node.type == 'typed_parameter':
            for child in node.children:
                if child.type == 'identifier':
                    name = child.text.decode('utf-8')
                elif child.type == 'type':
                    type_hint = source[child.start_byte:child.end_byte]
        elif node.type == 'default_parameter':
            for child in node.children:
                if child.type == 'identifier':
                    name = child.text.decode('utf-8')
                elif child.type != '=':
                    default = source[child.start_byte:child.end_byte]

        return ParameterInfo(name=name, type_hint=type_hint, default=default)

    def extract_classes(self, tree: Tree, source: str) -> List[ClassInfo]:
        """Extract class definitions."""
        classes = []

        def visit(node: Node):
            if node.type == 'class_definition':
                classes.append(self._extract_class(node, source))
            for child in node.children:
                visit(child)

        visit(tree.root_node)
        return classes

    def _extract_class(self, node: Node, source: str) -> ClassInfo:
        """Extract class information from node."""
        name = self._get_name(node)
        docstring = self._get_class_docstring(node, source)
        base_classes = self._get_base_classes(node, source)
        methods = self._get_method_names(node)
        attributes = self._get_attributes(node, source)

        return ClassInfo(
            name=name,
            docstring=docstring,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            base_classes=base_classes,
            interfaces=[],  # Python doesn't have explicit interfaces
            methods=methods,
            attributes=attributes,
        )

    def _get_class_docstring(self, node: Node, source: str) -> Optional[str]:
        """Extract class docstring."""
        for child in node.children:
            if child.type == 'block':
                for block_child in child.children:
                    if block_child.type == 'expression_statement':
                        expr = block_child.children[0] if block_child.children else None
                        if expr and expr.type == 'string':
                            return expr.text.decode('utf-8').strip('"""\'\'\'')
        return None

    def _get_base_classes(self, node: Node, source: str) -> List[str]:
        """Extract base class names."""
        bases = []
        for child in node.children:
            if child.type == 'argument_list':
                for arg in child.children:
                    if arg.type == 'identifier':
                        bases.append(arg.text.decode('utf-8'))
        return bases

    def _get_method_names(self, node: Node) -> List[str]:
        """Get method names in class."""
        methods = []
        for child in node.children:
            if child.type == 'block':
                for block_child in child.children:
                    if block_child.type == 'function_definition':
                        methods.append(self._get_name(block_child))
        return methods

    def _get_attributes(self, node: Node, source: str) -> List[str]:
        """Extract class attributes from __init__."""
        attributes = []
        for child in node.children:
            if child.type == 'block':
                for block_child in child.children:
                    if block_child.type == 'function_definition':
                        if self._get_name(block_child) == '__init__':
                            attributes.extend(self._extract_init_attributes(block_child, source))
        return attributes

    def _extract_init_attributes(self, node: Node, source: str) -> List[str]:
        """Extract self.x = ... assignments from __init__."""
        attributes = []

        def visit(n: Node):
            if n.type == 'assignment':
                left = n.children[0] if n.children else None
                if left and left.type == 'attribute':
                    # Check if it's self.something
                    obj = left.children[0] if left.children else None
                    if obj and obj.text.decode('utf-8') == 'self':
                        attr = left.children[2] if len(left.children) > 2 else None
                        if attr:
                            attributes.append(attr.text.decode('utf-8'))
            for child in n.children:
                visit(child)

        visit(node)
        return attributes

    def extract_imports(self, tree: Tree, source: str) -> List[ImportInfo]:
        """Extract import statements."""
        imports = []

        def visit(node: Node):
            if node.type == 'import_statement':
                imports.append(self._extract_import(node, source))
            elif node.type == 'import_from_statement':
                imports.append(self._extract_from_import(node, source))
            for child in node.children:
                visit(child)

        visit(tree.root_node)
        return imports

    def _extract_import(self, node: Node, source: str) -> ImportInfo:
        """Extract simple import statement."""
        module = ""
        alias = None

        for child in node.children:
            if child.type == 'dotted_name':
                module = child.text.decode('utf-8')
            elif child.type == 'aliased_import':
                for ac in child.children:
                    if ac.type == 'dotted_name':
                        module = ac.text.decode('utf-8')
                    elif ac.type == 'identifier':
                        alias = ac.text.decode('utf-8')

        return ImportInfo(
            module=module,
            items=[],
            alias=alias,
            is_relative=False,
        )

    def _extract_from_import(self, node: Node, source: str) -> ImportInfo:
        """Extract from ... import statement."""
        module = ""
        items = []
        is_relative = False

        for child in node.children:
            if child.type == 'dotted_name':
                module = child.text.decode('utf-8')
            elif child.type == 'relative_import':
                is_relative = True
                for rc in child.children:
                    if rc.type == 'dotted_name':
                        module = rc.text.decode('utf-8')
            elif child.type == 'identifier':
                items.append(child.text.decode('utf-8'))
            elif child.type == 'aliased_import':
                for ac in child.children:
                    if ac.type == 'identifier':
                        items.append(ac.text.decode('utf-8'))
                        break

        return ImportInfo(
            module=module,
            items=items,
            alias=None,
            is_relative=is_relative,
        )

    def extract_calls(self, tree: Tree, source: str) -> List[CallInfo]:
        """Extract function calls."""
        calls = []
        current_function = [None]  # Use list for closure

        def visit(node: Node):
            if node.type == 'function_definition':
                prev = current_function[0]
                current_function[0] = self._get_name(node)
                for child in node.children:
                    visit(child)
                current_function[0] = prev
            elif node.type == 'call':
                if current_function[0]:
                    call_info = self._extract_call(node, source, current_function[0])
                    if call_info:
                        calls.append(call_info)
                for child in node.children:
                    visit(child)
            else:
                for child in node.children:
                    visit(child)

        visit(tree.root_node)
        return calls

    def _extract_call(
        self,
        node: Node,
        source: str,
        caller: str
    ) -> Optional[CallInfo]:
        """Extract call information."""
        callee = ""
        is_method = False

        func = node.children[0] if node.children else None
        if func:
            if func.type == 'identifier':
                callee = func.text.decode('utf-8')
            elif func.type == 'attribute':
                callee = source[func.start_byte:func.end_byte]
                is_method = True

        if not callee:
            return None

        return CallInfo(
            caller=caller,
            callee=callee,
            line=node.start_point[0] + 1,
            is_method_call=is_method,
        )
```

### 5.2.3 Extractor Registry

```python
# parsing/extractors/__init__.py
from typing import Optional

from .base import LanguageExtractor
from .python import PythonExtractor
from .typescript import TypeScriptExtractor
from .javascript import JavaScriptExtractor
from .java import JavaExtractor
from .go import GoExtractor
from .rust import RustExtractor
from .csharp import CSharpExtractor


_EXTRACTORS = {
    'python': PythonExtractor(),
    'typescript': TypeScriptExtractor(),
    'javascript': JavaScriptExtractor(),
    'java': JavaExtractor(),
    'go': GoExtractor(),
    'rust': RustExtractor(),
    'csharp': CSharpExtractor(),
}


def get_extractor(language: str) -> Optional[LanguageExtractor]:
    """Get extractor for language."""
    return _EXTRACTORS.get(language)
```

---

## 6. Utils Module

### 6.1 Module Structure

```
utils/
    __init__.py
    hashing.py      # Content hashing
    gitignore.py    # Gitignore pattern matching
    logging.py      # Structured logging setup
```

### 6.2 Hashing Utilities

```python
# utils/hashing.py
import hashlib
from typing import Union


def compute_content_hash(content: Union[str, bytes]) -> str:
    """Compute SHA-256 hash of content.

    Args:
        content: String or bytes to hash.

    Returns:
        Hexadecimal hash string.
    """
    if isinstance(content, str):
        content = content.encode('utf-8')
    return hashlib.sha256(content).hexdigest()


def normalize_content(content: str) -> str:
    """Normalize content for consistent hashing.

    - Strip trailing whitespace
    - Normalize line endings to LF
    - Remove trailing newlines

    Args:
        content: Raw content string.

    Returns:
        Normalized content.
    """
    # Normalize line endings
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    # Strip trailing whitespace from lines
    lines = [line.rstrip() for line in content.split('\n')]
    # Remove trailing empty lines
    while lines and not lines[-1]:
        lines.pop()
    return '\n'.join(lines)
```

### 6.3 Gitignore Utilities

```python
# utils/gitignore.py
from pathlib import Path
from typing import List, Optional

import pathspec


class GitignoreFilter:
    """Filter files based on gitignore patterns."""

    def __init__(self, base_path: str):
        """Initialize with project base path.

        Args:
            base_path: Project root directory.
        """
        self.base_path = Path(base_path)
        self._spec = self._load_gitignore()

    def _load_gitignore(self) -> Optional[pathspec.PathSpec]:
        """Load gitignore patterns from file."""
        gitignore_path = self.base_path / '.gitignore'
        if not gitignore_path.exists():
            return None

        with open(gitignore_path, 'r') as f:
            patterns = f.read().splitlines()

        return pathspec.PathSpec.from_lines('gitwildmatch', patterns)

    def is_ignored(self, file_path: str) -> bool:
        """Check if file should be ignored.

        Args:
            file_path: Path to check (absolute or relative to base).

        Returns:
            True if file matches gitignore patterns.
        """
        if self._spec is None:
            return False

        # Convert to relative path
        path = Path(file_path)
        if path.is_absolute():
            try:
                path = path.relative_to(self.base_path)
            except ValueError:
                return False

        return self._spec.match_file(str(path))

    def filter_paths(self, paths: List[str]) -> List[str]:
        """Filter list of paths, removing ignored ones.

        Args:
            paths: List of file paths.

        Returns:
            Paths not matching gitignore patterns.
        """
        return [p for p in paths if not self.is_ignored(p)]
```

### 6.4 Logging Utilities

```python
# utils/logging.py
import logging
import sys
from typing import Optional

import structlog


def setup_logging(
    level: str = "INFO",
    format: str = "json",
    service_name: str = "memory-service"
) -> None:
    """Configure structured logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR).
        format: Output format ('json' or 'console').
        service_name: Service name for log context.
    """
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper()),
    )

    # Configure structlog processors
    shared_processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        add_service_name(service_name),
    ]

    if format == "json":
        processors = shared_processors + [
            structlog.processors.JSONRenderer()
        ]
    else:
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer()
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def add_service_name(service_name: str):
    """Processor to add service name to all logs."""
    def processor(logger, method_name, event_dict):
        event_dict["service"] = service_name
        return event_dict
    return processor


def get_logger(name: Optional[str] = None) -> structlog.BoundLogger:
    """Get a configured logger instance.

    Args:
        name: Logger name (usually __name__).

    Returns:
        Configured structlog logger.
    """
    return structlog.get_logger(name)


def sanitize_for_logging(data: dict) -> dict:
    """Remove sensitive data before logging.

    Args:
        data: Dictionary that may contain secrets.

    Returns:
        Dictionary with secrets redacted.
    """
    sensitive_keys = {
        'password', 'api_key', 'secret', 'token',
        'authorization', 'credential', 'key'
    }

    def redact(d):
        if isinstance(d, dict):
            return {
                k: '***REDACTED***' if any(s in k.lower() for s in sensitive_keys) else redact(v)
                for k, v in d.items()
            }
        elif isinstance(d, list):
            return [redact(item) for item in d]
        return d

    return redact(data)
```

---

## 7. Public API

### 7.1 Module Exports

```python
# models/__init__.py
from .base import BaseMemory, MemoryType, SyncStatus
from .memories import (
    RequirementsMemory,
    DesignMemory,
    CodePatternMemory,
    ComponentMemory,
    FunctionMemory,
    TestHistoryMemory,
    SessionMemory,
    UserPreferenceMemory,
    Priority,
    RequirementStatus,
    DesignType,
    DesignStatus,
    PatternType,
    ComponentType,
    TestStatus,
    PreferenceCategory,
    PreferenceScope,
)
from .code_elements import (
    FunctionInfo,
    ClassInfo,
    ImportInfo,
    CallInfo,
    ParameterInfo,
)
from .relationships import Relationship, RelationshipType

__all__ = [
    # Base
    'BaseMemory', 'MemoryType', 'SyncStatus',
    # Memory types
    'RequirementsMemory', 'DesignMemory', 'CodePatternMemory',
    'ComponentMemory', 'FunctionMemory', 'TestHistoryMemory',
    'SessionMemory', 'UserPreferenceMemory',
    # Enums
    'Priority', 'RequirementStatus', 'DesignType', 'DesignStatus',
    'PatternType', 'ComponentType', 'TestStatus',
    'PreferenceCategory', 'PreferenceScope',
    # Code elements
    'FunctionInfo', 'ClassInfo', 'ImportInfo', 'CallInfo', 'ParameterInfo',
    # Relationships
    'Relationship', 'RelationshipType',
]
```

```python
# utils/__init__.py
from .hashing import compute_content_hash, normalize_content
from .gitignore import GitignoreFilter
from .logging import setup_logging, get_logger, sanitize_for_logging

__all__ = [
    'compute_content_hash', 'normalize_content',
    'GitignoreFilter',
    'setup_logging', 'get_logger', 'sanitize_for_logging',
]
```

```python
# parsing/__init__.py
from .parser import ParserOrchestrator, EXTENSION_MAP
from .extractors import get_extractor

__all__ = [
    'ParserOrchestrator',
    'EXTENSION_MAP',
    'get_extractor',
]
```

---

## 8. Error Handling Design

### 8.1 Error Types

| Error Type | When Raised | Recoverability | Consumer Response |
|------------|-------------|----------------|-------------------|
| ValidationError | Invalid model data | Recoverable | Fix input data |
| ParseError | Malformed source code | Recoverable | Skip file or partial parse |
| UnsupportedLanguageError | Unknown file extension | Recoverable | Skip file |

### 8.2 Validation Errors

Pydantic provides detailed validation errors:

```python
from pydantic import ValidationError

try:
    memory = RequirementsMemory(**data)
except ValidationError as e:
    # e.errors() provides detailed field-level errors
    for error in e.errors():
        print(f"Field: {error['loc']}, Error: {error['msg']}")
```

---

## 9. Performance Design

### 9.1 Performance Goals

| Operation | Target Performance | Notes |
|-----------|-------------------|-------|
| Model serialization | < 1ms | Per memory |
| Model validation | < 5ms | Per memory |
| File parsing | < 100ms | Per file (typical size) |
| Gitignore check | < 1ms | Per file |

### 9.2 Optimization Strategies

- **Parser caching:** Tree-sitter parsers cached per language
- **Lazy loading:** Extractors instantiated once per language
- **Frozen dataclasses:** Immutable code elements enable hashing/caching

---

## 10. Thread Safety Design

### 10.1 Thread Safety Model

| Type/Component | Thread Safety | Notes |
|----------------|---------------|-------|
| Pydantic models | Thread-safe | Immutable after creation |
| ParserOrchestrator | Thread-safe | Parsers are per-thread safe |
| GitignoreFilter | Thread-safe | Read-only after init |
| Logger | Thread-safe | structlog is thread-safe |

---

## 11. Testing Design

### 11.1 Testability

- All modules are independently importable
- No global state (except logger configuration)
- Dependency injection via constructor parameters

### 11.2 Test Fixtures

```python
# tests/fixtures/sample_memories.py
from memory_service.models import RequirementsMemory, Priority, RequirementStatus

def sample_requirements_memory():
    return RequirementsMemory(
        requirement_id="REQ-MEM-FN-001",
        title="Test Requirement",
        description="A test requirement for unit tests",
        priority=Priority.HIGH,
        status=RequirementStatus.DRAFT,
        source_document="test.md",
        content="Test requirement content",
    )
```

### 11.3 Test Coverage Target

80% coverage for all library modules, with emphasis on:
- Model validation edge cases
- Parser extraction accuracy
- Gitignore pattern matching

---

## 12. Versioning and Compatibility

### 12.1 Versioning Strategy

Semantic versioning (MAJOR.MINOR.PATCH):
- MAJOR: Breaking model schema changes
- MINOR: New fields (with defaults), new extractors
- PATCH: Bug fixes

### 12.2 Public API Stability

| API Surface | Stability | Notes |
|-------------|-----------|-------|
| Memory models | Stable | Breaking changes bump major version |
| Code elements | Stable | Frozen dataclasses |
| Utils | Stable | Signature changes bump major |
| Extractors | Experimental | May improve extraction quality |

---

## 13. Documentation Design

### 13.1 API Documentation

All public functions and classes include:
- Type-annotated parameters and return values
- Google-style docstrings
- Usage examples in docstrings

Example:
```python
def compute_content_hash(content: Union[str, bytes]) -> str:
    """Compute SHA-256 hash of content.

    Args:
        content: String or bytes to hash.

    Returns:
        Hexadecimal hash string.

    Example:
        >>> compute_content_hash("hello")
        '2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824'
    """
```

---

## 14. Constraints and Assumptions

### 14.1 Technical Constraints

| Constraint | Source | Impact on Design |
|------------|--------|------------------|
| Python 3.12+ | Requirements | Modern typing features |
| Tree-sitter | ADR-004 | Grammar availability |
| Pydantic v2 | Dependencies | Model validation patterns |

### 14.2 Assumptions

| Assumption | Rationale | Risk if Invalid |
|------------|-----------|-----------------|
| UTF-8 encoding | Standard for source code | Parsing failures |
| Tree-sitter grammar quality | Active community | Extraction errors |
| Files fit in memory | Developer workstation | Need streaming parser |

---

## 15. Glossary

| Term | Definition |
|------|------------|
| AST | Abstract Syntax Tree |
| Extractor | Language-specific code element extraction |
| Frozen | Immutable after creation (dataclass/Pydantic) |
| Tree-sitter | Universal parser framework |

---

## Appendix A: Language Support Matrix

| Language | Grammar | Functions | Classes | Imports | Calls |
|----------|---------|-----------|---------|---------|-------|
| Python | tree-sitter-python | Yes | Yes | Yes | Yes |
| TypeScript | tree-sitter-typescript | Yes | Yes | Yes | Yes |
| JavaScript | tree-sitter-javascript | Yes | Yes | Yes | Yes |
| Java | tree-sitter-java | Yes | Yes | Yes | Yes |
| Go | tree-sitter-go | Yes | Struct | Yes | Yes |
| Rust | tree-sitter-rust | Yes | Struct/Enum/Trait | Yes | Yes |
| C# | tree-sitter-c-sharp | Yes | Yes | Yes | Yes |

---

## Appendix B: Reference Documents

| Document | Version | Relevance |
|----------|---------|-----------|
| ADR-004-code-parsing-architecture.md | Accepted | Parsing decisions |
| Tree-sitter documentation | Current | Grammar reference |
| Pydantic documentation | v2 | Model patterns |
