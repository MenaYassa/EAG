"""Deterministic G2.4.21 fixture support for immutable work-order evidence only."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from eag.governed_composition import RuntimeCompositionAttestation, RuntimeCompositionGate
from eag.governed_construction_work_order import (
    ConstructionWorkOrderAssessmentRequest,
    ConstructionWorkOrderProfile,
    LocalConstructionWorkOrderEvidence,
)
from eag.governed_outcome_policy import (
    OutcomeSemanticsAssessment,
    OutcomeSemanticsAssessmentRequest,
    OutcomeSemanticsAssessor,
)
from eag.governed_workspace import WorkspaceCustodyAttestation, WorkspaceCustodyGate
from test_support.g2_4_10_workspace_custody_fixture import custody_bindings, custody_store
from test_support.g2_4_11_composition_fixture import composition_manifest, composition_store
from test_support.g2_4_19_outcome_policy_fixture import (
    OutcomePolicyFixture,
    outcome_assessment_request,
    outcome_policy_fixture,
)


@dataclass(frozen=True, slots=True)
class ConstructionWorkOrderFixture:
    """Exact public upstream evidence plus one valid immutable work-order declaration."""

    outcome_fixture: OutcomePolicyFixture
    outcome_request: OutcomeSemanticsAssessmentRequest
    outcome_assessment: OutcomeSemanticsAssessment
    custody_attestation: WorkspaceCustodyAttestation
    composition_attestation: RuntimeCompositionAttestation
    work_order: LocalConstructionWorkOrderEvidence
    timestamp: datetime


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def construction_work_order_fixture(
    tmp_path: Path,
    *,
    identity: str = "construction-work-order",
) -> ConstructionWorkOrderFixture:
    """Build valid public evidence under test-owned paths without construction execution."""
    outcome_fixture_data = outcome_policy_fixture(identity=identity)
    timestamp = outcome_fixture_data.timestamp
    outcome_request_data = outcome_assessment_request(
        outcome_fixture_data,
        assessment_request_id=f"g2421-outcome-request-{identity}",
    )
    outcome_assessment = OutcomeSemanticsAssessor().assess(
        assessment_id=f"g2421-outcome-assessment-{identity}",
        request=outcome_request_data,
    )

    custody_data = custody_bindings(tmp_path, identity=identity)
    custody_admission = WorkspaceCustodyGate(custody_store=custody_store(custody_data.control_root)).attest(
        request=custody_data.request,
        occurred_at=timestamp,
    )
    assert custody_admission.attestation is not None
    custody = custody_admission.attestation

    base_manifest = composition_manifest(identity=identity)
    manifest = type(base_manifest)(
        composition_id=base_manifest.composition_id,
        execution_id=custody.execution_id,
        run_id=custody.run_id,
        runtime_id=base_manifest.runtime_id,
        executor_identity=base_manifest.executor_identity,
        component_identities=base_manifest.component_identities,
        dependency_bindings=base_manifest.dependency_bindings,
        composition_policy_digest=base_manifest.composition_policy_digest,
        invocation_binding_digest=base_manifest.invocation_binding_digest,
    )
    composition_admission = RuntimeCompositionGate(
        composition_store=composition_store(tmp_path / "composition-control")
    ).attest(
        attestation_id=f"g2421-composition-attestation-{identity}",
        manifest=manifest,
        occurred_at=timestamp,
    )
    assert composition_admission.attestation is not None
    composition = composition_admission.attestation

    contract = outcome_fixture_data.destination_fixture.contract
    destination_assessment = outcome_fixture_data.destination_assessment
    policy = outcome_fixture_data.policy
    work_order = LocalConstructionWorkOrderEvidence.issue(
        work_order_id=f"g2421-work-order-{identity}",
        execution_id=custody.execution_id,
        run_id=custody.run_id,
        workspace_id=custody.workspace_id,
        workspace_root_identity=custody.workspace_root_identity,
        workspace_custody_attestation_id=custody.attestation_id,
        workspace_custody_binding_digest=custody.binding_digest,
        runtime_composition_attestation_id=composition.attestation_id,
        runtime_composition_binding_digest=composition.binding_digest,
        destination_contract_id=contract.destination_contract_id,
        destination_contract_digest=contract.contract_digest,
        destination_contract_assessment_id=destination_assessment.assessment_id,
        destination_contract_assessment_digest=destination_assessment.assessment_digest,
        outcome_policy_id=policy.outcome_policy_id,
        outcome_policy_digest=policy.policy_digest,
        outcome_policy_assessment_id=outcome_assessment.assessment_id,
        outcome_policy_assessment_digest=outcome_assessment.assessment_digest,
        construction_requirements_digest=_digest(f"g2421:requirements:{identity}"),
        architecture_specification_digest=_digest(f"g2421:architecture:{identity}"),
        action_plan_digest=_digest(f"g2421:action-plan:{identity}"),
        declared_capability_ids=(
            "construction_architecture_declaration",
            "construction_requirements_declaration",
            "construction_work_order_evidence",
        ),
        max_file_actions=4,
        max_total_bytes=16_384,
        max_command_actions=0,
        construction_profile=ConstructionWorkOrderProfile.DISPOSABLE_LOCAL_CONSTRUCTION_WORK_ORDER_V1,
        issued_at=timestamp,
        expires_at=timestamp + timedelta(minutes=10),
    )
    return ConstructionWorkOrderFixture(
        outcome_fixture=outcome_fixture_data,
        outcome_request=outcome_request_data,
        outcome_assessment=outcome_assessment,
        custody_attestation=custody,
        composition_attestation=composition,
        work_order=work_order,
        timestamp=timestamp,
    )


def assessment_request(
    fixture: ConstructionWorkOrderFixture,
    *,
    assessment_request_id: str = "g2421-assessment-request",
    work_order: LocalConstructionWorkOrderEvidence | None = None,
    timestamp: datetime | None = None,
) -> ConstructionWorkOrderAssessmentRequest:
    """Create only valid typed request values; invalid inputs construct directly in tests."""
    return ConstructionWorkOrderAssessmentRequest(
        assessment_request_id=assessment_request_id,
        workspace_custody_attestation=fixture.custody_attestation,
        runtime_composition_attestation=fixture.composition_attestation,
        destination_contract_request=fixture.outcome_fixture.destination_request,
        destination_contract_assessment=fixture.outcome_fixture.destination_assessment,
        outcome_policy_request=fixture.outcome_request,
        outcome_policy_assessment=fixture.outcome_assessment,
        work_order=fixture.work_order if work_order is None else work_order,
        timestamp=fixture.timestamp if timestamp is None else timestamp,
    )


def work_order_variant(
    work_order: LocalConstructionWorkOrderEvidence,
    **changes: object,
) -> LocalConstructionWorkOrderEvidence:
    """Reissue a selected immutable work-order variation via its public constructor."""
    return LocalConstructionWorkOrderEvidence.issue(
        work_order_id=changes.get("work_order_id", work_order.work_order_id),
        execution_id=changes.get("execution_id", work_order.execution_id),
        run_id=changes.get("run_id", work_order.run_id),
        workspace_id=changes.get("workspace_id", work_order.workspace_id),
        workspace_root_identity=changes.get("workspace_root_identity", work_order.workspace_root_identity),
        workspace_custody_attestation_id=changes.get(
            "workspace_custody_attestation_id", work_order.workspace_custody_attestation_id
        ),
        workspace_custody_binding_digest=changes.get(
            "workspace_custody_binding_digest", work_order.workspace_custody_binding_digest
        ),
        runtime_composition_attestation_id=changes.get(
            "runtime_composition_attestation_id", work_order.runtime_composition_attestation_id
        ),
        runtime_composition_binding_digest=changes.get(
            "runtime_composition_binding_digest", work_order.runtime_composition_binding_digest
        ),
        destination_contract_id=changes.get("destination_contract_id", work_order.destination_contract_id),
        destination_contract_digest=changes.get(
            "destination_contract_digest", work_order.destination_contract_digest
        ),
        destination_contract_assessment_id=changes.get(
            "destination_contract_assessment_id", work_order.destination_contract_assessment_id
        ),
        destination_contract_assessment_digest=changes.get(
            "destination_contract_assessment_digest", work_order.destination_contract_assessment_digest
        ),
        outcome_policy_id=changes.get("outcome_policy_id", work_order.outcome_policy_id),
        outcome_policy_digest=changes.get("outcome_policy_digest", work_order.outcome_policy_digest),
        outcome_policy_assessment_id=changes.get(
            "outcome_policy_assessment_id", work_order.outcome_policy_assessment_id
        ),
        outcome_policy_assessment_digest=changes.get(
            "outcome_policy_assessment_digest", work_order.outcome_policy_assessment_digest
        ),
        construction_requirements_digest=changes.get(
            "construction_requirements_digest", work_order.construction_requirements_digest
        ),
        architecture_specification_digest=changes.get(
            "architecture_specification_digest", work_order.architecture_specification_digest
        ),
        action_plan_digest=changes.get("action_plan_digest", work_order.action_plan_digest),
        declared_capability_ids=changes.get("declared_capability_ids", work_order.declared_capability_ids),
        max_file_actions=changes.get("max_file_actions", work_order.max_file_actions),
        max_total_bytes=changes.get("max_total_bytes", work_order.max_total_bytes),
        max_command_actions=changes.get("max_command_actions", work_order.max_command_actions),
        construction_profile=changes.get("construction_profile", work_order.construction_profile),
        issued_at=changes.get("issued_at", work_order.issued_at),
        expires_at=changes.get("expires_at", work_order.expires_at),
    )


__all__ = [
    "ConstructionWorkOrderFixture",
    "assessment_request",
    "construction_work_order_fixture",
    "work_order_variant",
]
