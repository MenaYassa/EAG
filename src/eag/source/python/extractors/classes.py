import ast

from eag.source.python.extractors.functions import FunctionExtractor
from eag.source.python.models import PythonClass


class ClassExtractor:
    def __init__(self) -> None:
        self._function_extractor = FunctionExtractor()

    def extract(self, tree: ast.Module) -> tuple[PythonClass, ...]:
        classes: list[PythonClass] = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(self._extract_class(node))
        return tuple(classes)

    def _extract_class(self, node: ast.ClassDef) -> PythonClass:
        bases = tuple(ast.unparse(b) for b in node.bases)
        decorators = tuple(ast.unparse(d) for d in node.decorator_list)
        methods = self._function_extractor.extract_methods(node)
        return PythonClass(
            name=node.name,
            bases=bases,
            methods=methods,
            decorators=decorators,
            docstring=ast.get_docstring(node),
            line=node.lineno,
            col=node.col_offset,
        )
