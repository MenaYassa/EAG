"""Safe gateway failure and deterministic policy-violation contracts."""

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


class PolicyViolationCode(StrEnum):
    """Stable, content-safe policy rejection categories for future diagnostics."""

    DECISION_SCHEMA_VERSION_UNACCEPTED = "decision_schema_version_unaccepted"
    REQUIRED_CAPABILITY_OUTSIDE_ALLOWLIST = "required_capability_outside_allowlist"
    DUPLICATE_STEP_ID = "duplicate_step_id"
    STEP_CAPABILITY_OUTSIDE_ALLOWLIST = "step_capability_outside_allowlist"
    DEPENDENCY_NOT_EARLIER_STEP = "dependency_not_earlier_step"
    EXECUTABLE_PARAMETER_FORBIDDEN = "executable_parameter_forbidden"
    REQUIRED_CAPABILITIES_MISMATCH = "required_capabilities_mismatch"
    GROUNDING_REFERENCES_REQUIRED = "grounding_references_required"
    GROUNDING_REFERENCE_UNKNOWN = "grounding_reference_unknown"
    MUTATION_INTENT_CAPABILITY_MISMATCH = "mutation_intent_capability_mismatch"
    MUTATION_INTENT_COUNT_INVALID = "mutation_intent_count_invalid"
    MUTATION_INTENT_STEP_UNKNOWN = "mutation_intent_step_unknown"
    MUTATION_INTENT_STEP_DEPENDENCIES_FORBIDDEN = "mutation_intent_step_dependencies_forbidden"
    MUTATION_INTENT_OPERATION_UNSUPPORTED = "mutation_intent_operation_unsupported"
    MUTATION_INTENT_TARGET_INVALID = "mutation_intent_target_invalid"
    MUTATION_INTENT_CONTENT_INVALID = "mutation_intent_content_invalid"
    MUTATION_INTENT_CONTENT_TOO_LARGE = "mutation_intent_content_too_large"
    MUTATION_INTENT_GROUNDING_UNKNOWN = "mutation_intent_grounding_unknown"
    MUTATION_INTENT_PRESERVATION_BINDING_INVALID = "mutation_intent_preservation_binding_invalid"
    MUTATION_INTENT_PRESERVATION_BINDING_MISSING = "mutation_intent_preservation_binding_missing"


@dataclass(frozen=True, slots=True, kw_only=True)
class PolicyViolation:
    """Safe structured metadata for a deterministic EngineeringDecision policy rejection.

    It intentionally contains only stable validation metadata and structured decision identifiers.
    It never contains raw provider content, prompts, repository source, credentials, or secrets.
    """

    code: PolicyViolationCode
    stage: str
    message: str
    step_id: str | None = None
    dependency_step_id: str | None = None
    step_index: int | None = None
    dependency_index: int | None = None
    contract_version: str = "1.0"
    schema_version: str | None = None


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

    def __init__(self, violation: PolicyViolation) -> None:
        super().__init__(violation.message)
        self.violation = violation
