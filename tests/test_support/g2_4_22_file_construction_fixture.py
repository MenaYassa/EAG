"""Deterministic fixture support for published-G2.4.10-bound G2.4.22 construction."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from eag.governed_construction_work_order import (
    ConstructionWorkOrderAssessmentRequest,
    ConstructionWorkOrderAssessor,
)
from eag.governed_file_construction import (
    BoundedWorkspaceFileConstructor,
    ConstructionActionPlan,
    ConstructionAuthorizationRequest,
    ConstructionFileAction,
)
from eag.governed_workspace import (
    WorkspaceCustodyGate,
    WorkspaceCustodyRequest,
    WorkspaceCustodyRootHandoff,
)
from test_support.g2_4_10_workspace_custody_fixture import custody_bindings, custody_store
from test_support.g2_4_21_construction_work_order_fixture import (
    ConstructionWorkOrderFixture,
    construction_work_order_fixture,
    work_order_variant,
)


@dataclass(frozen=True, slots=True)
class FileConstructionFixture:
    """Exact evidence, one real live handoff, and a test-owned empty root."""

    work_order_fixture: ConstructionWorkOrderFixture
    authorization: ConstructionAuthorizationRequest
    handoff: WorkspaceCustodyRootHandoff
    constructor: BoundedWorkspaceFileConstructor
    custody_gate: WorkspaceCustodyGate
    workspace_root: Path


def construction_plan(*, actions: tuple[ConstructionFileAction, ...]) -> ConstructionActionPlan:
    """Build only an immutable plan with digest-derived sole identity."""
    return ConstructionActionPlan(actions=actions)


def file_construction_fixture(
    tmp_path: Path,
    *,
    identity: str = "g2422",
    actions: tuple[ConstructionFileAction, ...] | None = None,
) -> FileConstructionFixture:
    """Build valid G2.4.21 evidence bound to one fresh real Model A handoff."""
    plan = construction_plan(
        actions=actions
        or (
            ConstructionFileAction(sequence=1, relative_path="src/main.txt", content="hello\n"),
            ConstructionFileAction(sequence=2, relative_path="README.md", content="# example\n"),
        )
    )
    upstream = construction_work_order_fixture(tmp_path, identity=identity)
    base_custody = custody_bindings(tmp_path, identity=identity)
    handoff_request = WorkspaceCustodyRequest(
        attestation_id=f"{base_custody.request.attestation_id}-handoff",
        execution_id=base_custody.request.execution_id,
        run_id=base_custody.request.run_id,
        workspace_id=base_custody.request.workspace_id,
        workspace_root=base_custody.workspace_root,
        source_repository_root=base_custody.source_root,
        audit_root=base_custody.audit_root,
        control_root=base_custody.control_root,
        policy=base_custody.request.policy,
    )
    gate = WorkspaceCustodyGate(custody_store=custody_store(base_custody.control_root))
    handoff = gate.attest_and_acquire_root_handoff(request=handoff_request)
    assert handoff.attestation is not None
    assert handoff.binding is not None
    assert handoff.handle is not None

    bound_work_order = work_order_variant(
        upstream.work_order,
        action_plan_digest=plan.plan_digest,
        workspace_custody_attestation_id=handoff.attestation.attestation_id,
        workspace_custody_binding_digest=handoff.attestation.binding_digest,
        workspace_root_identity=handoff.attestation.workspace_root_identity,
    )
    assessment_request = ConstructionWorkOrderAssessmentRequest(
        assessment_request_id=f"g2422-assessment-request-{identity}",
        workspace_custody_attestation=handoff.attestation,
        runtime_composition_attestation=upstream.composition_attestation,
        destination_contract_request=upstream.outcome_fixture.destination_request,
        destination_contract_assessment=upstream.outcome_fixture.destination_assessment,
        outcome_policy_request=upstream.outcome_request,
        outcome_policy_assessment=upstream.outcome_assessment,
        work_order=bound_work_order,
        timestamp=upstream.timestamp,
    )
    assessment = ConstructionWorkOrderAssessor().assess(
        assessment_id=f"g2422-assessment-{identity}",
        request=assessment_request,
    )
    authorization = ConstructionAuthorizationRequest(
        authorization_id=f"g2422-authorization-{identity}",
        assessment_request=assessment_request,
        assessment=assessment,
        custody_request=handoff_request,
        custody_attestation=handoff.attestation,
        custody_root_binding=handoff.binding,
        plan=plan,
        timestamp=upstream.timestamp,
    )
    return FileConstructionFixture(
        work_order_fixture=upstream,
        authorization=authorization,
        handoff=handoff,
        constructor=BoundedWorkspaceFileConstructor(),
        custody_gate=gate,
        workspace_root=base_custody.workspace_root,
    )


__all__ = ["FileConstructionFixture", "construction_plan", "file_construction_fixture"]
