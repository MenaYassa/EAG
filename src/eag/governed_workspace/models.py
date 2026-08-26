"""Immutable G2.4.10 custody evidence and live root-handoff contracts."""

from __future__ import annotations

import hashlib
import json
import os
import threading
import weakref
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Literal, NoReturn

WORKSPACE_CUSTODY_REQUEST_SCHEMA_VERSION = "g2.4.10-custody-request.v2"
WORKSPACE_CUSTODY_ATTESTATION_SCHEMA_VERSION = "g2.4.10-custody-attestation.v2"
WORKSPACE_CUSTODY_OBJECT_IDENTITY_SCHEMA_VERSION = "g2.4.10-filesystem-object-identity.v1"
WORKSPACE_CUSTODY_ROOT_BINDING_SCHEMA_VERSION = "g2.4.10-custody-root-binding.v1"
WORKSPACE_CUSTODY_HANDOFF_CAPABILITY_PROFILE = "g2.4.10-descriptor-handoff-posix.v1"

_HANDLE_ISSUANCE_SENTINEL = object()
_HANDLE_ISSUANCE_LOCK = threading.RLock()


class WorkspaceCustodyError(ValueError):
    """Raised when custody evidence or a live handoff contract is invalid."""


class WorkspaceCustodyHandleError(WorkspaceCustodyError):
    """Raised when an opaque live root handle is misused."""


class WorkspaceCustodyDisposition(StrEnum):
    """Evidence-only outcome of a custody attestation."""

    ATTESTED = "attested"


class WorkspaceCustodyRejectionReason(StrEnum):
    """Typed fail-closed refusals from the custody boundary."""

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
    HANDOFF_CAPABILITY_UNSUPPORTED = "handoff_capability_unsupported"
    HANDLE_ALREADY_CONSUMED = "handle_already_consumed"
    HANDLE_CLOSED = "handle_closed"
    HANDLE_BINDING_MISMATCH = "handle_binding_mismatch"
    HANDLE_CONTEXT_MISMATCH = "handle_context_mismatch"
    CUSTODY_CONTINUITY_BROKEN = "custody_continuity_broken"


def _canonical(payload: object) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()


def _digest(payload: object) -> str:
    return hashlib.sha256(_canonical(payload)).hexdigest()


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
    """Return a redacted declared-path identity; it is never live-handoff authority."""
    if not isinstance(root, Path):
        raise TypeError("root must be a Path")
    return hashlib.sha256(str(root).encode()).hexdigest()


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkspaceCustodyPolicy:
    """Strict declarative checks; never an execution or construction policy."""

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

    def to_payload(self) -> dict[str, bool]:
        return {
            "forbid_root_symlinks": self.forbid_root_symlinks,
            "require_empty_workspace": self.require_empty_workspace,
            "require_existing_roots": self.require_existing_roots,
        }

    @property
    def digest(self) -> str:
        return _digest(self.to_payload())


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkspaceCustodyRequest:
    """Immutable prospective root declaration with v2 self-identifying canonical form."""

    attestation_id: str
    execution_id: str
    run_id: str
    workspace_id: str
    workspace_root: Path
    source_repository_root: Path
    audit_root: Path
    control_root: Path
    policy: WorkspaceCustodyPolicy = WorkspaceCustodyPolicy()
    custody_request_id: str | None = None
    schema_version: str = WORKSPACE_CUSTODY_REQUEST_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field_name in ("attestation_id", "execution_id", "run_id", "workspace_id"):
            object.__setattr__(self, field_name, _require_non_empty(getattr(self, field_name), field_name))
        for field_name in ("workspace_root", "source_repository_root", "audit_root", "control_root"):
            if not isinstance(getattr(self, field_name), Path):
                raise TypeError(f"{field_name} must be a Path")
        if not isinstance(self.policy, WorkspaceCustodyPolicy):
            raise TypeError("policy must be a WorkspaceCustodyPolicy")
        if self.schema_version != WORKSPACE_CUSTODY_REQUEST_SCHEMA_VERSION:
            raise WorkspaceCustodyError("unsupported custody request schema")
        request_id = self.custody_request_id or f"{self.attestation_id}:request"
        object.__setattr__(self, "custody_request_id", _require_non_empty(request_id, "custody_request_id"))

    def to_payload(self) -> dict[str, object]:
        return {
            "attestation_id": self.attestation_id,
            "audit_root": str(self.audit_root),
            "control_root": str(self.control_root),
            "custody_request_id": self.custody_request_id,
            "execution_id": self.execution_id,
            "policy": self.policy.to_payload(),
            "run_id": self.run_id,
            "schema_version": self.schema_version,
            "source_repository_root": str(self.source_repository_root),
            "workspace_id": self.workspace_id,
            "workspace_root": str(self.workspace_root),
        }

    @property
    def request_digest(self) -> str:
        return _digest(self.to_payload())


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkspaceCustodyFilesystemObjectIdentity:
    """Descriptor-observed object fact; not an anti-reuse reconstruction mechanism."""

    device_id: str
    inode: str
    schema_version: str = WORKSPACE_CUSTODY_OBJECT_IDENTITY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field_name in ("device_id", "inode"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.isdecimal() or int(value) < 0:
                raise WorkspaceCustodyError(f"{field_name} must be a non-negative decimal string")
        if self.schema_version != WORKSPACE_CUSTODY_OBJECT_IDENTITY_SCHEMA_VERSION:
            raise WorkspaceCustodyError("unsupported filesystem object identity schema")

    @classmethod
    def from_descriptor(cls, descriptor: int) -> WorkspaceCustodyFilesystemObjectIdentity:
        try:
            observed = os.fstat(descriptor)
        except OSError as error:
            raise WorkspaceCustodyError("workspace descriptor is unavailable") from error
        return cls(device_id=str(observed.st_dev), inode=str(observed.st_ino))

    def to_payload(self) -> dict[str, str]:
        return {"device_id": self.device_id, "inode": self.inode, "schema_version": self.schema_version}

    @property
    def digest(self) -> str:
        return _digest(self.to_payload())


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkspaceCustodyAttestation:
    """Immutable v2 custody evidence issued from one descriptor-first custody event."""

    attestation_id: str
    custody_request_id: str
    custody_request_digest: str
    execution_id: str
    run_id: str
    workspace_id: str
    workspace_root_identity: str
    source_repository_identity: str
    audit_root_identity: str
    control_root_identity: str
    workspace_object_identity: WorkspaceCustodyFilesystemObjectIdentity
    source_repository_object_identity: WorkspaceCustodyFilesystemObjectIdentity
    audit_root_object_identity: WorkspaceCustodyFilesystemObjectIdentity
    control_root_object_identity: WorkspaceCustodyFilesystemObjectIdentity
    custody_policy_digest: str
    isolation_binding_digest: str
    occurred_at: datetime
    disposition: WorkspaceCustodyDisposition
    binding_digest: str
    schema_version: str = WORKSPACE_CUSTODY_ATTESTATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field_name in ("attestation_id", "custody_request_id", "execution_id", "run_id", "workspace_id"):
            object.__setattr__(self, field_name, _require_non_empty(getattr(self, field_name), field_name))
        for field_name in (
            "custody_request_digest",
            "workspace_root_identity",
            "source_repository_identity",
            "audit_root_identity",
            "control_root_identity",
            "custody_policy_digest",
            "isolation_binding_digest",
            "binding_digest",
        ):
            object.__setattr__(self, field_name, _require_digest(getattr(self, field_name), field_name))
        for field_name in (
            "workspace_object_identity",
            "source_repository_object_identity",
            "audit_root_object_identity",
            "control_root_object_identity",
        ):
            if not isinstance(getattr(self, field_name), WorkspaceCustodyFilesystemObjectIdentity):
                raise TypeError(f"{field_name} must be a WorkspaceCustodyFilesystemObjectIdentity")
        object.__setattr__(self, "occurred_at", _canonical_occurrence(self.occurred_at))
        if self.disposition is not WorkspaceCustodyDisposition.ATTESTED:
            raise WorkspaceCustodyError("workspace custody attestation must be attested evidence")
        if self.schema_version != WORKSPACE_CUSTODY_ATTESTATION_SCHEMA_VERSION:
            raise WorkspaceCustodyError("unsupported custody attestation schema")
        if self.binding_digest != self.calculate_binding_digest():
            raise WorkspaceCustodyError("binding_digest does not match canonical custody evidence")

    @classmethod
    def issue_from_observations(
        cls,
        *,
        request: WorkspaceCustodyRequest,
        workspace_identity: WorkspaceCustodyFilesystemObjectIdentity,
        source_identity: WorkspaceCustodyFilesystemObjectIdentity,
        audit_identity: WorkspaceCustodyFilesystemObjectIdentity,
        control_identity: WorkspaceCustodyFilesystemObjectIdentity,
        occurred_at: datetime,
    ) -> WorkspaceCustodyAttestation:
        request_id = request.custody_request_id
        if request_id is None:
            raise WorkspaceCustodyError("v2 custody request must carry custody_request_id")
        occurred = _canonical_occurrence(occurred_at)
        path_workspace = root_identity(request.workspace_root)
        path_source = root_identity(request.source_repository_root)
        path_audit = root_identity(request.audit_root)
        path_control = root_identity(request.control_root)
        isolation_digest = isolation_binding_digest(
            execution_id=request.execution_id,
            run_id=request.run_id,
            workspace_id=request.workspace_id,
            workspace_root_identity=path_workspace,
            source_repository_identity=path_source,
            audit_root_identity=path_audit,
            control_root_identity=path_control,
        )
        payload = {
            "attestation_id": request.attestation_id,
            "audit_root_identity": path_audit,
            "audit_root_object_identity": audit_identity.to_payload(),
            "control_root_identity": path_control,
            "control_root_object_identity": control_identity.to_payload(),
            "custody_policy_digest": request.policy.digest,
            "custody_request_digest": request.request_digest,
            "custody_request_id": request_id,
            "execution_id": request.execution_id,
            "isolation_binding_digest": isolation_digest,
            "occurred_at": occurred.isoformat(),
            "run_id": request.run_id,
            "schema_version": WORKSPACE_CUSTODY_ATTESTATION_SCHEMA_VERSION,
            "source_repository_identity": path_source,
            "source_repository_object_identity": source_identity.to_payload(),
            "workspace_id": request.workspace_id,
            "workspace_root_identity": path_workspace,
            "workspace_object_identity": workspace_identity.to_payload(),
        }
        return cls(
            attestation_id=request.attestation_id,
            custody_request_id=request_id,
            custody_request_digest=request.request_digest,
            execution_id=request.execution_id,
            run_id=request.run_id,
            workspace_id=request.workspace_id,
            workspace_root_identity=path_workspace,
            source_repository_identity=path_source,
            audit_root_identity=path_audit,
            control_root_identity=path_control,
            workspace_object_identity=workspace_identity,
            source_repository_object_identity=source_identity,
            audit_root_object_identity=audit_identity,
            control_root_object_identity=control_identity,
            custody_policy_digest=request.policy.digest,
            isolation_binding_digest=isolation_digest,
            occurred_at=occurred,
            disposition=WorkspaceCustodyDisposition.ATTESTED,
            binding_digest=_digest(payload),
        )

    def calculate_binding_digest(self) -> str:
        return _digest(self._payload_without_digest())

    def _payload_without_digest(self) -> dict[str, object]:
        return {
            "attestation_id": self.attestation_id,
            "audit_root_identity": self.audit_root_identity,
            "audit_root_object_identity": self.audit_root_object_identity.to_payload(),
            "control_root_identity": self.control_root_identity,
            "control_root_object_identity": self.control_root_object_identity.to_payload(),
            "custody_policy_digest": self.custody_policy_digest,
            "custody_request_digest": self.custody_request_digest,
            "custody_request_id": self.custody_request_id,
            "execution_id": self.execution_id,
            "isolation_binding_digest": self.isolation_binding_digest,
            "occurred_at": self.occurred_at.isoformat(),
            "run_id": self.run_id,
            "schema_version": self.schema_version,
            "source_repository_identity": self.source_repository_identity,
            "source_repository_object_identity": self.source_repository_object_identity.to_payload(),
            "workspace_id": self.workspace_id,
            "workspace_root_identity": self.workspace_root_identity,
            "workspace_object_identity": self.workspace_object_identity.to_payload(),
        }

    def to_payload(self) -> dict[str, object]:
        payload = self._payload_without_digest()
        payload["binding_digest"] = self.binding_digest
        payload["disposition"] = self.disposition.value
        return payload

    @classmethod
    def from_payload(cls, payload: object) -> WorkspaceCustodyAttestation:
        if not isinstance(payload, dict):
            raise WorkspaceCustodyError("workspace custody payload must be an object")
        required = set(cls._required_payload_fields())
        if set(payload) != required:
            raise WorkspaceCustodyError("workspace custody payload has unexpected fields")
        try:
            return cls(
                attestation_id=payload["attestation_id"],
                custody_request_id=payload["custody_request_id"],
                custody_request_digest=payload["custody_request_digest"],
                execution_id=payload["execution_id"],
                run_id=payload["run_id"],
                workspace_id=payload["workspace_id"],
                workspace_root_identity=payload["workspace_root_identity"],
                source_repository_identity=payload["source_repository_identity"],
                audit_root_identity=payload["audit_root_identity"],
                control_root_identity=payload["control_root_identity"],
                workspace_object_identity=_object_identity(payload["workspace_object_identity"]),
                source_repository_object_identity=_object_identity(payload["source_repository_object_identity"]),
                audit_root_object_identity=_object_identity(payload["audit_root_object_identity"]),
                control_root_object_identity=_object_identity(payload["control_root_object_identity"]),
                custody_policy_digest=payload["custody_policy_digest"],
                isolation_binding_digest=payload["isolation_binding_digest"],
                occurred_at=datetime.fromisoformat(payload["occurred_at"]),
                disposition=WorkspaceCustodyDisposition(payload["disposition"]),
                binding_digest=payload["binding_digest"],
                schema_version=payload["schema_version"],
            )
        except (KeyError, TypeError, ValueError, WorkspaceCustodyError) as error:
            raise WorkspaceCustodyError("invalid workspace custody payload") from error

    @staticmethod
    def _required_payload_fields() -> tuple[str, ...]:
        return (
            "attestation_id",
            "audit_root_identity",
            "audit_root_object_identity",
            "binding_digest",
            "control_root_identity",
            "control_root_object_identity",
            "custody_policy_digest",
            "custody_request_digest",
            "custody_request_id",
            "disposition",
            "execution_id",
            "isolation_binding_digest",
            "occurred_at",
            "run_id",
            "schema_version",
            "source_repository_identity",
            "source_repository_object_identity",
            "workspace_id",
            "workspace_root_identity",
            "workspace_object_identity",
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkspaceCustodyAdmission:
    """Immutable evidence-only result from the existing published attestation API."""

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


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkspaceCustodyRootBinding:
    """Immutable evidence that one exact live workspace descriptor was custody-admitted."""

    binding_id: str
    custody_request_id: str
    custody_request_digest: str
    custody_attestation_id: str
    custody_attestation_binding_digest: str
    workspace_object_identity: WorkspaceCustodyFilesystemObjectIdentity
    containment_capability_profile: str
    containment_capability_digest: str
    acquired_at: datetime
    binding_digest: str
    schema_version: str = WORKSPACE_CUSTODY_ROOT_BINDING_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field_name in (
            "binding_id",
            "custody_request_id",
            "custody_attestation_id",
            "containment_capability_profile",
        ):
            object.__setattr__(self, field_name, _require_non_empty(getattr(self, field_name), field_name))
        for field_name in (
            "custody_request_digest",
            "custody_attestation_binding_digest",
            "containment_capability_digest",
            "binding_digest",
        ):
            object.__setattr__(self, field_name, _require_digest(getattr(self, field_name), field_name))
        if not isinstance(self.workspace_object_identity, WorkspaceCustodyFilesystemObjectIdentity):
            raise TypeError("workspace_object_identity must be a WorkspaceCustodyFilesystemObjectIdentity")
        object.__setattr__(self, "acquired_at", _canonical_occurrence(self.acquired_at))
        if self.schema_version != WORKSPACE_CUSTODY_ROOT_BINDING_SCHEMA_VERSION:
            raise WorkspaceCustodyError("unsupported custody root binding schema")
        if self.binding_digest != self.calculate_binding_digest():
            raise WorkspaceCustodyError("binding_digest does not match canonical custody root binding")

    @classmethod
    def issue(
        cls,
        *,
        request: WorkspaceCustodyRequest,
        attestation: WorkspaceCustodyAttestation,
        workspace_object_identity: WorkspaceCustodyFilesystemObjectIdentity,
        capability_digest: str,
        acquired_at: datetime,
    ) -> WorkspaceCustodyRootBinding:
        request_id = request.custody_request_id
        if request_id is None:
            raise WorkspaceCustodyError("v2 custody request must carry custody_request_id")
        occurred = _canonical_occurrence(acquired_at)
        binding_id = f"{attestation.attestation_id}:root-binding"
        normalized_capability_digest = _require_digest(capability_digest, "capability_digest")
        payload = {
            "acquired_at": occurred.isoformat(),
            "binding_id": binding_id,
            "containment_capability_digest": normalized_capability_digest,
            "containment_capability_profile": WORKSPACE_CUSTODY_HANDOFF_CAPABILITY_PROFILE,
            "custody_attestation_binding_digest": attestation.binding_digest,
            "custody_attestation_id": attestation.attestation_id,
            "custody_request_digest": request.request_digest,
            "custody_request_id": request_id,
            "schema_version": WORKSPACE_CUSTODY_ROOT_BINDING_SCHEMA_VERSION,
            "workspace_object_identity": workspace_object_identity.to_payload(),
        }
        return cls(
            binding_id=binding_id,
            custody_request_id=request_id,
            custody_request_digest=request.request_digest,
            custody_attestation_id=attestation.attestation_id,
            custody_attestation_binding_digest=attestation.binding_digest,
            workspace_object_identity=workspace_object_identity,
            containment_capability_profile=WORKSPACE_CUSTODY_HANDOFF_CAPABILITY_PROFILE,
            containment_capability_digest=normalized_capability_digest,
            acquired_at=occurred,
            binding_digest=_digest(payload),
        )

    def calculate_binding_digest(self) -> str:
        return _digest(
            {
                "acquired_at": self.acquired_at.isoformat(),
                "binding_id": self.binding_id,
                "containment_capability_digest": self.containment_capability_digest,
                "containment_capability_profile": self.containment_capability_profile,
                "custody_attestation_binding_digest": self.custody_attestation_binding_digest,
                "custody_attestation_id": self.custody_attestation_id,
                "custody_request_digest": self.custody_request_digest,
                "custody_request_id": self.custody_request_id,
                "schema_version": self.schema_version,
                "workspace_object_identity": self.workspace_object_identity.to_payload(),
            }
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkspaceCustodyRootHandoff:
    """Single integrated custody event output; it is not execution authority."""

    attestation: WorkspaceCustodyAttestation | None
    binding: WorkspaceCustodyRootBinding | None
    handle: WorkspaceCustodyRootHandle | None
    reason: WorkspaceCustodyRejectionReason | None = None

    def __post_init__(self) -> None:
        if self.reason is None:
            if not (
                isinstance(self.attestation, WorkspaceCustodyAttestation)
                and isinstance(self.binding, WorkspaceCustodyRootBinding)
                and isinstance(self.handle, WorkspaceCustodyRootHandle)
            ):
                raise WorkspaceCustodyError("successful root handoff requires attestation, binding, and handle")
            return
        if not isinstance(self.reason, WorkspaceCustodyRejectionReason):
            raise TypeError("reason must be a WorkspaceCustodyRejectionReason")
        if any(value is not None for value in (self.attestation, self.binding, self.handle)):
            raise WorkspaceCustodyError("rejected root handoff cannot expose live or immutable handoff outputs")


class WorkspaceCustodyRootHandle:
    """Opaque one-shot process/thread-local root descriptor for G2.4.22 only."""

    __slots__ = (
        "_binding_digest",
        "_closed",
        "_consumed",
        "_descriptor",
        "_pid",
        "_state_lock",
        "_thread_id",
        "_transitioning",
        "__weakref__",
    )

    def __init__(
        self,
        *,
        descriptor: int,
        binding: WorkspaceCustodyRootBinding,
        _issuance: object | None = None,
    ) -> None:
        if _issuance is not _HANDLE_ISSUANCE_SENTINEL:
            raise WorkspaceCustodyHandleError(WorkspaceCustodyRejectionReason.CUSTODY_CONTINUITY_BROKEN.value)
        if not isinstance(descriptor, int) or descriptor < 0:
            raise WorkspaceCustodyError("descriptor must be an open non-negative integer")
        self._descriptor = descriptor
        self._binding_digest = binding.binding_digest
        self._pid = os.getpid()
        self._thread_id = threading.get_ident()
        self._state_lock = threading.RLock()
        self._transitioning = False
        self._consumed = False
        self._closed = False

    @property
    def binding_digest(self) -> str:
        return self._binding_digest

    @property
    def is_closed(self) -> bool:
        return self._closed

    def consume_for_g2_4_22(self, *, binding: WorkspaceCustodyRootBinding) -> int:
        """Return the G2.4.10-issued descriptor only once to the named construction consumer."""
        with self._state_lock:
            if self._closed:
                raise WorkspaceCustodyHandleError(WorkspaceCustodyRejectionReason.HANDLE_CLOSED.value)
            if not _is_issued_root_handle(self):
                raise WorkspaceCustodyHandleError(WorkspaceCustodyRejectionReason.CUSTODY_CONTINUITY_BROKEN.value)
            if self._consumed or self._transitioning:
                raise WorkspaceCustodyHandleError(WorkspaceCustodyRejectionReason.HANDLE_ALREADY_CONSUMED.value)
            if os.getpid() != self._pid or threading.get_ident() != self._thread_id:
                raise WorkspaceCustodyHandleError(WorkspaceCustodyRejectionReason.HANDLE_CONTEXT_MISMATCH.value)
            self._transitioning = True
            try:
                if binding.binding_digest != self._binding_digest:
                    raise WorkspaceCustodyHandleError(WorkspaceCustodyRejectionReason.HANDLE_BINDING_MISMATCH.value)
                self._consumed = True
                return self._descriptor
            finally:
                self._transitioning = False

    def close(self) -> None:
        with self._state_lock:
            if self._closed:
                return
            if self._transitioning:
                raise WorkspaceCustodyHandleError(WorkspaceCustodyRejectionReason.HANDLE_ALREADY_CONSUMED.value)
            self._closed = True
            try:
                with suppress(OSError):
                    os.close(self._descriptor)
            finally:
                _revoke_issued_root_handle(self)

    def __enter__(self) -> WorkspaceCustodyRootHandle:
        if self._closed:
            raise WorkspaceCustodyHandleError(WorkspaceCustodyRejectionReason.HANDLE_CLOSED.value)
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> Literal[False]:
        del exc_type, exc, traceback
        self.close()
        return False

    def __copy__(self) -> NoReturn:
        raise WorkspaceCustodyHandleError("custody root handles cannot be copied")

    def __deepcopy__(self, memo: object) -> NoReturn:
        del memo
        raise WorkspaceCustodyHandleError("custody root handles cannot be copied")

    def __reduce__(self) -> NoReturn:
        raise WorkspaceCustodyHandleError("custody root handles cannot be serialized")

    def __getstate__(self) -> NoReturn:
        raise WorkspaceCustodyHandleError("custody root handles cannot be serialized")


_ISSUED_ROOT_HANDLES: weakref.WeakSet[WorkspaceCustodyRootHandle] = weakref.WeakSet()


def _issue_workspace_custody_root_handle(
    *,
    descriptor: int,
    binding: WorkspaceCustodyRootBinding,
) -> WorkspaceCustodyRootHandle:
    """Create and register one non-durable live handle for the successful custody handoff only."""
    handle = WorkspaceCustodyRootHandle(
        descriptor=descriptor,
        binding=binding,
        _issuance=_HANDLE_ISSUANCE_SENTINEL,
    )
    with _HANDLE_ISSUANCE_LOCK:
        _ISSUED_ROOT_HANDLES.add(handle)
    return handle


def _is_issued_root_handle(handle: WorkspaceCustodyRootHandle) -> bool:
    """Return whether the exact live handle object was issued by this process-local owner."""
    with _HANDLE_ISSUANCE_LOCK:
        return handle in _ISSUED_ROOT_HANDLES


def _revoke_issued_root_handle(handle: WorkspaceCustodyRootHandle) -> None:
    """Remove a closed live handle from the non-durable issuance registry."""
    with _HANDLE_ISSUANCE_LOCK:
        _ISSUED_ROOT_HANDLES.discard(handle)


def _object_identity(payload: object) -> WorkspaceCustodyFilesystemObjectIdentity:
    if not isinstance(payload, dict) or set(payload) != {"device_id", "inode", "schema_version"}:
        raise WorkspaceCustodyError("invalid filesystem object identity payload")
    return WorkspaceCustodyFilesystemObjectIdentity(
        device_id=payload["device_id"], inode=payload["inode"], schema_version=payload["schema_version"]
    )


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
    return _digest(
        {
            "audit_root_identity": _require_digest(audit_root_identity, "audit_root_identity"),
            "control_root_identity": _require_digest(control_root_identity, "control_root_identity"),
            "execution_id": _require_non_empty(execution_id, "execution_id"),
            "run_id": _require_non_empty(run_id, "run_id"),
            "source_repository_identity": _require_digest(source_repository_identity, "source_repository_identity"),
            "workspace_id": _require_non_empty(workspace_id, "workspace_id"),
            "workspace_root_identity": _require_digest(workspace_root_identity, "workspace_root_identity"),
        }
    )


__all__ = [
    "WORKSPACE_CUSTODY_ATTESTATION_SCHEMA_VERSION",
    "WORKSPACE_CUSTODY_HANDOFF_CAPABILITY_PROFILE",
    "WORKSPACE_CUSTODY_OBJECT_IDENTITY_SCHEMA_VERSION",
    "WORKSPACE_CUSTODY_REQUEST_SCHEMA_VERSION",
    "WORKSPACE_CUSTODY_ROOT_BINDING_SCHEMA_VERSION",
    "WorkspaceCustodyAdmission",
    "WorkspaceCustodyAttestation",
    "WorkspaceCustodyDisposition",
    "WorkspaceCustodyError",
    "WorkspaceCustodyFilesystemObjectIdentity",
    "WorkspaceCustodyHandleError",
    "WorkspaceCustodyPolicy",
    "WorkspaceCustodyRejectionReason",
    "WorkspaceCustodyRequest",
    "WorkspaceCustodyRootBinding",
    "WorkspaceCustodyRootHandle",
    "WorkspaceCustodyRootHandoff",
    "isolation_binding_digest",
    "root_identity",
]
