from pathlib import Path, PurePosixPath

import pytest

from eag.explorer.formatter import JsonFormatter, TerminalFormatter
from eag.explorer.models import (
    FindSymbolRequest,
    ModuleRequest,
    OverviewRequest,
    SearchRequest,
    StatisticsRequest,
)
from eag.explorer.runtime import ExplorerRuntime
from eag.index.builder import RepositoryIndexBuilder
from eag.source.models import (
    Dependency,
    ModuleIdentity,
    SourceFileIdentity,
    SourceLocation,
    Symbol,
    SymbolIdentity,
)
from eag.source.state import DependencyKind, SymbolKind


@pytest.fixture
def mock_index():
    builder = RepositoryIndexBuilder("test-repo")

    ident = SourceFileIdentity(
        absolute_path=Path("/repo/main.py"),
        repository_path=PurePosixPath("main.py"),
        language="python",
        fingerprint="abc",
    )
    module = ModuleIdentity(name="eag.main", path=PurePosixPath("main.py"))

    sym1 = Symbol(
        identity=SymbolIdentity(
            qualified_name="eag.main.Kernel", module="eag.main", kind=SymbolKind.CLASS
        ),
        location=SourceLocation(
            path=PurePosixPath("main.py"), line=1, column=0, end_line=1, end_column=10
        ),
    )
    sym2 = Symbol(
        identity=SymbolIdentity(
            qualified_name="eag.main.run", module="eag.main", kind=SymbolKind.FUNCTION
        ),
        location=SourceLocation(
            path=PurePosixPath("main.py"), line=5, column=0, end_line=5, end_column=10
        ),
    )
    dep = Dependency(source="module", target="os.path", kind=DependencyKind.IMPORT)

    from eag.source.models import AnalysisResult

    result = AnalysisResult(
        identity=ident, module=module, symbols=(sym1, sym2), dependencies=(dep,)
    )
    builder.add_result(result)
    return builder.build()


@pytest.fixture
def runtime(mock_index):
    return ExplorerRuntime(mock_index, "test-repo")


class TestExplorerRuntime:
    def test_overview(self, runtime):
        view = runtime.overview(OverviewRequest())
        assert view.repository == "test-repo"
        assert view.modules == 1
        assert view.symbols == 2
        assert "Repository Intelligence" in view.capabilities

    def test_statistics(self, runtime):
        view = runtime.statistics(StatisticsRequest())
        assert view.modules == 1
        assert view.classes == 1
        assert view.functions == 1
        assert view.symbols == 2

    def test_find_symbol_exact(self, runtime):
        view = runtime.find_symbol(FindSymbolRequest(name="eag.main.Kernel"))
        assert view.name == "Kernel"
        assert view.kind == "class"

    def test_find_symbol_short(self, runtime):
        view = runtime.find_symbol(FindSymbolRequest(name="Kernel"))
        assert view.name == "Kernel"

    def test_find_symbol_not_found(self, runtime):
        from eag.explorer.errors import SymbolNotFoundError

        with pytest.raises(SymbolNotFoundError):
            runtime.find_symbol(FindSymbolRequest(name="Nonexistent"))

    def test_module(self, runtime):
        view = runtime.module(ModuleRequest(name="eag.main"))
        assert view.name == "eag.main"
        assert len(view.symbols) == 2

    def test_search(self, runtime):
        view = runtime.search(SearchRequest(query="Kernel"))
        assert len(view.results) == 1
        assert "eag.main.Kernel" in view.results[0]


class TestFormatters:
    def test_terminal_formatter(self, runtime):
        view = runtime.overview(OverviewRequest())
        formatter = TerminalFormatter()
        output = formatter.format(view)

        assert "Engineering Overview" in output
        assert "test-repo" in output

    def test_json_formatter(self, runtime):
        view = runtime.overview(OverviewRequest())
        formatter = JsonFormatter()
        output = formatter.format(view)

        import json

        data = json.loads(output)

        # If the output string was double-serialized, unwrap it once more:
        if isinstance(data, str):
            data = json.loads(data)

        assert data["repository"] == "test-repo"
        assert data["modules"] == 1
