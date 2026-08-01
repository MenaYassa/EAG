"""Engineering Review domain models for EAG."""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Protocol, runtime_checkable

from eag.review.enums import (
    IssueCategory,
    ReviewDecision,
    Severity,
    SuggestionPriority,
)


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
class ReviewIssue:
    """An immutable representation of an issue found during review."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    category: IssueCategory
    severity: Severity
    title: str
    description: str = ""
    location: str = ""
    recommendation: str = ""
    confidence: float = 1.0
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        if not isinstance(self.category, IssueCategory):
            raise TypeError("category must be an IssueCategory")
        if not isinstance(self.severity, Severity):
            raise TypeError("severity must be a Severity")
        object.__setattr__(self, "title", _validate_non_empty_str(self.title, "title"))
        object.__setattr__(self, "confidence", _validate_confidence(self.confidence))
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class ReviewSuggestion:
    """An actionable suggestion generated during review."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    priority: SuggestionPriority
    message: str
    rationale: str = ""
    estimated_impact: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        if not isinstance(self.priority, SuggestionPriority):
            raise TypeError("priority must be a SuggestionPriority")
        object.__setattr__(self, "message", _validate_non_empty_str(self.message, "message"))
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class ReviewFinding:
    """A grouped set of issues and suggestions forming a specific finding."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    summary: str = ""
    issues: tuple[ReviewIssue, ...] = ()
    suggestions: tuple[ReviewSuggestion, ...] = ()
    score: int = 100

    def __post_init__(self) -> None:
        object.__setattr__(self, "title", _validate_non_empty_str(self.title, "title"))
        object.__setattr__(self, "score", _validate_score(self.score))
        if not isinstance(self.issues, tuple):
            raise TypeError("issues must be a tuple")
        if not isinstance(self.suggestions, tuple):
            raise TypeError("suggestions must be a tuple")


@dataclass(frozen=True, slots=True, kw_only=True)
class Reflection:
    """EAG's internal reasoning about the review results."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    root_cause: str
    reasoning: str
    confidence: float = 1.0
    recommended_actions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "root_cause", _validate_non_empty_str(self.root_cause, "root_cause")
        )
        object.__setattr__(self, "reasoning", _validate_non_empty_str(self.reasoning, "reasoning"))
        object.__setattr__(self, "confidence", _validate_confidence(self.confidence))
        if not isinstance(self.recommended_actions, tuple):
            raise TypeError("recommended_actions must be a tuple")


@dataclass(frozen=True, slots=True, kw_only=True)
class ReviewMetrics:
    """Metrics collected during the review process."""

    issues_found: int = 0
    warnings: int = 0
    errors: int = 0
    critical: int = 0
    review_time_ms: float = 0.0
    confidence: float = 1.0
    approval_rate: float = 0.0
    average_score: float = 0.0

    def __post_init__(self) -> None:
        for field_name in ["issues_found", "warnings", "errors", "critical"]:
            val = getattr(self, field_name)
            if not isinstance(val, int) or isinstance(val, bool) or val < 0:
                raise ValueError(f"{field_name} must be a non-negative integer")
        object.__setattr__(self, "confidence", _validate_confidence(self.confidence))


@dataclass(frozen=True, slots=True, kw_only=True)
class ReviewReport:
    """The final, immutable artifact produced by the Review Runtime."""

    review_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    decision: ReviewDecision
    overall_score: int
    findings: tuple[ReviewFinding, ...] = ()
    reflection: Reflection | None = None
    metrics: ReviewMetrics = field(default_factory=ReviewMetrics)
    duration_ms: float = 0.0
    summary: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.decision, ReviewDecision):
            raise TypeError("decision must be a ReviewDecision")
        object.__setattr__(self, "overall_score", _validate_score(self.overall_score))
        if not isinstance(self.findings, tuple):
            raise TypeError("findings must be a tuple")
        if self.reflection is not None and not isinstance(self.reflection, Reflection):
            raise TypeError("reflection must be a Reflection or None")
        if not isinstance(self.metrics, ReviewMetrics):
            raise TypeError("metrics must be a ReviewMetrics")


@dataclass(frozen=True, slots=True, kw_only=True)
class ReviewContext:
    """Context provided to analyzers during a review."""

    workspace_path: Path
    execution_success: bool = True
    artifacts: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        if not isinstance(self.workspace_path, Path):
            raise TypeError("workspace_path must be a Path")
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@runtime_checkable
class ReviewAnalyzer(Protocol):
    """The contract for a review analyzer."""

    def analyze(self, context: ReviewContext) -> tuple[ReviewIssue, ...]: ...
