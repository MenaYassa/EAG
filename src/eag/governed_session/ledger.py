"""Durable, fail-closed storage for non-executing activation and session replay claims."""

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

DURABLE_REPLAY_LEDGER_SCHEMA_VERSION = "g2.4.8"


class DurableReplayLedgerError(RuntimeError):
    """Base error for durable replay-ledger operations."""


class ReplayLedgerCorruptionError(DurableReplayLedgerError):
    """Raised when an existing durable replay record fails integrity validation."""


class ReplayLedgerUnavailableError(DurableReplayLedgerError):
    """Raised when durable replay state cannot be safely read, locked, or claimed."""


class ReplayLedgerEntryKind(StrEnum):
    """The only non-executing replay claims persisted by the session boundary."""

    ACTIVATION_CLAIMED = "activation_claimed"
    SESSION_ISSUED = "session_issued"
    SESSION_CONSUMED = "session_consumed"


class ReplayLedgerClaimDisposition(StrEnum):
    """Atomic claim outcome without any permit or execution capability."""

    CLAIMED = "claimed"
    ALREADY_CLAIMED = "already_claimed"
    CONFLICT = "conflict"


def _require_non_empty(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DurableReplayLedgerError(f"{field_name} cannot be empty")
    return value


def _require_digest(value: str, field_name: str) -> str:
    _require_non_empty(value, field_name)
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise DurableReplayLedgerError(f"{field_name} must be a lowercase SHA-256 digest")
    return value


@dataclass(frozen=True, slots=True, kw_only=True)
class DurableReplayLedgerRecord:
    """Immutable, redacted replay claim keyed by a deterministic identity and binding digest."""

    entry_kind: ReplayLedgerEntryKind
    identity_key: str
    binding_digest: str

    def __post_init__(self) -> None:
        if not isinstance(self.entry_kind, ReplayLedgerEntryKind):
            raise TypeError("entry_kind must be a ReplayLedgerEntryKind")
        object.__setattr__(self, "identity_key", _require_non_empty(self.identity_key, "identity_key"))
        object.__setattr__(self, "binding_digest", _require_digest(self.binding_digest, "binding_digest"))

    def to_payload(self) -> dict[str, str]:
        """Serialize only deterministic, redacted replay identity data."""
        return {
            "binding_digest": self.binding_digest,
            "entry_kind": self.entry_kind.value,
            "identity_key": self.identity_key,
            "schema_version": DURABLE_REPLAY_LEDGER_SCHEMA_VERSION,
        }

    @classmethod
    def from_payload(cls, payload: object) -> DurableReplayLedgerRecord:
        """Validate a canonical stored record; malformed data is fail-closed corruption."""
        if not isinstance(payload, dict):
            raise ReplayLedgerCorruptionError("durable replay record must be an object")
        try:
            if payload.get("schema_version") != DURABLE_REPLAY_LEDGER_SCHEMA_VERSION:
                raise ReplayLedgerCorruptionError("unsupported durable replay ledger schema")
            if set(payload) != {"binding_digest", "entry_kind", "identity_key", "schema_version"}:
                raise ReplayLedgerCorruptionError("durable replay record has unexpected fields")
            return cls(
                entry_kind=ReplayLedgerEntryKind(payload["entry_kind"]),
                identity_key=payload["identity_key"],
                binding_digest=payload["binding_digest"],
            )
        except (KeyError, TypeError, ValueError, DurableReplayLedgerError) as error:
            if isinstance(error, ReplayLedgerCorruptionError):
                raise
            raise ReplayLedgerCorruptionError("invalid durable replay record") from error


@dataclass(frozen=True, slots=True, kw_only=True)
class ReplayLedgerClaim:
    """Immutable result of one atomic replay-record claim."""

    disposition: ReplayLedgerClaimDisposition
    existing_record: DurableReplayLedgerRecord | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.disposition, ReplayLedgerClaimDisposition):
            raise TypeError("disposition must be a ReplayLedgerClaimDisposition")
        if self.disposition is ReplayLedgerClaimDisposition.CLAIMED:
            if self.existing_record is not None:
                raise DurableReplayLedgerError("new replay claim cannot carry an existing record")
            return
        if not isinstance(self.existing_record, DurableReplayLedgerRecord):
            raise DurableReplayLedgerError("existing replay claim requires its immutable stored record")


class DurableSessionReplayLedger(Protocol):
    """Minimal injected storage boundary for durable, non-executing replay claims."""

    @property
    def control_root(self) -> Path:
        """Return the caller-supplied durable control-plane root without creating it."""

    def claim(self, record: DurableReplayLedgerRecord) -> ReplayLedgerClaim:
        """Atomically claim a record without overwrite, reset, deletion, or permit issuance."""

    def read(
        self,
        *,
        entry_kind: ReplayLedgerEntryKind,
        identity_key: str,
    ) -> DurableReplayLedgerRecord | None:
        """Read one validated record or return None only when the deterministic key is absent."""


class FileDurableSessionReplayLedger:
    """File-backed durable replay ledger with per-root process-safe claim serialization."""

    def __init__(self, *, control_root: Path) -> None:
        if not isinstance(control_root, Path):
            raise TypeError("control_root must be a Path")
        self._control_root = control_root

    @property
    def control_root(self) -> Path:
        """Expose the non-executing control root for gate-level isolation validation."""
        return self._control_root

    def claim(self, record: DurableReplayLedgerRecord) -> ReplayLedgerClaim:
        """Atomically create one immutable record or return a replay/conflict observation."""
        if not isinstance(record, DurableReplayLedgerRecord):
            raise TypeError("record must be a DurableReplayLedgerRecord")
        with self._locked_root():
            existing = self._read_unlocked(record.entry_kind, record.identity_key)
            if existing is None:
                self._write_unlocked(record)
                return ReplayLedgerClaim(disposition=ReplayLedgerClaimDisposition.CLAIMED)
            if existing == record:
                return ReplayLedgerClaim(
                    disposition=ReplayLedgerClaimDisposition.ALREADY_CLAIMED,
                    existing_record=existing,
                )
            return ReplayLedgerClaim(
                disposition=ReplayLedgerClaimDisposition.CONFLICT,
                existing_record=existing,
            )

    def read(
        self,
        *,
        entry_kind: ReplayLedgerEntryKind,
        identity_key: str,
    ) -> DurableReplayLedgerRecord | None:
        """Return a validated immutable record without changing durable replay state."""
        if not isinstance(entry_kind, ReplayLedgerEntryKind):
            raise TypeError("entry_kind must be a ReplayLedgerEntryKind")
        _require_non_empty(identity_key, "identity_key")
        with self._locked_root():
            return self._read_unlocked(entry_kind, identity_key)

    @contextmanager
    def _locked_root(self) -> Iterator[None]:
        self._validate_root()
        lock_path = self._control_root / ".g2_4_8_replay_ledger.lock"
        if lock_path.is_symlink():
            raise ReplayLedgerUnavailableError("durable replay ledger lock is unsafe")
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        except OSError as error:
            raise ReplayLedgerUnavailableError("durable replay ledger lock is unavailable") from error
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        except ReplayLedgerCorruptionError:
            raise
        except ReplayLedgerUnavailableError:
            raise
        except OSError as error:
            raise ReplayLedgerUnavailableError("durable replay ledger operation failed") from error
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
                raise ReplayLedgerUnavailableError("durable replay control root is unavailable")
        except OSError as error:
            raise ReplayLedgerUnavailableError("durable replay control root is unavailable") from error

    def _read_unlocked(
        self,
        entry_kind: ReplayLedgerEntryKind,
        identity_key: str,
    ) -> DurableReplayLedgerRecord | None:
        record_path = self._record_path(entry_kind, identity_key)
        try:
            if not record_path.exists():
                return None
            if record_path.is_symlink():
                raise ReplayLedgerCorruptionError("durable replay record must not be a symlink")
            payload = json.loads(record_path.read_text(encoding="utf-8"))
        except OSError as error:
            raise ReplayLedgerUnavailableError("durable replay record is unavailable") from error
        except (TypeError, ValueError) as error:
            raise ReplayLedgerCorruptionError("durable replay record is not valid JSON") from error
        record = DurableReplayLedgerRecord.from_payload(payload)
        if record.entry_kind is not entry_kind or record.identity_key != identity_key:
            raise ReplayLedgerCorruptionError("durable replay record does not match its deterministic key")
        return record

    def _write_unlocked(self, record: DurableReplayLedgerRecord) -> None:
        record_path = self._record_path(record.entry_kind, record.identity_key)
        payload = json.dumps(record.to_payload(), separators=(",", ":"), sort_keys=True).encode("utf-8")
        try:
            descriptor = os.open(
                record_path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
                0o600,
            )
        except FileExistsError:
            raise ReplayLedgerUnavailableError("durable replay record appeared during a locked claim") from None
        except OSError as error:
            raise ReplayLedgerUnavailableError("durable replay record cannot be claimed") from error
        try:
            with os.fdopen(descriptor, "wb", closefd=True) as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError as error:
            raise ReplayLedgerUnavailableError("durable replay record cannot be persisted") from error

    def _record_path(self, entry_kind: ReplayLedgerEntryKind, identity_key: str) -> Path:
        key_digest = hashlib.sha256(f"{entry_kind.value}:{identity_key}".encode()).hexdigest()
        return self._control_root / f"{entry_kind.value}-{key_digest}.json"


__all__ = [
    "DURABLE_REPLAY_LEDGER_SCHEMA_VERSION",
    "DurableReplayLedgerError",
    "DurableReplayLedgerRecord",
    "DurableSessionReplayLedger",
    "FileDurableSessionReplayLedger",
    "ReplayLedgerClaim",
    "ReplayLedgerClaimDisposition",
    "ReplayLedgerCorruptionError",
    "ReplayLedgerEntryKind",
    "ReplayLedgerUnavailableError",
]
