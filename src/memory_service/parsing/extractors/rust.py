"""Rust code extractor using tree-sitter."""

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


class RustExtractor(LanguageExtractor):
    """Extract code elements from Rust source files.

    Uses tree-sitter-rust for parsing Rust source files.
    Handles functions, impl blocks, structs, enums, traits, and use statements.
    """

    @property
    def language(self) -> str:
        return "rust"

    def __init__(self) -> None:
        """Initialize Rust extractor."""
        try:
            import tree_sitter_languages

            self._parser = tree_sitter_languages.get_parser("rust")
            self._language = tree_sitter_languages.get_language("rust")
        except ImportError:
            self._parser = None
            self._language = None

    def extract(self, source: str, file_path: str) -> ParseResult:
        """Extract all code elements from Rust source."""
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

            result.module_docstring = self._extract_module_doc(root, source)
            result.imports = self._extract_imports_from_tree(root, source)
            result.classes = self._extract_types_from_tree(root, source, file_path)
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
        """Extract type definitions (structs, enums, traits)."""
        if not self._parser:
            return []

        tree = self._parser.parse(source.encode())
        return self._extract_types_from_tree(tree.root_node, source, file_path)

    def extract_imports(self, source: str) -> list[ImportInfo]:
        """Extract use statements."""
        if not self._parser:
            return []

        tree = self._parser.parse(source.encode())
        return self._extract_imports_from_tree(tree.root_node, source)

    def _extract_module_doc(self, root: Any, source: str) -> str | None:
        """Extract module-level documentation (//! or /*! comments)."""
        for child in root.children:
            if child.type == "line_comment":
                comment = source[child.start_byte : child.end_byte]
                if comment.startswith("//!"):
                    return comment[3:].strip()
            elif child.type == "block_comment":
                comment = source[child.start_byte : child.end_byte]
                if comment.startswith("/*!"):
                    return self._clean_block_comment(comment[3:])
            elif child.type not in ("line_comment", "block_comment", "inner_attribute_item"):
                break
        return None

    def _extract_imports_from_tree(self, root: Any, source: str) -> list[ImportInfo]:
        """Extract use statements from parse tree."""
        imports = []

        for node in self._find_nodes(root, ["use_declaration"]):
            line = node.start_point[0] + 1
            self._parse_use_tree(node, source, line, imports, "")

        return imports

    def _parse_use_tree(
        self,
        node: Any,
        source: str,
        line: int,
        imports: list[ImportInfo],
        prefix: str,
    ) -> None:
        """Parse a use tree recursively."""
        for child in node.children:
            if child.type == "scoped_identifier":
                module = source[child.start_byte : child.end_byte]
                if prefix:
                    module = f"{prefix}::{module}"
                imports.append(ImportInfo(module=module, line=line))

            elif child.type == "identifier":
                name = source[child.start_byte : child.end_byte]
                if prefix:
                    module = f"{prefix}::{name}"
                else:
                    module = name
                imports.append(ImportInfo(module=module, line=line))

            elif child.type == "use_as_clause":
                # use foo as bar
                name_node = child.children[0] if child.children else None
                alias_node = self._find_child(child, "identifier")
                if name_node:
                    name = source[name_node.start_byte : name_node.end_byte]
                    if prefix:
                        name = f"{prefix}::{name}"
                    alias = source[alias_node.start_byte : alias_node.end_byte] if alias_node else None
                    imports.append(ImportInfo(module=name, alias=alias, line=line))

            elif child.type == "use_list":
                # use foo::{bar, baz}
                for item in child.children:
                    if item.type == "identifier":
                        name = source[item.start_byte : item.end_byte]
                        module = f"{prefix}::{name}" if prefix else name
                        imports.append(ImportInfo(module=module, line=line))
                    elif item.type == "use_as_clause":
                        self._parse_use_tree(item, source, line, imports, prefix)
                    elif item.type == "scoped_use_list":
                        self._parse_use_tree(item, source, line, imports, prefix)

            elif child.type == "scoped_use_list":
                # Extract the path prefix and recurse
                path_node = self._find_child(child, "scoped_identifier")
                if not path_node:
                    path_node = self._find_child(child, "identifier")
                    if not path_node:
                        path_node = self._find_child(child, "crate")
                        if not path_node:
                            path_node = self._find_child(child, "self")

                new_prefix = ""
                if path_node:
                    new_prefix = source[path_node.start_byte : path_node.end_byte]
                    if prefix:
                        new_prefix = f"{prefix}::{new_prefix}"

                use_list = self._find_child(child, "use_list")
                if use_list:
                    self._parse_use_tree(use_list, source, line, imports, new_prefix)

            elif child.type == "use_wildcard":
                # use foo::*
                module = f"{prefix}::*" if prefix else "*"
                imports.append(ImportInfo(module=module, line=line))

    def _extract_functions_from_tree(
        self,
        root: Any,
        source: str,
        file_path: str,
        top_level_only: bool = False,
    ) -> list[FunctionInfo]:
        """Extract function definitions from parse tree."""
        functions = []

        for node in self._find_nodes(root, ["function_item"]):
            if top_level_only:
                # Skip functions inside impl blocks
                parent = node.parent
                while parent:
                    if parent.type in ("impl_item", "trait_item"):
                        break
                    parent = parent.parent
                if parent and parent.type in ("impl_item", "trait_item"):
                    continue

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
        """Extract struct, enum, and trait definitions from parse tree."""
        types = []

        for node in self._find_nodes(root, ["struct_item", "enum_item", "trait_item"]):
            type_info = self._parse_type_node(node, source, file_path, root)
            if type_info:
                types.append(type_info)

        return types

    def _parse_function_node(
        self,
        node: Any,
        source: str,
        file_path: str,
        containing_type: str | None = None,
    ) -> FunctionInfo | None:
        """Parse a function definition node."""
        # Get function name
        name_node = self._find_child(node, "identifier")
        if not name_node:
            return None

        name = source[name_node.start_byte : name_node.end_byte]

        # Get visibility modifier
        visibility = self._get_visibility(node, source)

        # Get attributes as decorators
        decorators = self._get_attributes(node, source)

        # Check for async
        is_async = False
        for child in node.children:
            if source[child.start_byte : child.end_byte] == "async":
                is_async = True
                break

        # Get parameters
        params_node = self._find_child(node, "parameters")
        parameters, is_method = self._parse_parameters(params_node, source)

        # Get return type
        return_type = None
        ret_node = self._find_child(node, "return_type")
        if ret_node:
            type_node = ret_node.children[-1] if ret_node.children else None
            if type_node:
                return_type = source[type_node.start_byte : type_node.end_byte]

        # Get documentation
        docstring = self._get_rust_doc(node, source)

        # Build signature
        params_str = ", ".join(
            f"{p.name}: {p.type_annotation}" if p.type_annotation else p.name
            for p in parameters
        )
        vis_str = f"{visibility} " if visibility else ""
        async_str = "async " if is_async else ""
        ret_str = f" -> {return_type}" if return_type else ""
        signature = f"{vis_str}{async_str}fn {name}({params_str}){ret_str}"

        return FunctionInfo(
            name=name,
            signature=signature,
            file_path=file_path,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            docstring=docstring,
            parameters=parameters,
            return_type=return_type,
            decorators=tuple(decorators),
            is_async=is_async,
            is_method=is_method,
            containing_class=containing_type,
        )

    def _parse_type_node(
        self,
        node: Any,
        source: str,
        file_path: str,
        root: Any,
    ) -> ClassInfo | None:
        """Parse a struct, enum, or trait definition."""
        is_trait = node.type == "trait_item"
        is_enum = node.type == "enum_item"

        # Get type name
        name_node = self._find_child(node, "type_identifier")
        if not name_node:
            return None

        name = source[name_node.start_byte : name_node.end_byte]

        # Get visibility
        visibility = self._get_visibility(node, source)

        # Get attributes as decorators
        decorators = self._get_attributes(node, source)
        if visibility:
            decorators.insert(0, visibility)

        # Get supertraits (for traits) or derive traits
        bases = []
        trait_bounds = self._find_child(node, "trait_bounds")
        if trait_bounds:
            for child in trait_bounds.children:
                if child.type in ("type_identifier", "scoped_type_identifier", "generic_type"):
                    bases.append(source[child.start_byte : child.end_byte])

        # Get documentation
        docstring = self._get_rust_doc(node, source)

        # Find methods from impl blocks
        methods = []
        for impl_node in self._find_nodes(root, ["impl_item"]):
            # Check if this impl is for our type
            type_node = self._find_child(impl_node, "type_identifier")
            if not type_node:
                type_node = self._find_child(impl_node, "generic_type")

            if type_node:
                impl_type = source[type_node.start_byte : type_node.end_byte]
                # Handle generic types like Foo<T>
                impl_type_name = impl_type.split("<")[0]
                if impl_type_name == name:
                    # Get trait being implemented (if any)
                    trait_node = None
                    for child in impl_node.children:
                        if child.type == "type_identifier" and child != type_node:
                            trait_node = child
                            break
                        elif child.type == "scoped_type_identifier":
                            trait_node = child
                            break

                    # Extract methods from declaration_list
                    decl_list = self._find_child(impl_node, "declaration_list")
                    if decl_list:
                        for func_node in self._find_nodes(decl_list, ["function_item"]):
                            method_info = self._parse_function_node(func_node, source, file_path, name)
                            if method_info:
                                methods.append(method_info)

        # For traits, also extract method signatures
        if is_trait:
            decl_list = self._find_child(node, "declaration_list")
            if decl_list:
                for func_node in self._find_nodes(decl_list, ["function_signature_item", "function_item"]):
                    method_info = self._parse_function_node(func_node, source, file_path, name)
                    if method_info:
                        methods.append(method_info)

        return ClassInfo(
            name=name,
            file_path=file_path,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            docstring=docstring,
            bases=tuple(bases),
            decorators=tuple(decorators),
            methods=tuple(methods),
            is_abstract=is_trait,
        )

    def _parse_parameters(
        self,
        params_node: Any,
        source: str,
    ) -> tuple[tuple[ParameterInfo, ...], bool]:
        """Parse function parameters. Returns (parameters, is_method)."""
        parameters = []
        is_method = False

        if not params_node:
            return tuple(parameters), is_method

        for child in params_node.children:
            if child.type == "self_parameter":
                # &self, &mut self, self, mut self
                self_text = source[child.start_byte : child.end_byte]
                parameters.append(ParameterInfo(name=self_text, type_annotation="Self"))
                is_method = True

            elif child.type == "parameter":
                name_node = self._find_child(child, "identifier")
                if name_node:
                    name = source[name_node.start_byte : name_node.end_byte]
                    type_node = None
                    for c in child.children:
                        if c.type not in ("identifier", "mutable_specifier", ":"):
                            type_node = c
                            break
                    type_str = source[type_node.start_byte : type_node.end_byte] if type_node else None
                    parameters.append(ParameterInfo(name=name, type_annotation=type_str))
                else:
                    # Pattern parameter (destructuring)
                    pattern_node = self._find_child(child, "tuple_pattern")
                    if not pattern_node:
                        pattern_node = self._find_child(child, "struct_pattern")
                    if pattern_node:
                        pattern = source[pattern_node.start_byte : pattern_node.end_byte]
                        parameters.append(ParameterInfo(name=pattern))

        return tuple(parameters), is_method

    def _get_visibility(self, node: Any, source: str) -> str | None:
        """Get visibility modifier (pub, pub(crate), etc.)."""
        vis_node = self._find_child(node, "visibility_modifier")
        if vis_node:
            return source[vis_node.start_byte : vis_node.end_byte]
        return None

    def _get_attributes(self, node: Any, source: str) -> list[str]:
        """Get attributes (#[...]) as decorators."""
        attributes = []

        prev = node.prev_sibling
        while prev:
            if prev.type == "attribute_item":
                attr_text = source[prev.start_byte : prev.end_byte]
                # Extract attribute name
                match = re.match(r"#\[(\w+)", attr_text)
                if match:
                    attributes.insert(0, match.group(1))
            elif prev.type not in ("line_comment", "block_comment"):
                break
            prev = prev.prev_sibling

        return attributes

    def _get_rust_doc(self, node: Any, source: str) -> str | None:
        """Get Rust documentation comment (/// or /** comments)."""
        comments = []
        prev = node.prev_sibling

        while prev:
            if prev.type == "line_comment":
                comment = source[prev.start_byte : prev.end_byte]
                if comment.startswith("///"):
                    comments.insert(0, comment[3:].strip())
                else:
                    break
            elif prev.type == "block_comment":
                comment = source[prev.start_byte : prev.end_byte]
                if comment.startswith("/**"):
                    comments.insert(0, self._clean_block_comment(comment[3:]))
                else:
                    break
            elif prev.type == "attribute_item":
                # Skip attributes
                prev = prev.prev_sibling
                continue
            else:
                break
            prev = prev.prev_sibling

        return "\n".join(comments) if comments else None

    def _clean_block_comment(self, comment: str) -> str:
        """Clean block comment."""
        if comment.endswith("*/"):
            comment = comment[:-2]
        lines = []
        for line in comment.split("\n"):
            line = line.strip()
            if line.startswith("*"):
                line = line[1:].strip()
            lines.append(line)
        return "\n".join(lines).strip()

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
