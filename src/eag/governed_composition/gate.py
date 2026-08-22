"""Read-only validation and immutable recording for runtime composition provenance evidence."""

from __future__ import annotations

from datetime import datetime

from eag.governed_composition.models import (
    RuntimeCompositionAdmission,
    RuntimeCompositionAttestation,
    RuntimeCompositionManifest,
    RuntimeCompositionRejectionReason,
)
from eag.governed_composition.store import (
    DurableRuntimeCompositionStore,
    RuntimeCompositionClaimDisposition,
    RuntimeCompositionStoreCorruptionError,
    RuntimeCompositionStoreUnavailableError,
)


class RuntimeCompositionGate:
    """Create and validate composition evidence only; it has no executor, session, permit, or runtime authority."""

    def __init__(self, *, composition_store: DurableRuntimeCompositionStore) -> None:
        if not callable(getattr(composition_store, "claim", None)) or not callable(
            getattr(composition_store, "read", None)
        ):
            raise TypeError("composition_store must expose claim(attestation) and read(attestation_id)")
        self._composition_store = composition_store

    def attest(
        self,
        *,
        attestation_id: str,
        manifest: RuntimeCompositionManifest,
        occurred_at: datetime,
    ) -> RuntimeCompositionAdmission:
        """Atomically record one immutable composition attestation without constructing or invoking a runtime."""
        attestation = RuntimeCompositionAttestation.issue(
            attestation_id=attestation_id,
            manifest=manifest,
            occurred_at=occurred_at,
        )
        try:
            claim = self._composition_store.claim(attestation)
        except RuntimeCompositionStoreCorruptionError:
            return RuntimeCompositionAdmission(
                attestation=None,
                reason=RuntimeCompositionRejectionReason.STORE_CORRUPT,
            )
        except RuntimeCompositionStoreUnavailableError:
            return RuntimeCompositionAdmission(
                attestation=None,
                reason=RuntimeCompositionRejectionReason.STORE_UNAVAILABLE,
            )
        if claim.disposition is RuntimeCompositionClaimDisposition.CLAIMED:
            return RuntimeCompositionAdmission(attestation=attestation)
        if claim.disposition is RuntimeCompositionClaimDisposition.DUPLICATE:
            return RuntimeCompositionAdmission(
                attestation=None,
                reason=RuntimeCompositionRejectionReason.ATTESTATION_ID_DUPLICATE,
            )
        return RuntimeCompositionAdmission(
            attestation=None,
            reason=RuntimeCompositionRejectionReason.ATTESTATION_ID_CONFLICT,
        )

    def validate(
        self,
        *,
        attestation: RuntimeCompositionAttestation | None,
        manifest: RuntimeCompositionManifest,
    ) -> RuntimeCompositionRejectionReason | None:
        """Validate exact durable evidence only; the caller retains all execution and session decisions."""
        if attestation is None:
            return RuntimeCompositionRejectionReason.MISSING_ATTESTATION
        if not isinstance(attestation, RuntimeCompositionAttestation):
            raise TypeError("attestation must be a RuntimeCompositionAttestation or None")
        if not isinstance(manifest, RuntimeCompositionManifest):
            raise TypeError("manifest must be a RuntimeCompositionManifest")
        try:
            stored = self._composition_store.read(attestation_id=attestation.attestation_id)
        except RuntimeCompositionStoreCorruptionError:
            return RuntimeCompositionRejectionReason.STORE_CORRUPT
        except RuntimeCompositionStoreUnavailableError:
            return RuntimeCompositionRejectionReason.STORE_UNAVAILABLE
        if stored is None:
            return RuntimeCompositionRejectionReason.ATTESTATION_UNKNOWN
        if stored != attestation:
            return RuntimeCompositionRejectionReason.ATTESTATION_ID_CONFLICT
        expected = RuntimeCompositionAttestation.issue(
            attestation_id=attestation.attestation_id,
            manifest=manifest,
            occurred_at=attestation.occurred_at,
        )
        if expected != attestation:
            return RuntimeCompositionRejectionReason.ATTESTATION_BINDING_MISMATCH
        return None


__all__ = ["RuntimeCompositionGate"]
