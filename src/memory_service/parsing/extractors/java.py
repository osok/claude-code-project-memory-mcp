"""Java code extractor using tree-sitter."""

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


class JavaExtractor(LanguageExtractor):
    """Extract code elements from Java source files.

    Uses tree-sitter-java for parsing Java source files.
    Handles classes, interfaces, enums, methods, and imports.
    """

    @property
    def language(self) -> str:
        return "java"

    def __init__(self) -> None:
        """Initialize Java extractor."""
        try:
            import tree_sitter_languages

            self._parser = tree_sitter_languages.get_parser("java")
            self._language = tree_sitter_languages.get_language("java")
        except ImportError:
            self._parser = None
            self._language = None

    def extract(self, source: str, file_path: str) -> ParseResult:
        """Extract all code elements from Java source."""
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
            result.classes = self._extract_classes_from_tree(root, source, file_path)
            # Top-level functions don't exist in Java, but we extract them from classes
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
        for class_info in self._extract_classes_from_tree(tree.root_node, source, file_path):
            functions.extend(class_info.methods)
        return functions

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

    def _extract_package_doc(self, root: Any, source: str) -> str | None:
        """Extract package-level Javadoc comment."""
        for child in root.children:
            if child.type == "comment":
                comment = source[child.start_byte : child.end_byte]
                if comment.startswith("/**"):
                    return self._clean_javadoc(comment)
            elif child.type == "block_comment":
                comment = source[child.start_byte : child.end_byte]
                if comment.startswith("/**"):
                    return self._clean_javadoc(comment)
            elif child.type not in ("comment", "block_comment", "package_declaration"):
                break
        return None

    def _extract_imports_from_tree(self, root: Any, source: str) -> list[ImportInfo]:
        """Extract imports from parse tree."""
        imports = []

        for node in self._find_nodes(root, ["import_declaration"]):
            line = node.start_point[0] + 1

            # Check for static import
            is_static = False
            for child in node.children:
                if source[child.start_byte : child.end_byte] == "static":
                    is_static = True
                    break

            # Get the scoped identifier
            scope_node = self._find_child(node, "scoped_identifier")
            if not scope_node:
                # Try simple identifier
                id_node = self._find_child(node, "identifier")
                if id_node:
                    module = source[id_node.start_byte : id_node.end_byte]
                else:
                    continue
            else:
                module = source[scope_node.start_byte : scope_node.end_byte]

            # Check for wildcard import
            asterisk = self._find_child(node, "asterisk")
            if asterisk:
                module += ".*"

            imports.append(ImportInfo(
                module=module,
                line=line,
            ))

        return imports

    def _extract_classes_from_tree(
        self,
        root: Any,
        source: str,
        file_path: str,
    ) -> list[ClassInfo]:
        """Extract class, interface, and enum definitions from parse tree."""
        classes = []

        for node in self._find_nodes(root, ["class_declaration", "interface_declaration", "enum_declaration"]):
            class_info = self._parse_class_node(node, source, file_path)
            if class_info:
                classes.append(class_info)

        return classes

    def _parse_class_node(
        self,
        node: Any,
        source: str,
        file_path: str,
    ) -> ClassInfo | None:
        """Parse a class/interface/enum definition node."""
        # Get class name
        name_node = self._find_child(node, "identifier")
        if not name_node:
            return None

        name = source[name_node.start_byte : name_node.end_byte]

        # Get modifiers (public, abstract, final, etc.)
        modifiers = self._get_modifiers(node, source)

        # Get annotations as decorators
        decorators = self._get_annotations(node, source)

        # Get base classes (extends)
        bases = []
        superclass = self._find_child(node, "superclass")
        if superclass:
            type_node = self._find_child(superclass, "type_identifier")
            if type_node:
                bases.append(source[type_node.start_byte : type_node.end_byte])

        # Get interfaces (implements)
        super_interfaces = self._find_child(node, "super_interfaces")
        if super_interfaces:
            for child in self._find_nodes(super_interfaces, ["type_identifier", "generic_type"]):
                interface_name = source[child.start_byte : child.end_byte]
                bases.append(f"implements {interface_name}")

        # For interfaces, get extends
        extends_interfaces = self._find_child(node, "extends_interfaces")
        if extends_interfaces:
            for child in self._find_nodes(extends_interfaces, ["type_identifier", "generic_type"]):
                interface_name = source[child.start_byte : child.end_byte]
                bases.append(f"extends {interface_name}")

        # Get Javadoc
        docstring = self._get_javadoc_comment(node, source)

        # Extract methods
        methods = []
        body = self._find_child(node, "class_body")
        if not body:
            body = self._find_child(node, "interface_body")
        if not body:
            body = self._find_child(node, "enum_body")

        if body:
            for method_node in self._find_nodes(body, ["method_declaration", "constructor_declaration"]):
                method = self._parse_method_node(method_node, source, file_path, name)
                if method:
                    methods.append(method)

        is_interface = node.type == "interface_declaration"
        is_abstract = "abstract" in modifiers or is_interface

        return ClassInfo(
            name=name,
            file_path=file_path,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            docstring=docstring,
            bases=tuple(bases),
            decorators=tuple(decorators + modifiers),
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
        """Parse a method or constructor definition node."""
        is_constructor = node.type == "constructor_declaration"

        # Get method name
        if is_constructor:
            name_node = self._find_child(node, "identifier")
        else:
            name_node = self._find_child(node, "identifier")

        if not name_node:
            return None

        name = source[name_node.start_byte : name_node.end_byte]

        # Get modifiers
        modifiers = self._get_modifiers(node, source)

        # Get annotations
        annotations = self._get_annotations(node, source)

        # Get return type
        return_type = None
        if not is_constructor:
            # Look for type nodes before the identifier
            for child in node.children:
                if child.type in ("type_identifier", "generic_type", "void_type", "integral_type",
                                 "floating_point_type", "boolean_type", "array_type"):
                    return_type = source[child.start_byte : child.end_byte]
                    break

        # Get parameters
        params_node = self._find_child(node, "formal_parameters")
        parameters = self._parse_parameters(params_node, source) if params_node else ()

        # Get throws clause
        throws = []
        throws_node = self._find_child(node, "throws")
        if throws_node:
            for child in self._find_nodes(throws_node, ["type_identifier"]):
                throws.append(source[child.start_byte : child.end_byte])

        # Get Javadoc
        docstring = self._get_javadoc_comment(node, source)

        # Build signature
        params_str = ", ".join(
            f"{p.type_annotation} {p.name}" if p.type_annotation else p.name
            for p in parameters
        )
        mods_str = " ".join(modifiers)
        if mods_str:
            mods_str += " "
        ret_str = f"{return_type} " if return_type else ""
        throws_str = f" throws {', '.join(throws)}" if throws else ""
        signature = f"{mods_str}{ret_str}{name}({params_str}){throws_str}"

        is_static = "static" in modifiers
        is_abstract = "abstract" in modifiers

        return FunctionInfo(
            name=name,
            signature=signature,
            file_path=file_path,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            docstring=docstring,
            parameters=parameters,
            return_type=return_type,
            decorators=tuple(annotations),
            is_method=True,
            is_static=is_static,
            containing_class=class_name,
        )

    def _parse_parameters(self, params_node: Any, source: str) -> tuple[ParameterInfo, ...]:
        """Parse method parameters."""
        parameters = []

        for child in params_node.children:
            if child.type == "formal_parameter":
                param = self._parse_single_parameter(child, source)
                if param:
                    parameters.append(param)
            elif child.type == "spread_parameter":
                # Varargs: Type... name
                type_node = None
                name_node = None
                for c in child.children:
                    if c.type in ("type_identifier", "generic_type", "array_type"):
                        type_node = c
                    elif c.type == "variable_declarator":
                        name_node = self._find_child(c, "identifier")
                    elif c.type == "identifier":
                        name_node = c

                name = source[name_node.start_byte : name_node.end_byte] if name_node else "args"
                type_ann = source[type_node.start_byte : type_node.end_byte] if type_node else None
                parameters.append(ParameterInfo(
                    name=name,
                    type_annotation=f"{type_ann}..." if type_ann else None,
                    is_variadic=True,
                ))

        return tuple(parameters)

    def _parse_single_parameter(self, node: Any, source: str) -> ParameterInfo | None:
        """Parse a single formal parameter."""
        type_node = None
        name_node = None

        for child in node.children:
            if child.type in ("type_identifier", "generic_type", "array_type",
                            "integral_type", "floating_point_type", "boolean_type"):
                type_node = child
            elif child.type == "identifier":
                name_node = child
            elif child.type == "variable_declarator":
                name_node = self._find_child(child, "identifier")

        if not name_node:
            return None

        name = source[name_node.start_byte : name_node.end_byte]
        type_ann = source[type_node.start_byte : type_node.end_byte] if type_node else None

        return ParameterInfo(
            name=name,
            type_annotation=type_ann,
        )

    def _get_modifiers(self, node: Any, source: str) -> list[str]:
        """Get modifiers for a class or method."""
        modifiers = []
        modifier_keywords = {"public", "private", "protected", "static", "final",
                           "abstract", "synchronized", "native", "strictfp", "transient", "volatile"}

        for child in node.children:
            if child.type == "modifiers":
                for mod_child in child.children:
                    text = source[mod_child.start_byte : mod_child.end_byte]
                    if text in modifier_keywords:
                        modifiers.append(text)
            text = source[child.start_byte : child.end_byte]
            if text in modifier_keywords:
                modifiers.append(text)

        return modifiers

    def _get_annotations(self, node: Any, source: str) -> list[str]:
        """Get annotations for a class or method."""
        annotations = []

        # Look for annotations in modifiers or as siblings
        for child in node.children:
            if child.type == "modifiers":
                for mod_child in child.children:
                    if mod_child.type in ("annotation", "marker_annotation"):
                        ann_text = source[mod_child.start_byte : mod_child.end_byte]
                        # Extract annotation name
                        match = re.match(r"@(\w+)", ann_text)
                        if match:
                            annotations.append(match.group(1))
            elif child.type in ("annotation", "marker_annotation"):
                ann_text = source[child.start_byte : child.end_byte]
                match = re.match(r"@(\w+)", ann_text)
                if match:
                    annotations.append(match.group(1))

        return annotations

    def _get_javadoc_comment(self, node: Any, source: str) -> str | None:
        """Get Javadoc comment before a node."""
        prev = node.prev_sibling
        while prev:
            if prev.type in ("comment", "block_comment"):
                comment = source[prev.start_byte : prev.end_byte]
                if comment.startswith("/**"):
                    return self._clean_javadoc(comment)
            elif prev.type not in ("comment", "block_comment", "annotation", "marker_annotation", "modifiers"):
                break
            prev = prev.prev_sibling
        return None

    def _clean_javadoc(self, comment: str) -> str:
        """Clean Javadoc comment."""
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
