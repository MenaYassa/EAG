"""Deterministic G2.4.13 readiness evidence for session-gate tests only."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

from eag.governed_activation import GovernedActivationRequest
from eag.governed_composition import RuntimeCompositionGate
from eag.governed_runtime.models import GovernedExecutionRequest
from eag.governed_session import (
    ControlledSessionReadinessEvidence,
    ControlledSessionReadinessGate,
    RuntimeAvailability,
)
from eag.governed_workspace import (
    WorkspaceCustodyGate,
    WorkspaceCustodyPolicy,
    WorkspaceCustodyRequest,
)
from test_support.g2_4_10_workspace_custody_fixture import custody_store
from test_support.g2_4_11_composition_fixture import composition_manifest, composition_store


@dataclass(frozen=True, slots=True)
class ReadinessFixture:
    """Existing evidence owners plus valid immutable evidence for one deterministic test identity."""

    gate: ControlledSessionReadinessGate
    evidence: ControlledSessionReadinessEvidence
    custody_gate: WorkspaceCustodyGate
    composition_gate: RuntimeCompositionGate


def readiness_fixture(
    tmp_path: Path,
    *,
    identity: str,
    activation_request: GovernedActivationRequest,
    runtime_request: GovernedExecutionRequest,
    runtime_availability: RuntimeAvailability,
) -> ReadinessFixture:
    """Attest fixture roots and composition through existing public evidence authorities only."""
    isolation = activation_request.isolation
    assert isolation.workspace_root is not None
    assert isolation.source_repository_root is not None
    assert isolation.audit_root is not None
    workspace_root = isolation.workspace_root
    source_root = isolation.source_repository_root
    audit_root = isolation.audit_root
    workspace_root.mkdir(parents=True, exist_ok=True)
    source_root.mkdir(parents=True, exist_ok=True)
    audit_root.mkdir(parents=True, exist_ok=True)
    custody_control_root = tmp_path / f"g2413-custody-control-{_suffix(identity)}"
    custody_control_root.mkdir(parents=True, exist_ok=True)
    custody_request = WorkspaceCustodyRequest(
        attestation_id=f"g2413-custody-{identity}",
        execution_id=runtime_request.execution_id,
        run_id=runtime_request.run_id,
        workspace_id=f"g2413-workspace-{identity}",
        workspace_root=workspace_root,
        source_repository_root=source_root,
        audit_root=audit_root,
        control_root=custody_control_root,
        policy=WorkspaceCustodyPolicy(),
    )
    custody_gate = WorkspaceCustodyGate(custody_store=custody_store(custody_control_root))
    custody_admission = custody_gate.attest(
        request=custody_request,
        occurred_at=datetime(2026, 8, 22, tzinfo=UTC),
    )
    assert custody_admission.attestation is not None

    composition_control_root = tmp_path / f"g2413-composition-control-{_suffix(identity)}"
    composition_gate = RuntimeCompositionGate(
        composition_store=composition_store(composition_control_root)
    )
    manifest = replace(
        composition_manifest(identity=identity, runtime_id=runtime_availability.runtime_id),
        execution_id=runtime_request.execution_id,
        run_id=runtime_request.run_id,
    )
    composition_admission = composition_gate.attest(
        attestation_id=f"g2413-composition-{identity}",
        manifest=manifest,
        occurred_at=datetime(2026, 8, 22, tzinfo=UTC),
    )
    assert composition_admission.attestation is not None
    return ReadinessFixture(
        gate=ControlledSessionReadinessGate(
            custody_gate=custody_gate,
            composition_gate=composition_gate,
        ),
        evidence=ControlledSessionReadinessEvidence(
            custody_request=custody_request,
            custody_attestation=custody_admission.attestation,
            composition_manifest=manifest,
            composition_attestation=composition_admission.attestation,
        ),
        custody_gate=custody_gate,
        composition_gate=composition_gate,
    )


def _suffix(identity: str) -> str:
    return hashlib.sha256(identity.encode()).hexdigest()[:12]


__all__ = ["ReadinessFixture", "readiness_fixture"]
