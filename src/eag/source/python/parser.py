import ast
import tokenize
from pathlib import Path

from eag.source.errors import AnalysisFailedError


class PythonParser:
    def parse(self, path: Path) -> ast.Module:
        try:
            with tokenize.open(path) as f:
                source = f.read()
            return ast.parse(source, filename=str(path))
        except SyntaxError as e:
            raise AnalysisFailedError(f"Syntax error in {path}: {e}") from e
        except Exception as e:
            raise AnalysisFailedError(f"Failed to parse {path}: {e}") from e
