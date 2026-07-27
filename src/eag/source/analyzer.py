from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from eag.source.models import AnalysisResult


@dataclass(frozen=True, slots=True, kw_only=True)
class AnalysisContext:
    path: Path
    repository_root: Path
    settings: Any
    cache: Any


@runtime_checkable
class SourceAnalyzer(Protocol):
    language: str
    extensions: frozenset[str]

    def supports(self, path: Path) -> bool: ...

    def analyze(self, context: AnalysisContext) -> AnalysisResult: ...
