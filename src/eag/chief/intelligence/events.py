"""AI Intelligence events for EAG."""

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class IntelligenceEvent:
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True, kw_only=True)
class ProviderRegistered(IntelligenceEvent):
    provider_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ModelRegistered(IntelligenceEvent):
    model_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SelectionStarted(IntelligenceEvent):
    capability: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SelectionCompleted(IntelligenceEvent):
    model_id: str
    confidence: float


@dataclass(frozen=True, slots=True, kw_only=True)
class ProviderUnavailable(IntelligenceEvent):
    provider_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class FallbackTriggered(IntelligenceEvent):
    primary_model_id: str
    fallback_model_id: str