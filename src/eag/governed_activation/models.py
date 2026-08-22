"""Immutable, library-only contracts for controlled governed-activation admission."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from eag.governed_audit.recorder import GovernedExecutionAuditObserver


class GovernedActivationError(ValueError):
    """Raised when an activation contract is structurally invalid."""


class ActivationDisposition(StrEnum):
    """Read-only outcome of pure governed activation admission."""

    APPROVED_TO_START = "approved_to_start"
    REJECTED = "rejected"


class ActivationRejectionReason(StrEnum):
    """Typed safe refusal reasons emitted before any governed execution work."""

    MISSING_CALLER_CONFIRMATION = "missing_caller_confirmation"
    INVALID_CALLER_CONFIRMATION = "invalid_caller_confirmation"
    MISSING_PROVIDER_POLICY = "missing_provider_policy"
    INVALID_PROVIDER_POLICY = "invalid_provider_policy"
    MISSING_ISOLATION_ROOT = "missing_isolation_root"
    SOURCE_WORKSPACE_SELECTED = "source_workspace_selected"
    IDENTICAL_WORKSPACE_AND_AUDIT_ROOT = "identical_workspace_and_audit_root"
    AUDIT_ROOT_INSIDE_WORKSPACE = "audit_root_inside_workspace"
    AUDIT_ROOT_INSIDE_SOURCE_REPOSITORY = "audit_root_inside_source_repository"
    AUDIT_ROOT_UNAVAILABLE = "audit_root_unavailable"
    EMPTY_EXECUTION_ID = "empty_execution_id"
    MISSING_AUDIT_OBSERVER = "missing_audit_observer"


def _require_non_empty(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GovernedActivationError(f"{field_name} cannot be empty")
    return value


@dataclass(frozen=True, slots=True, kw_only=True)
class CallerActivationConfirmation:
    """Explicit caller attestation bound to exactly one governed execution identity."""

    confirmation_id: str
    execution_id: str
    affirmed: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "confirmation_id", _require_non_empty(self.confirmation_id, "confirmation_id"))
        object.__setattr__(self, "execution_id", _require_non_empty(self.execution_id, "execution_id"))
        if not isinstance(self.affirmed, bool):
            raise TypeError("affirmed must be a bool")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProviderExecutionPolicy:
    """Declared provider controls that admission validates but never executes."""

    max_attempts: int
    allow_fallback: bool
    timeout_ms: int
    max_schema_repair_attempts: int = 0
    max_total_tokens: int = 8_000
    max_estimated_cost: float = 1.0

    def __post_init__(self) -> None:
        if not isinstance(self.max_attempts, int) or isinstance(self.max_attempts, bool):
            raise TypeError("max_attempts must be an int")
        if not isinstance(self.allow_fallback, bool):
            raise TypeError("allow_fallback must be a bool")
        if not isinstance(self.timeout_ms, int) or isinstance(self.timeout_ms, bool):
            raise TypeError("timeout_ms must be an int")
        if not isinstance(self.max_schema_repair_attempts, int) or isinstance(
            self.max_schema_repair_attempts, bool
        ):
            raise TypeError("max_schema_repair_attempts must be an int")
        if not isinstance(self.max_total_tokens, int) or isinstance(self.max_total_tokens, bool):
            raise TypeError("max_total_tokens must be an int")
        if not isinstance(self.max_estimated_cost, (int, float)) or isinstance(
            self.max_estimated_cost, bool
        ):
            raise TypeError("max_estimated_cost must be numeric")


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionIsolation:
    """Explicit paths and identity for one prospective governed execution."""

    workspace_root: Path | None
    audit_root: Path | None
    source_repository_root: Path | None
    execution_id: str

    def __post_init__(self) -> None:
        for field_name in ("workspace_root", "audit_root", "source_repository_root"):
            value = getattr(self, field_name)
            if value is not None and not isinstance(value, Path):
                raise TypeError(f"{field_name} must be a Path or None")
        if not isinstance(self.execution_id, str):
            raise TypeError("execution_id must be a str")


@dataclass(frozen=True, slots=True, kw_only=True)
class GovernedActivationRequest:
    """Complete explicit admission input; it contains no runtime or provider handle."""

    confirmation: CallerActivationConfirmation | None
    provider_policy: ProviderExecutionPolicy | None
    isolation: ExecutionIsolation
    audit_observer: GovernedExecutionAuditObserver | None

    def __post_init__(self) -> None:
        if self.confirmation is not None and not isinstance(self.confirmation, CallerActivationConfirmation):
            raise TypeError("confirmation must be CallerActivationConfirmation or None")
        if self.provider_policy is not None and not isinstance(self.provider_policy, ProviderExecutionPolicy):
            raise TypeError("provider_policy must be ProviderExecutionPolicy or None")
        if not isinstance(self.isolation, ExecutionIsolation):
            raise TypeError("isolation must be an ExecutionIsolation")


@dataclass(frozen=True, slots=True, kw_only=True)
class GovernedActivationDecision:
    """Pure admission result; it grants no executable handle or mutation authority."""

    disposition: ActivationDisposition
    execution_id: str
    activation_id: str
    reason: ActivationRejectionReason | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.disposition, ActivationDisposition):
            raise TypeError("disposition must be an ActivationDisposition")
        object.__setattr__(self, "execution_id", _require_non_empty(self.execution_id, "execution_id"))
        object.__setattr__(self, "activation_id", _require_non_empty(self.activation_id, "activation_id"))
        if self.disposition is ActivationDisposition.APPROVED_TO_START and self.reason is not None:
            raise GovernedActivationError("approved decisions cannot carry a rejection reason")
        if self.disposition is ActivationDisposition.REJECTED and self.reason is None:
            raise GovernedActivationError("rejected decisions require a typed reason")
        if self.reason is not None and not isinstance(self.reason, ActivationRejectionReason):
            raise TypeError("reason must be an ActivationRejectionReason or None")


@dataclass(frozen=True, slots=True, kw_only=True)
class GovernedActivationReceipt:
    """Redacted immutable activation evidence, not a runtime or execution receipt."""

    decision: GovernedActivationDecision
    policy_digest: str

    def __post_init__(self) -> None:
        if not isinstance(self.decision, GovernedActivationDecision):
            raise TypeError("decision must be a GovernedActivationDecision")
        if len(self.policy_digest) != 64 or any(
            character not in "0123456789abcdef" for character in self.policy_digest
        ):
            raise GovernedActivationError("policy_digest must be a lowercase SHA-256 digest")


def activation_id_for(confirmation_id: str, execution_id: str) -> str:
    """Derive a deterministic redacted identity for a caller-confirmed activation attempt."""
    return hashlib.sha256(f"{confirmation_id}:{execution_id}".encode()).hexdigest()


__all__ = [
    "ActivationDisposition",
    "ActivationRejectionReason",
    "CallerActivationConfirmation",
    "ExecutionIsolation",
    "GovernedActivationDecision",
    "GovernedActivationError",
    "GovernedActivationReceipt",
    "GovernedActivationRequest",
    "ProviderExecutionPolicy",
    "activation_id_for",
]
