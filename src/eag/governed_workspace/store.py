"""Durable, fail-closed storage for immutable governed workspace custody evidence."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from eag.governed_workspace.models import WorkspaceCustodyAttestation, WorkspaceCustodyError

GOVERNED_WORKSPACE_CUSTODY_STORE_SCHEMA_VERSION = "g2.4.10"


class WorkspaceCustodyStoreError(RuntimeError):
    """Base error for custody-store operations."""


class WorkspaceCustodyStoreCorruptionError(WorkspaceCustodyStoreError):
    """Raised when a stored custody record is not canonical immutable evidence."""


class WorkspaceCustodyStoreUnavailableError(WorkspaceCustodyStoreError):
    """Raised when custody storage cannot safely read, lock, or write durable state."""


class WorkspaceCustodyClaimDisposition(StrEnum):
    """Outcome of one atomic custody claim; it has no activation or execution effect."""

    CLAIMED = "claimed"
    DUPLICATE = "duplicate"
    CONFLICT = "conflict"


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkspaceCustodyClaim:
    """Immutable claim outcome for one attestation identity."""

    disposition: WorkspaceCustodyClaimDisposition
    existing_attestation: WorkspaceCustodyAttestation | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.disposition, WorkspaceCustodyClaimDisposition):
            raise TypeError("disposition must be a WorkspaceCustodyClaimDisposition")
        if self.disposition is WorkspaceCustodyClaimDisposition.CLAIMED:
            if self.existing_attestation is not None:
                raise WorkspaceCustodyStoreError("new custody claim cannot carry existing evidence")
            return
        if not isinstance(self.existing_attestation, WorkspaceCustodyAttestation):
            raise WorkspaceCustodyStoreError("duplicate/conflicting claim requires existing attestation")


class DurableWorkspaceCustodyStore(Protocol):
    """Injected durable boundary for immutable custody evidence only."""

    @property
    def control_root(self) -> Path:
        """Return the caller-provided durable control root without creating it."""

    def claim(self, attestation: WorkspaceCustodyAttestation) -> WorkspaceCustodyClaim:
        """Atomically claim immutable custody evidence with no overwrite or mutation capability."""

    def read(self, *, attestation_id: str) -> WorkspaceCustodyAttestation | None:
        """Read one canonical attestation or None only when its deterministic record is absent."""


class FileDurableWorkspaceCustodyStore:
    """File-backed immutable custody store with cross-process root locking and no reset/delete path."""

    def __init__(self, *, control_root: Path) -> None:
        if not isinstance(control_root, Path):
            raise TypeError("control_root must be a Path")
        self._control_root = control_root

    @property
    def control_root(self) -> Path:
        """Expose root for read-only control-plane isolation validation only."""
        return self._control_root

    def claim(self, attestation: WorkspaceCustodyAttestation) -> WorkspaceCustodyClaim:
        """Atomically persist immutable evidence or observe duplicate/conflicting evidence."""
        if not isinstance(attestation, WorkspaceCustodyAttestation):
            raise TypeError("attestation must be a WorkspaceCustodyAttestation")
        with self._locked_root():
            existing = self._read_unlocked(attestation.attestation_id)
            if existing is None:
                self._write_unlocked(attestation)
                return WorkspaceCustodyClaim(disposition=WorkspaceCustodyClaimDisposition.CLAIMED)
            if existing == attestation:
                return WorkspaceCustodyClaim(
                    disposition=WorkspaceCustodyClaimDisposition.DUPLICATE,
                    existing_attestation=existing,
                )
            return WorkspaceCustodyClaim(
                disposition=WorkspaceCustodyClaimDisposition.CONFLICT,
                existing_attestation=existing,
            )

    def read(self, *, attestation_id: str) -> WorkspaceCustodyAttestation | None:
        """Read validated immutable evidence without changing durable custody state."""
        _require_non_empty(attestation_id, "attestation_id")
        with self._locked_root():
            return self._read_unlocked(attestation_id)

    @contextmanager
    def _locked_root(self) -> Iterator[None]:
        self._validate_root()
        lock_path = self._control_root / ".g2_4_10_workspace_custody.lock"
        if lock_path.is_symlink():
            raise WorkspaceCustodyStoreUnavailableError("workspace custody lock is unsafe")
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        except OSError as error:
            raise WorkspaceCustodyStoreUnavailableError("workspace custody lock is unavailable") from error
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        except WorkspaceCustodyStoreCorruptionError:
            raise
        except WorkspaceCustodyStoreUnavailableError:
            raise
        except OSError as error:
            raise WorkspaceCustodyStoreUnavailableError("workspace custody operation failed") from error
        finally:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)

    def _validate_root(self) -> None:
        try:
            if (
                not self._control_root.exists()
                or not self._control_root.is_dir()
                or self._control_root.is_symlink()
            ):
                raise WorkspaceCustodyStoreUnavailableError("workspace custody control root is unavailable")
        except OSError as error:
            raise WorkspaceCustodyStoreUnavailableError("workspace custody control root is unavailable") from error

    def _read_unlocked(self, attestation_id: str) -> WorkspaceCustodyAttestation | None:
        record_path = self._record_path(attestation_id)
        try:
            if not record_path.exists():
                return None
            if record_path.is_symlink():
                raise WorkspaceCustodyStoreCorruptionError("workspace custody record must not be a symlink")
            payload = json.loads(record_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or payload.get("schema_version") != GOVERNED_WORKSPACE_CUSTODY_STORE_SCHEMA_VERSION:
                raise WorkspaceCustodyStoreCorruptionError("unsupported workspace custody record schema")
            if set(payload) != {"attestation", "schema_version"}:
                raise WorkspaceCustodyStoreCorruptionError("workspace custody record has unexpected fields")
            attestation = WorkspaceCustodyAttestation.from_payload(payload["attestation"])
        except OSError as error:
            raise WorkspaceCustodyStoreUnavailableError("workspace custody record is unavailable") from error
        except (TypeError, ValueError, WorkspaceCustodyError) as error:
            raise WorkspaceCustodyStoreCorruptionError("invalid workspace custody record") from error
        if attestation.attestation_id != attestation_id:
            raise WorkspaceCustodyStoreCorruptionError("workspace custody record does not match its deterministic key")
        return attestation

    def _write_unlocked(self, attestation: WorkspaceCustodyAttestation) -> None:
        record_path = self._record_path(attestation.attestation_id)
        payload = json.dumps(
            {
                "attestation": attestation.to_payload(),
                "schema_version": GOVERNED_WORKSPACE_CUSTODY_STORE_SCHEMA_VERSION,
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
        try:
            descriptor = os.open(
                record_path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
                0o600,
            )
        except FileExistsError:
            raise WorkspaceCustodyStoreUnavailableError("workspace custody record appeared during locked claim") from None
        except OSError as error:
            raise WorkspaceCustodyStoreUnavailableError("workspace custody record cannot be claimed") from error
        try:
            with os.fdopen(descriptor, "wb", closefd=True) as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError as error:
            raise WorkspaceCustodyStoreUnavailableError("workspace custody record cannot be persisted") from error

    def _record_path(self, attestation_id: str) -> Path:
        key_digest = hashlib.sha256(attestation_id.encode()).hexdigest()
        return self._control_root / f"attestation-{key_digest}.json"


def _require_non_empty(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WorkspaceCustodyStoreError(f"{field_name} cannot be empty")
    return value


__all__ = [
    "GOVERNED_WORKSPACE_CUSTODY_STORE_SCHEMA_VERSION",
    "DurableWorkspaceCustodyStore",
    "FileDurableWorkspaceCustodyStore",
    "WorkspaceCustodyClaim",
    "WorkspaceCustodyClaimDisposition",
    "WorkspaceCustodyStoreCorruptionError",
    "WorkspaceCustodyStoreError",
    "WorkspaceCustodyStoreUnavailableError",
]
