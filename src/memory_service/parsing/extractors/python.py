"""Python code extractor using tree-sitter."""

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


class PythonExtractor(LanguageExtractor):
    """Extract code elements from Python source files."""

    @property
    def language(self) -> str:
        return "python"

    def __init__(self) -> None:
        """Initialize Python extractor."""
        try:
            import tree_sitter_languages

            self._parser = tree_sitter_languages.get_parser("python")
            self._language = tree_sitter_languages.get_language("python")
        except ImportError:
            self._parser = None
            self._language = None

    def extract(self, source: str, file_path: str) -> ParseResult:
        """Extract all code elements from Python source."""
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
            result.calls = self._extract_calls_from_tree(root, source)

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
        """Extract module-level docstring."""
        for child in root.children:
            if child.type == "expression_statement":
                expr = child.children[0] if child.children else None
                if expr and expr.type == "string":
                    docstring = source[expr.start_byte : expr.end_byte]
                    return self._clean_docstring(docstring)
            elif child.type not in ("comment",):
                break
        return None

    def _extract_imports_from_tree(self, root: Any, source: str) -> list[ImportInfo]:
        """Extract imports from parse tree."""
        imports = []

        for node in self._find_nodes(root, ["import_statement", "import_from_statement"]):
            line = node.start_point[0] + 1

            if node.type == "import_statement":
                # import x, y, z
                for name_node in self._find_nodes(node, ["dotted_name", "aliased_import"]):
                    if name_node.type == "aliased_import":
                        module = source[name_node.children[0].start_byte : name_node.children[0].end_byte]
                        alias_node = self._find_child(name_node, "identifier")
                        alias = source[alias_node.start_byte : alias_node.end_byte] if alias_node else None
                    else:
                        module = source[name_node.start_byte : name_node.end_byte]
                        alias = None

                    imports.append(ImportInfo(
                        module=module,
                        alias=alias,
                        line=line,
                    ))

            elif node.type == "import_from_statement":
                # from x import y
                module_node = self._find_child(node, "dotted_name")
                if not module_node:
                    module_node = self._find_child(node, "relative_import")

                module = source[module_node.start_byte : module_node.end_byte] if module_node else ""
                is_relative = module.startswith(".")

                # Find imported names
                for name_node in self._find_nodes(node, ["dotted_name", "aliased_import"]):
                    if name_node == module_node:
                        continue

                    if name_node.type == "aliased_import":
                        name = source[name_node.children[0].start_byte : name_node.children[0].end_byte]
                        alias_node = self._find_child(name_node, "identifier")
                        alias = source[alias_node.start_byte : alias_node.end_byte] if alias_node else None
                    else:
                        name = source[name_node.start_byte : name_node.end_byte]
                        alias = None

                    imports.append(ImportInfo(
                        module=module,
                        name=name,
                        alias=alias,
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

        for node in self._find_nodes(root, ["function_definition"]):
            # Skip if inside a class and we want top-level only
            if top_level_only:
                parent = node.parent
                while parent:
                    if parent.type == "class_definition":
                        break
                    parent = parent.parent
                if parent and parent.type == "class_definition":
                    continue

            func_info = self._parse_function_node(node, source, file_path)
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

        for node in self._find_nodes(root, ["class_definition"]):
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
        # Get function name
        name_node = self._find_child(node, "identifier")
        if not name_node:
            return None

        name = source[name_node.start_byte : name_node.end_byte]

        # Get parameters
        params_node = self._find_child(node, "parameters")
        parameters = self._parse_parameters(params_node, source) if params_node else ()

        # Get return type
        return_type_node = self._find_child(node, "type")
        return_type = (
            source[return_type_node.start_byte : return_type_node.end_byte]
            if return_type_node
            else None
        )

        # Get decorators
        decorators = self._get_decorators(node, source)

        # Get docstring
        body = self._find_child(node, "block")
        docstring = self._get_function_docstring(body, source) if body else None

        # Check for async
        is_async = any(
            child.type == "async"
            for child in (node.prev_sibling,) if child
        ) or source[node.start_byte:node.start_byte + 5] == "async"

        # Build signature with async prefix if applicable
        params_str = ", ".join(
            f"{p.name}: {p.type_annotation}" if p.type_annotation else p.name
            for p in parameters
        )
        ret_str = f" -> {return_type}" if return_type else ""
        async_prefix = "async def " if is_async else "def "
        signature = f"{async_prefix}{name}({params_str}){ret_str}"

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
            is_method=False,
            is_static="staticmethod" in decorators,
            is_classmethod="classmethod" in decorators,
            is_property="property" in decorators,
        )

    def _parse_class_node(
        self,
        node: Any,
        source: str,
        file_path: str,
    ) -> ClassInfo | None:
        """Parse a class definition node."""
        # Get class name
        name_node = self._find_child(node, "identifier")
        if not name_node:
            return None

        name = source[name_node.start_byte : name_node.end_byte]

        # Get base classes
        bases = []
        arg_list = self._find_child(node, "argument_list")
        if arg_list:
            for child in arg_list.children:
                if child.type in ("identifier", "attribute"):
                    bases.append(source[child.start_byte : child.end_byte])

        # Get decorators
        decorators = self._get_decorators(node, source)

        # Get docstring
        body = self._find_child(node, "block")
        docstring = self._get_function_docstring(body, source) if body else None

        # Extract methods
        methods = []
        if body:
            for method_node in self._find_nodes(body, ["function_definition"]):
                method = self._parse_function_node(method_node, source, file_path)
                if method:
                    method = FunctionInfo(
                        **{**method.__dict__, "is_method": True, "containing_class": name}
                    )
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
            is_dataclass="dataclass" in decorators,
            is_abstract="ABC" in bases or "abstractmethod" in str(decorators),
        )

    def _parse_parameters(self, params_node: Any, source: str) -> tuple[ParameterInfo, ...]:
        """Parse function parameters."""
        parameters = []

        for child in params_node.children:
            if child.type in ("identifier", "typed_parameter", "default_parameter", "typed_default_parameter"):
                param = self._parse_single_parameter(child, source)
                if param:
                    parameters.append(param)
            elif child.type == "list_splat_pattern":
                # *args
                name_node = child.children[0] if child.children else None
                name = source[name_node.start_byte : name_node.end_byte] if name_node else "args"
                parameters.append(ParameterInfo(name=f"*{name}", is_variadic=True))
            elif child.type == "dictionary_splat_pattern":
                # **kwargs
                name_node = child.children[0] if child.children else None
                name = source[name_node.start_byte : name_node.end_byte] if name_node else "kwargs"
                parameters.append(ParameterInfo(name=f"**{name}", is_variadic=True))

        return tuple(parameters)

    def _parse_single_parameter(self, node: Any, source: str) -> ParameterInfo | None:
        """Parse a single parameter node."""
        if node.type == "identifier":
            name = source[node.start_byte : node.end_byte]
            return ParameterInfo(name=name)

        elif node.type == "typed_parameter":
            name_node = self._find_child(node, "identifier")
            type_node = self._find_child(node, "type")
            name = source[name_node.start_byte : name_node.end_byte] if name_node else ""
            type_ann = source[type_node.start_byte : type_node.end_byte] if type_node else None
            return ParameterInfo(name=name, type_annotation=type_ann)

        elif node.type in ("default_parameter", "typed_default_parameter"):
            name_node = self._find_child(node, "identifier")
            type_node = self._find_child(node, "type")
            name = source[name_node.start_byte : name_node.end_byte] if name_node else ""
            type_ann = source[type_node.start_byte : type_node.end_byte] if type_node else None

            # Get default value (last child that's not name or type)
            default = None
            for child in reversed(node.children):
                if child.type not in ("identifier", "type", ":"):
                    default = source[child.start_byte : child.end_byte]
                    break

            return ParameterInfo(name=name, type_annotation=type_ann, default_value=default)

        return None

    def _get_decorators(self, node: Any, source: str) -> tuple[str, ...]:
        """Get decorators for a function or class."""
        decorators = []

        # Check previous siblings for decorators
        prev = node.prev_sibling
        while prev and prev.type == "decorator":
            dec_text = source[prev.start_byte : prev.end_byte]
            # Extract decorator name (after @, before parentheses)
            match = re.match(r"@(\w+)", dec_text)
            if match:
                decorators.append(match.group(1))
            prev = prev.prev_sibling

        return tuple(reversed(decorators))

    def _get_function_docstring(self, body_node: Any, source: str) -> str | None:
        """Extract docstring from function body."""
        for child in body_node.children:
            if child.type == "expression_statement":
                expr = child.children[0] if child.children else None
                if expr and expr.type == "string":
                    docstring = source[expr.start_byte : expr.end_byte]
                    return self._clean_docstring(docstring)
            elif child.type not in ("comment", "pass_statement"):
                break
        return None

    def _clean_docstring(self, docstring: str) -> str:
        """Clean up a docstring by removing quotes and normalizing whitespace."""
        # Remove triple quotes
        if docstring.startswith('"""') or docstring.startswith("'''"):
            docstring = docstring[3:-3]
        elif docstring.startswith('"') or docstring.startswith("'"):
            docstring = docstring[1:-1]

        return docstring.strip()

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

    def _extract_calls_from_tree(self, root: Any, source: str) -> list[CallInfo]:
        """Extract function and method calls from parse tree."""
        calls = []

        for node in self._find_nodes(root, ["call"]):
            call_info = self._parse_call_node(node, source)
            if call_info:
                calls.append(call_info)

        return calls

    def _parse_call_node(self, node: Any, source: str) -> CallInfo | None:
        """Parse a function/method call node."""
        # Get the function being called
        func_node = node.children[0] if node.children else None
        if not func_node:
            return None

        line = node.start_point[0] + 1
        column = node.start_point[1]

        # Determine if it's a method call (attribute access)
        if func_node.type == "attribute":
            # Method call: obj.method()
            receiver_node = func_node.children[0] if func_node.children else None
            attr_node = self._find_child(func_node, "identifier")

            receiver = source[receiver_node.start_byte : receiver_node.end_byte] if receiver_node else None
            name = source[attr_node.start_byte : attr_node.end_byte] if attr_node else ""
            is_method_call = True
        elif func_node.type == "identifier":
            # Simple function call: func()
            name = source[func_node.start_byte : func_node.end_byte]
            receiver = None
            is_method_call = False
        else:
            # Other call types (e.g., subscript calls)
            name = source[func_node.start_byte : func_node.end_byte]
            receiver = None
            is_method_call = False

        # Get arguments
        args_node = self._find_child(node, "argument_list")
        arguments = self._parse_call_arguments(args_node, source) if args_node else ()

        return CallInfo(
            name=name,
            line=line,
            column=column,
            receiver=receiver,
            arguments=arguments,
            is_method_call=is_method_call,
        )

    def _parse_call_arguments(self, args_node: Any, source: str) -> tuple[str, ...]:
        """Parse call arguments."""
        arguments = []
        for child in args_node.children:
            if child.type not in ("(", ")", ","):
                arg_text = source[child.start_byte : child.end_byte]
                arguments.append(arg_text)
        return tuple(arguments)
