from dataclasses import FrozenInstanceError
from pathlib import Path, PurePosixPath

import pytest

from eag.source.metrics import AnalysisMetrics
from eag.source.models import (
    AnalysisResult,
    Dependency,
    Documentation,
    ModuleIdentity,
    SourceFileIdentity,
    SourceLocation,
    Symbol,
    SymbolIdentity,
)
from eag.source.state import (
    DependencyKind,
    SymbolKind,
    Visibility,
)


class TestSourceLocation:
    def test_valid(self):
        loc = SourceLocation(
            path=PurePosixPath("src/eag/cli.py"), line=10, column=4, end_line=10, end_column=20
        )
        assert loc.line == 10

    def test_line_must_be_positive(self):
        with pytest.raises(ValueError):
            SourceLocation(
                path=PurePosixPath("src/main.py"), line=0, column=0, end_line=0, end_column=0
            )

    def test_end_line_before_start_line(self):
        with pytest.raises(ValueError):
            SourceLocation(
                path=PurePosixPath("src/main.py"), line=10, column=0, end_line=5, end_column=0
            )

    def test_immutable(self):
        loc = SourceLocation(
            path=PurePosixPath("src/main.py"), line=1, column=1, end_line=1, end_column=1
        )
        with pytest.raises(FrozenInstanceError):
            loc.line = 5


class TestDocumentation:
    def test_defaults(self):
        doc = Documentation()
        assert doc.summary == ""

    def test_immutable(self):
        doc = Documentation(summary="Test")
        with pytest.raises(FrozenInstanceError):
            doc.summary = "New"


class TestSourceFileIdentity:
    def test_valid(self):
        ident = SourceFileIdentity(
            absolute_path=Path("/repo/src/main.py"),
            repository_path=PurePosixPath("src/main.py"),
            language="python",
            fingerprint="abc123",
        )
        assert ident.language == "python"

    def test_relative_path_rejected(self):
        with pytest.raises(ValueError):
            SourceFileIdentity(
                absolute_path=Path("repo/src/main.py"),
                repository_path=PurePosixPath("src/main.py"),
                language="python",
                fingerprint="abc123",
            )

    def test_empty_language_rejected(self):
        with pytest.raises(ValueError):
            SourceFileIdentity(
                absolute_path=Path("/repo/src/main.py"),
                repository_path=PurePosixPath("src/main.py"),
                language="",
                fingerprint="abc123",
            )


class TestSymbolIdentity:
    def test_valid(self):
        ident = SymbolIdentity(
            qualified_name="eag.main.run", module="eag.main", kind=SymbolKind.FUNCTION
        )
        assert ident.kind == SymbolKind.FUNCTION

    def test_empty_qualified_name_rejected(self):
        with pytest.raises(ValueError):
            SymbolIdentity(qualified_name="", module="eag.main", kind=SymbolKind.FUNCTION)


class TestSymbol:
    def setup_method(self):
        self.ident = SymbolIdentity(
            qualified_name="eag.main.run", module="eag.main", kind=SymbolKind.FUNCTION
        )
        self.loc = SourceLocation(
            path=PurePosixPath("src/main.py"), line=1, column=0, end_line=1, end_column=10
        )

    def test_valid(self):
        sym = Symbol(identity=self.ident, location=self.loc)
        assert sym.visibility == Visibility.PUBLIC

    def test_invalid_attributes_type(self):
        with pytest.raises(TypeError):
            Symbol(identity=self.ident, location=self.loc, attributes={"key": "val"})  # type: ignore[arg-type]

    def test_immutable(self):
        sym = Symbol(identity=self.ident, location=self.loc)
        with pytest.raises(FrozenInstanceError):
            sym.visibility = Visibility.PRIVATE


class TestDependency:
    def test_valid(self):
        dep = Dependency(source="eag.main", target="os.path", kind=DependencyKind.IMPORT)
        assert dep.resolved is False

    def test_empty_target_rejected(self):
        with pytest.raises(ValueError):
            Dependency(source="eag.main", target="", kind=DependencyKind.IMPORT)


class TestAnalysisResult:
    def setup_method(self):
        self.ident = SourceFileIdentity(
            absolute_path=Path("/repo/src/main.py"),
            repository_path=PurePosixPath("src/main.py"),
            language="python",
            fingerprint="abc123",
        )
        self.module = ModuleIdentity(name="eag.main", path=PurePosixPath("src/main.py"))

    def test_defaults(self):
        res = AnalysisResult(identity=self.ident, module=self.module)
        assert res.symbols == ()
        assert isinstance(res.metrics, AnalysisMetrics)

    def test_invalid_symbols_type(self):
        with pytest.raises(TypeError):
            AnalysisResult(identity=self.ident, module=self.module, symbols=[])  # type: ignore[arg-type]
