"""Immutable, non-executing workspace custody evidence for a prospective governed execution."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path


class WorkspaceCustodyError(ValueError):
    """Raised when workspace custody evidence is structurally invalid."""


class WorkspaceCustodyDisposition(StrEnum):
    """Evidence-only outcome of a custody attestation; it grants no execution authority."""

    ATTESTED = "attested"


class WorkspaceCustodyRejectionReason(StrEnum):
    """Typed safe refusals from the non-executing workspace custody boundary."""

    INVALID_ISOLATION = "invalid_isolation"
    UNSAFE_ROOT = "unsafe_root"
    NONEMPTY_WORKSPACE = "nonempty_workspace"
    MISSING_ATTESTATION = "missing_attestation"
    ATTESTATION_UNKNOWN = "attestation_unknown"
    ATTESTATION_BINDING_MISMATCH = "attestation_binding_mismatch"
    STORE_UNAVAILABLE = "store_unavailable"
    STORE_CORRUPT = "store_corrupt"
    ATTESTATION_ID_DUPLICATE = "attestation_id_duplicate"
    ATTESTATION_ID_CONFLICT = "attestation_id_conflict"


def _require_non_empty(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WorkspaceCustodyError(f"{field_name} cannot be empty")
    return value


def _require_digest(value: str, field_name: str) -> str:
    _require_non_empty(value, field_name)
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise WorkspaceCustodyError(f"{field_name} must be a lowercase SHA-256 digest")
    return value


def _canonical_occurrence(value: datetime) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError("occurred_at must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise WorkspaceCustodyError("occurred_at must be timezone-aware")
    return value.astimezone(UTC)


def root_identity(root: Path) -> str:
    """Return a redacted canonical root identity without creating, opening, or changing that root."""
    if not isinstance(root, Path):
        raise TypeError("root must be a Path")
    return hashlib.sha256(str(root.resolve()).encode()).hexdigest()


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkspaceCustodyPolicy:
    """Strict declarative custody checks; it is not a workspace operation policy."""

    require_existing_roots: bool = True
    require_empty_workspace: bool = True
    forbid_root_symlinks: bool = True

    def __post_init__(self) -> None:
        for field_name in (
            "require_existing_roots",
            "require_empty_workspace",
            "forbid_root_symlinks",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise TypeError(f"{field_name} must be a bool")

    @property
    def digest(self) -> str:
        payload = {
            "forbid_root_symlinks": self.forbid_root_symlinks,
            "require_empty_workspace": self.require_empty_workspace,
            "require_existing_roots": self.require_existing_roots,
        }
        return hashlib.sha256(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkspaceCustodyRequest:
    """Explicit prospective-root declaration; validation is read-only and creates no workspace."""

    attestation_id: str
    execution_id: str
    run_id: str
    workspace_id: str
    workspace_root: Path
    source_repository_root: Path
    audit_root: Path
    control_root: Path
    policy: WorkspaceCustodyPolicy = WorkspaceCustodyPolicy()

    def __post_init__(self) -> None:
        for field_name in ("attestation_id", "execution_id", "run_id", "workspace_id"):
            object.__setattr__(self, field_name, _require_non_empty(getattr(self, field_name), field_name))
        for field_name in ("workspace_root", "source_repository_root", "audit_root", "control_root"):
            if not isinstance(getattr(self, field_name), Path):
                raise TypeError(f"{field_name} must be a Path")
        if not isinstance(self.policy, WorkspaceCustodyPolicy):
            raise TypeError("policy must be a WorkspaceCustodyPolicy")


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkspaceCustodyAttestation:
    """Redacted immutable custody evidence bound to one exact prospective workspace configuration."""

    attestation_id: str
    execution_id: str
    run_id: str
    workspace_id: str
    workspace_root_identity: str
    source_repository_identity: str
    audit_root_identity: str
    control_root_identity: str
    custody_policy_digest: str
    isolation_binding_digest: str
    occurred_at: datetime
    disposition: WorkspaceCustodyDisposition
    binding_digest: str

    def __post_init__(self) -> None:
        for field_name in ("attestation_id", "execution_id", "run_id", "workspace_id"):
            object.__setattr__(self, field_name, _require_non_empty(getattr(self, field_name), field_name))
        for field_name in (
            "workspace_root_identity",
            "source_repository_identity",
            "audit_root_identity",
            "control_root_identity",
            "custody_policy_digest",
            "isolation_binding_digest",
            "binding_digest",
        ):
            object.__setattr__(self, field_name, _require_digest(getattr(self, field_name), field_name))
        object.__setattr__(self, "occurred_at", _canonical_occurrence(self.occurred_at))
        if self.disposition is not WorkspaceCustodyDisposition.ATTESTED:
            raise WorkspaceCustodyError("workspace custody attestation must be attested evidence")
        if self.binding_digest != self.calculate_binding_digest():
            raise WorkspaceCustodyError("binding_digest does not match canonical custody evidence")

    @classmethod
    def issue(cls, *, request: WorkspaceCustodyRequest, occurred_at: datetime) -> WorkspaceCustodyAttestation:
        """Create self-validating custody evidence only after a gate has performed read-only validation."""
        occurred = _canonical_occurrence(occurred_at)
        workspace_identity = root_identity(request.workspace_root)
        source_identity = root_identity(request.source_repository_root)
        audit_identity = root_identity(request.audit_root)
        control_identity = root_identity(request.control_root)
        isolation_digest = isolation_binding_digest(
            execution_id=request.execution_id,
            run_id=request.run_id,
            workspace_id=request.workspace_id,
            workspace_root_identity=workspace_identity,
            source_repository_identity=source_identity,
            audit_root_identity=audit_identity,
            control_root_identity=control_identity,
        )
        payload = {
            "attestation_id": request.attestation_id,
            "audit_root_identity": audit_identity,
            "control_root_identity": control_identity,
            "custody_policy_digest": request.policy.digest,
            "execution_id": request.execution_id,
            "isolation_binding_digest": isolation_digest,
            "occurred_at": occurred.isoformat(),
            "run_id": request.run_id,
            "source_repository_identity": source_identity,
            "workspace_id": request.workspace_id,
            "workspace_root_identity": workspace_identity,
        }
        binding_digest = hashlib.sha256(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        ).hexdigest()
        return cls(
            attestation_id=request.attestation_id,
            execution_id=request.execution_id,
            run_id=request.run_id,
            workspace_id=request.workspace_id,
            workspace_root_identity=workspace_identity,
            source_repository_identity=source_identity,
            audit_root_identity=audit_identity,
            control_root_identity=control_identity,
            custody_policy_digest=request.policy.digest,
            isolation_binding_digest=isolation_digest,
            occurred_at=occurred,
            disposition=WorkspaceCustodyDisposition.ATTESTED,
            binding_digest=binding_digest,
        )

    def calculate_binding_digest(self) -> str:
        payload = {
            "attestation_id": self.attestation_id,
            "audit_root_identity": self.audit_root_identity,
            "control_root_identity": self.control_root_identity,
            "custody_policy_digest": self.custody_policy_digest,
            "execution_id": self.execution_id,
            "isolation_binding_digest": self.isolation_binding_digest,
            "occurred_at": self.occurred_at.isoformat(),
            "run_id": self.run_id,
            "source_repository_identity": self.source_repository_identity,
            "workspace_id": self.workspace_id,
            "workspace_root_identity": self.workspace_root_identity,
        }
        return hashlib.sha256(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()).hexdigest()

    def to_payload(self) -> dict[str, str]:
        """Return the deterministic redacted durable representation with no mutable metadata."""
        return {
            "attestation_id": self.attestation_id,
            "audit_root_identity": self.audit_root_identity,
            "binding_digest": self.binding_digest,
            "control_root_identity": self.control_root_identity,
            "custody_policy_digest": self.custody_policy_digest,
            "disposition": self.disposition.value,
            "execution_id": self.execution_id,
            "isolation_binding_digest": self.isolation_binding_digest,
            "occurred_at": self.occurred_at.isoformat(),
            "run_id": self.run_id,
            "source_repository_identity": self.source_repository_identity,
            "workspace_id": self.workspace_id,
            "workspace_root_identity": self.workspace_root_identity,
        }

    @classmethod
    def from_payload(cls, payload: object) -> WorkspaceCustodyAttestation:
        """Parse only the complete canonical durable representation; all deviations are corruption."""
        if not isinstance(payload, dict):
            raise WorkspaceCustodyError("workspace custody payload must be an object")
        required_fields = {
            "attestation_id",
            "audit_root_identity",
            "binding_digest",
            "control_root_identity",
            "custody_policy_digest",
            "disposition",
            "execution_id",
            "isolation_binding_digest",
            "occurred_at",
            "run_id",
            "source_repository_identity",
            "workspace_id",
            "workspace_root_identity",
        }
        if set(payload) != required_fields:
            raise WorkspaceCustodyError("workspace custody payload has unexpected fields")
        try:
            return cls(
                attestation_id=payload["attestation_id"],
                execution_id=payload["execution_id"],
                run_id=payload["run_id"],
                workspace_id=payload["workspace_id"],
                workspace_root_identity=payload["workspace_root_identity"],
                source_repository_identity=payload["source_repository_identity"],
                audit_root_identity=payload["audit_root_identity"],
                control_root_identity=payload["control_root_identity"],
                custody_policy_digest=payload["custody_policy_digest"],
                isolation_binding_digest=payload["isolation_binding_digest"],
                occurred_at=datetime.fromisoformat(payload["occurred_at"]),
                disposition=WorkspaceCustodyDisposition(payload["disposition"]),
                binding_digest=payload["binding_digest"],
            )
        except (KeyError, TypeError, ValueError, WorkspaceCustodyError) as error:
            raise WorkspaceCustodyError("invalid workspace custody payload") from error


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkspaceCustodyAdmission:
    """Immutable evidence-only result; it never contains a session, permit, runtime, or workspace handle."""

    attestation: WorkspaceCustodyAttestation | None
    reason: WorkspaceCustodyRejectionReason | None = None

    def __post_init__(self) -> None:
        if self.attestation is not None:
            if not isinstance(self.attestation, WorkspaceCustodyAttestation):
                raise TypeError("attestation must be a WorkspaceCustodyAttestation or None")
            if self.reason is not None:
                raise WorkspaceCustodyError("attested custody cannot carry a rejection reason")
            return
        if not isinstance(self.reason, WorkspaceCustodyRejectionReason):
            raise WorkspaceCustodyError("rejected custody admission requires a typed reason")


def isolation_binding_digest(
    *,
    execution_id: str,
    run_id: str,
    workspace_id: str,
    workspace_root_identity: str,
    source_repository_identity: str,
    audit_root_identity: str,
    control_root_identity: str,
) -> str:
    """Hash exact redacted root and execution bindings without retaining raw paths."""
    payload = {
        "audit_root_identity": _require_digest(audit_root_identity, "audit_root_identity"),
        "control_root_identity": _require_digest(control_root_identity, "control_root_identity"),
        "execution_id": _require_non_empty(execution_id, "execution_id"),
        "run_id": _require_non_empty(run_id, "run_id"),
        "source_repository_identity": _require_digest(source_repository_identity, "source_repository_identity"),
        "workspace_id": _require_non_empty(workspace_id, "workspace_id"),
        "workspace_root_identity": _require_digest(workspace_root_identity, "workspace_root_identity"),
    }
    return hashlib.sha256(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()).hexdigest()


__all__ = [
    "WorkspaceCustodyAdmission",
    "WorkspaceCustodyAttestation",
    "WorkspaceCustodyDisposition",
    "WorkspaceCustodyError",
    "WorkspaceCustodyPolicy",
    "WorkspaceCustodyRejectionReason",
    "WorkspaceCustodyRequest",
    "isolation_binding_digest",
    "root_identity",
]
