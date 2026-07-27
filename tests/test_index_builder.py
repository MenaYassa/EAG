from pathlib import Path, PurePosixPath

import pytest

from eag.index.builder import RepositoryIndexBuilder
from eag.source.models import (
    AnalysisResult,
    Dependency,
    ModuleIdentity,
    SourceFileIdentity,
    SourceLocation,
    Symbol,
    SymbolIdentity,
)
from eag.source.state import DependencyKind, SymbolKind


@pytest.fixture
def mock_result():
    def _create(module_name: str, symbols: list[Symbol], deps: list[Dependency]):
        ident = SourceFileIdentity(
            absolute_path=Path(f"/repo/{module_name.replace('.', '/')}.py"),
            repository_path=PurePosixPath(f"{module_name.replace('.', '/')}.py"),
            language="python",
            fingerprint="abc",
        )
        module = ModuleIdentity(
            name=module_name, path=PurePosixPath(f"{module_name.replace('.', '/')}.py")
        )
        return AnalysisResult(
            identity=ident, module=module, symbols=tuple(symbols), dependencies=tuple(deps)
        )

    return _create


class TestRepositoryIndexBuilder:
    def test_build_empty(self):
        builder = RepositoryIndexBuilder("test")
        idx = builder.build()
        assert idx.statistics.modules == 0
        assert idx.symbols == ()

    def test_add_result(self, mock_result):
        builder = RepositoryIndexBuilder("test")

        sym = Symbol(
            identity=SymbolIdentity(
                qualified_name="eag.main.run", module="eag.main", kind=SymbolKind.FUNCTION
            ),
            location=SourceLocation(
                path=PurePosixPath("main.py"), line=1, column=0, end_line=1, end_column=10
            ),
        )
        dep = Dependency(source="eag.main", target="os.path", kind=DependencyKind.IMPORT)

        result = mock_result("eag.main", [sym], [dep])
        builder.add_result(result)

        idx = builder.build()

        assert idx.statistics.modules == 1
        assert idx.statistics.symbols == 1
        assert idx.statistics.functions == 1
        assert idx.statistics.dependencies == 1

        assert idx.find_symbol("eag.main.run") == sym
        assert idx.find_module("eag.main").name == "eag.main"
