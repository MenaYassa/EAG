"""Execution domain vocabulary for EAG."""

from enum import StrEnum


class ProviderHealthStatus(StrEnum):
    """Health status of an AI provider."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ExecutionState(StrEnum):
    """Lifecycle state of an execution."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"
    FALLING_BACK = "falling_back"


class TraceEventType(StrEnum):
    """Events recorded in an execution trace."""

    STARTED = "started"
    PROVIDER_SELECTED = "provider_selected"
    REQUEST_SENT = "request_sent"
    RESPONSE_RECEIVED = "response_received"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY_STARTED = "retry_started"
    RETRY_FINISHED = "retry_finished"
    FALLBACK_STARTED = "fallback_started"
    FALLBACK_COMPLETED = "fallback_completed"
    DISCOVERY_STARTED = "discovery_started"
    DISCOVERY_COMPLETED = "discovery_completed"
    STREAMING_STARTED = "streaming_started"
    STREAMING_FINISHED = "streaming_finished"
    PRICING_CALCULATED = "pricing_calculated"


class RetryStrategy(StrEnum):
    """Strategies for retrying failed executions."""

    NONE = "none"
    FIXED = "fixed"
    EXPONENTIAL = "exponential"


class DiscoveryStatus(StrEnum):
    """Status of a model discovery operation."""

    SUCCESS = "success"
    FAILED = "failed"
    CACHED = "cached"
