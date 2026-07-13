from dataclasses import replace
from pathlib import Path

from eag.source.analyzer import AnalysisContext, SourceAnalyzer
from eag.source.errors import AnalysisFailedError
from eag.source.models import AnalysisResult
from eag.source.python.extractors import (
    ClassExtractor,
    FunctionExtractor,
    ImportExtractor,
    ModuleExtractor,
    SemanticExtractor,
)
from eag.source.python.parser import PythonParser
from eag.source.python.translator import PythonTranslator


class PythonAnalyzer(SourceAnalyzer):
    language = "python"
    extensions = frozenset({".py"})

    def __init__(self) -> None:
        self._parser = PythonParser()
        self._module_extractor = ModuleExtractor()
        self._import_extractor = ImportExtractor()
        self._function_extractor = FunctionExtractor()
        self._class_extractor = ClassExtractor()
        self._translator = PythonTranslator()
        self._semantic_extractor = SemanticExtractor()

    def supports(self, path: Path) -> bool:
        return path.suffix in self.extensions

    def analyze(self, context: AnalysisContext) -> AnalysisResult:
        path = context.path

        try:
            lines = path.read_text().splitlines()
        except Exception as e:
            raise AnalysisFailedError(f"Failed to read {path}: {e}") from e

        tree = self._parser.parse(path)

        module_name = self._derive_module_name(path, context.repository_root)

        py_module = self._module_extractor.extract(tree, module_name)
        py_imports = self._import_extractor.extract(tree)
        py_functions = self._function_extractor.extract(tree)
        py_classes = self._class_extractor.extract(tree)
        py_semantic = self._semantic_extractor.extract(tree, module_name)

        py_module = replace(
            py_module,
            imports=py_imports,
            functions=py_functions,
            classes=py_classes,
            semantic_relationships=py_semantic,
        )

        result = self._translator.translate(path, context.repository_root, py_module, lines)
        return result

    def _derive_module_name(self, path: Path, repo_root: Path) -> str:
        try:
            rel_path = path.relative_to(repo_root)
            parts = list(rel_path.with_suffix("").parts)

            # Strip 'src' if it's the root package directory
            if parts and parts[0] == "src":
                parts.pop(0)

            if parts and parts[-1] == "__init__":
                parts.pop()
            return ".".join(parts)
        except ValueError:
            return path.stem
