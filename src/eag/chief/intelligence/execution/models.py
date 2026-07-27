"""Execution domain models for EAG."""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any

from eag.chief.intelligence.execution.enums import ExecutionState, ProviderHealthStatus, TraceEventType


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


@dataclass(frozen=True, slots=True, kw_only=True)
class ProviderHealth:
    """Health status of an AI provider."""
    provider_id: str
    status: ProviderHealthStatus = ProviderHealthStatus.UNKNOWN
    latency_ms: float = 0.0
    error_rate: float = 0.0
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