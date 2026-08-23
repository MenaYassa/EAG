"""Durable, fail-closed immutable storage for G2.4.17 transition control."""

from __future__ import annotations

import fcntl
import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol, runtime_checkable

from eag.governed_transition_control.models import (
    ExternalTransitionControlRequest,
    TransitionControlEvidenceError,
    TransitionControlRecord,
    TransitionControlRecordState,
)


class TransitionControlLedgerError(RuntimeError):
    """Base error for durable transition-control state."""


class TransitionControlLedgerUnavailableError(TransitionControlLedgerError):
    """Raised when durable control state cannot be safely read or claimed."""


class TransitionControlLedgerCorruptionError(TransitionControlLedgerError):
    """Raised when durable control state is malformed, incomplete, or unsafe."""


class TransitionControlClaimDisposition(StrEnum):
    """Atomic immutable claim outcomes with no execution implication."""

    CLAIMED = "claimed"
    DUPLICATE = "duplicate"
    CONFLICT = "conflict"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True, slots=True, kw_only=True)
class TransitionControlClaim:
    """Immutable result of one ledger claim attempt."""

    disposition: TransitionControlClaimDisposition
    record: TransitionControlRecord

    def __post_init__(self) -> None:
        if not isinstance(self.disposition, TransitionControlClaimDisposition):
            raise TypeError("disposition must be a TransitionControlClaimDisposition")
        if not isinstance(self.record, TransitionControlRecord):
            raise TypeError("record must be a TransitionControlRecord")
        if self.disposition is TransitionControlClaimDisposition.AMBIGUOUS:
            if self.record.state is not TransitionControlRecordState.AMBIGUOUS:
                raise TransitionControlLedgerError("ambiguous claim must reference an ambiguous record")
        elif self.record.state is not TransitionControlRecordState.CLAIMED:
            raise TransitionControlLedgerError("non-ambiguous claim must reference a claimed record")


@runtime_checkable
class DurableTransitionControlLedger(Protocol):
    """Minimal injected ledger authority with only immutable claim and read operations."""

    @property
    def control_root(self) -> Path:
        """Return the caller-provided ledger root without creating it."""

    def claim(self, request: ExternalTransitionControlRequest) -> TransitionControlClaim:
        """Atomically claim one exact pre-execution transition-control identity."""

    def read(self, *, control_key: str) -> TransitionControlRecord | None:
        """Read one strict validated immutable record, or `None` only when absent."""


class FileDurableTransitionControlLedger:
    """File-backed immutable transition-control state.

    This mechanism can neither authorize external work nor execute it. It only
    persists pre-execution control evidence keyed by a canonical idempotency key.
    """

    def __init__(self, *, control_root: Path) -> None:
        if not isinstance(control_root, Path):
            raise TypeError("control_root must be a Path")
        self._control_root = control_root

    @property
    def control_root(self) -> Path:
        return self._control_root

    def claim(self, request: ExternalTransitionControlRequest) -> TransitionControlClaim:
        if not isinstance(request, ExternalTransitionControlRequest):
            raise TypeError("request must be an ExternalTransitionControlRequest")
        with self._locked_root():
            existing = self._read_unlocked(request.control_key)
            if existing is None:
                record = TransitionControlRecord.create(
                    control_id=f"control-{request.control_key[:16]}",
                    request=request,
                    state=TransitionControlRecordState.CLAIMED,
                    occurred_at=request.occurred_at,
                )
                self._write_unlocked(record)
                return TransitionControlClaim(
                    disposition=TransitionControlClaimDisposition.CLAIMED,
                    record=record,
                )
            if existing.state is TransitionControlRecordState.AMBIGUOUS:
                return TransitionControlClaim(
                    disposition=TransitionControlClaimDisposition.AMBIGUOUS,
                    record=existing,
                )
            if existing.binding_digest == request.binding_digest:
                return TransitionControlClaim(
                    disposition=TransitionControlClaimDisposition.DUPLICATE,
                    record=existing,
                )
            return TransitionControlClaim(
                disposition=TransitionControlClaimDisposition.CONFLICT,
                record=existing,
            )

    def read(self, *, control_key: str) -> TransitionControlRecord | None:
        _require_control_key(control_key)
        with self._locked_root():
            return self._read_unlocked(control_key)

    @contextmanager
    def _locked_root(self) -> Iterator[None]:
        self._validate_root()
        lock_path = self._control_root / ".g2_4_17_transition_control.lock"
        if lock_path.is_symlink():
            raise TransitionControlLedgerUnavailableError("transition control lock is unsafe")
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        except OSError as error:
            raise TransitionControlLedgerUnavailableError("transition control lock is unavailable") from error
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        except (TransitionControlLedgerUnavailableError, TransitionControlLedgerCorruptionError):
            raise
        except OSError as error:
            raise TransitionControlLedgerUnavailableError("transition control operation failed") from error
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
                raise TransitionControlLedgerUnavailableError("transition control root is unavailable")
        except OSError as error:
            raise TransitionControlLedgerUnavailableError("transition control root is unavailable") from error

    def _read_unlocked(self, control_key: str) -> TransitionControlRecord | None:
        record_path = self._record_path(control_key)
        try:
            if record_path.is_symlink():
                raise TransitionControlLedgerCorruptionError(
                    "transition control record must not be a symlink"
                )
            if not record_path.exists():
                return None
            payload = json.loads(record_path.read_text(encoding="utf-8"))
        except OSError as error:
            raise TransitionControlLedgerUnavailableError("transition control record is unavailable") from error
        except (TypeError, ValueError) as error:
            raise TransitionControlLedgerCorruptionError("transition control record is not valid JSON") from error
        try:
            record = TransitionControlRecord.from_payload(payload)
        except TransitionControlEvidenceError as error:
            raise TransitionControlLedgerCorruptionError("transition control record is corrupt") from error
        if record.control_key != control_key:
            raise TransitionControlLedgerCorruptionError(
                "transition control record does not match its deterministic key"
            )
        return record

    def _write_unlocked(self, record: TransitionControlRecord) -> None:
        record_path = self._record_path(record.control_key)
        payload = json.dumps(record.to_payload(), separators=(",", ":"), sort_keys=True).encode("utf-8")
        try:
            descriptor = os.open(
                record_path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
                0o600,
            )
        except FileExistsError:
            raise TransitionControlLedgerUnavailableError(
                "transition control record appeared during locked claim"
            ) from None
        except OSError as error:
            raise TransitionControlLedgerUnavailableError("transition control record cannot be claimed") from error
        try:
            with os.fdopen(descriptor, "wb", closefd=True) as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError as error:
            raise TransitionControlLedgerUnavailableError("transition control record cannot be persisted") from error

    def _record_path(self, control_key: str) -> Path:
        return self._control_root / f"control-{_require_control_key(control_key)}.json"


def _require_control_key(value: object) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise TransitionControlLedgerError("control_key must be a lower-case SHA-256 digest")
    return value


__all__ = [
    "DurableTransitionControlLedger",
    "FileDurableTransitionControlLedger",
    "TransitionControlClaim",
    "TransitionControlClaimDisposition",
    "TransitionControlLedgerCorruptionError",
    "TransitionControlLedgerError",
    "TransitionControlLedgerUnavailableError",
]
