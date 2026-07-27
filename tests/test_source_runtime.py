from pathlib import Path, PurePosixPath

import pytest

from eag.events import EventBus
from eag.source.events import (
    SourceAnalysisCompleted,
    SourceAnalysisFailed,
    SourceAnalysisStarted,
)
from eag.source.models import (
    AnalysisResult,
    ModuleIdentity,
    SourceFileIdentity,
)
from eag.source.registry import SourceAnalyzerRegistry
from eag.source.runtime import SourceRuntime


class MockAnalyzer:
    language = "python"
    extensions = frozenset({".py"})

    def supports(self, path: Path) -> bool:
        return path.suffix in self.extensions

    def analyze(self, context):
        ident = SourceFileIdentity(
            absolute_path=Path("/repo/main.py"),
            repository_path=PurePosixPath("main.py"),
            language="python",
            fingerprint="123",
        )
        module = ModuleIdentity(name="main", path=PurePosixPath("main.py"))
        return AnalysisResult(identity=ident, module=module)


class FailingAnalyzer:
    language = "python"
    extensions = frozenset({".py"})

    def supports(self, path: Path) -> bool:
        return path.suffix in self.extensions

    def analyze(self, context):
        raise RuntimeError("Parse error")


class TestSourceRuntime:
    def test_supported_languages(self):
        registry = SourceAnalyzerRegistry()
        registry.register(MockAnalyzer())
        runtime = SourceRuntime(registry, EventBus())
        assert "python" in runtime.supported_languages()

    def test_analyze_file_success(self, tmp_path):
        file = tmp_path / "main.py"
        file.write_text("print('hello')")

        registry = SourceAnalyzerRegistry()
        registry.register(MockAnalyzer())
        event_bus = EventBus()
        runtime = SourceRuntime(registry, event_bus)

        events = []
        event_bus.subscribe(SourceAnalysisStarted, lambda e: events.append(e))
        event_bus.subscribe(SourceAnalysisCompleted, lambda e: events.append(e))

        result = runtime.analyze_file(file, tmp_path, {}, {})

        assert isinstance(result, AnalysisResult)
        assert len(events) == 2
        assert isinstance(events[0], SourceAnalysisStarted)
        assert isinstance(events[1], SourceAnalysisCompleted)

    def test_analyze_file_failed(self, tmp_path):
        file = tmp_path / "main.py"
        file.write_text("def broken(")

        registry = SourceAnalyzerRegistry()
        registry.register(FailingAnalyzer())
        event_bus = EventBus()
        runtime = SourceRuntime(registry, event_bus)

        events = []
        event_bus.subscribe(SourceAnalysisStarted, lambda e: events.append(e))
        event_bus.subscribe(SourceAnalysisFailed, lambda e: events.append(e))

        with pytest.raises(RuntimeError):
            runtime.analyze_file(file, tmp_path, {}, {})

        assert len(events) == 2
        assert isinstance(events[0], SourceAnalysisStarted)
        assert isinstance(events[1], SourceAnalysisFailed)
        assert "Parse error" in events[1].error
