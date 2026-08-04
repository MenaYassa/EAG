"""Reflection domain models for EAG."""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any

from eag.reflection.enums import FindingCategory, RecommendationPriority, Severity


def _validate_mapping(value: Mapping[str, Any], field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a Mapping")
    return MappingProxyType(dict(value))


def _validate_non_empty_str(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} cannot be empty or whitespace")
    return value.strip()


def _validate_confidence(value: float) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TypeError("confidence must be a float")
    if not (0.0 <= value <= 1.0):
        raise ValueError("confidence must be between 0.0 and 1.0")
    return float(value)


def _validate_score(value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError("score must be an integer")
    if not (0 <= value <= 100):
        raise ValueError("score must be between 0 and 100")
    return value


@dataclass(frozen=True, slots=True, kw_only=True)
class ReflectionFinding:
    """An immutable representation of an issue found during reflection."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    category: FindingCategory
    severity: Severity
    title: str
    description: str = ""
    evidence: str = ""
    confidence: float = 1.0
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        if not isinstance(self.category, FindingCategory):
            raise TypeError("category must be a FindingCategory")
        if not isinstance(self.severity, Severity):
            raise TypeError("severity must be a Severity")
        object.__setattr__(self, "title", _validate_non_empty_str(self.title, "title"))
        object.__setattr__(self, "confidence", _validate_confidence(self.confidence))
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class ReflectionRecommendation:
    """An actionable recommendation generated during reflection."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    priority: RecommendationPriority
    title: str
    description: str = ""
    action: str = ""
    confidence: float = 1.0
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        if not isinstance(self.priority, RecommendationPriority):
            raise TypeError("priority must be a RecommendationPriority")
        object.__setattr__(self, "title", _validate_non_empty_str(self.title, "title"))
        object.__setattr__(self, "confidence", _validate_confidence(self.confidence))
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class ReflectionSummary:
    """A summary of the reflection process."""

    strengths: tuple[str, ...] = ()
    weaknesses: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    opportunities: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in ["strengths", "weaknesses", "risks", "opportunities"]:
            if not isinstance(getattr(self, field_name), tuple):
                raise TypeError(f"{field_name} must be a tuple")


@dataclass(frozen=True, slots=True, kw_only=True)
class ReflectionMetrics:
    """Metrics derived during the reflection process."""

    planning_score: int = 100
    execution_score: int = 100
    review_score: int = 100
    worker_score: int = 100
    architecture_score: int = 100
    overall_score: int = 100

    def __post_init__(self) -> None:
        for field_name in [
            "planning_score",
            "execution_score",
            "review_score",
            "worker_score",
            "architecture_score",
            "overall_score",
        ]:
            object.__setattr__(self, field_name, _validate_score(getattr(self, field_name)))


@dataclass(frozen=True, slots=True, kw_only=True)
class ReflectionContext:
    """Context provided to the reflection engine."""

    run_id: str
    run_result: Any  # ChiefRuntime RunResult
    review_report: Any | None = None  # ReviewRuntime ReviewReport
    benchmark_result: Any | None = None  # BenchmarkRuntime BenchmarkResult
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _validate_non_empty_str(self.run_id, "run_id"))
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class ReflectionReport:
    """The final, immutable artifact produced by the Reflection Runtime."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    summary: ReflectionSummary = field(default_factory=ReflectionSummary)
    findings: tuple[ReflectionFinding, ...] = ()
    recommendations: tuple[ReflectionRecommendation, ...] = ()
    metrics: ReflectionMetrics = field(default_factory=ReflectionMetrics)
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _validate_non_empty_str(self.run_id, "run_id"))
        if not isinstance(self.summary, ReflectionSummary):
            raise TypeError("summary must be a ReflectionSummary")
        if not isinstance(self.findings, tuple):
            raise TypeError("findings must be a tuple")
        if not isinstance(self.recommendations, tuple):
            raise TypeError("recommendations must be a tuple")
        if not isinstance(self.metrics, ReflectionMetrics):
            raise TypeError("metrics must be a ReflectionMetrics")
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))
