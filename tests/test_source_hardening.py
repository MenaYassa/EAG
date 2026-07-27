"""Hardening tests for the Source Intelligence Platform (Sprint 6.5A)."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from eag.source.models import (
    SymbolKind,
)
from eag.source.python.provider import PythonSourceProvider
from eag.source.runtime import SourceRuntime


@dataclass
class MockEventBus:
    published_events: list[Any] = field(default_factory=list)

    def publish(self, event: Any) -> None:
        self.published_events.append(event)


@pytest.fixture
def provider() -> PythonSourceProvider:
    return PythonSourceProvider()


@pytest.fixture
def event_bus() -> MockEventBus:
    return MockEventBus()


@pytest.fixture
def runtime(event_bus: MockEventBus) -> SourceRuntime:
    return SourceRuntime(event_bus=event_bus)


class TestQualifiedNames:
    def test_nested_qualified_names(self, provider: PythonSourceProvider) -> None:
        code = "class A:\n    class B:\n        def x(self):\n            pass\n"
        doc = provider.parse(Path("test.py"), code)

        qnames = {s.qualified_name for s in doc.symbols}
        assert "A" in qnames
        assert "A.B" in qnames
        assert "A.B.x" in qnames

    def test_method_parent(self, provider: PythonSourceProvider) -> None:
        code = "class User:\n    def login(self):\n        pass\n"
        doc = provider.parse(Path("test.py"), code)

        method = next(s for s in doc.symbols if s.name == "login")
        assert method.parent == "User"
        assert method.kind == SymbolKind.METHOD


class TestAdvancedSymbols:
    def test_async_support(self, provider: PythonSourceProvider) -> None:
        code = "async def fetch_data():\n    pass\n"
        doc = provider.parse(Path("test.py"), code)

        func = doc.symbols[0]
        assert func.is_async is True

    def test_generator_support(self, provider: PythonSourceProvider) -> None:
        code = "def stream_data():\n    yield 1\n"
        doc = provider.parse(Path("test.py"), code)

        func = doc.symbols[0]
        assert func.is_generator is True

    def test_decorator_extraction(self, provider: PythonSourceProvider) -> None:
        code = "import functools\n\n@functools.lru_cache\ndef expensive_func():\n    pass\n"
        doc = provider.parse(Path("test.py"), code)

        func = next(s for s in doc.symbols if s.name == "expensive_func")
        assert "lru_cache" in func.decorators


class TestSymbolReferences:
    def test_reference_resolution(self, provider: PythonSourceProvider) -> None:
        code = "def foo():\n    pass\n\ndef bar():\n    foo()\n"
        doc = provider.parse(Path("test.py"), code)

        foo_sym = next(s for s in doc.symbols if s.name == "foo")
        assert len(foo_sym.references) == 1
        assert foo_sym.references[0].target == "foo"
        assert foo_sym.references[0].source == "bar"

    def test_multiple_references(self, provider: PythonSourceProvider) -> None:
        code = "def foo():\n    pass\n\ndef bar():\n    foo()\n    foo()\n"
        doc = provider.parse(Path("test.py"), code)

        foo_sym = next(s for s in doc.symbols if s.name == "foo")
        assert len(foo_sym.references) == 2


class TestImportUsage:
    def test_used_import(self, provider: PythonSourceProvider) -> None:
        code = "import os\n\nprint(os.getcwd())\n"
        doc = provider.parse(Path("test.py"), code)

        assert len(doc.imports) == 1
        assert doc.imports[0].used is True

    def test_unused_import(self, provider: PythonSourceProvider) -> None:
        code = "import os\n"
        doc = provider.parse(Path("test.py"), code)

        assert len(doc.imports) == 1
        assert doc.imports[0].used is False

    def test_from_import_usage(self, provider: PythonSourceProvider) -> None:
        code = "from pathlib import Path\n\np = Path('.')\n"
        doc = provider.parse(Path("test.py"), code)

        imp = doc.imports[0]
        assert imp.name == "Path"
        assert imp.used is True


class TestRuntimeDiagnostics:
    def test_runtime_metrics(self, runtime: SourceRuntime) -> None:
        runtime.parse(Path("test.py"), "def foo():\n    pass\n")
        metrics = runtime.metrics()

        assert metrics.files_parsed == 1
        assert metrics.symbols_extracted == 1
        assert metrics.imports_extracted == 0
        assert metrics.parse_failures == 0
        assert metrics.parse_time_ms > 0

    def test_runtime_health(self, runtime: SourceRuntime) -> None:
        health = runtime.health()
        assert health.providers_loaded == 1
        assert health.state == "READY"

    def test_runtime_explain(self, runtime: SourceRuntime) -> None:
        runtime.parse(Path("test.py"), "def foo():\n    pass\n")
        explanation = runtime.explain()

        assert "Source Intelligence Platform" in explanation
        assert "Files Parsed: 1" in explanation
        assert "Symbols Extracted: 1" in explanation


class TestSourceEvents:
    def test_source_parsed_event_published(
        self, runtime: SourceRuntime, event_bus: MockEventBus
    ) -> None:
        runtime.parse(Path("test.py"), "def foo():\n    pass\n")

        from eag.source.events import SourceParsed

        assert any(isinstance(e, SourceParsed) for e in event_bus.published_events)
        event = next(e for e in event_bus.published_events if isinstance(e, SourceParsed))
        assert event.symbol_count == 1
        assert event.success is True


class TestSymbolDeterminism:
    def test_deterministic_identities(self, provider: PythonSourceProvider) -> None:
        """Ensures identical code produces identical symbol IDs and ordering."""
        code = "def foo():\n    pass\n\nclass Bar:\n    def baz(self):\n        pass\n"
        path = Path("test_determinism.py")

        # Parse the exact same file twice
        doc1 = provider.parse(path, code)
        doc2 = provider.parse(path, code)

        # 1. Assert ordering is identical
        assert [s.name for s in doc1.symbols] == [s.name for s in doc2.symbols]

        # 2. Assert qualified names match
        foo1 = next(s for s in doc1.symbols if s.name == "foo")
        foo2 = next(s for s in doc2.symbols if s.name == "foo")
        assert foo1.qualified_name == foo2.qualified_name

        # 3. Assert IDs match perfectly across runs
        assert foo1.id == foo2.id
