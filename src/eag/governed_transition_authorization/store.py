"""Durable, fail-closed storage for immutable G2.4.16 authorization evidence."""

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
from typing import Protocol, runtime_checkable

from eag.governed_transition_authorization.models import (
    ExternalTransitionAuthorizationReceipt,
    TransitionAuthorizationEvidenceError,
)


class TransitionAuthorizationStoreError(RuntimeError):
    """Base error for durable authorization evidence storage."""


class TransitionAuthorizationStoreUnavailableError(TransitionAuthorizationStoreError):
    """Raised when durable authorization evidence storage cannot be safely used."""


class TransitionAuthorizationStoreCorruptionError(TransitionAuthorizationStoreError):
    """Raised when persisted authorization evidence is incomplete, malformed, or unsafe."""


class AuthorizationClaimDisposition(StrEnum):
    """Atomic immutable authorization evidence claim outcomes."""

    CLAIMED = "claimed"
    DUPLICATE = "duplicate"
    CONFLICT = "conflict"


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthorizationClaim:
    """Immutable result of one non-overwriting durable authorization evidence claim."""

    disposition: AuthorizationClaimDisposition
    existing_receipt: ExternalTransitionAuthorizationReceipt | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.disposition, AuthorizationClaimDisposition):
            raise TypeError("disposition must be an AuthorizationClaimDisposition")
        if self.disposition is AuthorizationClaimDisposition.CLAIMED:
            if self.existing_receipt is not None:
                raise TransitionAuthorizationStoreError("new claim cannot include an existing receipt")
            return
        if not isinstance(self.existing_receipt, ExternalTransitionAuthorizationReceipt):
            raise TransitionAuthorizationStoreError("duplicate/conflict claim requires an existing receipt")


@runtime_checkable
class DurableTransitionAuthorizationStore(Protocol):
    """Minimal injected store with only immutable claim and validated read operations."""

    @property
    def control_root(self) -> Path:
        """Return the caller-supplied authorization evidence root without creating it."""

    def claim(self, receipt: ExternalTransitionAuthorizationReceipt) -> AuthorizationClaim:
        """Atomically persist one immutable receipt without overwrite, reset, release, or consumption."""

    def read(self, *, authorization_id: str) -> ExternalTransitionAuthorizationReceipt | None:
        """Read one validated receipt or return None only when its deterministic identity is absent."""


class FileDurableTransitionAuthorizationStore:
    """File-backed durable immutable authorization evidence storage.

    This class is a storage mechanism only. It cannot authorize a transition, issue a permit,
    consume evidence, connect to a destination, or perform an external action.
    """

    def __init__(self, *, control_root: Path) -> None:
        if not isinstance(control_root, Path):
            raise TypeError("control_root must be a Path")
        self._control_root = control_root

    @property
    def control_root(self) -> Path:
        return self._control_root

    def claim(self, receipt: ExternalTransitionAuthorizationReceipt) -> AuthorizationClaim:
        if not isinstance(receipt, ExternalTransitionAuthorizationReceipt):
            raise TypeError("receipt must be an ExternalTransitionAuthorizationReceipt")
        with self._locked_root():
            existing = self._read_unlocked(receipt.authorization_id)
            if existing is None:
                self._write_unlocked(receipt)
                return AuthorizationClaim(disposition=AuthorizationClaimDisposition.CLAIMED)
            if existing == receipt:
                return AuthorizationClaim(
                    disposition=AuthorizationClaimDisposition.DUPLICATE,
                    existing_receipt=existing,
                )
            return AuthorizationClaim(
                disposition=AuthorizationClaimDisposition.CONFLICT,
                existing_receipt=existing,
            )

    def read(self, *, authorization_id: str) -> ExternalTransitionAuthorizationReceipt | None:
        require_authorization_id(authorization_id)
        with self._locked_root():
            return self._read_unlocked(authorization_id)

    @contextmanager
    def _locked_root(self) -> Iterator[None]:
        self._validate_root()
        lock_path = self._control_root / ".g2_4_16_transition_authorization.lock"
        if lock_path.is_symlink():
            raise TransitionAuthorizationStoreUnavailableError("authorization store lock is unsafe")
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        except OSError as error:
            raise TransitionAuthorizationStoreUnavailableError("authorization store lock is unavailable") from error
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        except (TransitionAuthorizationStoreUnavailableError, TransitionAuthorizationStoreCorruptionError):
            raise
        except OSError as error:
            raise TransitionAuthorizationStoreUnavailableError("authorization store operation failed") from error
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
                raise TransitionAuthorizationStoreUnavailableError(
                    "authorization store control root is unavailable"
                )
        except OSError as error:
            raise TransitionAuthorizationStoreUnavailableError(
                "authorization store control root is unavailable"
            ) from error

    def _read_unlocked(self, authorization_id: str) -> ExternalTransitionAuthorizationReceipt | None:
        record_path = self._record_path(authorization_id)
        try:
            if record_path.is_symlink():
                raise TransitionAuthorizationStoreCorruptionError(
                    "authorization store record must not be a symlink"
                )
            if not record_path.exists():
                return None
            payload = json.loads(record_path.read_text(encoding="utf-8"))
        except OSError as error:
            raise TransitionAuthorizationStoreUnavailableError("authorization record is unavailable") from error
        except (TypeError, ValueError) as error:
            raise TransitionAuthorizationStoreCorruptionError("authorization record is not valid JSON") from error
        try:
            receipt = ExternalTransitionAuthorizationReceipt.from_payload(payload)
        except TransitionAuthorizationEvidenceError as error:
            raise TransitionAuthorizationStoreCorruptionError("authorization record is corrupt") from error
        if receipt.authorization_id != authorization_id:
            raise TransitionAuthorizationStoreCorruptionError(
                "authorization record does not match its deterministic identity"
            )
        return receipt

    def _write_unlocked(self, receipt: ExternalTransitionAuthorizationReceipt) -> None:
        record_path = self._record_path(receipt.authorization_id)
        payload = json.dumps(receipt.to_payload(), separators=(",", ":"), sort_keys=True).encode("utf-8")
        try:
            descriptor = os.open(
                record_path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
                0o600,
            )
        except FileExistsError:
            raise TransitionAuthorizationStoreUnavailableError(
                "authorization record appeared during locked claim"
            ) from None
        except OSError as error:
            raise TransitionAuthorizationStoreUnavailableError("authorization record cannot be claimed") from error
        try:
            with os.fdopen(descriptor, "wb", closefd=True) as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError as error:
            raise TransitionAuthorizationStoreUnavailableError("authorization record cannot be persisted") from error

    def _record_path(self, authorization_id: str) -> Path:
        digest = hashlib.sha256(authorization_id.encode("utf-8")).hexdigest()
        return self._control_root / f"authorization-{digest}.json"


def require_authorization_id(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TransitionAuthorizationStoreError("authorization_id cannot be empty")
    return value


__all__ = [
    "AuthorizationClaim",
    "AuthorizationClaimDisposition",
    "DurableTransitionAuthorizationStore",
    "FileDurableTransitionAuthorizationStore",
    "TransitionAuthorizationStoreCorruptionError",
    "TransitionAuthorizationStoreError",
    "TransitionAuthorizationStoreUnavailableError",
]
