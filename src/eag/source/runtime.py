from pathlib import Path
from typing import Any

from eag.events import EventBus
from eag.source.analyzer import AnalysisContext
from eag.source.events import (
    SourceAnalysisCompleted,
    SourceAnalysisFailed,
    SourceAnalysisStarted,
)
from eag.source.models import AnalysisResult
from eag.source.registry import SourceAnalyzerRegistry


class SourceRuntime:
    def __init__(self, registry: SourceAnalyzerRegistry, event_bus: EventBus) -> None:
        self._registry = registry
        self._event_bus = event_bus

    def supported_languages(self) -> list[str]:
        return self._registry.supported_languages()

    def analyze_file(
        self,
        path: Path,
        repository_root: Path,
        settings: Any,
        cache: Any,
    ) -> AnalysisResult:
        self._event_bus.publish(SourceAnalysisStarted(path=path))
        try:
            analyzer = self._registry.detect(path)
            context = AnalysisContext(
                path=path,
                repository_root=repository_root,
                settings=settings,
                cache=cache,
            )
            result = analyzer.analyze(context)
            self._event_bus.publish(SourceAnalysisCompleted(path=path, result=result))
            return result
        except Exception as e:
            self._event_bus.publish(SourceAnalysisFailed(path=path, error=str(e)))
            raise

    def analyze(
        self,
        path: Path,
        repository_root: Path,
        settings: Any,
        cache: Any,
    ) -> AnalysisResult:
        return self.analyze_file(path, repository_root, settings, cache)
