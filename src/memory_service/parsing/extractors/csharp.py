"""C# code extractor using tree-sitter."""

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


class CSharpExtractor(LanguageExtractor):
    """Extract code elements from C# source files.

    Uses tree-sitter-c-sharp for parsing C# source files.
    Handles classes, interfaces, structs, methods, properties, and using directives.
    """

    @property
    def language(self) -> str:
        return "c_sharp"

    def __init__(self) -> None:
        """Initialize C# extractor."""
        try:
            import tree_sitter_languages

            self._parser = tree_sitter_languages.get_parser("c_sharp")
            self._language = tree_sitter_languages.get_language("c_sharp")
        except ImportError:
            self._parser = None
            self._language = None

    def extract(self, source: str, file_path: str) -> ParseResult:
        """Extract all code elements from C# source."""
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

            result.module_docstring = self._extract_file_doc(root, source)
            result.imports = self._extract_imports_from_tree(root, source)
            result.classes = self._extract_types_from_tree(root, source, file_path)
            # C# doesn't have top-level functions (except in C# 9+ top-level statements)
            result.functions = []

        except Exception as e:
            result.errors.append(f"Parse error: {e}")

        return result

    def extract_functions(self, source: str, file_path: str) -> list[FunctionInfo]:
        """Extract all method definitions."""
        if not self._parser:
            return []

        tree = self._parser.parse(source.encode())
        functions = []
        for class_info in self._extract_types_from_tree(tree.root_node, source, file_path):
            functions.extend(class_info.methods)
        return functions

    def extract_classes(self, source: str, file_path: str) -> list[ClassInfo]:
        """Extract type definitions."""
        if not self._parser:
            return []

        tree = self._parser.parse(source.encode())
        return self._extract_types_from_tree(tree.root_node, source, file_path)

    def extract_imports(self, source: str) -> list[ImportInfo]:
        """Extract using directives."""
        if not self._parser:
            return []

        tree = self._parser.parse(source.encode())
        return self._extract_imports_from_tree(tree.root_node, source)

    def _extract_file_doc(self, root: Any, source: str) -> str | None:
        """Extract file-level documentation comment."""
        for child in root.children:
            if child.type == "comment":
                comment = source[child.start_byte : child.end_byte]
                if comment.startswith("///"):
                    return comment[3:].strip()
                elif comment.startswith("//"):
                    return comment[2:].strip()
                elif comment.startswith("/*"):
                    return self._clean_block_comment(comment)
            elif child.type not in ("comment", "using_directive", "extern_alias_directive"):
                break
        return None

    def _extract_imports_from_tree(self, root: Any, source: str) -> list[ImportInfo]:
        """Extract using directives from parse tree."""
        imports = []

        for node in self._find_nodes(root, ["using_directive"]):
            line = node.start_point[0] + 1

            # Check for static using
            is_static = False
            for child in node.children:
                if source[child.start_byte : child.end_byte] == "static":
                    is_static = True
                    break

            # Get the namespace or type
            name_node = self._find_child(node, "qualified_name")
            if not name_node:
                name_node = self._find_child(node, "identifier")
            if not name_node:
                name_node = self._find_child(node, "generic_name")

            if name_node:
                module = source[name_node.start_byte : name_node.end_byte]

                # Check for alias
                alias = None
                alias_node = self._find_child(node, "name_equals")
                if alias_node:
                    id_node = self._find_child(alias_node, "identifier")
                    if id_node:
                        alias = source[id_node.start_byte : id_node.end_byte]

                imports.append(ImportInfo(
                    module=module,
                    alias=alias,
                    line=line,
                ))

        return imports

    def _extract_types_from_tree(
        self,
        root: Any,
        source: str,
        file_path: str,
    ) -> list[ClassInfo]:
        """Extract class, interface, struct, and enum definitions."""
        types = []

        type_nodes = [
            "class_declaration",
            "interface_declaration",
            "struct_declaration",
            "enum_declaration",
            "record_declaration",
        ]

        for node in self._find_nodes(root, type_nodes):
            type_info = self._parse_type_node(node, source, file_path)
            if type_info:
                types.append(type_info)

        return types

    def _parse_type_node(
        self,
        node: Any,
        source: str,
        file_path: str,
    ) -> ClassInfo | None:
        """Parse a type definition node."""
        is_interface = node.type == "interface_declaration"
        is_enum = node.type == "enum_declaration"

        # Get type name
        name_node = self._find_child(node, "identifier")
        if not name_node:
            return None

        name = source[name_node.start_byte : name_node.end_byte]

        # Get modifiers
        modifiers = self._get_modifiers(node, source)

        # Get attributes as decorators
        decorators = self._get_attributes(node, source)
        decorators.extend(modifiers)

        # Get base types
        bases = []
        base_list = self._find_child(node, "base_list")
        if base_list:
            for child in self._find_nodes(base_list, ["identifier", "qualified_name", "generic_name"]):
                bases.append(source[child.start_byte : child.end_byte])

        # Get documentation
        docstring = self._get_xml_doc(node, source)

        # Extract methods
        methods = []
        body = self._find_child(node, "declaration_list")
        if body:
            # Methods
            for method_node in self._find_nodes(body, ["method_declaration"]):
                method_info = self._parse_method_node(method_node, source, file_path, name)
                if method_info:
                    methods.append(method_info)

            # Constructors
            for ctor_node in self._find_nodes(body, ["constructor_declaration"]):
                ctor_info = self._parse_constructor_node(ctor_node, source, file_path, name)
                if ctor_info:
                    methods.append(ctor_info)

            # Properties (as methods)
            for prop_node in self._find_nodes(body, ["property_declaration"]):
                prop_info = self._parse_property_node(prop_node, source, file_path, name)
                if prop_info:
                    methods.append(prop_info)

        is_abstract = "abstract" in modifiers or is_interface

        return ClassInfo(
            name=name,
            file_path=file_path,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            docstring=docstring,
            bases=tuple(bases),
            decorators=tuple(decorators),
            methods=tuple(methods),
            is_abstract=is_abstract,
        )

    def _parse_method_node(
        self,
        node: Any,
        source: str,
        file_path: str,
        class_name: str,
    ) -> FunctionInfo | None:
        """Parse a method declaration node."""
        # Get method name
        name_node = self._find_child(node, "identifier")
        if not name_node:
            return None

        name = source[name_node.start_byte : name_node.end_byte]

        # Get modifiers
        modifiers = self._get_modifiers(node, source)

        # Get attributes
        attributes = self._get_attributes(node, source)

        # Get return type
        return_type = None
        for child in node.children:
            if child.type in ("predefined_type", "identifier", "qualified_name",
                            "generic_name", "array_type", "nullable_type", "tuple_type"):
                return_type = source[child.start_byte : child.end_byte]
                break

        # Get parameters
        params_node = self._find_child(node, "parameter_list")
        parameters = self._parse_parameters(params_node, source) if params_node else ()

        # Get documentation
        docstring = self._get_xml_doc(node, source)

        # Build signature
        params_str = ", ".join(
            f"{p.type_annotation} {p.name}" if p.type_annotation else p.name
            for p in parameters
        )
        mods_str = " ".join(modifiers)
        if mods_str:
            mods_str += " "
        ret_str = f"{return_type} " if return_type else ""
        signature = f"{mods_str}{ret_str}{name}({params_str})"

        is_static = "static" in modifiers
        is_async = "async" in modifiers

        return FunctionInfo(
            name=name,
            signature=signature,
            file_path=file_path,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            docstring=docstring,
            parameters=parameters,
            return_type=return_type,
            decorators=tuple(attributes),
            is_async=is_async,
            is_method=True,
            is_static=is_static,
            containing_class=class_name,
        )

    def _parse_constructor_node(
        self,
        node: Any,
        source: str,
        file_path: str,
        class_name: str,
    ) -> FunctionInfo | None:
        """Parse a constructor declaration node."""
        name_node = self._find_child(node, "identifier")
        if not name_node:
            return None

        name = source[name_node.start_byte : name_node.end_byte]

        # Get modifiers
        modifiers = self._get_modifiers(node, source)

        # Get parameters
        params_node = self._find_child(node, "parameter_list")
        parameters = self._parse_parameters(params_node, source) if params_node else ()

        # Get documentation
        docstring = self._get_xml_doc(node, source)

        # Build signature
        params_str = ", ".join(
            f"{p.type_annotation} {p.name}" if p.type_annotation else p.name
            for p in parameters
        )
        mods_str = " ".join(modifiers)
        if mods_str:
            mods_str += " "
        signature = f"{mods_str}{name}({params_str})"

        return FunctionInfo(
            name=name,
            signature=signature,
            file_path=file_path,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            docstring=docstring,
            parameters=parameters,
            is_method=True,
            containing_class=class_name,
        )

    def _parse_property_node(
        self,
        node: Any,
        source: str,
        file_path: str,
        class_name: str,
    ) -> FunctionInfo | None:
        """Parse a property declaration as a method."""
        name_node = self._find_child(node, "identifier")
        if not name_node:
            return None

        name = source[name_node.start_byte : name_node.end_byte]

        # Get modifiers
        modifiers = self._get_modifiers(node, source)

        # Get property type
        prop_type = None
        for child in node.children:
            if child.type in ("predefined_type", "identifier", "qualified_name",
                            "generic_name", "array_type", "nullable_type"):
                prop_type = source[child.start_byte : child.end_byte]
                break

        # Get documentation
        docstring = self._get_xml_doc(node, source)

        # Build signature
        mods_str = " ".join(modifiers)
        if mods_str:
            mods_str += " "
        signature = f"{mods_str}{prop_type} {name} {{ get; set; }}"

        is_static = "static" in modifiers

        return FunctionInfo(
            name=name,
            signature=signature,
            file_path=file_path,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            docstring=docstring,
            return_type=prop_type,
            is_method=True,
            is_static=is_static,
            is_property=True,
            containing_class=class_name,
        )

    def _parse_parameters(self, params_node: Any, source: str) -> tuple[ParameterInfo, ...]:
        """Parse method parameters."""
        parameters = []

        if not params_node:
            return tuple(parameters)

        for child in params_node.children:
            if child.type == "parameter":
                param = self._parse_single_parameter(child, source)
                if param:
                    parameters.append(param)

        return tuple(parameters)

    def _parse_single_parameter(self, node: Any, source: str) -> ParameterInfo | None:
        """Parse a single parameter."""
        name_node = self._find_child(node, "identifier")
        if not name_node:
            return None

        name = source[name_node.start_byte : name_node.end_byte]

        # Get type
        type_str = None
        for child in node.children:
            if child.type in ("predefined_type", "identifier", "qualified_name",
                            "generic_name", "array_type", "nullable_type"):
                type_str = source[child.start_byte : child.end_byte]
                break

        # Get default value
        default = None
        equals_value = self._find_child(node, "equals_value_clause")
        if equals_value:
            for child in equals_value.children:
                if child.type != "=":
                    default = source[child.start_byte : child.end_byte]
                    break

        # Check for params keyword (variadic)
        is_variadic = False
        for child in node.children:
            if source[child.start_byte : child.end_byte] == "params":
                is_variadic = True
                break

        return ParameterInfo(
            name=name,
            type_annotation=type_str,
            default_value=default,
            is_variadic=is_variadic,
        )

    def _get_modifiers(self, node: Any, source: str) -> list[str]:
        """Get modifiers for a type or method."""
        modifiers = []
        modifier_keywords = {
            "public", "private", "protected", "internal",
            "static", "abstract", "virtual", "override", "sealed",
            "readonly", "const", "async", "partial", "extern", "new",
        }

        for child in node.children:
            if child.type == "modifier":
                text = source[child.start_byte : child.end_byte]
                if text in modifier_keywords:
                    modifiers.append(text)
            text = source[child.start_byte : child.end_byte]
            if text in modifier_keywords:
                modifiers.append(text)

        return modifiers

    def _get_attributes(self, node: Any, source: str) -> list[str]:
        """Get attributes as decorators."""
        attributes = []

        prev = node.prev_sibling
        while prev:
            if prev.type == "attribute_list":
                for attr in self._find_nodes(prev, ["attribute"]):
                    name_node = self._find_child(attr, "identifier")
                    if not name_node:
                        name_node = self._find_child(attr, "qualified_name")
                    if name_node:
                        attr_name = source[name_node.start_byte : name_node.end_byte]
                        attributes.insert(0, attr_name)
            elif prev.type not in ("comment", "attribute_list"):
                break
            prev = prev.prev_sibling

        return attributes

    def _get_xml_doc(self, node: Any, source: str) -> str | None:
        """Get XML documentation comment (/// comments)."""
        comments = []
        prev = node.prev_sibling

        while prev:
            if prev.type == "comment":
                comment = source[prev.start_byte : prev.end_byte]
                if comment.startswith("///"):
                    # Extract text content from XML
                    text = comment[3:].strip()
                    # Remove XML tags for readability
                    text = re.sub(r"<[^>]+>", "", text).strip()
                    if text:
                        comments.insert(0, text)
                else:
                    break
            elif prev.type == "attribute_list":
                # Skip attributes
                prev = prev.prev_sibling
                continue
            else:
                break
            prev = prev.prev_sibling

        return "\n".join(comments) if comments else None

    def _clean_block_comment(self, comment: str) -> str:
        """Clean block comment."""
        if comment.startswith("/*"):
            comment = comment[2:]
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
