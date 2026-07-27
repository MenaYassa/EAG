"""Capability domain events for EAG Chief Engineer."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from eag.events import Event  # Make sure this base Event is imported


@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityEvent(Event):  # <-- Inherit Event here!
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityRegistered(CapabilityEvent):
    capability_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityMatched(CapabilityEvent):
    goal_id: str
    capability_id: str
    score: float


@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityRanked(CapabilityEvent):
    goal_id: str
    ranked_count: int


@dataclass(frozen=True, slots=True, kw_only=True)
class RecommendationProduced(CapabilityEvent):
    goal_id: str
    winner_id: str | None
    confidence: float
