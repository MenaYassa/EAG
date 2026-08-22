"""Durable, fail-closed storage for immutable governed human-approval evidence."""

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

from eag.governed_approval.models import GovernedApprovalError, GovernedApprovalReceipt

GOVERNED_APPROVAL_STORE_SCHEMA_VERSION = "g2.4.9"


class GovernedApprovalStoreError(RuntimeError):
    """Base error for governed approval-store operations."""


class GovernedApprovalStoreCorruptionError(GovernedApprovalStoreError):
    """Raised when a stored approval cannot be validated as canonical immutable evidence."""


class GovernedApprovalStoreUnavailableError(GovernedApprovalStoreError):
    """Raised when approval storage cannot safely read, lock, or write durable state."""


class GovernedApprovalClaimDisposition(StrEnum):
    """Outcome of an atomic immutable approval claim with no authorization side effect."""

    CLAIMED = "claimed"
    DUPLICATE = "duplicate"
    CONFLICT = "conflict"


@dataclass(frozen=True, slots=True, kw_only=True)
class GovernedApprovalClaim:
    """Immutable result of claiming one approval identity in durable storage."""

    disposition: GovernedApprovalClaimDisposition
    existing_receipt: GovernedApprovalReceipt | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.disposition, GovernedApprovalClaimDisposition):
            raise TypeError("disposition must be a GovernedApprovalClaimDisposition")
        if self.disposition is GovernedApprovalClaimDisposition.CLAIMED:
            if self.existing_receipt is not None:
                raise GovernedApprovalStoreError("new approval claim cannot carry an existing receipt")
            return
        if not isinstance(self.existing_receipt, GovernedApprovalReceipt):
            raise GovernedApprovalStoreError("duplicate/conflicting claim requires an existing receipt")


class DurableGovernedApprovalStore(Protocol):
    """Injected storage boundary for immutable approval evidence only."""

    @property
    def control_root(self) -> Path:
        """Return the caller-supplied control root without creating it."""

    def claim(self, receipt: GovernedApprovalReceipt) -> GovernedApprovalClaim:
        """Atomically claim an immutable approval ID without overwrite or mutation."""

    def read(self, *, approval_id: str) -> GovernedApprovalReceipt | None:
        """Read one canonical approval receipt or None only when its deterministic key is absent."""


class FileDurableGovernedApprovalStore:
    """File-backed immutable approval evidence store with per-root cross-process locking."""

    def __init__(self, *, control_root: Path) -> None:
        if not isinstance(control_root, Path):
            raise TypeError("control_root must be a Path")
        self._control_root = control_root

    @property
    def control_root(self) -> Path:
        """Expose the root exclusively for gate-level control-plane isolation validation."""
        return self._control_root

    def claim(self, receipt: GovernedApprovalReceipt) -> GovernedApprovalClaim:
        """Atomically persist immutable evidence or observe a duplicate/conflicting record."""
        if not isinstance(receipt, GovernedApprovalReceipt):
            raise TypeError("receipt must be a GovernedApprovalReceipt")
        with self._locked_root():
            existing = self._read_unlocked(receipt.approval_id)
            if existing is None:
                self._write_unlocked(receipt)
                return GovernedApprovalClaim(disposition=GovernedApprovalClaimDisposition.CLAIMED)
            if existing == receipt:
                return GovernedApprovalClaim(
                    disposition=GovernedApprovalClaimDisposition.DUPLICATE,
                    existing_receipt=existing,
                )
            return GovernedApprovalClaim(
                disposition=GovernedApprovalClaimDisposition.CONFLICT,
                existing_receipt=existing,
            )

    def read(self, *, approval_id: str) -> GovernedApprovalReceipt | None:
        """Return a validated approval receipt without changing durable approval evidence."""
        _require_non_empty(approval_id, "approval_id")
        with self._locked_root():
            return self._read_unlocked(approval_id)

    @contextmanager
    def _locked_root(self) -> Iterator[None]:
        self._validate_root()
        lock_path = self._control_root / ".g2_4_9_governed_approval.lock"
        if lock_path.is_symlink():
            raise GovernedApprovalStoreUnavailableError("governed approval store lock is unsafe")
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        except OSError as error:
            raise GovernedApprovalStoreUnavailableError("governed approval store lock is unavailable") from error
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        except GovernedApprovalStoreCorruptionError:
            raise
        except GovernedApprovalStoreUnavailableError:
            raise
        except OSError as error:
            raise GovernedApprovalStoreUnavailableError("governed approval store operation failed") from error
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
                raise GovernedApprovalStoreUnavailableError("governed approval control root is unavailable")
        except OSError as error:
            raise GovernedApprovalStoreUnavailableError("governed approval control root is unavailable") from error

    def _read_unlocked(self, approval_id: str) -> GovernedApprovalReceipt | None:
        record_path = self._record_path(approval_id)
        try:
            if not record_path.exists():
                return None
            if record_path.is_symlink():
                raise GovernedApprovalStoreCorruptionError("governed approval record must not be a symlink")
            payload = json.loads(record_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or payload.get("schema_version") != GOVERNED_APPROVAL_STORE_SCHEMA_VERSION:
                raise GovernedApprovalStoreCorruptionError("unsupported governed approval record schema")
            if set(payload) != {"receipt", "schema_version"}:
                raise GovernedApprovalStoreCorruptionError("governed approval record has unexpected fields")
            receipt = GovernedApprovalReceipt.from_payload(payload["receipt"])
        except OSError as error:
            raise GovernedApprovalStoreUnavailableError("governed approval record is unavailable") from error
        except (TypeError, ValueError, GovernedApprovalError) as error:
            raise GovernedApprovalStoreCorruptionError("invalid governed approval record") from error
        if receipt.approval_id != approval_id:
            raise GovernedApprovalStoreCorruptionError("governed approval record does not match its deterministic key")
        return receipt

    def _write_unlocked(self, receipt: GovernedApprovalReceipt) -> None:
        record_path = self._record_path(receipt.approval_id)
        payload = json.dumps(
            {
                "receipt": receipt.to_payload(),
                "schema_version": GOVERNED_APPROVAL_STORE_SCHEMA_VERSION,
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
            raise GovernedApprovalStoreUnavailableError("governed approval record appeared during locked claim") from None
        except OSError as error:
            raise GovernedApprovalStoreUnavailableError("governed approval record cannot be claimed") from error
        try:
            with os.fdopen(descriptor, "wb", closefd=True) as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError as error:
            raise GovernedApprovalStoreUnavailableError("governed approval record cannot be persisted") from error

    def _record_path(self, approval_id: str) -> Path:
        key_digest = hashlib.sha256(approval_id.encode()).hexdigest()
        return self._control_root / f"approval-{key_digest}.json"


def _require_non_empty(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GovernedApprovalStoreError(f"{field_name} cannot be empty")
    return value


__all__ = [
    "GOVERNED_APPROVAL_STORE_SCHEMA_VERSION",
    "DurableGovernedApprovalStore",
    "FileDurableGovernedApprovalStore",
    "GovernedApprovalClaim",
    "GovernedApprovalClaimDisposition",
    "GovernedApprovalStoreCorruptionError",
    "GovernedApprovalStoreError",
    "GovernedApprovalStoreUnavailableError",
]
