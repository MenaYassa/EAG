import ast

from eag.source.python.models import PythonModule


class ModuleExtractor:
    def extract(self, tree: ast.Module, module_name: str) -> PythonModule:
        docstring = ast.get_docstring(tree)
        return PythonModule(name=module_name, docstring=docstring)
