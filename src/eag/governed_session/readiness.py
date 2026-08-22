"""Read-only pre-session validation of published custody and composition evidence."""

from __future__ import annotations

from eag.governed_activation import GovernedActivationRequest
from eag.governed_composition import (
    RuntimeCompositionGate,
    RuntimeCompositionRejectionReason,
)
from eag.governed_runtime.models import GovernedExecutionRequest
from eag.governed_session.models import RuntimeAvailability
from eag.governed_session.readiness_models import (
    ControlledSessionReadinessAdmission,
    ControlledSessionReadinessDecision,
    ControlledSessionReadinessEvidence,
    ReadinessDisposition,
    ReadinessRejectionReason,
)
from eag.governed_workspace import WorkspaceCustodyGate, WorkspaceCustodyRejectionReason


class ControlledSessionReadinessGate:
    """Validate existing preparation evidence before the session gate may claim replay state.

    The gate is deliberately read-only: it does not attest custody/composition, issue a session or
    permit, invoke a runtime, create a workspace, or write an audit record. Custody and composition
    validation stays delegated to their published evidence owners.
    """

    def __init__(
        self,
        *,
        custody_gate: WorkspaceCustodyGate,
        composition_gate: RuntimeCompositionGate,
    ) -> None:
        if not isinstance(custody_gate, WorkspaceCustodyGate):
            raise TypeError("custody_gate must be a WorkspaceCustodyGate")
        if not isinstance(composition_gate, RuntimeCompositionGate):
            raise TypeError("composition_gate must be a RuntimeCompositionGate")
        self._custody_gate = custody_gate
        self._composition_gate = composition_gate

    def validate_for_session(
        self,
        *,
        evidence: ControlledSessionReadinessEvidence | None,
        activation_request: GovernedActivationRequest,
        runtime_request: GovernedExecutionRequest,
        runtime_availability: RuntimeAvailability | None,
    ) -> ControlledSessionReadinessAdmission:
        """Return readiness only after exact evidence and request cross-binding validation."""
        if evidence is None or evidence.custody_request is None or evidence.custody_attestation is None:
            return _rejected(ReadinessRejectionReason.MISSING_WORKSPACE_CUSTODY_EVIDENCE)
        custody_rejection = self._custody_gate.validate(
            attestation=evidence.custody_attestation,
            request=evidence.custody_request,
        )
        if custody_rejection is not None:
            return _rejected(_custody_rejection(custody_rejection))
        if not _custody_binds_request(
            evidence=evidence,
            activation_request=activation_request,
            runtime_request=runtime_request,
        ):
            return _rejected(ReadinessRejectionReason.WORKSPACE_CUSTODY_BINDING_MISMATCH)

        if (
            evidence.composition_manifest is None
            or evidence.composition_attestation is None
        ):
            return _rejected(ReadinessRejectionReason.MISSING_RUNTIME_COMPOSITION_EVIDENCE)
        composition_rejection = self._composition_gate.validate(
            attestation=evidence.composition_attestation,
            manifest=evidence.composition_manifest,
        )
        if composition_rejection is not None:
            return _rejected(_composition_rejection(composition_rejection))
        if not _composition_binds_request(
            evidence=evidence,
            activation_request=activation_request,
            runtime_request=runtime_request,
            runtime_availability=runtime_availability,
        ):
            return _rejected(ReadinessRejectionReason.RUNTIME_COMPOSITION_BINDING_MISMATCH)
        return ControlledSessionReadinessAdmission(
            evidence=evidence,
            decision=ControlledSessionReadinessDecision(disposition=ReadinessDisposition.READY),
        )


def _custody_binds_request(
    *,
    evidence: ControlledSessionReadinessEvidence,
    activation_request: GovernedActivationRequest,
    runtime_request: GovernedExecutionRequest,
) -> bool:
    custody_request = evidence.custody_request
    assert custody_request is not None
    isolation = activation_request.isolation
    roots = (
        (custody_request.workspace_root, isolation.workspace_root),
        (custody_request.source_repository_root, isolation.source_repository_root),
        (custody_request.audit_root, isolation.audit_root),
    )
    if any(expected is None or supplied.resolve() != expected.resolve() for supplied, expected in roots):
        return False
    return (
        custody_request.execution_id == activation_request.isolation.execution_id
        and custody_request.execution_id == runtime_request.execution_id
        and custody_request.run_id == runtime_request.run_id
    )


def _composition_binds_request(
    *,
    evidence: ControlledSessionReadinessEvidence,
    activation_request: GovernedActivationRequest,
    runtime_request: GovernedExecutionRequest,
    runtime_availability: RuntimeAvailability | None,
) -> bool:
    manifest = evidence.composition_manifest
    if manifest is None or runtime_availability is None:
        return False
    return (
        manifest.execution_id == activation_request.isolation.execution_id
        and manifest.execution_id == runtime_request.execution_id
        and manifest.run_id == runtime_request.run_id
        and manifest.runtime_id == runtime_availability.runtime_id
    )


def _custody_rejection(reason: WorkspaceCustodyRejectionReason) -> ReadinessRejectionReason:
    mapping = {
        WorkspaceCustodyRejectionReason.MISSING_ATTESTATION: (
            ReadinessRejectionReason.MISSING_WORKSPACE_CUSTODY_EVIDENCE
        ),
        WorkspaceCustodyRejectionReason.STORE_UNAVAILABLE: (
            ReadinessRejectionReason.WORKSPACE_CUSTODY_STORE_UNAVAILABLE
        ),
        WorkspaceCustodyRejectionReason.STORE_CORRUPT: (
            ReadinessRejectionReason.WORKSPACE_CUSTODY_STORE_CORRUPT
        ),
    }
    return mapping.get(reason, ReadinessRejectionReason.WORKSPACE_CUSTODY_BINDING_MISMATCH)


def _composition_rejection(reason: RuntimeCompositionRejectionReason) -> ReadinessRejectionReason:
    mapping = {
        RuntimeCompositionRejectionReason.MISSING_ATTESTATION: (
            ReadinessRejectionReason.MISSING_RUNTIME_COMPOSITION_EVIDENCE
        ),
        RuntimeCompositionRejectionReason.STORE_UNAVAILABLE: (
            ReadinessRejectionReason.RUNTIME_COMPOSITION_STORE_UNAVAILABLE
        ),
        RuntimeCompositionRejectionReason.STORE_CORRUPT: (
            ReadinessRejectionReason.RUNTIME_COMPOSITION_STORE_CORRUPT
        ),
    }
    return mapping.get(reason, ReadinessRejectionReason.RUNTIME_COMPOSITION_BINDING_MISMATCH)


def _rejected(reason: ReadinessRejectionReason) -> ControlledSessionReadinessAdmission:
    return ControlledSessionReadinessAdmission(
        evidence=None,
        decision=ControlledSessionReadinessDecision(
            disposition=ReadinessDisposition.REJECTED,
            reason=reason,
        ),
    )


__all__ = ["ControlledSessionReadinessGate"]
