"""JavaScript code extractor using tree-sitter."""

import re
from typing import Any

from memory_service.models.code_elements import (
    CallInfo,
    ClassInfo,
    FunctionInfo,
    ImportInfo,
    ParameterInfo,
    ParseResult,
)
from memory_service.parsing.extractors.base import LanguageExtractor


class JavaScriptExtractor(LanguageExtractor):
    """Extract code elements from JavaScript source files.

    Uses tree-sitter-javascript for parsing JS and JSX files.
    Handles functions, arrow functions, classes, and imports (ES6 and CommonJS).
    """

    @property
    def language(self) -> str:
        return "javascript"

    def __init__(self) -> None:
        """Initialize JavaScript extractor."""
        try:
            import tree_sitter_languages

            self._parser = tree_sitter_languages.get_parser("javascript")
            self._language = tree_sitter_languages.get_language("javascript")
        except ImportError:
            self._parser = None
            self._language = None

    def extract(self, source: str, file_path: str) -> ParseResult:
        """Extract all code elements from JavaScript source."""
        result = ParseResult(
            file_path=file_path,
            language=self.language,
        )

        if not self._parser:
            result.errors.append("tree-sitter-languages not available")
            return result

        try:
            tree = self._parser.parse(source.encode())
            root = tree.root_node

            result.module_docstring = self._extract_module_docstring(root, source)
            result.imports = self._extract_imports_from_tree(root, source)
            result.classes = self._extract_classes_from_tree(root, source, file_path)
            result.functions = self._extract_functions_from_tree(
                root, source, file_path, top_level_only=True
            )

        except Exception as e:
            result.errors.append(f"Parse error: {e}")

        return result

    def extract_functions(self, source: str, file_path: str) -> list[FunctionInfo]:
        """Extract function definitions."""
        if not self._parser:
            return []

        tree = self._parser.parse(source.encode())
        return self._extract_functions_from_tree(
            tree.root_node, source, file_path, top_level_only=False
        )

    def extract_classes(self, source: str, file_path: str) -> list[ClassInfo]:
        """Extract class definitions."""
        if not self._parser:
            return []

        tree = self._parser.parse(source.encode())
        return self._extract_classes_from_tree(tree.root_node, source, file_path)

    def extract_imports(self, source: str) -> list[ImportInfo]:
        """Extract import statements."""
        if not self._parser:
            return []

        tree = self._parser.parse(source.encode())
        return self._extract_imports_from_tree(tree.root_node, source)

    def _extract_module_docstring(self, root: Any, source: str) -> str | None:
        """Extract file-level documentation comment."""
        for child in root.children:
            if child.type == "comment":
                comment = source[child.start_byte : child.end_byte]
                if comment.startswith("/**"):
                    return self._clean_jsdoc(comment)
                elif comment.startswith("//"):
                    return comment[2:].strip()
            elif child.type not in ("comment",):
                break
        return None

    def _extract_imports_from_tree(self, root: Any, source: str) -> list[ImportInfo]:
        """Extract imports from parse tree (ES6 and CommonJS)."""
        imports = []

        # ES6 imports: import x from 'y'
        for node in self._find_nodes(root, ["import_statement"]):
            line = node.start_point[0] + 1

            # Get the module specifier
            source_node = self._find_child(node, "string")
            if not source_node:
                continue

            module = source[source_node.start_byte + 1 : source_node.end_byte - 1]
            is_relative = module.startswith(".")

            # Check for import clause
            import_clause = self._find_child(node, "import_clause")
            if import_clause:
                # Default import: import x from 'y'
                default_import = self._find_child(import_clause, "identifier")
                if default_import:
                    name = source[default_import.start_byte : default_import.end_byte]
                    imports.append(ImportInfo(
                        module=module,
                        name=name,
                        line=line,
                        is_relative=is_relative,
                    ))

                # Named imports: import { x, y } from 'z'
                named_imports = self._find_child(import_clause, "named_imports")
                if named_imports:
                    for spec in self._find_nodes(named_imports, ["import_specifier"]):
                        name_node = spec.children[0] if spec.children else None
                        alias_node = None

                        for i, child in enumerate(spec.children):
                            if child.type == "identifier":
                                if name_node is None:
                                    name_node = child
                                else:
                                    alias_node = child
                            elif source[child.start_byte : child.end_byte] == "as":
                                if i + 1 < len(spec.children):
                                    alias_node = spec.children[i + 1]

                        if name_node:
                            name = source[name_node.start_byte : name_node.end_byte]
                            alias = (
                                source[alias_node.start_byte : alias_node.end_byte]
                                if alias_node and alias_node != name_node
                                else None
                            )
                            imports.append(ImportInfo(
                                module=module,
                                name=name,
                                alias=alias,
                                line=line,
                                is_relative=is_relative,
                            ))

                # Namespace import: import * as x from 'y'
                namespace_import = self._find_child(import_clause, "namespace_import")
                if namespace_import:
                    alias_node = self._find_child(namespace_import, "identifier")
                    if alias_node:
                        alias = source[alias_node.start_byte : alias_node.end_byte]
                        imports.append(ImportInfo(
                            module=module,
                            name="*",
                            alias=alias,
                            line=line,
                            is_relative=is_relative,
                        ))
            else:
                # Side-effect import: import 'module'
                imports.append(ImportInfo(
                    module=module,
                    line=line,
                    is_relative=is_relative,
                ))

        # CommonJS: const x = require('y')
        for node in self._find_nodes(root, ["lexical_declaration", "variable_declaration"]):
            for declarator in self._find_nodes(node, ["variable_declarator"]):
                call_node = self._find_child(declarator, "call_expression")
                if call_node:
                    func_node = self._find_child(call_node, "identifier")
                    if func_node and source[func_node.start_byte : func_node.end_byte] == "require":
                        args = self._find_child(call_node, "arguments")
                        if args:
                            string_node = self._find_child(args, "string")
                            if string_node:
                                module = source[string_node.start_byte + 1 : string_node.end_byte - 1]
                                name_node = self._find_child(declarator, "identifier")
                                object_pattern = self._find_child(declarator, "object_pattern")

                                if name_node:
                                    # const x = require('y')
                                    imports.append(ImportInfo(
                                        module=module,
                                        name=source[name_node.start_byte : name_node.end_byte],
                                        line=node.start_point[0] + 1,
                                        is_relative=module.startswith("."),
                                    ))
                                elif object_pattern:
                                    # const { x, y } = require('z')
                                    for prop in self._find_nodes(object_pattern, ["shorthand_property_identifier_pattern", "pair_pattern"]):
                                        if prop.type == "shorthand_property_identifier_pattern":
                                            name = source[prop.start_byte : prop.end_byte]
                                            imports.append(ImportInfo(
                                                module=module,
                                                name=name,
                                                line=node.start_point[0] + 1,
                                                is_relative=module.startswith("."),
                                            ))

        return imports

    def _extract_functions_from_tree(
        self,
        root: Any,
        source: str,
        file_path: str,
        top_level_only: bool = False,
    ) -> list[FunctionInfo]:
        """Extract function definitions from parse tree."""
        functions = []
        function_types = [
            "function_declaration",
            "function_expression",
            "arrow_function",
            "method_definition",
            "generator_function_declaration",
        ]

        for node in self._find_nodes(root, function_types):
            if top_level_only:
                parent = node.parent
                is_in_class = False
                while parent:
                    if parent.type in ("class_declaration", "class_expression", "class_body"):
                        is_in_class = True
                        break
                    parent = parent.parent
                if is_in_class:
                    continue

            func_info = self._parse_function_node(node, source, file_path)
            if func_info:
                functions.append(func_info)

        # Handle arrow functions assigned to variables
        for node in self._find_nodes(root, ["lexical_declaration", "variable_declaration"]):
            if top_level_only:
                parent = node.parent
                is_in_class = False
                while parent:
                    if parent.type in ("class_declaration", "class_expression", "class_body"):
                        is_in_class = True
                        break
                    parent = parent.parent
                if is_in_class:
                    continue

            for declarator in self._find_nodes(node, ["variable_declarator"]):
                value_node = self._find_child(declarator, "arrow_function")
                if not value_node:
                    value_node = self._find_child(declarator, "function_expression")
                if value_node:
                    name_node = self._find_child(declarator, "identifier")
                    if name_node:
                        func_info = self._parse_named_function_expression(
                            value_node, name_node, source, file_path
                        )
                        if func_info:
                            functions.append(func_info)

        return functions

    def _extract_classes_from_tree(
        self,
        root: Any,
        source: str,
        file_path: str,
    ) -> list[ClassInfo]:
        """Extract class definitions from parse tree."""
        classes = []

        for node in self._find_nodes(root, ["class_declaration", "class_expression"]):
            class_info = self._parse_class_node(node, source, file_path)
            if class_info:
                classes.append(class_info)

        return classes

    def _parse_function_node(
        self,
        node: Any,
        source: str,
        file_path: str,
    ) -> FunctionInfo | None:
        """Parse a function definition node."""
        name_node = self._find_child(node, "identifier")
        if not name_node:
            if node.type == "arrow_function":
                return None
            name = "<anonymous>"
        else:
            name = source[name_node.start_byte : name_node.end_byte]

        # Get parameters
        params_node = self._find_child(node, "formal_parameters")
        parameters = self._parse_parameters(params_node, source) if params_node else ()

        # Get JSDoc comment
        docstring = self._get_jsdoc_comment(node, source)

        # Build signature
        params_str = ", ".join(p.name for p in parameters)
        is_async = self._is_async(node, source)
        async_prefix = "async " if is_async else ""
        is_generator = node.type == "generator_function_declaration"
        gen_marker = "*" if is_generator else ""
        signature = f"{async_prefix}function{gen_marker} {name}({params_str})"

        return FunctionInfo(
            name=name,
            signature=signature,
            file_path=file_path,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            docstring=docstring,
            parameters=parameters,
            is_async=is_async,
            is_method=node.type == "method_definition",
        )

    def _parse_named_function_expression(
        self,
        func_node: Any,
        name_node: Any,
        source: str,
        file_path: str,
    ) -> FunctionInfo | None:
        """Parse a function expression or arrow function assigned to a variable."""
        name = source[name_node.start_byte : name_node.end_byte]

        # Get parameters
        params_node = self._find_child(func_node, "formal_parameters")
        if not params_node:
            # Single parameter arrow function
            param_node = self._find_child(func_node, "identifier")
            if param_node:
                param_name = source[param_node.start_byte : param_node.end_byte]
                parameters = (ParameterInfo(name=param_name),)
            else:
                parameters = ()
        else:
            parameters = self._parse_parameters(params_node, source)

        is_async = self._is_async(func_node, source)
        is_arrow = func_node.type == "arrow_function"

        # Build signature
        params_str = ", ".join(p.name for p in parameters)
        async_prefix = "async " if is_async else ""
        if is_arrow:
            signature = f"{async_prefix}{name} = ({params_str}) => ..."
        else:
            signature = f"{async_prefix}function {name}({params_str})"

        # Get JSDoc from variable declaration
        docstring = self._get_jsdoc_comment(name_node.parent.parent, source)

        return FunctionInfo(
            name=name,
            signature=signature,
            file_path=file_path,
            start_line=func_node.start_point[0] + 1,
            end_line=func_node.end_point[0] + 1,
            docstring=docstring,
            parameters=parameters,
            is_async=is_async,
        )

    def _parse_class_node(
        self,
        node: Any,
        source: str,
        file_path: str,
    ) -> ClassInfo | None:
        """Parse a class definition node."""
        name_node = self._find_child(node, "identifier")
        if not name_node:
            return None

        name = source[name_node.start_byte : name_node.end_byte]

        # Get base classes
        bases = []
        heritage = self._find_child(node, "class_heritage")
        if heritage:
            for child in heritage.children:
                if child.type in ("identifier", "member_expression"):
                    bases.append(source[child.start_byte : child.end_byte])

        # Get JSDoc
        docstring = self._get_jsdoc_comment(node, source)

        # Extract methods
        methods = []
        body = self._find_child(node, "class_body")
        if body:
            for method_node in self._find_nodes(body, ["method_definition"]):
                method = self._parse_method_node(method_node, source, file_path, name)
                if method:
                    methods.append(method)

        return ClassInfo(
            name=name,
            file_path=file_path,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            docstring=docstring,
            bases=tuple(bases),
            methods=tuple(methods),
        )

    def _parse_method_node(
        self,
        node: Any,
        source: str,
        file_path: str,
        class_name: str,
    ) -> FunctionInfo | None:
        """Parse a method definition node."""
        name_node = self._find_child(node, "property_identifier")
        if not name_node:
            name_node = self._find_child(node, "computed_property_name")
        if not name_node:
            return None

        name = source[name_node.start_byte : name_node.end_byte]

        # Check for static
        is_static = False
        for child in node.children:
            if source[child.start_byte : child.end_byte] == "static":
                is_static = True
                break

        # Get parameters
        params_node = self._find_child(node, "formal_parameters")
        parameters = self._parse_parameters(params_node, source) if params_node else ()

        # Check for getter/setter
        is_property = False
        for child in node.children:
            child_text = source[child.start_byte : child.end_byte]
            if child_text in ("get", "set"):
                is_property = True
                break

        is_async = self._is_async(node, source)

        # Build signature
        params_str = ", ".join(p.name for p in parameters)
        static_str = "static " if is_static else ""
        async_str = "async " if is_async else ""
        signature = f"{static_str}{async_str}{name}({params_str})"

        docstring = self._get_jsdoc_comment(node, source)

        return FunctionInfo(
            name=name,
            signature=signature,
            file_path=file_path,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            docstring=docstring,
            parameters=parameters,
            is_async=is_async,
            is_method=True,
            is_static=is_static,
            is_property=is_property,
            containing_class=class_name,
        )

    def _parse_parameters(self, params_node: Any, source: str) -> tuple[ParameterInfo, ...]:
        """Parse function parameters."""
        parameters = []

        for child in params_node.children:
            if child.type == "identifier":
                name = source[child.start_byte : child.end_byte]
                parameters.append(ParameterInfo(name=name))
            elif child.type == "assignment_pattern":
                # Parameter with default value
                name_node = self._find_child(child, "identifier")
                if name_node:
                    name = source[name_node.start_byte : name_node.end_byte]
                    # Find default value
                    default = None
                    for i, c in enumerate(child.children):
                        if source[c.start_byte : c.end_byte] == "=":
                            if i + 1 < len(child.children):
                                default_node = child.children[i + 1]
                                default = source[default_node.start_byte : default_node.end_byte]
                    parameters.append(ParameterInfo(name=name, default_value=default))
            elif child.type == "rest_pattern":
                # ...args
                name_node = self._find_child(child, "identifier")
                name = source[name_node.start_byte : name_node.end_byte] if name_node else "args"
                parameters.append(ParameterInfo(name=f"...{name}", is_variadic=True))
            elif child.type in ("object_pattern", "array_pattern"):
                # Destructuring parameter
                pattern = source[child.start_byte : child.end_byte]
                parameters.append(ParameterInfo(name=pattern))

        return tuple(parameters)

    def _get_jsdoc_comment(self, node: Any, source: str) -> str | None:
        """Get JSDoc comment before a node."""
        prev = node.prev_sibling
        while prev:
            if prev.type == "comment":
                comment = source[prev.start_byte : prev.end_byte]
                if comment.startswith("/**"):
                    return self._clean_jsdoc(comment)
            elif prev.type != "comment":
                break
            prev = prev.prev_sibling
        return None

    def _clean_jsdoc(self, comment: str) -> str:
        """Clean JSDoc comment."""
        comment = comment.strip()
        if comment.startswith("/**"):
            comment = comment[3:]
        if comment.endswith("*/"):
            comment = comment[:-2]

        lines = []
        for line in comment.split("\n"):
            line = line.strip()
            if line.startswith("*"):
                line = line[1:].strip()
            lines.append(line)

        return "\n".join(lines).strip()

    def _is_async(self, node: Any, source: str) -> bool:
        """Check if function is async."""
        for child in node.children:
            if source[child.start_byte : child.end_byte] == "async":
                return True
        return False

    def _find_nodes(self, root: Any, types: list[str]) -> list[Any]:
        """Find all nodes of given types in tree."""
        results = []

        def visit(node: Any) -> None:
            if node.type in types:
                results.append(node)
            for child in node.children:
                visit(child)

        visit(root)
        return results

    def _find_child(self, node: Any, type_name: str) -> Any | None:
        """Find first child of given type."""
        for child in node.children:
            if child.type == type_name:
                return child
        return None
