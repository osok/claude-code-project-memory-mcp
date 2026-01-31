# ADR-004: Code Parsing Architecture

## Status

Accepted

## Context

The memory system must parse source code to extract functions, classes, imports, and relationships. This is critical for:
- Building the function index (duplicate detection)
- Populating the Neo4j knowledge graph
- Supporting multiple programming languages

Requirements addressed:
- REQ-MEM-FN-060: Index file/directory, parse code to extract functions, classes, imports
- REQ-MEM-FN-061: Language-specific parsers (tree-sitter or equivalent)
- REQ-MEM-FN-062: Incremental indexing
- REQ-MEM-FN-063: Support Python, TypeScript, JavaScript, Java, Go, Rust, C#
- REQ-MEM-FN-064: Extract relationships (calls, inheritance, imports)

## Options Considered

### Option 1: Regular Expression Based Parsing

- **Pros**:
  - No external dependencies
  - Fast for simple patterns
  - Easy to customize
- **Cons**:
  - Cannot handle language complexity (nesting, context)
  - Fragile with edge cases
  - Requires per-language regex sets
  - Cannot build accurate AST

### Option 2: Language-Specific Parsers (python ast, TypeScript compiler, etc.)

- **Pros**:
  - Highly accurate for each language
  - Access to full type information
  - Official tooling support
- **Cons**:
  - Different parser per language
  - Inconsistent APIs
  - Heavy dependencies
  - Complex maintenance

### Option 3: Tree-sitter Universal Parser

- **Pros**:
  - Single parsing framework for all languages
  - Consistent API across languages
  - Incremental parsing support
  - Active community with grammar support
  - Lightweight and fast
  - Error-tolerant (parses partial/invalid code)
- **Cons**:
  - Grammar quality varies by language
  - Some advanced type information not available
  - Need to map tree-sitter nodes to our schema

## Decision

**Option 3: Tree-sitter** - Use tree-sitter as the universal parsing framework with language grammar plugins.

### Architecture

```
Source File
    |
    v
[Language Detector]
    |
    v
[Tree-sitter Parser + Grammar]
    |
    v
[AST]
    |
    v
[Language-specific Extractor]
    |
    v
[Normalized Code Elements]
    |
    +-- Functions --> Qdrant + Neo4j
    +-- Classes --> Qdrant + Neo4j
    +-- Imports --> Neo4j relationships
    +-- Calls --> Neo4j relationships
```

### Components

1. **Language Detector**
   - File extension mapping (primary)
   - Shebang line detection (fallback for scripts)
   - Content-based heuristics (fallback)

   ```python
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
   ```

2. **Grammar Registry**
   - Lazy-loaded tree-sitter grammars
   - Using `tree-sitter-languages` package for pre-built binaries
   - Singleton registry to avoid reloading

3. **Language Extractors** (per-language modules)
   - Each extractor implements common interface:

   ```python
   class LanguageExtractor(Protocol):
       def extract_functions(self, tree: Tree) -> List[FunctionInfo]
       def extract_classes(self, tree: Tree) -> List[ClassInfo]
       def extract_imports(self, tree: Tree) -> List[ImportInfo]
       def extract_calls(self, tree: Tree) -> List[CallInfo]
   ```

   - Language-specific node type mappings
   - Handle language idioms (e.g., Python decorators, Java annotations)

4. **Normalized Schema**

   ```python
   @dataclass
   class FunctionInfo:
       name: str
       signature: str
       docstring: Optional[str]
       start_line: int
       end_line: int
       body: str
       containing_class: Optional[str]
       decorators: List[str]
       parameters: List[ParameterInfo]

   @dataclass
   class ClassInfo:
       name: str
       docstring: Optional[str]
       start_line: int
       end_line: int
       base_classes: List[str]
       interfaces: List[str]
       methods: List[str]
       attributes: List[str]

   @dataclass
   class ImportInfo:
       module: str
       items: List[str]  # specific imports, empty for module import
       alias: Optional[str]
       is_relative: bool

   @dataclass
   class CallInfo:
       caller: str  # function/method name
       callee: str  # called function/method
       line: int
       is_method_call: bool
   ```

### Incremental Parsing Strategy

1. **File-level tracking**: Store content hash per file in SQLite
2. **Change detection**: Compare hash on re-index
3. **Targeted re-parse**: Only parse changed files
4. **Relationship cleanup**: Remove old relationships for changed files before re-indexing

```python
class IndexState:
    # SQLite table
    # file_path TEXT PRIMARY KEY
    # content_hash TEXT
    # indexed_at TIMESTAMP
    # functions_count INTEGER
    # classes_count INTEGER
```

### Supported Language Details

| Language | Grammar | Function Nodes | Class Nodes | Import Nodes |
|----------|---------|----------------|-------------|--------------|
| Python | tree-sitter-python | function_definition | class_definition | import_statement, import_from_statement |
| TypeScript | tree-sitter-typescript | function_declaration, method_definition, arrow_function | class_declaration, interface_declaration | import_statement |
| JavaScript | tree-sitter-javascript | function_declaration, method_definition, arrow_function | class_declaration | import_statement |
| Java | tree-sitter-java | method_declaration, constructor_declaration | class_declaration, interface_declaration | import_declaration |
| Go | tree-sitter-go | function_declaration, method_declaration | type_declaration (struct) | import_declaration |
| Rust | tree-sitter-rust | function_item, impl_item | struct_item, enum_item, trait_item | use_declaration |
| C# | tree-sitter-c-sharp | method_declaration, constructor_declaration | class_declaration, interface_declaration | using_directive |

## Consequences

### Positive
- Single parsing framework simplifies codebase
- Consistent extraction API across languages
- Tree-sitter is battle-tested and widely used
- Incremental parsing enables efficient updates
- Error-tolerant parsing handles incomplete code
- Active community maintains grammars

### Negative
- Some type information not available (requires full compilation)
- Grammar quality varies (though all required languages have good support)
- Need language-specific extractors despite common framework

### Risks
- **Risk**: Tree-sitter grammar bugs cause incorrect extraction
- **Mitigation**: Comprehensive test suite with known code samples; log warnings for extraction failures

- **Risk**: New language requested that lacks tree-sitter grammar
- **Mitigation**: Architecture supports adding new language extractors; most popular languages already supported

## Requirements Addressed

- REQ-MEM-FN-060 (file indexing)
- REQ-MEM-FN-061 (tree-sitter parsing)
- REQ-MEM-FN-062 (incremental indexing)
- REQ-MEM-FN-063 (multi-language support)
- REQ-MEM-FN-064 (relationship extraction)
- REQ-MEM-PERF-005 (1000 files/minute indexing)

## References

- Tree-sitter: https://tree-sitter.github.io/tree-sitter/
- tree-sitter-languages: https://github.com/grantjenks/py-tree-sitter-languages
