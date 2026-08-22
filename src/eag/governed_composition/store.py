"""Durable, fail-closed storage for immutable runtime composition evidence."""

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

from eag.governed_composition.models import RuntimeCompositionAttestation, RuntimeCompositionError

GOVERNED_RUNTIME_COMPOSITION_STORE_SCHEMA_VERSION = "g2.4.11"


class RuntimeCompositionStoreError(RuntimeError):
    """Base error for composition-store operations."""


class RuntimeCompositionStoreCorruptionError(RuntimeCompositionStoreError):
    """Raised when stored composition evidence is not canonical immutable data."""


class RuntimeCompositionStoreUnavailableError(RuntimeCompositionStoreError):
    """Raised when composition storage cannot safely read, lock, or write durable state."""


class RuntimeCompositionClaimDisposition(StrEnum):
    """Outcome of one atomic evidence claim; it has no runtime creation or dispatch effect."""

    CLAIMED = "claimed"
    DUPLICATE = "duplicate"
    CONFLICT = "conflict"


@dataclass(frozen=True, slots=True, kw_only=True)
class RuntimeCompositionClaim:
    """Immutable claim outcome for one composition attestation identity."""

    disposition: RuntimeCompositionClaimDisposition
    existing_attestation: RuntimeCompositionAttestation | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.disposition, RuntimeCompositionClaimDisposition):
            raise TypeError("disposition must be a RuntimeCompositionClaimDisposition")
        if self.disposition is RuntimeCompositionClaimDisposition.CLAIMED:
            if self.existing_attestation is not None:
                raise RuntimeCompositionStoreError("new composition claim cannot carry existing evidence")
            return
        if not isinstance(self.existing_attestation, RuntimeCompositionAttestation):
            raise RuntimeCompositionStoreError("duplicate/conflicting claim requires existing attestation")


class DurableRuntimeCompositionStore(Protocol):
    """Injected durable boundary for immutable composition evidence only."""

    @property
    def control_root(self) -> Path:
        """Return the caller-supplied durable control root without creating it."""

    def claim(self, attestation: RuntimeCompositionAttestation) -> RuntimeCompositionClaim:
        """Atomically claim immutable composition evidence with no overwrite or update capability."""

    def read(self, *, attestation_id: str) -> RuntimeCompositionAttestation | None:
        """Read one canonical attestation or None only when its deterministic record is absent."""


class FileDurableRuntimeCompositionStore:
    """File-backed immutable composition store with cross-process locking and no reset/delete path."""

    def __init__(self, *, control_root: Path) -> None:
        if not isinstance(control_root, Path):
            raise TypeError("control_root must be a Path")
        self._control_root = control_root

    @property
    def control_root(self) -> Path:
        """Expose root for evidence-store isolation inspection only."""
        return self._control_root

    def claim(self, attestation: RuntimeCompositionAttestation) -> RuntimeCompositionClaim:
        """Atomically persist immutable evidence or observe duplicate/conflicting evidence."""
        if not isinstance(attestation, RuntimeCompositionAttestation):
            raise TypeError("attestation must be a RuntimeCompositionAttestation")
        with self._locked_root():
            existing = self._read_unlocked(attestation.attestation_id)
            if existing is None:
                self._write_unlocked(attestation)
                return RuntimeCompositionClaim(disposition=RuntimeCompositionClaimDisposition.CLAIMED)
            if existing == attestation:
                return RuntimeCompositionClaim(
                    disposition=RuntimeCompositionClaimDisposition.DUPLICATE,
                    existing_attestation=existing,
                )
            return RuntimeCompositionClaim(
                disposition=RuntimeCompositionClaimDisposition.CONFLICT,
                existing_attestation=existing,
            )

    def read(self, *, attestation_id: str) -> RuntimeCompositionAttestation | None:
        """Read validated immutable evidence without changing durable composition state."""
        _require_non_empty(attestation_id, "attestation_id")
        with self._locked_root():
            return self._read_unlocked(attestation_id)

    @contextmanager
    def _locked_root(self) -> Iterator[None]:
        self._validate_root()
        lock_path = self._control_root / ".g2_4_11_runtime_composition.lock"
        if lock_path.is_symlink():
            raise RuntimeCompositionStoreUnavailableError("runtime composition lock is unsafe")
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        except OSError as error:
            raise RuntimeCompositionStoreUnavailableError("runtime composition lock is unavailable") from error
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        except RuntimeCompositionStoreCorruptionError:
            raise
        except RuntimeCompositionStoreUnavailableError:
            raise
        except OSError as error:
            raise RuntimeCompositionStoreUnavailableError("runtime composition operation failed") from error
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
                raise RuntimeCompositionStoreUnavailableError("runtime composition control root is unavailable")
        except OSError as error:
            raise RuntimeCompositionStoreUnavailableError("runtime composition control root is unavailable") from error

    def _read_unlocked(self, attestation_id: str) -> RuntimeCompositionAttestation | None:
        record_path = self._record_path(attestation_id)
        try:
            if not record_path.exists():
                return None
            if record_path.is_symlink():
                raise RuntimeCompositionStoreCorruptionError("runtime composition record must not be a symlink")
            payload = json.loads(record_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or payload.get("schema_version") != GOVERNED_RUNTIME_COMPOSITION_STORE_SCHEMA_VERSION:
                raise RuntimeCompositionStoreCorruptionError("unsupported runtime composition record schema")
            if set(payload) != {"attestation", "schema_version"}:
                raise RuntimeCompositionStoreCorruptionError("runtime composition record has unexpected fields")
            attestation = RuntimeCompositionAttestation.from_payload(payload["attestation"])
        except OSError as error:
            raise RuntimeCompositionStoreUnavailableError("runtime composition record is unavailable") from error
        except (TypeError, ValueError, RuntimeCompositionError) as error:
            raise RuntimeCompositionStoreCorruptionError("invalid runtime composition record") from error
        if attestation.attestation_id != attestation_id:
            raise RuntimeCompositionStoreCorruptionError("runtime composition record does not match deterministic key")
        return attestation

    def _write_unlocked(self, attestation: RuntimeCompositionAttestation) -> None:
        record_path = self._record_path(attestation.attestation_id)
        payload = json.dumps(
            {
                "attestation": attestation.to_payload(),
                "schema_version": GOVERNED_RUNTIME_COMPOSITION_STORE_SCHEMA_VERSION,
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
            raise RuntimeCompositionStoreUnavailableError("runtime composition record appeared during locked claim") from None
        except OSError as error:
            raise RuntimeCompositionStoreUnavailableError("runtime composition record cannot be claimed") from error
        try:
            with os.fdopen(descriptor, "wb", closefd=True) as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError as error:
            raise RuntimeCompositionStoreUnavailableError("runtime composition record cannot be persisted") from error

    def _record_path(self, attestation_id: str) -> Path:
        return self._control_root / f"attestation-{hashlib.sha256(attestation_id.encode()).hexdigest()}.json"


def _require_non_empty(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeCompositionStoreError(f"{field_name} cannot be empty")
    return value


__all__ = [
    "GOVERNED_RUNTIME_COMPOSITION_STORE_SCHEMA_VERSION",
    "DurableRuntimeCompositionStore",
    "FileDurableRuntimeCompositionStore",
    "RuntimeCompositionClaim",
    "RuntimeCompositionClaimDisposition",
    "RuntimeCompositionStoreCorruptionError",
    "RuntimeCompositionStoreError",
    "RuntimeCompositionStoreUnavailableError",
]
