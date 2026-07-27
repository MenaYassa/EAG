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


class TraceEventType(StrEnum):
    """Events recorded in an execution trace."""
    STARTED = "started"
    PROVIDER_SELECTED = "provider_selected"
    REQUEST_SENT = "request_sent"
    RESPONSE_RECEIVED = "response_received"
    COMPLETED = "completed"
    FAILED = "failed"