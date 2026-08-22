"""Immutable, non-executing human approval evidence for one governed session request."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class GovernedApprovalError(ValueError):
    """Raised when immutable governed-approval evidence is structurally invalid."""


class GovernedApprovalDisposition(StrEnum):
    """An operator decision recorded as evidence only; it grants no execution capability."""

    APPROVED = "approved"
    DENIED = "denied"


class GovernedApprovalRejectionReason(StrEnum):
    """Typed reasons for rejecting a presented governed approval before session creation."""

    MISSING_APPROVAL = "missing_approval"
    APPROVAL_DENIED = "approval_denied"
    APPROVAL_UNKNOWN = "approval_unknown"
    APPROVAL_BINDING_MISMATCH = "approval_binding_mismatch"
    APPROVAL_STORE_UNAVAILABLE = "approval_store_unavailable"
    APPROVAL_STORE_CORRUPT = "approval_store_corrupt"
    APPROVAL_ID_DUPLICATE = "approval_id_duplicate"
    APPROVAL_ID_CONFLICT = "approval_id_conflict"


def _require_non_empty(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GovernedApprovalError(f"{field_name} cannot be empty")
    return value


def _require_digest(value: str, field_name: str) -> str:
    _require_non_empty(value, field_name)
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise GovernedApprovalError(f"{field_name} must be a lowercase SHA-256 digest")
    return value


def _canonical_occurrence(value: datetime) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError("occurred_at must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise GovernedApprovalError("occurred_at must be timezone-aware")
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True, kw_only=True)
class GovernedApprovalReceipt:
    """Immutable human decision evidence bound to one exact prospective governed session."""

    approval_id: str
    approver_identity: str
    occurred_at: datetime
    disposition: GovernedApprovalDisposition
    activation_id: str
    activation_receipt_digest: str
    execution_id: str
    run_id: str
    runtime_request_digest: str
    provider_policy_digest: str
    isolation_binding_digest: str
    audit_observer_identity: str
    runtime_id: str
    binding_digest: str

    def __post_init__(self) -> None:
        for field_name in (
            "approval_id",
            "approver_identity",
            "activation_id",
            "execution_id",
            "run_id",
            "audit_observer_identity",
            "runtime_id",
        ):
            object.__setattr__(self, field_name, _require_non_empty(getattr(self, field_name), field_name))
        for field_name in (
            "activation_receipt_digest",
            "runtime_request_digest",
            "provider_policy_digest",
            "isolation_binding_digest",
            "binding_digest",
        ):
            object.__setattr__(self, field_name, _require_digest(getattr(self, field_name), field_name))
        object.__setattr__(self, "occurred_at", _canonical_occurrence(self.occurred_at))
        if not isinstance(self.disposition, GovernedApprovalDisposition):
            raise TypeError("disposition must be a GovernedApprovalDisposition")
        if self.binding_digest != self.calculate_binding_digest():
            raise GovernedApprovalError("binding_digest does not match canonical approval evidence")

    @classmethod
    def issue(
        cls,
        *,
        approval_id: str,
        approver_identity: str,
        occurred_at: datetime,
        disposition: GovernedApprovalDisposition,
        activation_id: str,
        activation_receipt_digest: str,
        execution_id: str,
        run_id: str,
        runtime_request_digest: str,
        provider_policy_digest: str,
        isolation_binding_digest: str,
        audit_observer_identity: str,
        runtime_id: str,
    ) -> GovernedApprovalReceipt:
        """Create one self-verifying immutable receipt; this method grants no session or permit."""
        occurred = _canonical_occurrence(occurred_at)
        payload = {
            "activation_id": activation_id,
            "activation_receipt_digest": activation_receipt_digest,
            "approval_id": approval_id,
            "approver_identity": approver_identity,
            "audit_observer_identity": audit_observer_identity,
            "disposition": disposition.value,
            "execution_id": execution_id,
            "isolation_binding_digest": isolation_binding_digest,
            "occurred_at": occurred.isoformat(),
            "provider_policy_digest": provider_policy_digest,
            "run_id": run_id,
            "runtime_id": runtime_id,
            "runtime_request_digest": runtime_request_digest,
        }
        binding_digest = hashlib.sha256(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        ).hexdigest()
        return cls(
            approval_id=approval_id,
            approver_identity=approver_identity,
            occurred_at=occurred,
            disposition=disposition,
            activation_id=activation_id,
            activation_receipt_digest=activation_receipt_digest,
            execution_id=execution_id,
            run_id=run_id,
            runtime_request_digest=runtime_request_digest,
            provider_policy_digest=provider_policy_digest,
            isolation_binding_digest=isolation_binding_digest,
            audit_observer_identity=audit_observer_identity,
            runtime_id=runtime_id,
            binding_digest=binding_digest,
        )

    def calculate_binding_digest(self) -> str:
        """Calculate the deterministic digest of every approval binding except the digest itself."""
        payload = {
            "activation_id": self.activation_id,
            "activation_receipt_digest": self.activation_receipt_digest,
            "approval_id": self.approval_id,
            "approver_identity": self.approver_identity,
            "audit_observer_identity": self.audit_observer_identity,
            "disposition": self.disposition.value,
            "execution_id": self.execution_id,
            "isolation_binding_digest": self.isolation_binding_digest,
            "occurred_at": self.occurred_at.isoformat(),
            "provider_policy_digest": self.provider_policy_digest,
            "run_id": self.run_id,
            "runtime_id": self.runtime_id,
            "runtime_request_digest": self.runtime_request_digest,
        }
        return hashlib.sha256(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()).hexdigest()

    def to_payload(self) -> dict[str, str]:
        """Return deterministic, redacted, metadata-free durable approval evidence."""
        return {
            "activation_id": self.activation_id,
            "activation_receipt_digest": self.activation_receipt_digest,
            "approval_id": self.approval_id,
            "approver_identity": self.approver_identity,
            "audit_observer_identity": self.audit_observer_identity,
            "binding_digest": self.binding_digest,
            "disposition": self.disposition.value,
            "execution_id": self.execution_id,
            "isolation_binding_digest": self.isolation_binding_digest,
            "occurred_at": self.occurred_at.isoformat(),
            "provider_policy_digest": self.provider_policy_digest,
            "run_id": self.run_id,
            "runtime_id": self.runtime_id,
            "runtime_request_digest": self.runtime_request_digest,
        }

    @classmethod
    def from_payload(cls, payload: object) -> GovernedApprovalReceipt:
        """Parse only the canonical durable representation; any deviation is corruption."""
        if not isinstance(payload, dict):
            raise GovernedApprovalError("governed approval payload must be an object")
        required_fields = {
            "activation_id",
            "activation_receipt_digest",
            "approval_id",
            "approver_identity",
            "audit_observer_identity",
            "binding_digest",
            "disposition",
            "execution_id",
            "isolation_binding_digest",
            "occurred_at",
            "provider_policy_digest",
            "run_id",
            "runtime_id",
            "runtime_request_digest",
        }
        if set(payload) != required_fields:
            raise GovernedApprovalError("governed approval payload has unexpected fields")
        try:
            occurred_at = datetime.fromisoformat(payload["occurred_at"])
            return cls(
                approval_id=payload["approval_id"],
                approver_identity=payload["approver_identity"],
                occurred_at=occurred_at,
                disposition=GovernedApprovalDisposition(payload["disposition"]),
                activation_id=payload["activation_id"],
                activation_receipt_digest=payload["activation_receipt_digest"],
                execution_id=payload["execution_id"],
                run_id=payload["run_id"],
                runtime_request_digest=payload["runtime_request_digest"],
                provider_policy_digest=payload["provider_policy_digest"],
                isolation_binding_digest=payload["isolation_binding_digest"],
                audit_observer_identity=payload["audit_observer_identity"],
                runtime_id=payload["runtime_id"],
                binding_digest=payload["binding_digest"],
            )
        except (KeyError, TypeError, ValueError, GovernedApprovalError) as error:
            raise GovernedApprovalError("invalid governed approval payload") from error


@dataclass(frozen=True, slots=True, kw_only=True)
class GovernedApprovalAdmission:
    """Immutable result of recording one approval evidence record; no session or permit is exposed."""

    receipt: GovernedApprovalReceipt | None
    reason: GovernedApprovalRejectionReason | None = None

    def __post_init__(self) -> None:
        if self.receipt is not None:
            if not isinstance(self.receipt, GovernedApprovalReceipt):
                raise TypeError("receipt must be a GovernedApprovalReceipt or None")
            if self.reason is not None:
                raise GovernedApprovalError("recorded approval cannot carry a rejection reason")
            return
        if not isinstance(self.reason, GovernedApprovalRejectionReason):
            raise GovernedApprovalError("rejected approval admission requires a typed reason")


__all__ = [
    "GovernedApprovalAdmission",
    "GovernedApprovalDisposition",
    "GovernedApprovalError",
    "GovernedApprovalReceipt",
    "GovernedApprovalRejectionReason",
]
