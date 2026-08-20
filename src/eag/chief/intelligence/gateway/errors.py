"""Normalized governed-gateway error contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class GatewayErrorKind(StrEnum):
    """Stable categories for expected gateway outcomes."""

    REQUEST_INVALID = "request_invalid"
    ROUTING_UNAVAILABLE = "routing_unavailable"
    PROVIDER_TIMEOUT = "provider_timeout"
    PROVIDER_TRANSIENT_FAILURE = "provider_transient_failure"
    PROVIDER_PERMANENT_FAILURE = "provider_permanent_failure"
    RESPONSE_EMPTY_OR_MALFORMED = "response_empty_or_malformed"
    SCHEMA_INVALID = "schema_invalid"
    POLICY_REJECTED = "policy_rejected"
    BUDGET_EXCEEDED = "budget_exceeded"
    ALL_ATTEMPTS_FAILED = "all_attempts_failed"


@dataclass(frozen=True, slots=True, kw_only=True)
class GatewayError:
    """A safe, provider-neutral failure returned by the gateway."""

    kind: GatewayErrorKind
    message: str
    retryable: bool = False
    provider_id: str | None = None
    model_id: str | None = None
    attempts: int = 0
    trace_id: str = ""


class GatewayValidationError(ValueError):
    """Base class for invalid structured gateway inputs or outputs."""


class SchemaValidationError(GatewayValidationError):
    """Raised when a provider response cannot satisfy the strict decision schema."""


class PolicyValidationError(GatewayValidationError):
    """Raised when a schema-valid decision violates deterministic gateway policy."""
