"""Immutable, execution-free contracts for controlled activation-to-runtime session admission."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class GovernedSessionError(ValueError):
    """Raised when a controlled runtime-session contract is structurally invalid."""


class SessionDisposition(StrEnum):
    """Outcome of session creation or a one-time runtime-start admission check."""

    SESSION_CREATED = "session_created"
    RUNTIME_START_ALLOWED = "runtime_start_allowed"
    REJECTED = "rejected"


class SessionRejectionReason(StrEnum):
    """Typed refusal reasons emitted before any governed runtime operation begins."""

    MISSING_ACTIVATION_RECEIPT = "missing_activation_receipt"
    ACTIVATION_NOT_APPROVED = "activation_not_approved"
    ACTIVATION_RECEIPT_MISMATCH = "activation_receipt_mismatch"
    ACTIVATION_RECEIPT_REPLAYED = "activation_receipt_replayed"
    EXECUTION_ID_MISMATCH = "execution_id_mismatch"
    RUN_ID_MISMATCH = "run_id_mismatch"
    REQUEST_IDENTITY_MISMATCH = "request_identity_mismatch"
    PROVIDER_POLICY_MISMATCH = "provider_policy_mismatch"
    ISOLATION_BINDING_MISMATCH = "isolation_binding_mismatch"
    AUDIT_BINDING_MISMATCH = "audit_binding_mismatch"
    RUNTIME_UNAVAILABLE = "runtime_unavailable"
    SESSION_CONSUMED = "session_consumed"
    SESSION_UNKNOWN = "session_unknown"
    REPLAY_LEDGER_UNAVAILABLE = "replay_ledger_unavailable"
    REPLAY_LEDGER_CORRUPT = "replay_ledger_corrupt"
    REPLAY_LEDGER_CONFLICT = "replay_ledger_conflict"
    REPLAY_LEDGER_ISOLATION_MISMATCH = "replay_ledger_isolation_mismatch"
    MISSING_HUMAN_APPROVAL = "missing_human_approval"
    HUMAN_APPROVAL_DENIED = "human_approval_denied"
    HUMAN_APPROVAL_UNKNOWN = "human_approval_unknown"
    HUMAN_APPROVAL_BINDING_MISMATCH = "human_approval_binding_mismatch"
    HUMAN_APPROVAL_STORE_UNAVAILABLE = "human_approval_store_unavailable"
    HUMAN_APPROVAL_STORE_CORRUPT = "human_approval_store_corrupt"
    HUMAN_APPROVAL_CONFLICT = "human_approval_conflict"
    MISSING_WORKSPACE_CUSTODY_EVIDENCE = "missing_workspace_custody_evidence"
    WORKSPACE_CUSTODY_BINDING_MISMATCH = "workspace_custody_binding_mismatch"
    WORKSPACE_CUSTODY_STORE_UNAVAILABLE = "workspace_custody_store_unavailable"
    WORKSPACE_CUSTODY_STORE_CORRUPT = "workspace_custody_store_corrupt"
    MISSING_RUNTIME_COMPOSITION_EVIDENCE = "missing_runtime_composition_evidence"
    RUNTIME_COMPOSITION_BINDING_MISMATCH = "runtime_composition_binding_mismatch"
    RUNTIME_COMPOSITION_STORE_UNAVAILABLE = "runtime_composition_store_unavailable"
    RUNTIME_COMPOSITION_STORE_CORRUPT = "runtime_composition_store_corrupt"


def _require_non_empty(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GovernedSessionError(f"{field_name} cannot be empty")
    return value


@dataclass(frozen=True, slots=True, kw_only=True)
class RuntimeAvailability:
    """A declarative runtime-availability binding; it does not hold or invoke a runtime."""

    runtime_id: str
    available: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "runtime_id", _require_non_empty(self.runtime_id, "runtime_id"))
        if not isinstance(self.available, bool):
            raise TypeError("available must be a bool")


@dataclass(frozen=True, slots=True, kw_only=True)
class ControlledRuntimeSession:
    """Immutable binding for one approved, future G2.4.4 runtime start only."""

    session_id: str
    activation_id: str
    activation_receipt_digest: str
    execution_id: str
    run_id: str
    request_digest: str
    provider_policy_digest: str
    isolation_binding_digest: str
    audit_observer_identity: str
    runtime_id: str

    def __post_init__(self) -> None:
        for field_name in (
            "session_id",
            "activation_id",
            "activation_receipt_digest",
            "execution_id",
            "run_id",
            "request_digest",
            "provider_policy_digest",
            "isolation_binding_digest",
            "audit_observer_identity",
            "runtime_id",
        ):
            object.__setattr__(self, field_name, _require_non_empty(getattr(self, field_name), field_name))


@dataclass(frozen=True, slots=True, kw_only=True)
class ControlledSessionDecision:
    """Pure session-gate output without an executable runtime or mutation capability."""

    disposition: SessionDisposition
    session_id: str | None = None
    execution_id: str | None = None
    run_id: str | None = None
    reason: SessionRejectionReason | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.disposition, SessionDisposition):
            raise TypeError("disposition must be a SessionDisposition")
        if self.disposition is SessionDisposition.REJECTED:
            if self.reason is None:
                raise GovernedSessionError("rejected decisions require a reason")
            if not isinstance(self.reason, SessionRejectionReason):
                raise TypeError("reason must be a SessionRejectionReason")
            return
        if self.reason is not None:
            raise GovernedSessionError("non-rejected decisions cannot carry a refusal reason")
        for field_name in ("session_id", "execution_id", "run_id"):
            value = getattr(self, field_name)
            if value is None:
                raise GovernedSessionError(f"{field_name} is required for an approved decision")
            _require_non_empty(value, field_name)


@dataclass(frozen=True, slots=True, kw_only=True)
class ControlledSessionAdmission:
    """Pure result of binding an activation receipt to one future runtime-start session."""

    session: ControlledRuntimeSession | None
    decision: ControlledSessionDecision

    def __post_init__(self) -> None:
        if not isinstance(self.decision, ControlledSessionDecision):
            raise TypeError("decision must be a ControlledSessionDecision")
        if self.decision.disposition is SessionDisposition.SESSION_CREATED:
            if not isinstance(self.session, ControlledRuntimeSession):
                raise GovernedSessionError("approved session admission requires a session")
            if self.session.session_id != self.decision.session_id:
                raise GovernedSessionError("session and decision identities must match")
        elif self.session is not None:
            raise GovernedSessionError("rejected session admission cannot expose a session")


__all__ = [
    "ControlledRuntimeSession",
    "ControlledSessionAdmission",
    "ControlledSessionDecision",
    "GovernedSessionError",
    "RuntimeAvailability",
    "SessionDisposition",
    "SessionRejectionReason",
]
