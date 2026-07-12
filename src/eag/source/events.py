from dataclasses import dataclass
from pathlib import Path

from eag.events import Event
from eag.source.models import AnalysisResult


@dataclass(frozen=True, kw_only=True)
class SourceEvent(Event):
    path: Path


@dataclass(frozen=True, kw_only=True)
class SourceAnalysisStarted(SourceEvent):
    pass


@dataclass(frozen=True, kw_only=True)
class SourceAnalysisCompleted(SourceEvent):
    result: AnalysisResult


@dataclass(frozen=True, kw_only=True)
class SourceAnalysisFailed(SourceEvent):
    error: str
