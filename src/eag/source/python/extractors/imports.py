import ast

from eag.source.python.models import PythonImport


class ImportExtractor:
    def extract(self, tree: ast.Module) -> tuple[PythonImport, ...]:
        imports: list[PythonImport] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(PythonImport(module=alias.name, alias=alias.asname))
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imports.append(
                        PythonImport(
                            module=node.module or "",
                            symbol=alias.name,
                            alias=alias.asname,
                            relative_level=node.level or 0,
                        )
                    )
        return tuple(imports)
