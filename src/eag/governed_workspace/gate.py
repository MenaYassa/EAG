"""G2.4.10 custody evidence and descriptor-first live-handoff admission."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path

from eag.governed_workspace.models import (
    WORKSPACE_CUSTODY_HANDOFF_CAPABILITY_PROFILE,
    WorkspaceCustodyAdmission,
    WorkspaceCustodyAttestation,
    WorkspaceCustodyFilesystemObjectIdentity,
    WorkspaceCustodyRejectionReason,
    WorkspaceCustodyRequest,
    WorkspaceCustodyRootBinding,
    WorkspaceCustodyRootHandoff,
    _issue_workspace_custody_root_handle,
)
from eag.governed_workspace.store import (
    DurableWorkspaceCustodyStore,
    WorkspaceCustodyClaimDisposition,
    WorkspaceCustodyStoreCorruptionError,
    WorkspaceCustodyStoreUnavailableError,
)


class WorkspaceCustodyGate:
    """Own custody evidence and live root acquisition; it owns no construction action."""

    def __init__(
        self,
        *,
        custody_store: DurableWorkspaceCustodyStore,
        capability_probe: Callable[[], bool] | None = None,
    ) -> None:
        if not callable(getattr(custody_store, "claim", None)) or not callable(
            getattr(custody_store, "read", None)
        ):
            raise TypeError("custody_store must expose claim(attestation) and read(attestation_id)")
        if not isinstance(getattr(custody_store, "control_root", None), Path):
            raise TypeError("custody_store must expose a Path control_root")
        if capability_probe is not None and not callable(capability_probe):
            raise TypeError("capability_probe must be callable or None")
        self._custody_store = custody_store
        self._capability_probe = capability_probe or _handoff_capability_available

    def attest(self, *, request: WorkspaceCustodyRequest, occurred_at: datetime) -> WorkspaceCustodyAdmission:
        """Preserve published evidence-only semantics while issuing v2 descriptor-observed evidence."""
        admission, descriptors = self._admit_descriptors(request=request, occurred_at=occurred_at)
        try:
            if admission.reason is not None:
                return WorkspaceCustodyAdmission(attestation=None, reason=admission.reason)
            assert admission.attestation is not None
            claim = self._claim(admission.attestation)
            if claim is WorkspaceCustodyRejectionReason.ATTESTATION_ID_DUPLICATE:
                return WorkspaceCustodyAdmission(attestation=None, reason=claim)
            if claim is WorkspaceCustodyRejectionReason.ATTESTATION_ID_CONFLICT:
                return WorkspaceCustodyAdmission(attestation=None, reason=claim)
            if claim is WorkspaceCustodyRejectionReason.STORE_CORRUPT:
                return WorkspaceCustodyAdmission(attestation=None, reason=claim)
            if claim is WorkspaceCustodyRejectionReason.STORE_UNAVAILABLE:
                return WorkspaceCustodyAdmission(attestation=None, reason=claim)
            return WorkspaceCustodyAdmission(attestation=admission.attestation)
        finally:
            _close_all(descriptors)

    def validate(
        self,
        *,
        attestation: WorkspaceCustodyAttestation | None,
        request: WorkspaceCustodyRequest,
    ) -> WorkspaceCustodyRejectionReason | None:
        """Preserve durable evidence validation; it never provides a live handoff."""
        if attestation is None:
            return WorkspaceCustodyRejectionReason.MISSING_ATTESTATION
        if not isinstance(attestation, WorkspaceCustodyAttestation):
            raise TypeError("attestation must be a WorkspaceCustodyAttestation or None")
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
        admission, descriptors = self._admit_descriptors(request=request, occurred_at=attestation.occurred_at)
        try:
            if admission.reason is not None:
                return admission.reason
            if admission.attestation != attestation:
                return WorkspaceCustodyRejectionReason.ATTESTATION_BINDING_MISMATCH
            return None
        finally:
            _close_all(descriptors)

    def attest_and_acquire_root_handoff(
        self,
        *,
        request: WorkspaceCustodyRequest,
    ) -> WorkspaceCustodyRootHandoff:
        """Issue v2 evidence and retain its exact live workspace descriptor for one handoff."""
        if not _handoff_capability_available() or not self._capability_probe():
            return _rejected_handoff(WorkspaceCustodyRejectionReason.HANDOFF_CAPABILITY_UNSUPPORTED)
        occurred_at = datetime.now(UTC)
        admission, descriptors = self._admit_descriptors(request=request, occurred_at=occurred_at)
        workspace_fd = descriptors.get("workspace")
        try:
            if admission.reason is not None or admission.attestation is None or workspace_fd is None:
                return _rejected_handoff(admission.reason or WorkspaceCustodyRejectionReason.UNSAFE_ROOT)
            claim = self._claim(admission.attestation)
            if claim is not None:
                return _rejected_handoff(claim)
            capability_digest = _handoff_capability_digest()
            binding = WorkspaceCustodyRootBinding.issue(
                request=request,
                attestation=admission.attestation,
                workspace_object_identity=WorkspaceCustodyFilesystemObjectIdentity.from_descriptor(workspace_fd),
                capability_digest=capability_digest,
                acquired_at=occurred_at,
            )
            handle = _issue_workspace_custody_root_handle(
                descriptor=workspace_fd,
                binding=binding,
            )
            descriptors.pop("workspace")
            return WorkspaceCustodyRootHandoff(
                attestation=admission.attestation,
                binding=binding,
                handle=handle,
            )
        finally:
            _close_all(descriptors)

    def _claim(self, attestation: WorkspaceCustodyAttestation) -> WorkspaceCustodyRejectionReason | None:
        try:
            claim = self._custody_store.claim(attestation)
        except WorkspaceCustodyStoreCorruptionError:
            return WorkspaceCustodyRejectionReason.STORE_CORRUPT
        except WorkspaceCustodyStoreUnavailableError:
            return WorkspaceCustodyRejectionReason.STORE_UNAVAILABLE
        if claim.disposition is WorkspaceCustodyClaimDisposition.CLAIMED:
            return None
        if claim.disposition is WorkspaceCustodyClaimDisposition.DUPLICATE:
            return WorkspaceCustodyRejectionReason.ATTESTATION_ID_DUPLICATE
        return WorkspaceCustodyRejectionReason.ATTESTATION_ID_CONFLICT

    def _admit_descriptors(
        self,
        *,
        request: WorkspaceCustodyRequest,
        occurred_at: datetime,
    ) -> tuple[WorkspaceCustodyAdmission, dict[str, int]]:
        if not isinstance(request, WorkspaceCustodyRequest):
            raise TypeError("request must be a WorkspaceCustodyRequest")
        if not _handoff_capability_available() or not self._capability_probe():
            return _rejected_admission(WorkspaceCustodyRejectionReason.HANDOFF_CAPABILITY_UNSUPPORTED)
        if request.control_root.resolve() != self._custody_store.control_root.resolve():
            return _rejected_admission(WorkspaceCustodyRejectionReason.INVALID_ISOLATION)
        descriptors = _open_declared_roots(request)
        if descriptors is None:
            return _rejected_admission(WorkspaceCustodyRejectionReason.UNSAFE_ROOT)
        rejection = _descriptor_rejection(request=request, descriptors=descriptors)
        if rejection is not None:
            _close_all(descriptors)
            return _rejected_admission(rejection)
        identities = {
            name: WorkspaceCustodyFilesystemObjectIdentity.from_descriptor(descriptor)
            for name, descriptor in descriptors.items()
        }
        attestation = WorkspaceCustodyAttestation.issue_from_observations(
            request=request,
            workspace_identity=identities["workspace"],
            source_identity=identities["source"],
            audit_identity=identities["audit"],
            control_identity=identities["control"],
            occurred_at=occurred_at,
        )
        return WorkspaceCustodyAdmission(attestation=attestation), descriptors


def _rejected_admission(
    reason: WorkspaceCustodyRejectionReason,
) -> tuple[WorkspaceCustodyAdmission, dict[str, int]]:
    return WorkspaceCustodyAdmission(attestation=None, reason=reason), {}


def _rejected_handoff(reason: WorkspaceCustodyRejectionReason) -> WorkspaceCustodyRootHandoff:
    return WorkspaceCustodyRootHandoff(attestation=None, binding=None, handle=None, reason=reason)


def _handoff_capability_available() -> bool:
    required = ("O_DIRECTORY", "O_NOFOLLOW", "O_CLOEXEC")
    return all(hasattr(os, name) for name in required) and os.open in os.supports_dir_fd


def _handoff_capability_digest() -> str:
    payload = {
        "profile": WORKSPACE_CUSTODY_HANDOFF_CAPABILITY_PROFILE,
        "root_directory_open": True,
        "root_no_follow": True,
        "descriptor_fstat": True,
        "descriptor_scandir": True,
        "descriptor_relative_open": True,
    }
    return hashlib.sha256(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()).hexdigest()


def _open_declared_roots(request: WorkspaceCustodyRequest) -> dict[str, int] | None:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    roots = {
        "workspace": request.workspace_root,
        "source": request.source_repository_root,
        "audit": request.audit_root,
        "control": request.control_root,
    }
    descriptors: dict[str, int] = {}
    try:
        for name, root in roots.items():
            descriptors[name] = os.open(root, flags)
        return descriptors
    except OSError:
        _close_all(descriptors)
        return None


def _descriptor_rejection(
    *,
    request: WorkspaceCustodyRequest,
    descriptors: dict[str, int],
) -> WorkspaceCustodyRejectionReason | None:
    identities = {name: WorkspaceCustodyFilesystemObjectIdentity.from_descriptor(fd) for name, fd in descriptors.items()}
    if len({identity.digest for identity in identities.values()}) != len(identities):
        return WorkspaceCustodyRejectionReason.INVALID_ISOLATION
    if request.policy.require_empty_workspace and not _descriptor_empty(descriptors["workspace"]):
        return WorkspaceCustodyRejectionReason.NONEMPTY_WORKSPACE
    if _any_nested(descriptors):
        return WorkspaceCustodyRejectionReason.INVALID_ISOLATION
    return None


def _descriptor_empty(descriptor: int) -> bool:
    try:
        with os.scandir(descriptor) as entries:
            return next(entries, None) is None
    except OSError:
        return False


def _any_nested(descriptors: dict[str, int]) -> bool:
    names = tuple(descriptors)
    for ancestor_name in names:
        for descendant_name in names:
            if ancestor_name == descendant_name:
                continue
            if _is_ancestor(descriptors[ancestor_name], descriptors[descendant_name]):
                return True
    return False


def _is_ancestor(ancestor: int, descendant: int) -> bool:
    target = WorkspaceCustodyFilesystemObjectIdentity.from_descriptor(ancestor)
    current = os.dup(descendant)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        while True:
            observed = WorkspaceCustodyFilesystemObjectIdentity.from_descriptor(current)
            if observed == target:
                return True
            parent = os.open("..", flags, dir_fd=current)
            parent_identity = WorkspaceCustodyFilesystemObjectIdentity.from_descriptor(parent)
            if parent_identity == observed:
                os.close(parent)
                return False
            os.close(current)
            current = parent
    except OSError:
        return True
    finally:
        with suppress(OSError):
            os.close(current)


def _close_all(descriptors: dict[str, int]) -> None:
    for descriptor in descriptors.values():
        with suppress(OSError):
            os.close(descriptor)


__all__ = ["WorkspaceCustodyGate"]
