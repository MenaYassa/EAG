import ast

from eag.source.python.models import PythonFunction, PythonParameter


class FunctionExtractor:
    def extract(self, tree: ast.Module) -> tuple[PythonFunction, ...]:
        functions: list[PythonFunction] = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(self._extract_function(node))
        return tuple(functions)

    def extract_methods(self, class_node: ast.ClassDef) -> tuple[PythonFunction, ...]:
        methods: list[PythonFunction] = []
        for node in ast.iter_child_nodes(class_node):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(self._extract_function(node))
        return tuple(methods)

    def _extract_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> PythonFunction:
        params = self._extract_arguments(node.args)
        returns = ast.unparse(node.returns) if node.returns else None
        decorators = tuple(ast.unparse(d) for d in node.decorator_list)
        return PythonFunction(
            name=node.name,
            parameters=params,
            returns=returns,
            decorators=decorators,
            is_async=isinstance(node, ast.AsyncFunctionDef),
            docstring=ast.get_docstring(node),
            line=node.lineno,
            col=node.col_offset,
        )

    def _extract_arguments(self, args: ast.arguments) -> tuple[PythonParameter, ...]:
        params: list[PythonParameter] = []

        defaults_offset = len(args.args) - len(args.defaults)
        for i, arg in enumerate(args.args):
            default = None
            if i >= defaults_offset:
                default = ast.unparse(args.defaults[i - defaults_offset])
            params.append(
                PythonParameter(
                    name=arg.arg,
                    annotation=ast.unparse(arg.annotation) if arg.annotation else None,
                    default=default,
                    kind="POSITIONAL",
                )
            )

        if args.vararg:
            params.append(
                PythonParameter(
                    name=args.vararg.arg,
                    annotation=ast.unparse(args.vararg.annotation)
                    if args.vararg.annotation
                    else None,
                    kind="VARARGS",
                )
            )

        for i, arg in enumerate(args.kwonlyargs):
            default_node = args.kw_defaults[i]
            default = ast.unparse(default_node) if default_node else None
            params.append(
                PythonParameter(
                    name=arg.arg,
                    annotation=ast.unparse(arg.annotation) if arg.annotation else None,
                    default=default,
                    kind="KEYWORD",
                )
            )

        if args.kwarg:
            params.append(
                PythonParameter(
                    name=args.kwarg.arg,
                    annotation=ast.unparse(args.kwarg.annotation)
                    if args.kwarg.annotation
                    else None,
                    kind="KWARGS",
                )
            )

        return tuple(params)
