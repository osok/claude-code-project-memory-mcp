"""TypeScript code extractor using tree-sitter."""

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


class TypeScriptExtractor(LanguageExtractor):
    """Extract code elements from TypeScript source files.

    Uses tree-sitter-typescript for parsing TypeScript and TSX files.
    Handles functions, arrow functions, classes, interfaces, and imports.
    """

    @property
    def language(self) -> str:
        return "typescript"

    def __init__(self) -> None:
        """Initialize TypeScript extractor."""
        try:
            import tree_sitter_languages

            self._parser = tree_sitter_languages.get_parser("typescript")
            self._language = tree_sitter_languages.get_language("typescript")
        except ImportError:
            self._parser = None
            self._language = None

    def extract(self, source: str, file_path: str) -> ParseResult:
        """Extract all code elements from TypeScript source."""
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
        # Look for leading comment block
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
        """Extract imports from parse tree."""
        imports = []

        for node in self._find_nodes(root, ["import_statement"]):
            line = node.start_point[0] + 1

            # Get the module specifier (source)
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

                        # Check for alias: import { x as y }
                        for i, child in enumerate(spec.children):
                            if child.type == "identifier":
                                if alias_node is None:
                                    name_node = child
                                else:
                                    alias_node = child
                            elif source[child.start_byte : child.end_byte] == "as":
                                # Next identifier is alias
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
            # Skip if inside a class and we want top-level only
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

        # Also handle exported arrow functions assigned to variables
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
                if value_node:
                    name_node = self._find_child(declarator, "identifier")
                    if name_node:
                        func_info = self._parse_arrow_function_with_name(
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
        """Extract class and interface definitions from parse tree."""
        classes = []

        # Include abstract_class_declaration for abstract classes
        class_types = ["class_declaration", "class_expression", "abstract_class_declaration"]
        for node in self._find_nodes(root, class_types):
            class_info = self._parse_class_node(node, source, file_path)
            if class_info:
                classes.append(class_info)

        # Extract TypeScript interfaces (stored as ClassInfo with is_abstract=True)
        for node in self._find_nodes(root, ["interface_declaration"]):
            interface_info = self._parse_interface_node(node, source, file_path)
            if interface_info:
                classes.append(interface_info)

        return classes

    def _parse_interface_node(
        self,
        node: Any,
        source: str,
        file_path: str,
    ) -> ClassInfo | None:
        """Parse a TypeScript interface declaration node."""
        # Get interface name
        name_node = self._find_child(node, "type_identifier")
        if not name_node:
            return None

        name = source[name_node.start_byte : name_node.end_byte]

        # Get extended interfaces
        bases = []
        extends_clause = self._find_child(node, "extends_type_clause")
        if extends_clause:
            for child in extends_clause.children:
                if child.type in ("type_identifier", "generic_type"):
                    bases.append(source[child.start_byte : child.end_byte])

        # Get documentation
        docstring = self._get_jsdoc_comment(node, source)

        # Extract method signatures from interface body
        methods = []
        body = self._find_child(node, "interface_body") or self._find_child(node, "object_type")
        if body:
            for prop in self._find_nodes(body, ["method_signature", "property_signature"]):
                if prop.type == "method_signature":
                    method = self._parse_method_signature(prop, source, file_path, name)
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
            is_abstract=True,  # Interfaces are treated as abstract
        )

    def _parse_method_signature(
        self,
        node: Any,
        source: str,
        file_path: str,
        interface_name: str,
    ) -> FunctionInfo | None:
        """Parse an interface method signature."""
        name_node = self._find_child(node, "property_identifier")
        if not name_node:
            return None

        name = source[name_node.start_byte : name_node.end_byte]

        # Get parameters
        params_node = self._find_child(node, "formal_parameters")
        parameters = self._parse_parameters(params_node, source) if params_node else ()

        # Get return type
        return_type = None
        type_annotation = self._find_child(node, "type_annotation")
        if type_annotation:
            for child in type_annotation.children:
                if child.type not in (":", ):
                    return_type = source[child.start_byte : child.end_byte]
                    break

        # Build signature
        params_str = ", ".join(
            f"{p.name}: {p.type_annotation}" if p.type_annotation else p.name
            for p in parameters
        )
        ret_str = f": {return_type}" if return_type else ""
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

    def _parse_function_node(
        self,
        node: Any,
        source: str,
        file_path: str,
    ) -> FunctionInfo | None:
        """Parse a function definition node."""
        # Get function name
        name_node = self._find_child(node, "identifier")
        if not name_node:
            # For arrow functions or anonymous functions, skip
            if node.type == "arrow_function":
                return None
            name = "<anonymous>"
        else:
            name = source[name_node.start_byte : name_node.end_byte]

        # Get parameters
        params_node = self._find_child(node, "formal_parameters")
        parameters = self._parse_parameters(params_node, source) if params_node else ()

        # Get return type
        return_type = None
        type_annotation = self._find_child(node, "type_annotation")
        if type_annotation:
            # Skip the ': ' part
            for child in type_annotation.children:
                if child.type not in (":", ):
                    return_type = source[child.start_byte : child.end_byte]
                    break

        # Get decorators
        decorators = self._get_decorators(node, source)

        # Get docstring (JSDoc comment before function)
        docstring = self._get_jsdoc_comment(node, source)

        # Build signature
        params_str = ", ".join(
            f"{p.name}: {p.type_annotation}" if p.type_annotation else p.name
            for p in parameters
        )
        ret_str = f": {return_type}" if return_type else ""
        is_async = self._is_async(node, source)
        async_prefix = "async " if is_async else ""
        is_generator = node.type == "generator_function_declaration"
        gen_marker = "*" if is_generator else ""
        signature = f"{async_prefix}function{gen_marker} {name}({params_str}){ret_str}"

        return FunctionInfo(
            name=name,
            signature=signature,
            file_path=file_path,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            docstring=docstring,
            parameters=parameters,
            return_type=return_type,
            decorators=decorators,
            is_async=is_async,
            is_method=node.type == "method_definition",
        )

    def _parse_arrow_function_with_name(
        self,
        arrow_node: Any,
        name_node: Any,
        source: str,
        file_path: str,
    ) -> FunctionInfo | None:
        """Parse an arrow function assigned to a variable."""
        name = source[name_node.start_byte : name_node.end_byte]

        # Get parameters
        params_node = self._find_child(arrow_node, "formal_parameters")
        if not params_node:
            # Single parameter without parens: x => x
            params_node = self._find_child(arrow_node, "identifier")
            if params_node:
                param_name = source[params_node.start_byte : params_node.end_byte]
                parameters = (ParameterInfo(name=param_name),)
            else:
                parameters = ()
        else:
            parameters = self._parse_parameters(params_node, source)

        # Get return type from variable declarator's type annotation
        return_type = None
        parent = name_node.parent
        if parent:
            type_annotation = self._find_child(parent, "type_annotation")
            if type_annotation:
                for child in type_annotation.children:
                    if child.type not in (":", ):
                        return_type = source[child.start_byte : child.end_byte]
                        break

        is_async = self._is_async(arrow_node, source)

        # Build signature
        params_str = ", ".join(
            f"{p.name}: {p.type_annotation}" if p.type_annotation else p.name
            for p in parameters
        )
        ret_str = f": {return_type}" if return_type else ""
        async_prefix = "async " if is_async else ""
        signature = f"{async_prefix}{name} = ({params_str}){ret_str} => ..."

        # Get JSDoc from variable declaration
        docstring = self._get_jsdoc_comment(name_node.parent.parent, source)

        return FunctionInfo(
            name=name,
            signature=signature,
            file_path=file_path,
            start_line=arrow_node.start_point[0] + 1,
            end_line=arrow_node.end_point[0] + 1,
            docstring=docstring,
            parameters=parameters,
            return_type=return_type,
            is_async=is_async,
        )

    def _parse_class_node(
        self,
        node: Any,
        source: str,
        file_path: str,
    ) -> ClassInfo | None:
        """Parse a class definition node."""
        # Get class name
        name_node = self._find_child(node, "type_identifier")
        if not name_node:
            name_node = self._find_child(node, "identifier")
        if not name_node:
            return None

        name = source[name_node.start_byte : name_node.end_byte]

        # Get base classes (extends)
        bases = []
        heritage = self._find_child(node, "class_heritage")
        if heritage:
            extends_clause = self._find_child(heritage, "extends_clause")
            if extends_clause:
                for child in extends_clause.children:
                    if child.type in ("identifier", "type_identifier", "member_expression"):
                        bases.append(source[child.start_byte : child.end_byte])

            # Get implements clause
            implements_clause = self._find_child(heritage, "implements_clause")
            if implements_clause:
                for child in implements_clause.children:
                    if child.type in ("identifier", "type_identifier", "generic_type"):
                        interface_name = source[child.start_byte : child.end_byte]
                        bases.append(f"implements {interface_name}")

        # Get decorators
        decorators = self._get_decorators(node, source)

        # Get docstring (JSDoc)
        docstring = self._get_jsdoc_comment(node, source)

        # Extract methods
        methods = []
        body = self._find_child(node, "class_body")
        if body:
            for method_node in self._find_nodes(body, ["method_definition", "public_field_definition"]):
                if method_node.type == "method_definition":
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
            decorators=decorators,
            methods=tuple(methods),
            is_abstract="abstract" in decorators or self._is_abstract_class(node, source),
        )

    def _parse_method_node(
        self,
        node: Any,
        source: str,
        file_path: str,
        class_name: str,
    ) -> FunctionInfo | None:
        """Parse a method definition node."""
        # Get method name
        name_node = self._find_child(node, "property_identifier")
        if not name_node:
            name_node = self._find_child(node, "computed_property_name")
        if not name_node:
            return None

        name = source[name_node.start_byte : name_node.end_byte]

        # Check access modifiers
        is_static = False
        is_private = False
        accessibility = None

        for child in node.children:
            child_text = source[child.start_byte : child.end_byte]
            if child_text == "static":
                is_static = True
            elif child_text == "private":
                accessibility = "private"
            elif child_text == "protected":
                accessibility = "protected"
            elif child_text == "public":
                accessibility = "public"

        # Get parameters
        params_node = self._find_child(node, "formal_parameters")
        parameters = self._parse_parameters(params_node, source) if params_node else ()

        # Get return type
        return_type = None
        type_annotation = self._find_child(node, "type_annotation")
        if type_annotation:
            for child in type_annotation.children:
                if child.type not in (":", ):
                    return_type = source[child.start_byte : child.end_byte]
                    break

        # Check for getter/setter
        is_property = False
        for child in node.children:
            child_text = source[child.start_byte : child.end_byte]
            if child_text in ("get", "set"):
                is_property = True
                break

        is_async = self._is_async(node, source)

        # Build signature
        params_str = ", ".join(
            f"{p.name}: {p.type_annotation}" if p.type_annotation else p.name
            for p in parameters
        )
        ret_str = f": {return_type}" if return_type else ""
        static_str = "static " if is_static else ""
        async_str = "async " if is_async else ""
        signature = f"{static_str}{async_str}{name}({params_str}){ret_str}"

        docstring = self._get_jsdoc_comment(node, source)

        return FunctionInfo(
            name=name,
            signature=signature,
            file_path=file_path,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            docstring=docstring,
            parameters=parameters,
            return_type=return_type,
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
            if child.type in ("required_parameter", "optional_parameter"):
                param = self._parse_single_parameter(child, source)
                if param:
                    parameters.append(param)
            elif child.type == "rest_pattern":
                # ...args
                name_node = self._find_child(child, "identifier")
                name = source[name_node.start_byte : name_node.end_byte] if name_node else "args"
                type_ann = None
                type_node = self._find_child(child, "type_annotation")
                if type_node:
                    for tc in type_node.children:
                        if tc.type not in (":", ):
                            type_ann = source[tc.start_byte : tc.end_byte]
                            break
                parameters.append(ParameterInfo(name=f"...{name}", type_annotation=type_ann, is_variadic=True))
            elif child.type == "identifier":
                # Simple parameter
                name = source[child.start_byte : child.end_byte]
                parameters.append(ParameterInfo(name=name))

        return tuple(parameters)

    def _parse_single_parameter(self, node: Any, source: str) -> ParameterInfo | None:
        """Parse a single parameter node."""
        # Get parameter name
        name_node = None
        for child in node.children:
            if child.type == "identifier":
                name_node = child
                break
            elif child.type in ("object_pattern", "array_pattern"):
                # Destructuring pattern
                name_node = child
                break

        if not name_node:
            return None

        name = source[name_node.start_byte : name_node.end_byte]

        # Get type annotation
        type_ann = None
        type_node = self._find_child(node, "type_annotation")
        if type_node:
            for child in type_node.children:
                if child.type not in (":", ):
                    type_ann = source[child.start_byte : child.end_byte]
                    break

        # Get default value
        default = None
        for i, child in enumerate(node.children):
            if source[child.start_byte : child.end_byte] == "=":
                if i + 1 < len(node.children):
                    default_node = node.children[i + 1]
                    default = source[default_node.start_byte : default_node.end_byte]
                    break

        is_optional = node.type == "optional_parameter" or "?" in name

        return ParameterInfo(
            name=name.rstrip("?"),
            type_annotation=type_ann,
            default_value=default,
        )

    def _get_decorators(self, node: Any, source: str) -> tuple[str, ...]:
        """Get decorators for a class or method."""
        decorators = []

        # Check previous siblings for decorator patterns
        prev = node.prev_sibling
        while prev:
            if prev.type == "decorator":
                dec_text = source[prev.start_byte : prev.end_byte]
                match = re.match(r"@(\w+)", dec_text)
                if match:
                    decorators.append(match.group(1))
            elif prev.type != "comment":
                break
            prev = prev.prev_sibling

        # Check for inline modifiers like 'abstract', 'export'
        for child in node.children:
            text = source[child.start_byte : child.end_byte]
            if text in ("abstract", "export", "default"):
                decorators.append(text)

        return tuple(reversed(decorators))

    def _get_jsdoc_comment(self, node: Any, source: str) -> str | None:
        """Get JSDoc comment before a node."""
        prev = node.prev_sibling
        while prev:
            if prev.type == "comment":
                comment = source[prev.start_byte : prev.end_byte]
                if comment.startswith("/**"):
                    return self._clean_jsdoc(comment)
            elif prev.type not in ("decorator", "comment"):
                break
            prev = prev.prev_sibling
        return None

    def _clean_jsdoc(self, comment: str) -> str:
        """Clean JSDoc comment."""
        # Remove /** and */
        comment = comment.strip()
        if comment.startswith("/**"):
            comment = comment[3:]
        if comment.endswith("*/"):
            comment = comment[:-2]

        # Remove leading * from each line
        lines = []
        for line in comment.split("\n"):
            line = line.strip()
            if line.startswith("*"):
                line = line[1:].strip()
            lines.append(line)

        return "\n".join(lines).strip()

    def _is_async(self, node: Any, source: str) -> bool:
        """Check if function is async."""
        # Check for 'async' keyword in children
        for child in node.children:
            if source[child.start_byte : child.end_byte] == "async":
                return True
        return False

    def _is_abstract_class(self, node: Any, source: str) -> bool:
        """Check if class is abstract."""
        for child in node.children:
            if source[child.start_byte : child.end_byte] == "abstract":
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
