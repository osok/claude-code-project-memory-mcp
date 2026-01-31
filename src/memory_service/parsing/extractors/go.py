"""Go code extractor using tree-sitter."""

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


class GoExtractor(LanguageExtractor):
    """Extract code elements from Go source files.

    Uses tree-sitter-go for parsing Go source files.
    Handles functions, methods (with receivers), structs, interfaces, and imports.
    """

    @property
    def language(self) -> str:
        return "go"

    def __init__(self) -> None:
        """Initialize Go extractor."""
        try:
            import tree_sitter_languages

            self._parser = tree_sitter_languages.get_parser("go")
            self._language = tree_sitter_languages.get_language("go")
        except ImportError:
            self._parser = None
            self._language = None

    def extract(self, source: str, file_path: str) -> ParseResult:
        """Extract all code elements from Go source."""
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

            result.module_docstring = self._extract_package_doc(root, source)
            result.imports = self._extract_imports_from_tree(root, source)
            result.classes = self._extract_types_from_tree(root, source, file_path)
            result.functions = self._extract_functions_from_tree(root, source, file_path)

        except Exception as e:
            result.errors.append(f"Parse error: {e}")

        return result

    def extract_functions(self, source: str, file_path: str) -> list[FunctionInfo]:
        """Extract function definitions."""
        if not self._parser:
            return []

        tree = self._parser.parse(source.encode())
        return self._extract_functions_from_tree(tree.root_node, source, file_path)

    def extract_classes(self, source: str, file_path: str) -> list[ClassInfo]:
        """Extract type definitions (structs and interfaces)."""
        if not self._parser:
            return []

        tree = self._parser.parse(source.encode())
        return self._extract_types_from_tree(tree.root_node, source, file_path)

    def extract_imports(self, source: str) -> list[ImportInfo]:
        """Extract import statements."""
        if not self._parser:
            return []

        tree = self._parser.parse(source.encode())
        return self._extract_imports_from_tree(tree.root_node, source)

    def _extract_package_doc(self, root: Any, source: str) -> str | None:
        """Extract package-level documentation comment."""
        for child in root.children:
            if child.type == "comment":
                comment = source[child.start_byte : child.end_byte]
                if comment.startswith("//"):
                    return comment[2:].strip()
                elif comment.startswith("/*"):
                    return self._clean_block_comment(comment)
            elif child.type not in ("comment", "package_clause"):
                break
        return None

    def _extract_imports_from_tree(self, root: Any, source: str) -> list[ImportInfo]:
        """Extract imports from parse tree."""
        imports = []

        for node in self._find_nodes(root, ["import_declaration"]):
            # Single import: import "fmt"
            import_spec = self._find_child(node, "import_spec")
            if import_spec:
                self._parse_import_spec(import_spec, source, imports)

            # Import block: import ( "fmt" "os" )
            import_spec_list = self._find_child(node, "import_spec_list")
            if import_spec_list:
                for spec in self._find_nodes(import_spec_list, ["import_spec"]):
                    self._parse_import_spec(spec, source, imports)

        return imports

    def _parse_import_spec(self, node: Any, source: str, imports: list[ImportInfo]) -> None:
        """Parse a single import spec."""
        line = node.start_point[0] + 1

        # Get module path
        path_node = self._find_child(node, "interpreted_string_literal")
        if not path_node:
            return

        module = source[path_node.start_byte + 1 : path_node.end_byte - 1]

        # Check for alias
        alias = None
        name_node = self._find_child(node, "package_identifier")
        if name_node:
            alias = source[name_node.start_byte : name_node.end_byte]

        # Check for blank import (import _ "module")
        blank_node = self._find_child(node, "blank_identifier")
        if blank_node:
            alias = "_"

        # Check for dot import (import . "module")
        dot_node = self._find_child(node, "dot")
        if dot_node:
            alias = "."

        imports.append(ImportInfo(
            module=module,
            alias=alias,
            line=line,
        ))

    def _extract_functions_from_tree(
        self,
        root: Any,
        source: str,
        file_path: str,
    ) -> list[FunctionInfo]:
        """Extract function and method definitions from parse tree."""
        functions = []

        for node in self._find_nodes(root, ["function_declaration", "method_declaration"]):
            func_info = self._parse_function_node(node, source, file_path)
            if func_info:
                functions.append(func_info)

        return functions

    def _extract_types_from_tree(
        self,
        root: Any,
        source: str,
        file_path: str,
    ) -> list[ClassInfo]:
        """Extract struct and interface definitions from parse tree."""
        types = []

        for node in self._find_nodes(root, ["type_declaration"]):
            for spec in self._find_nodes(node, ["type_spec"]):
                type_info = self._parse_type_spec(spec, source, file_path, root)
                if type_info:
                    types.append(type_info)

        return types

    def _parse_function_node(
        self,
        node: Any,
        source: str,
        file_path: str,
    ) -> FunctionInfo | None:
        """Parse a function or method declaration."""
        is_method = node.type == "method_declaration"

        # Get function name
        name_node = self._find_child(node, "identifier")
        if not name_node:
            name_node = self._find_child(node, "field_identifier")
        if not name_node:
            return None

        name = source[name_node.start_byte : name_node.end_byte]

        # Get receiver (for methods)
        receiver_type = None
        if is_method:
            receiver = self._find_child(node, "parameter_list")
            if receiver:
                for child in receiver.children:
                    if child.type == "parameter_declaration":
                        type_node = self._find_type_in_param(child, source)
                        if type_node:
                            receiver_type = source[type_node.start_byte : type_node.end_byte]
                            break

        # Get parameters
        params_node = None
        for child in node.children:
            if child.type == "parameter_list":
                if is_method and params_node is None:
                    # First parameter_list is receiver, second is params
                    params_node = child
                    continue
                params_node = child
                break

        parameters = self._parse_parameters(params_node, source) if params_node else ()

        # Get return type
        return_type = None
        result_node = self._find_child(node, "result")
        if result_node:
            return_type = source[result_node.start_byte : result_node.end_byte].strip()

        # Get documentation comment
        docstring = self._get_go_doc(node, source)

        # Build signature
        params_str = ", ".join(
            f"{p.name} {p.type_annotation}" if p.type_annotation else p.name
            for p in parameters
        )
        receiver_str = f"({receiver_type}) " if receiver_type else ""
        ret_str = f" {return_type}" if return_type else ""
        signature = f"func {receiver_str}{name}({params_str}){ret_str}"

        return FunctionInfo(
            name=name,
            signature=signature,
            file_path=file_path,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            docstring=docstring,
            parameters=parameters,
            return_type=return_type,
            is_method=is_method,
            containing_class=receiver_type.lstrip("*") if receiver_type else None,
        )

    def _parse_type_spec(
        self,
        node: Any,
        source: str,
        file_path: str,
        root: Any,
    ) -> ClassInfo | None:
        """Parse a type specification (struct or interface)."""
        # Get type name
        name_node = self._find_child(node, "type_identifier")
        if not name_node:
            return None

        name = source[name_node.start_byte : name_node.end_byte]

        # Determine if struct or interface
        struct_type = self._find_child(node, "struct_type")
        interface_type = self._find_child(node, "interface_type")

        is_interface = interface_type is not None

        # Get embedded types (bases)
        bases = []
        type_body = struct_type or interface_type
        if type_body:
            for child in type_body.children:
                if child.type == "field_declaration_list":
                    for field in child.children:
                        # Embedded field (no name, just type)
                        if field.type == "field_declaration":
                            children = [c for c in field.children if c.type not in (",", "(", ")")]
                            if len(children) == 1:
                                type_node = children[0]
                                if type_node.type in ("type_identifier", "qualified_type", "pointer_type"):
                                    bases.append(source[type_node.start_byte : type_node.end_byte])

        # Get documentation
        docstring = self._get_go_doc(node.parent, source)

        # Find methods for this type
        methods = []
        for func_node in self._find_nodes(root, ["method_declaration"]):
            receiver = self._find_child(func_node, "parameter_list")
            if receiver:
                for child in receiver.children:
                    if child.type == "parameter_declaration":
                        type_node = self._find_type_in_param(child, source)
                        if type_node:
                            receiver_type = source[type_node.start_byte : type_node.end_byte]
                            if receiver_type.lstrip("*") == name:
                                method_info = self._parse_function_node(func_node, source, file_path)
                                if method_info:
                                    methods.append(method_info)
                                break

        # For interfaces, extract method signatures
        if interface_type:
            for child in interface_type.children:
                if child.type == "method_spec_list":
                    for method_spec in self._find_nodes(child, ["method_spec"]):
                        method_info = self._parse_method_spec(method_spec, source, file_path, name)
                        if method_info:
                            methods.append(method_info)

        return ClassInfo(
            name=name,
            file_path=file_path,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            docstring=docstring,
            bases=tuple(bases),
            methods=tuple(methods),
            is_abstract=is_interface,
        )

    def _parse_method_spec(
        self,
        node: Any,
        source: str,
        file_path: str,
        interface_name: str,
    ) -> FunctionInfo | None:
        """Parse an interface method specification."""
        name_node = self._find_child(node, "field_identifier")
        if not name_node:
            return None

        name = source[name_node.start_byte : name_node.end_byte]

        # Get parameters
        params_node = self._find_child(node, "parameter_list")
        parameters = self._parse_parameters(params_node, source) if params_node else ()

        # Get return type
        return_type = None
        result_node = self._find_child(node, "result")
        if result_node:
            return_type = source[result_node.start_byte : result_node.end_byte].strip()

        # Build signature
        params_str = ", ".join(
            f"{p.name} {p.type_annotation}" if p.type_annotation else p.name
            for p in parameters
        )
        ret_str = f" {return_type}" if return_type else ""
        signature = f"{name}({params_str}){ret_str}"

        return FunctionInfo(
            name=name,
            signature=signature,
            file_path=file_path,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            parameters=parameters,
            return_type=return_type,
            is_method=True,
            containing_class=interface_name,
        )

    def _parse_parameters(self, params_node: Any, source: str) -> tuple[ParameterInfo, ...]:
        """Parse function parameters."""
        parameters = []

        if not params_node:
            return tuple(parameters)

        for child in params_node.children:
            if child.type == "parameter_declaration":
                # Can have multiple names with same type: x, y int
                names = []
                type_str = None

                for c in child.children:
                    if c.type == "identifier":
                        names.append(source[c.start_byte : c.end_byte])
                    elif c.type in ("type_identifier", "qualified_type", "pointer_type",
                                   "slice_type", "array_type", "map_type", "channel_type",
                                   "function_type", "interface_type", "struct_type"):
                        type_str = source[c.start_byte : c.end_byte]

                if not names:
                    # Anonymous parameter (just type)
                    if type_str:
                        parameters.append(ParameterInfo(name="", type_annotation=type_str))
                else:
                    for name in names:
                        parameters.append(ParameterInfo(name=name, type_annotation=type_str))

            elif child.type == "variadic_parameter_declaration":
                # ...args
                name_node = self._find_child(child, "identifier")
                type_node = None
                for c in child.children:
                    if c.type in ("type_identifier", "qualified_type", "pointer_type",
                                 "slice_type", "array_type", "map_type", "interface_type"):
                        type_node = c
                        break

                name = source[name_node.start_byte : name_node.end_byte] if name_node else "args"
                type_str = source[type_node.start_byte : type_node.end_byte] if type_node else None
                parameters.append(ParameterInfo(
                    name=name,
                    type_annotation=f"...{type_str}" if type_str else "...",
                    is_variadic=True,
                ))

        return tuple(parameters)

    def _find_type_in_param(self, param_node: Any, source: str) -> Any | None:
        """Find the type node within a parameter declaration."""
        for c in param_node.children:
            if c.type in ("type_identifier", "qualified_type", "pointer_type",
                         "slice_type", "array_type", "map_type", "channel_type",
                         "function_type", "interface_type", "struct_type"):
                return c
        return None

    def _get_go_doc(self, node: Any, source: str) -> str | None:
        """Get Go documentation comment before a node."""
        prev = node.prev_sibling
        comments = []

        while prev and prev.type == "comment":
            comment = source[prev.start_byte : prev.end_byte]
            if comment.startswith("//"):
                comments.insert(0, comment[2:].strip())
            elif comment.startswith("/*"):
                comments.insert(0, self._clean_block_comment(comment))
            prev = prev.prev_sibling

        return "\n".join(comments) if comments else None

    def _clean_block_comment(self, comment: str) -> str:
        """Clean block comment."""
        comment = comment.strip()
        if comment.startswith("/*"):
            comment = comment[2:]
        if comment.endswith("*/"):
            comment = comment[:-2]
        return comment.strip()

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
