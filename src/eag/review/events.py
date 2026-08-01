"""Engineering Review events for EAG."""

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class ReviewEvent:
    review_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True, kw_only=True)
class ReviewStarted(ReviewEvent):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class IssueDetected(ReviewEvent):
    issue_id: str
    severity: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SuggestionGenerated(ReviewEvent):
    suggestion_id: str
    priority: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ReflectionStarted(ReviewEvent):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class ReflectionCompleted(ReviewEvent):
    confidence: float


@dataclass(frozen=True, slots=True, kw_only=True)
class ReviewCompleted(ReviewEvent):
    decision: str
    score: int
