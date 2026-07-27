"""Source domain events for EAG."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceEvent:
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceParsed(SourceEvent):
    path: str
    language: str
    symbol_count: int
    import_count: int
    success: bool


# ─── Retained for High-Level Semantic Analysis Backward Compatibility ─────────


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceAnalysisStarted(SourceEvent):
    path: Path


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceAnalysisCompleted(SourceEvent):
    path: Path
    result: Any


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceAnalysisFailed(SourceEvent):
    path: Path
    error: str


@dataclass(frozen=True, slots=True, kw_only=True)
class TransformationStarted(SourceEvent):
    name: str
    target: str


@dataclass(frozen=True, slots=True, kw_only=True)
class TransformationValidated(SourceEvent):
    name: str
    success: bool
    diagnostics: tuple[Any, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class TransformationApplied(SourceEvent):
    name: str
    files_modified: int
    duration_ms: float
