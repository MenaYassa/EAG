from pathlib import Path

import pytest

from eag.source.analyzer import AnalysisContext
from eag.source.python.analyzer import PythonAnalyzer
from eag.source.state import SymbolKind, Visibility


@pytest.fixture
def analyzer():
    return PythonAnalyzer()


@pytest.fixture
def context(tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    src_dir = repo_root / "src" / "eag"
    src_dir.mkdir(parents=True)

    file_path = src_dir / "main.py"
    file_path.write_text('''
"""Module docstring."""
import os
from pathlib import Path

@dataclass
class User:
    """User class."""
    name: str
    
    def greet(self) -> str:
        return f"Hello {self.name}"

def main(name: str) -> None:
    """Main function."""
    print(f"Hello {name}")

CONSTANT = 42
''')

    return AnalysisContext(path=file_path, repository_root=repo_root, settings={}, cache=None)


def test_analyzer_supports(analyzer, tmp_path):
    assert analyzer.supports(tmp_path / "test.py") is True
    assert analyzer.supports(tmp_path / "test.js") is False


def test_analyzer_produces_result(analyzer, context):
    result = analyzer.analyze(context)

    assert result.identity.language == "python"
    assert result.module.name == "src.eag.main"

    # Verify extracted symbols documentation summaries
    main_func = next(s for s in result.symbols if s.identity.qualified_name.endswith(".main"))
    assert main_func.documentation.summary == "Main function."

    user_class = next(s for s in result.symbols if s.identity.qualified_name.endswith(".User"))
    assert user_class.documentation.summary == "User class."

    # Check overall symbols list properties
    assert len(result.symbols) == 3  # User class, greet method, main function

    assert user_class.identity.kind == SymbolKind.CLASS
    assert "is_dataclass" in user_class.attributes

    assert main_func.identity.kind == SymbolKind.FUNCTION
    assert main_func.visibility == Visibility.PUBLIC

    # Check dependencies
    assert len(result.dependencies) == 2
    assert any(d.target == "os" for d in result.dependencies)
    assert any(d.target == "pathlib.Path" for d in result.dependencies)

    # Check metrics
    assert result.metrics.lines > 0
    assert result.metrics.symbols == 3
    assert result.metrics.dependencies == 2


def test_analyzer_syntax_error(analyzer, tmp_path):
    file_path = tmp_path / "bad.py"
    file_path.write_text("def broken(:")

    context = AnalysisContext(path=file_path, repository_root=tmp_path, settings={}, cache=None)

    from eag.source.errors import AnalysisFailedError

    with pytest.raises(AnalysisFailedError):
        analyzer.analyze(context)
