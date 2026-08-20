"""Redacted lifecycle events for governed LLM gateway requests."""

from __future__ import annotations

from dataclasses import dataclass

from eag.chief.intelligence.events import IntelligenceEvent
from eag.chief.intelligence.gateway.errors import GatewayErrorKind


@dataclass(frozen=True, slots=True, kw_only=True)
class GatewayEvent(IntelligenceEvent):
    """Base event correlated by request and trace without raw prompt/response content."""

    request_id: str
    trace_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class GatewayRequestStarted(GatewayEvent):
    schema_version: str


@dataclass(frozen=True, slots=True, kw_only=True)
class GatewayContextAssembled(GatewayEvent):
    context_fingerprint: str
    available_capability_count: int


@dataclass(frozen=True, slots=True, kw_only=True)
class GatewayRoutingSelected(GatewayEvent):
    provider_id: str
    model_id: str
    confidence: float


@dataclass(frozen=True, slots=True, kw_only=True)
class GatewayAttemptStarted(GatewayEvent):
    attempt: int
    provider_id: str
    model_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class GatewayAttemptFailed(GatewayEvent):
    attempt: int
    kind: GatewayErrorKind


@dataclass(frozen=True, slots=True, kw_only=True)
class GatewayFallbackTriggered(GatewayEvent):
    primary_model_id: str
    fallback_model_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class GatewayResponseValidated(GatewayEvent):
    plan_step_count: int
    required_capability_count: int


@dataclass(frozen=True, slots=True, kw_only=True)
class GatewayPolicyRejected(GatewayEvent):
    reason: str


@dataclass(frozen=True, slots=True, kw_only=True)
class GatewayCompleted(GatewayEvent):
    total_tokens: int
    estimated_cost: float


@dataclass(frozen=True, slots=True, kw_only=True)
class GatewayFailed(GatewayEvent):
    kind: GatewayErrorKind
    attempts: int
