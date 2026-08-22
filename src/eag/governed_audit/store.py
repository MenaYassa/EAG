"""Append-only, read-only persistence for immutable governed audit envelopes."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
from contextlib import suppress
from pathlib import Path
from typing import Protocol

from eag.governed_audit.models import (
    AuditCollisionError,
    AuditIntegrityError,
    GovernedAuditError,
    GovernedExecutionAuditEnvelope,
)


class AuditStoreWriteError(GovernedAuditError):
    """Raised when a requested immutable audit append cannot be durably written."""


class GovernedExecutionAuditStore(Protocol):
    """Minimal persistence/query surface with no execution or lifecycle methods."""

    def append(self, envelope: GovernedExecutionAuditEnvelope) -> GovernedExecutionAuditEnvelope: ...

    def get(self, execution_id: str) -> GovernedExecutionAuditEnvelope | None: ...

    def list(self) -> tuple[GovernedExecutionAuditEnvelope, ...]: ...

    def find_by_evidence(self, reference_id: str) -> tuple[GovernedExecutionAuditEnvelope, ...]: ...


_locks_guard = threading.Lock()
_locks: dict[str, threading.Lock] = {}


class FileGovernedExecutionAuditStore:
    """Small atomic per-execution JSON store for read-only audit records."""

    def __init__(self, audit_root: Path) -> None:
        if not isinstance(audit_root, Path):
            raise TypeError("audit_root must be a Path")
        self._audit_root = audit_root.resolve()

    @property
    def audit_root(self) -> Path:
        """Return the caller-owned persistence root without mutating subject workspaces."""
        return self._audit_root

    def append(self, envelope: GovernedExecutionAuditEnvelope) -> GovernedExecutionAuditEnvelope:
        if not isinstance(envelope, GovernedExecutionAuditEnvelope):
            raise TypeError("envelope must be a GovernedExecutionAuditEnvelope")
        encoded = _canonical_bytes(envelope)
        with self._lock():
            self._ensure_root()
            path = self._path_for(envelope.execution_id)
            if path.exists():
                existing = self._load_path(path)
                if existing.record_digest == envelope.record_digest:
                    return existing
                raise AuditCollisionError(
                    "execution ID is already bound to a different immutable audit record"
                )
            self._atomic_write(path, encoded)
            persisted = self._load_path(path)
            if persisted.record_digest != envelope.record_digest:
                raise AuditIntegrityError("persisted audit record differs from requested immutable record")
            return persisted

    def get(self, execution_id: str) -> GovernedExecutionAuditEnvelope | None:
        _require_execution_id(execution_id)
        with self._lock():
            path = self._path_for(execution_id)
            if not path.exists():
                return None
            return self._load_path(path)

    def list(self) -> tuple[GovernedExecutionAuditEnvelope, ...]:
        with self._lock():
            if not self._audit_root.exists():
                return ()
            if not self._audit_root.is_dir():
                raise AuditStoreWriteError("audit root is not a directory")
            records = tuple(self._load_path(path) for path in sorted(self._audit_root.glob("*.json")))
        return tuple(sorted(records, key=lambda item: item.execution_id))

    def find_by_evidence(self, reference_id: str) -> tuple[GovernedExecutionAuditEnvelope, ...]:
        _require_execution_id(reference_id)
        return tuple(
            record
            for record in self.list()
            if any(evidence.reference_id == reference_id for evidence in record.evidence)
        )

    def _path_for(self, execution_id: str) -> Path:
        _require_execution_id(execution_id)
        filename = hashlib.sha256(execution_id.encode("utf-8")).hexdigest()
        return self._audit_root / f"{filename}.json"

    def _ensure_root(self) -> None:
        try:
            self._audit_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        except OSError as error:
            raise AuditStoreWriteError("audit root cannot be created") from error
        if not self._audit_root.is_dir():
            raise AuditStoreWriteError("audit root is not a directory")

    def _atomic_write(self, path: Path, encoded: bytes) -> None:
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix=".audit-",
                suffix=".tmp",
                dir=self._audit_root,
                delete=False,
            ) as handle:
                temporary_path = Path(handle.name)
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, path)
            _fsync_directory(self._audit_root)
        except OSError as error:
            raise AuditStoreWriteError("atomic audit persistence failed") from error
        finally:
            if temporary_path is not None:
                with suppress(OSError):
                    temporary_path.unlink(missing_ok=True)

    def _load_path(self, path: Path) -> GovernedExecutionAuditEnvelope:
        try:
            raw = path.read_bytes()
            payload = json.loads(raw.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AuditIntegrityError("audit record cannot be decoded") from error
        envelope = GovernedExecutionAuditEnvelope.from_payload(payload)
        expected = self._path_for(envelope.execution_id)
        if path != expected:
            raise AuditIntegrityError("audit filename does not match envelope execution identity")
        if _canonical_bytes(envelope) != raw:
            raise AuditIntegrityError("audit record is not canonically serialized")
        return envelope

    def _lock(self) -> threading.Lock:
        key = str(self._audit_root)
        with _locks_guard:
            return _locks.setdefault(key, threading.Lock())


def _canonical_bytes(envelope: GovernedExecutionAuditEnvelope) -> bytes:
    return (
        json.dumps(
            envelope.to_payload(),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _require_execution_id(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("execution_id/reference_id cannot be empty")
    return value


def _fsync_directory(path: Path) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError as error:
        raise AuditStoreWriteError("audit directory cannot be opened for synchronization") from error
    try:
        os.fsync(descriptor)
    except OSError as error:
        raise AuditStoreWriteError("audit directory cannot be synchronized") from error
    finally:
        os.close(descriptor)


__all__ = [
    "AuditStoreWriteError",
    "FileGovernedExecutionAuditStore",
    "GovernedExecutionAuditStore",
]
