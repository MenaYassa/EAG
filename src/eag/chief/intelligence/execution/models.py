"""Execution domain models for EAG."""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any

from eag.chief.intelligence.execution.enums import (
    DiscoveryStatus,
    ExecutionState,
    ProviderHealthStatus,
    RetryStrategy,
    TraceEventType,
)


def _validate_mapping(value: Mapping[str, Any], field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a Mapping")
    return MappingProxyType(dict(value))


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionOptions:
    """Options for executing an AI request."""

    temperature: float = 0.7
    max_tokens: int = 1000
    timeout_ms: int = 30000
    retry_count: int = 2
    retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    stream: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class TraceEvent:
    """A single event in an execution trace."""

    type: TraceEventType
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    message: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionTrace:
    """An immutable trace of an execution's lifecycle."""

    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    events: tuple[TraceEvent, ...] = ()

    def add_event(self, event: TraceEvent) -> "ExecutionTrace":
        """Returns a new trace with the event added."""
        return ExecutionTrace(trace_id=self.trace_id, events=self.events + (event,))


@dataclass(frozen=True, slots=True, kw_only=True)
class UsageMetrics:
    """Token usage metrics for an execution."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionResult:
    """The immutable result of an AI execution."""

    success: bool
    content: str = ""
    usage: UsageMetrics = field(default_factory=UsageMetrics)
    duration_ms: float = 0.0
    provider_id: str = ""
    model_id: str = ""
    state: ExecutionState = ExecutionState.SUCCESS
    trace: ExecutionTrace = field(default_factory=ExecutionTrace)
    error: str | None = None
    attempts: int = 1
    fallback_used: bool = False


@dataclass(frozen=True, slots=True, kw_only=True)
class ProviderHealth:
    """Health status of an AI provider."""

    provider_id: str
    status: ProviderHealthStatus = ProviderHealthStatus.UNKNOWN
    latency_ms: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    consecutive_failures: int = 0
    last_success: datetime | None = None
    last_failure: datetime | None = None

    @property
    def is_available(self) -> bool:
        return self.status in [ProviderHealthStatus.HEALTHY, ProviderHealthStatus.DEGRADED]


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionContext:
    """Context for a single execution request."""

    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    prompt: str
    model_id: str
    provider_id: str
    options: ExecutionOptions = field(default_factory=ExecutionOptions)
    trace: ExecutionTrace = field(default_factory=ExecutionTrace)


@dataclass(frozen=True, slots=True, kw_only=True)
class DiscoveredModel:
    """A model discovered from a provider."""

    provider_id: str
    model_id: str
    name: str
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)


@dataclass(frozen=True, slots=True, kw_only=True)
class DiscoveryReport:
    """The result of a model discovery operation."""

    provider_id: str
    status: DiscoveryStatus
    models: tuple[DiscoveredModel, ...] = ()
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    error: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class RetryDecision:
    """Decision on whether to retry an execution."""

    should_retry: bool
    delay_ms: float = 0.0
    attempt: int = 1
    reason: str = ""


@dataclass(frozen=True, slots=True, kw_only=True)
class FallbackReport:
    """Report detailing a fallback execution."""
    primary_provider: str
    fallback_provider: str
    success: bool
    attempts: int = 1
    
    @property
    def fallback_used(self) -> bool:
        return self.primary_provider != self.fallback_provider

@dataclass(frozen=True, slots=True, kw_only=True)
class ModelPricing:
    """Pricing information for a model."""

    model_id: str
    prompt_price_per_1k: float = 0.0
    completion_price_per_1k: float = 0.0


@dataclass(frozen=True, slots=True, kw_only=True)
class StreamChunk:
    """A single chunk in a streaming response."""

    content: str
    is_final: bool = False
    usage: UsageMetrics | None = None
