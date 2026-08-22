"""Read-only validation and immutable recording for governed workspace custody evidence."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from eag.governed_workspace.models import (
    WorkspaceCustodyAdmission,
    WorkspaceCustodyAttestation,
    WorkspaceCustodyRejectionReason,
    WorkspaceCustodyRequest,
)
from eag.governed_workspace.store import (
    DurableWorkspaceCustodyStore,
    WorkspaceCustodyClaimDisposition,
    WorkspaceCustodyStoreCorruptionError,
    WorkspaceCustodyStoreUnavailableError,
)


class WorkspaceCustodyGate:
    """Create and validate custody evidence only; it has no workspace, activation, session, or execution authority."""

    def __init__(self, *, custody_store: DurableWorkspaceCustodyStore) -> None:
        if not callable(getattr(custody_store, "claim", None)) or not callable(
            getattr(custody_store, "read", None)
        ):
            raise TypeError("custody_store must expose claim(attestation) and read(attestation_id)")
        if not isinstance(getattr(custody_store, "control_root", None), Path):
            raise TypeError("custody_store must expose a Path control_root")
        self._custody_store = custody_store

    def attest(self, *, request: WorkspaceCustodyRequest, occurred_at: datetime) -> WorkspaceCustodyAdmission:
        """Validate roots read-only and atomically record one immutable attestation; no workspace is created."""
        rejection = _request_rejection(request, self._custody_store.control_root)
        if rejection is not None:
            return WorkspaceCustodyAdmission(attestation=None, reason=rejection)
        attestation = WorkspaceCustodyAttestation.issue(request=request, occurred_at=occurred_at)
        try:
            claim = self._custody_store.claim(attestation)
        except WorkspaceCustodyStoreCorruptionError:
            return WorkspaceCustodyAdmission(
                attestation=None,
                reason=WorkspaceCustodyRejectionReason.STORE_CORRUPT,
            )
        except WorkspaceCustodyStoreUnavailableError:
            return WorkspaceCustodyAdmission(
                attestation=None,
                reason=WorkspaceCustodyRejectionReason.STORE_UNAVAILABLE,
            )
        if claim.disposition is WorkspaceCustodyClaimDisposition.CLAIMED:
            return WorkspaceCustodyAdmission(attestation=attestation)
        if claim.disposition is WorkspaceCustodyClaimDisposition.DUPLICATE:
            return WorkspaceCustodyAdmission(
                attestation=None,
                reason=WorkspaceCustodyRejectionReason.ATTESTATION_ID_DUPLICATE,
            )
        return WorkspaceCustodyAdmission(
            attestation=None,
            reason=WorkspaceCustodyRejectionReason.ATTESTATION_ID_CONFLICT,
        )

    def validate(
        self,
        *,
        attestation: WorkspaceCustodyAttestation | None,
        request: WorkspaceCustodyRequest,
    ) -> WorkspaceCustodyRejectionReason | None:
        """Revalidate exact durable evidence before another authority decides whether to admit execution."""
        if attestation is None:
            return WorkspaceCustodyRejectionReason.MISSING_ATTESTATION
        if not isinstance(attestation, WorkspaceCustodyAttestation):
            raise TypeError("attestation must be a WorkspaceCustodyAttestation or None")
        rejection = _request_rejection(request, self._custody_store.control_root)
        if rejection is not None:
            return rejection
        try:
            stored = self._custody_store.read(attestation_id=attestation.attestation_id)
        except WorkspaceCustodyStoreCorruptionError:
            return WorkspaceCustodyRejectionReason.STORE_CORRUPT
        except WorkspaceCustodyStoreUnavailableError:
            return WorkspaceCustodyRejectionReason.STORE_UNAVAILABLE
        if stored is None:
            return WorkspaceCustodyRejectionReason.ATTESTATION_UNKNOWN
        if stored != attestation:
            return WorkspaceCustodyRejectionReason.ATTESTATION_ID_CONFLICT
        expected = WorkspaceCustodyAttestation.issue(request=request, occurred_at=attestation.occurred_at)
        if expected != attestation:
            return WorkspaceCustodyRejectionReason.ATTESTATION_BINDING_MISMATCH
        return None


def _request_rejection(
    request: WorkspaceCustodyRequest,
    store_root: Path,
) -> WorkspaceCustodyRejectionReason | None:
    roots = (
        request.workspace_root,
        request.source_repository_root,
        request.audit_root,
        request.control_root,
    )
    if request.control_root.resolve() != store_root.resolve():
        return WorkspaceCustodyRejectionReason.INVALID_ISOLATION
    if request.policy.require_existing_roots and any(not root.exists() or not root.is_dir() for root in roots):
        return WorkspaceCustodyRejectionReason.UNSAFE_ROOT
    if request.policy.forbid_root_symlinks and any(root.is_symlink() for root in roots):
        return WorkspaceCustodyRejectionReason.UNSAFE_ROOT
    try:
        resolved_workspace, resolved_source, resolved_audit, resolved_control = (
            root.resolve(strict=True) for root in roots
        )
    except OSError:
        return WorkspaceCustodyRejectionReason.UNSAFE_ROOT
    resolved = (resolved_workspace, resolved_source, resolved_audit, resolved_control)
    if len(set(resolved)) != len(resolved):
        return WorkspaceCustodyRejectionReason.INVALID_ISOLATION
    if any(
        candidate.is_relative_to(other)
        for candidate in resolved
        for other in resolved
        if candidate != other
    ):
        return WorkspaceCustodyRejectionReason.INVALID_ISOLATION
    if request.policy.require_empty_workspace:
        try:
            if any(resolved_workspace.iterdir()):
                return WorkspaceCustodyRejectionReason.NONEMPTY_WORKSPACE
        except OSError:
            return WorkspaceCustodyRejectionReason.UNSAFE_ROOT
    return None


__all__ = ["WorkspaceCustodyGate"]
