"""Immutable, non-executing pre-session readiness evidence contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from eag.governed_composition import RuntimeCompositionAttestation, RuntimeCompositionManifest
from eag.governed_workspace import WorkspaceCustodyAttestation, WorkspaceCustodyRequest


class ControlledSessionReadinessError(ValueError):
    """Raised when a pre-session readiness contract is structurally invalid."""


class ReadinessDisposition(StrEnum):
    """Pure evidence-validation outcome; it grants no session, permit, or execution authority."""

    READY = "ready"
    REJECTED = "rejected"


class ReadinessRejectionReason(StrEnum):
    """Typed fail-closed refusals from the non-executing readiness boundary."""

    MISSING_WORKSPACE_CUSTODY_EVIDENCE = "missing_workspace_custody_evidence"
    WORKSPACE_CUSTODY_BINDING_MISMATCH = "workspace_custody_binding_mismatch"
    WORKSPACE_CUSTODY_STORE_UNAVAILABLE = "workspace_custody_store_unavailable"
    WORKSPACE_CUSTODY_STORE_CORRUPT = "workspace_custody_store_corrupt"
    MISSING_RUNTIME_COMPOSITION_EVIDENCE = "missing_runtime_composition_evidence"
    RUNTIME_COMPOSITION_BINDING_MISMATCH = "runtime_composition_binding_mismatch"
    RUNTIME_COMPOSITION_STORE_UNAVAILABLE = "runtime_composition_store_unavailable"
    RUNTIME_COMPOSITION_STORE_CORRUPT = "runtime_composition_store_corrupt"


@dataclass(frozen=True, slots=True, kw_only=True)
class ControlledSessionReadinessEvidence:
    """Existing custody and composition evidence required before session issuance.

    This aggregate contains no session, permit, runtime, executor, workspace handle, credential,
    or operational method. Its optional evidence fields permit a validator to return a precise,
    typed missing-evidence refusal without creating or changing any evidence.
    """

    custody_request: WorkspaceCustodyRequest | None
    custody_attestation: WorkspaceCustodyAttestation | None
    composition_manifest: RuntimeCompositionManifest | None
    composition_attestation: RuntimeCompositionAttestation | None

    def __post_init__(self) -> None:
        if self.custody_request is not None and not isinstance(
            self.custody_request, WorkspaceCustodyRequest
        ):
            raise TypeError("custody_request must be a WorkspaceCustodyRequest or None")
        if self.custody_attestation is not None and not isinstance(
            self.custody_attestation, WorkspaceCustodyAttestation
        ):
            raise TypeError("custody_attestation must be a WorkspaceCustodyAttestation or None")
        if self.composition_manifest is not None and not isinstance(
            self.composition_manifest, RuntimeCompositionManifest
        ):
            raise TypeError("composition_manifest must be a RuntimeCompositionManifest or None")
        if self.composition_attestation is not None and not isinstance(
            self.composition_attestation, RuntimeCompositionAttestation
        ):
            raise TypeError(
                "composition_attestation must be a RuntimeCompositionAttestation or None"
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ControlledSessionReadinessDecision:
    """Pure readiness decision that cannot issue or consume a controlled session."""

    disposition: ReadinessDisposition
    reason: ReadinessRejectionReason | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.disposition, ReadinessDisposition):
            raise TypeError("disposition must be a ReadinessDisposition")
        if self.disposition is ReadinessDisposition.READY:
            if self.reason is not None:
                raise ControlledSessionReadinessError("ready decision cannot carry a rejection reason")
            return
        if not isinstance(self.reason, ReadinessRejectionReason):
            raise ControlledSessionReadinessError("rejected readiness decision requires a typed reason")


@dataclass(frozen=True, slots=True, kw_only=True)
class ControlledSessionReadinessAdmission:
    """Immutable evidence-only readiness result with no session or execution capability."""

    evidence: ControlledSessionReadinessEvidence | None
    decision: ControlledSessionReadinessDecision

    def __post_init__(self) -> None:
        if not isinstance(self.decision, ControlledSessionReadinessDecision):
            raise TypeError("decision must be a ControlledSessionReadinessDecision")
        if self.decision.disposition is ReadinessDisposition.READY:
            if not isinstance(self.evidence, ControlledSessionReadinessEvidence):
                raise ControlledSessionReadinessError("ready admission requires readiness evidence")
        elif self.evidence is not None:
            raise ControlledSessionReadinessError("rejected readiness admission cannot expose evidence")


__all__ = [
    "ControlledSessionReadinessAdmission",
    "ControlledSessionReadinessDecision",
    "ControlledSessionReadinessError",
    "ControlledSessionReadinessEvidence",
    "ReadinessDisposition",
    "ReadinessRejectionReason",
]
