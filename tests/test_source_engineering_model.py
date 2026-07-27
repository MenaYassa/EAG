"""Tests for the Engineering Source Model (Sprint 6.5A)."""

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from eag.source.models import (
    Diagnostic,
    DiagnosticSeverity,
    EngineeringSymbol,
    ImportModel,
    Language,
    Location,
    SourceDocument,
    SymbolKind,
    SymbolVisibility,
)
from eag.source.python.provider import PythonSourceProvider
from eag.source.registry import SourceRegistry
from eag.source.runtime import SourceRuntime


@pytest.fixture
def provider() -> PythonSourceProvider:
    return PythonSourceProvider()


@pytest.fixture
def runtime() -> SourceRuntime:
    return SourceRuntime()


class TestSourceModels:
    def test_document_is_immutable(self) -> None:
        doc = SourceDocument(path=Path("test.py"), language=Language.PYTHON, checksum="abc")
        with pytest.raises((FrozenInstanceError, AttributeError)):
            doc.checksum = "new"  # type: ignore[misc]

    def test_symbol_is_immutable(self) -> None:
        sym = EngineeringSymbol(name="foo", kind=SymbolKind.FUNCTION)
        with pytest.raises((FrozenInstanceError, AttributeError)):
            sym.name = "bar"  # type: ignore[misc]

    def test_import_model_is_immutable(self) -> None:
        imp = ImportModel(module="os")
        with pytest.raises((FrozenInstanceError, AttributeError)):
            imp.module = "sys"  # type: ignore[misc]

    def test_diagnostic_is_immutable(self) -> None:
        diag = Diagnostic(
            severity=DiagnosticSeverity.ERROR, message="Fail", location=Location(line=1)
        )
        with pytest.raises((FrozenInstanceError, AttributeError)):
            diag.message = "Ok"  # type: ignore[misc]


class TestPythonProviderExtraction:
    def test_extract_single_function(self, provider: PythonSourceProvider) -> None:
        code = "def hello():\n    pass\n"
        doc = provider.parse(Path("test.py"), code)

        assert len(doc.symbols) == 1
        assert doc.symbols[0].name == "hello"
        assert doc.symbols[0].kind == SymbolKind.FUNCTION

    def test_extract_multiple_functions(self, provider: PythonSourceProvider) -> None:
        code = "def foo():\n    pass\n\ndef bar():\n    pass\n"
        doc = provider.parse(Path("test.py"), code)

        assert len(doc.symbols) == 2
        names = [s.name for s in doc.symbols]
        assert "foo" in names
        assert "bar" in names

    def test_extract_class(self, provider: PythonSourceProvider) -> None:
        code = "class User:\n    pass\n"
        doc = provider.parse(Path("test.py"), code)

        assert len(doc.symbols) == 1
        assert doc.symbols[0].name == "User"
        assert doc.symbols[0].kind == SymbolKind.CLASS

    def test_extract_nested_class(self, provider: PythonSourceProvider) -> None:
        code = "class User:\n    class Profile:\n        pass\n"
        doc = provider.parse(Path("test.py"), code)

        # ast.walk flattens, so we expect both classes
        assert len(doc.symbols) == 2
        names = [s.name for s in doc.symbols]
        assert "User" in names
        assert "Profile" in names

    def test_extract_visibility(self, provider: PythonSourceProvider) -> None:
        code = (
            "def _protected():\n    pass\n\ndef __private():\n    pass\n\ndef public():\n    pass\n"
        )
        doc = provider.parse(Path("test.py"), code)

        visibilities = {s.name: s.visibility for s in doc.symbols}
        assert visibilities["_protected"] == SymbolVisibility.PROTECTED
        assert visibilities["__private"] == SymbolVisibility.PRIVATE
        assert visibilities["public"] == SymbolVisibility.PUBLIC


class TestPythonProviderImports:
    def test_simple_import(self, provider: PythonSourceProvider) -> None:
        code = "import os\n"
        doc = provider.parse(Path("test.py"), code)

        assert len(doc.imports) == 1
        assert doc.imports[0].module == "os"
        assert doc.imports[0].name is None

    def test_from_import(self, provider: PythonSourceProvider) -> None:
        code = "from os import path\n"
        doc = provider.parse(Path("test.py"), code)

        assert len(doc.imports) == 1
        assert doc.imports[0].module == "os"
        assert doc.imports[0].name == "path"

    def test_alias_import(self, provider: PythonSourceProvider) -> None:
        code = "import numpy as np\n"
        doc = provider.parse(Path("test.py"), code)

        assert len(doc.imports) == 1
        assert doc.imports[0].module == "numpy"
        assert doc.imports[0].alias == "np"

    def test_relative_import(self, provider: PythonSourceProvider) -> None:
        code = "from . import utils\n"
        doc = provider.parse(Path("test.py"), code)

        assert len(doc.imports) == 1
        assert doc.imports[0].relative is True
        assert doc.imports[0].name == "utils"


class TestPythonProviderDocument:
    def test_empty_file(self, provider: PythonSourceProvider) -> None:
        doc = provider.parse(Path("test.py"), "")
        assert len(doc.symbols) == 0
        assert len(doc.diagnostics) == 0

    def test_unicode_content(self, provider: PythonSourceProvider) -> None:
        code = "# This is a comment with unicode: ñ, ü, 😊\ndef foo():\n    pass\n"
        doc = provider.parse(Path("test.py"), code)
        assert len(doc.symbols) == 1

    def test_checksum_determinism(self, provider: PythonSourceProvider) -> None:
        code = "def foo():\n    pass\n"
        doc1 = provider.parse(Path("test.py"), code)
        doc2 = provider.parse(Path("test.py"), code)
        assert doc1.checksum == doc2.checksum

    def test_syntax_error_diagnostic(self, provider: PythonSourceProvider) -> None:
        code = "def foo(:\n    pass\n"
        doc = provider.parse(Path("test.py"), code)

        assert len(doc.diagnostics) == 1
        assert doc.diagnostics[0].severity == DiagnosticSeverity.ERROR
        assert "syntax-error" in doc.diagnostics[0].rule


class TestSourceRuntime:
    def test_provider_registration(self) -> None:
        registry = SourceRegistry()
        SourceRuntime(registry=registry)
        assert len(registry.list()) == 1

    def test_unsupported_language_raises(self) -> None:
        rt = SourceRuntime()
        with pytest.raises(Exception, match="No source provider supports path"):
            rt.parse(Path("test.ts"), "const x = 1;")
