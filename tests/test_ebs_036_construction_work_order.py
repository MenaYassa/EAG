"""EBS-036 — deterministic proof for G2.4.21 construction work-order evidence only."""

from __future__ import annotations

import ast
import inspect
from dataclasses import FrozenInstanceError
from datetime import timedelta, timezone
from pathlib import Path

import pytest
from test_support.g2_4_18_destination_contract_fixture import (
    assessment_request as destination_assessment_request,
)
from test_support.g2_4_19_outcome_policy_fixture import outcome_assessment_request
from test_support.g2_4_21_construction_work_order_fixture import (
    assessment_request,
    construction_work_order_fixture,
    work_order_variant,
)

import eag.governed_construction_work_order as boundary
from eag.governed_construction_work_order import (
    ConstructionWorkOrderAssessmentRequest,
    ConstructionWorkOrderAssessor,
    ConstructionWorkOrderDisposition,
    ConstructionWorkOrderEvidenceError,
    ConstructionWorkOrderFindingCode,
    LocalConstructionWorkOrderEvidence,
)
from eag.governed_destination_contract import DestinationContractAssessor
from eag.governed_outcome_policy import OutcomeSemanticsAssessor


def _authoritative_projection(request: ConstructionWorkOrderAssessmentRequest) -> dict[str, object]:
    """Return every non-derived construction work-order binding plus assessment time."""
    work_order = request.work_order
    return {
        "work_order_id": work_order.work_order_id,
        "execution_id": work_order.execution_id,
        "run_id": work_order.run_id,
        "workspace_id": work_order.workspace_id,
        "workspace_root_identity": work_order.workspace_root_identity,
        "workspace_custody_attestation_id": work_order.workspace_custody_attestation_id,
        "workspace_custody_binding_digest": work_order.workspace_custody_binding_digest,
        "runtime_composition_attestation_id": work_order.runtime_composition_attestation_id,
        "runtime_composition_binding_digest": work_order.runtime_composition_binding_digest,
        "destination_contract_id": work_order.destination_contract_id,
        "destination_contract_digest": work_order.destination_contract_digest,
        "destination_contract_assessment_id": work_order.destination_contract_assessment_id,
        "destination_contract_assessment_digest": work_order.destination_contract_assessment_digest,
        "outcome_policy_id": work_order.outcome_policy_id,
        "outcome_policy_digest": work_order.outcome_policy_digest,
        "outcome_policy_assessment_id": work_order.outcome_policy_assessment_id,
        "outcome_policy_assessment_digest": work_order.outcome_policy_assessment_digest,
        "construction_requirements_digest": work_order.construction_requirements_digest,
        "architecture_specification_digest": work_order.architecture_specification_digest,
        "action_plan_digest": work_order.action_plan_digest,
        "declared_capability_ids": work_order.declared_capability_ids,
        "max_file_actions": work_order.max_file_actions,
        "max_total_bytes": work_order.max_total_bytes,
        "max_command_actions": work_order.max_command_actions,
        "construction_profile": work_order.construction_profile,
        "policy_issued_at": work_order.issued_at,
        "policy_expires_at": work_order.expires_at,
        "request_timestamp": request.timestamp,
    }


def _assert_exact_one_change(
    *,
    baseline: ConstructionWorkOrderAssessmentRequest,
    candidate: ConstructionWorkOrderAssessmentRequest,
    expected_changed_field: str,
) -> None:
    before = _authoritative_projection(baseline)
    after = _authoritative_projection(candidate)
    assert tuple(before) == tuple(after)
    assert before[expected_changed_field] != after[expected_changed_field]
    for field_name in before:
        if field_name != expected_changed_field:
            assert before[field_name] == after[field_name], field_name


def _upstream_projection(request: ConstructionWorkOrderAssessmentRequest) -> dict[str, object]:
    """Expose immutable upstream request/assessment chain identities separately from the work order."""
    return {
        **_authoritative_projection(request),
        "destination_contract_request_id": request.destination_contract_request.assessment_request_id,
        "destination_contract_request_digest": request.destination_contract_request.request_digest,
        "destination_contract_assessment_id": request.destination_contract_assessment.assessment_id,
        "destination_contract_assessment_digest": request.destination_contract_assessment.assessment_digest,
        "outcome_policy_request_id": request.outcome_policy_request.assessment_request_id,
        "outcome_policy_request_digest": request.outcome_policy_request.request_digest,
        "outcome_policy_assessment_id": request.outcome_policy_assessment.assessment_id,
        "outcome_policy_assessment_digest": request.outcome_policy_assessment.assessment_digest,
        "outcome_policy_assessed_request_id": request.outcome_policy_assessment.assessed_request_id,
        "outcome_policy_assessed_request_digest": request.outcome_policy_assessment.assessed_request_digest,
    }


def _assert_only_upstream_fields_change(
    *,
    baseline: ConstructionWorkOrderAssessmentRequest,
    candidate: ConstructionWorkOrderAssessmentRequest,
    changed_fields: set[str],
) -> None:
    before = _upstream_projection(baseline)
    after = _upstream_projection(candidate)
    assert tuple(before) == tuple(after)
    for field_name in before:
        if field_name in changed_fields:
            assert before[field_name] != after[field_name], field_name
        else:
            assert before[field_name] == after[field_name], field_name


def _request_with_upstream(
    *,
    baseline: ConstructionWorkOrderAssessmentRequest,
    assessment_request_id: str,
    destination_contract_request: object | None = None,
    destination_contract_assessment: object | None = None,
    outcome_policy_request: object | None = None,
    outcome_policy_assessment: object | None = None,
) -> ConstructionWorkOrderAssessmentRequest:
    return ConstructionWorkOrderAssessmentRequest(
        assessment_request_id=assessment_request_id,
        workspace_custody_attestation=baseline.workspace_custody_attestation,
        runtime_composition_attestation=baseline.runtime_composition_attestation,
        destination_contract_request=(
            baseline.destination_contract_request
            if destination_contract_request is None
            else destination_contract_request
        ),
        destination_contract_assessment=(
            baseline.destination_contract_assessment
            if destination_contract_assessment is None
            else destination_contract_assessment
        ),
        outcome_policy_request=(
            baseline.outcome_policy_request if outcome_policy_request is None else outcome_policy_request
        ),
        outcome_policy_assessment=(
            baseline.outcome_policy_assessment
            if outcome_policy_assessment is None
            else outcome_policy_assessment
        ),
        work_order=baseline.work_order,
        timestamp=baseline.timestamp,
    )


def _tree_state(root: Path) -> tuple[tuple[str, bytes], ...]:
    return tuple(
        (str(path.relative_to(root)), path.read_bytes())
        for path in sorted(root.rglob("*"))
        if path.is_file()
    )


def _assess_preserving_state(
    *,
    root: Path,
    request: ConstructionWorkOrderAssessmentRequest,
    assessment_id: str,
):
    request_before = request.to_payload()
    work_order_before = request.work_order.to_payload()
    state_before = _tree_state(root)
    assessment = ConstructionWorkOrderAssessor().assess(assessment_id=assessment_id, request=request)
    assert request.to_payload() == request_before
    assert request.work_order.to_payload() == work_order_before
    assert _tree_state(root) == state_before
    return assessment


def _codes(assessment: object) -> set[ConstructionWorkOrderFindingCode]:
    return {finding.code for finding in assessment.findings}


def _assert_branch(
    *,
    tmp_path: Path,
    baseline: ConstructionWorkOrderAssessmentRequest,
    candidate: ConstructionWorkOrderAssessmentRequest,
    changed_field: str,
    assessment_id: str,
    disposition: ConstructionWorkOrderDisposition,
    finding: ConstructionWorkOrderFindingCode | None = None,
) -> None:
    _assert_exact_one_change(
        baseline=baseline,
        candidate=candidate,
        expected_changed_field=changed_field,
    )
    assessment = _assess_preserving_state(
        root=tmp_path,
        request=candidate,
        assessment_id=assessment_id,
    )
    assert assessment.disposition is disposition
    if finding is None:
        assert assessment.findings == ()
    else:
        assert finding in _codes(assessment)


def test_ebs_036_construction_work_order_evidence_boundary(tmp_path: Path) -> None:
    """Prove exact static work-order evidence semantics and capability absence only."""
    fixture = construction_work_order_fixture(tmp_path, identity="ebs036")
    baseline = assessment_request(
        fixture,
        assessment_request_id="ebs036-baseline",
        timestamp=fixture.timestamp + timedelta(seconds=2),
    )
    baseline_assessment = _assess_preserving_state(
        root=tmp_path,
        request=baseline,
        assessment_id="ebs036-valid",
    )
    assert baseline_assessment.disposition is ConstructionWorkOrderDisposition.CONSTRUCTION_WORK_ORDER_ATTESTED
    assert baseline_assessment.findings == ()
    assert baseline_assessment.work_order_id == fixture.work_order.work_order_id
    assert baseline_assessment.workspace_id == fixture.work_order.workspace_id
    assert fixture.outcome_assessment.assessed_request_id == baseline.outcome_policy_request.assessment_request_id
    assert fixture.outcome_assessment.assessed_request_digest == baseline.outcome_policy_request.request_digest

    # Substitute an otherwise valid G2.4.18 assessment while preserving the work order and every
    # other upstream relationship. The existing contract-binding finding must fail closed.
    substituted_destination_assessment = DestinationContractAssessor().assess(
        assessment_id="ebs036-substituted-destination-assessment",
        request=baseline.destination_contract_request,
    )
    substituted_destination_request = _request_with_upstream(
        baseline=baseline,
        assessment_request_id="ebs036-substituted-destination-chain",
        destination_contract_assessment=substituted_destination_assessment,
    )
    _assert_only_upstream_fields_change(
        baseline=baseline,
        candidate=substituted_destination_request,
        changed_fields={
            "destination_contract_assessment_id",
            "destination_contract_assessment_digest",
        },
    )
    substituted_destination_result = _assess_preserving_state(
        root=tmp_path,
        request=substituted_destination_request,
        assessment_id="ebs036-substituted-destination-result",
    )
    assert substituted_destination_result.disposition is ConstructionWorkOrderDisposition.NOT_ATTESTED
    assert ConstructionWorkOrderFindingCode.CONTRACT_BINDING_MISMATCH in _codes(substituted_destination_result)

    # Supply a different valid G2.4.18 request beside the baseline assessment. The outcome-policy
    # request remains bound to the baseline contract request, so this mismatched chain must refuse.
    alternate_destination_request = destination_assessment_request(
        fixture.outcome_fixture.destination_fixture,
        assessment_request_id="ebs036-alternate-destination-request",
    )
    mismatched_destination_request = _request_with_upstream(
        baseline=baseline,
        assessment_request_id="ebs036-mismatched-destination-chain",
        destination_contract_request=alternate_destination_request,
    )
    _assert_only_upstream_fields_change(
        baseline=baseline,
        candidate=mismatched_destination_request,
        changed_fields={"destination_contract_request_id"},
    )
    mismatched_destination_result = _assess_preserving_state(
        root=tmp_path,
        request=mismatched_destination_request,
        assessment_id="ebs036-mismatched-destination-result",
    )
    assert mismatched_destination_result.disposition is ConstructionWorkOrderDisposition.NOT_ATTESTED
    assert ConstructionWorkOrderFindingCode.CONTRACT_BINDING_MISMATCH in _codes(mismatched_destination_result)

    # A distinct valid G2.4.19 request cannot be paired with an assessment linked to the baseline
    # request. Typed assessed_request_id/digest provenance, not generic evidence references, refuses it.
    alternate_outcome_request = outcome_assessment_request(
        fixture.outcome_fixture,
        assessment_request_id="ebs036-alternate-outcome-request",
        timestamp=fixture.timestamp + timedelta(seconds=1),
    )
    mismatched_outcome_request = _request_with_upstream(
        baseline=baseline,
        assessment_request_id="ebs036-mismatched-outcome-request-chain",
        outcome_policy_request=alternate_outcome_request,
    )
    _assert_only_upstream_fields_change(
        baseline=baseline,
        candidate=mismatched_outcome_request,
        changed_fields={"outcome_policy_request_id", "outcome_policy_request_digest"},
    )
    mismatched_outcome_request_result = _assess_preserving_state(
        root=tmp_path,
        request=mismatched_outcome_request,
        assessment_id="ebs036-mismatched-outcome-request-result",
    )
    assert mismatched_outcome_request_result.disposition is ConstructionWorkOrderDisposition.NOT_ATTESTED
    assert ConstructionWorkOrderFindingCode.OUTCOME_POLICY_BINDING_MISMATCH in _codes(
        mismatched_outcome_request_result
    )

    # Substitute an otherwise valid outcome assessment linked to the alternate request while the
    # supplied request remains baseline. Both typed provenance fields change and must fail closed.
    substituted_outcome_assessment = OutcomeSemanticsAssessor().assess(
        assessment_id="ebs036-substituted-outcome-assessment",
        request=alternate_outcome_request,
    )
    substituted_outcome_request = _request_with_upstream(
        baseline=baseline,
        assessment_request_id="ebs036-substituted-outcome-chain",
        outcome_policy_assessment=substituted_outcome_assessment,
    )
    _assert_only_upstream_fields_change(
        baseline=baseline,
        candidate=substituted_outcome_request,
        changed_fields={
            "outcome_policy_assessment_id",
            "outcome_policy_assessment_digest",
            "outcome_policy_assessed_request_id",
            "outcome_policy_assessed_request_digest",
        },
    )
    substituted_outcome_result = _assess_preserving_state(
        root=tmp_path,
        request=substituted_outcome_request,
        assessment_id="ebs036-substituted-outcome-result",
    )
    assert substituted_outcome_result.disposition is ConstructionWorkOrderDisposition.NOT_ATTESTED
    assert ConstructionWorkOrderFindingCode.OUTCOME_POLICY_BINDING_MISMATCH in _codes(substituted_outcome_result)

    # Work-order identity is self-identity only: a valid distinct declaration is attested,
    # with no policy selection, precedence, conflict, registry, or reconciliation authority.
    _assert_branch(
        tmp_path=tmp_path,
        baseline=baseline,
        candidate=assessment_request(
            fixture,
            assessment_request_id="ebs036-self-identity",
            work_order=work_order_variant(fixture.work_order, work_order_id="ebs036-distinct-work-order"),
            timestamp=baseline.timestamp,
        ),
        changed_field="work_order_id",
        assessment_id="ebs036-self-identity-result",
        disposition=ConstructionWorkOrderDisposition.CONSTRUCTION_WORK_ORDER_ATTESTED,
    )

    _assert_branch(
        tmp_path=tmp_path,
        baseline=baseline,
        candidate=assessment_request(
            fixture,
            assessment_request_id="ebs036-execution-id",
            work_order=work_order_variant(fixture.work_order, execution_id="different-execution"),
            timestamp=baseline.timestamp,
        ),
        changed_field="execution_id",
        assessment_id="ebs036-execution-id-result",
        disposition=ConstructionWorkOrderDisposition.NOT_ATTESTED,
        finding=ConstructionWorkOrderFindingCode.WORKSPACE_BINDING_MISMATCH,
    )
    _assert_branch(
        tmp_path=tmp_path,
        baseline=baseline,
        candidate=assessment_request(
            fixture,
            assessment_request_id="ebs036-run-id",
            work_order=work_order_variant(fixture.work_order, run_id="different-run"),
            timestamp=baseline.timestamp,
        ),
        changed_field="run_id",
        assessment_id="ebs036-run-id-result",
        disposition=ConstructionWorkOrderDisposition.NOT_ATTESTED,
        finding=ConstructionWorkOrderFindingCode.WORKSPACE_BINDING_MISMATCH,
    )
    _assert_branch(
        tmp_path=tmp_path,
        baseline=baseline,
        candidate=assessment_request(
            fixture,
            assessment_request_id="ebs036-workspace-id",
            work_order=work_order_variant(fixture.work_order, workspace_id="different-workspace"),
            timestamp=baseline.timestamp,
        ),
        changed_field="workspace_id",
        assessment_id="ebs036-workspace-id-result",
        disposition=ConstructionWorkOrderDisposition.NOT_ATTESTED,
        finding=ConstructionWorkOrderFindingCode.WORKSPACE_BINDING_MISMATCH,
    )
    _assert_branch(
        tmp_path=tmp_path,
        baseline=baseline,
        candidate=assessment_request(
            fixture,
            assessment_request_id="ebs036-workspace-root",
            work_order=work_order_variant(fixture.work_order, workspace_root_identity="a" * 64),
            timestamp=baseline.timestamp,
        ),
        changed_field="workspace_root_identity",
        assessment_id="ebs036-workspace-root-result",
        disposition=ConstructionWorkOrderDisposition.NOT_ATTESTED,
        finding=ConstructionWorkOrderFindingCode.WORKSPACE_BINDING_MISMATCH,
    )
    _assert_branch(
        tmp_path=tmp_path,
        baseline=baseline,
        candidate=assessment_request(
            fixture,
            assessment_request_id="ebs036-custody-id",
            work_order=work_order_variant(
                fixture.work_order,
                workspace_custody_attestation_id="different-custody-attestation",
            ),
            timestamp=baseline.timestamp,
        ),
        changed_field="workspace_custody_attestation_id",
        assessment_id="ebs036-custody-id-result",
        disposition=ConstructionWorkOrderDisposition.NOT_ATTESTED,
        finding=ConstructionWorkOrderFindingCode.WORKSPACE_CUSTODY_BINDING_MISMATCH,
    )
    _assert_branch(
        tmp_path=tmp_path,
        baseline=baseline,
        candidate=assessment_request(
            fixture,
            assessment_request_id="ebs036-custody-digest",
            work_order=work_order_variant(fixture.work_order, workspace_custody_binding_digest="b" * 64),
            timestamp=baseline.timestamp,
        ),
        changed_field="workspace_custody_binding_digest",
        assessment_id="ebs036-custody-digest-result",
        disposition=ConstructionWorkOrderDisposition.NOT_ATTESTED,
        finding=ConstructionWorkOrderFindingCode.WORKSPACE_CUSTODY_BINDING_MISMATCH,
    )
    _assert_branch(
        tmp_path=tmp_path,
        baseline=baseline,
        candidate=assessment_request(
            fixture,
            assessment_request_id="ebs036-composition-id",
            work_order=work_order_variant(
                fixture.work_order,
                runtime_composition_attestation_id="different-composition-attestation",
            ),
            timestamp=baseline.timestamp,
        ),
        changed_field="runtime_composition_attestation_id",
        assessment_id="ebs036-composition-id-result",
        disposition=ConstructionWorkOrderDisposition.NOT_ATTESTED,
        finding=ConstructionWorkOrderFindingCode.RUNTIME_COMPOSITION_BINDING_MISMATCH,
    )
    _assert_branch(
        tmp_path=tmp_path,
        baseline=baseline,
        candidate=assessment_request(
            fixture,
            assessment_request_id="ebs036-composition-digest",
            work_order=work_order_variant(fixture.work_order, runtime_composition_binding_digest="c" * 64),
            timestamp=baseline.timestamp,
        ),
        changed_field="runtime_composition_binding_digest",
        assessment_id="ebs036-composition-digest-result",
        disposition=ConstructionWorkOrderDisposition.NOT_ATTESTED,
        finding=ConstructionWorkOrderFindingCode.RUNTIME_COMPOSITION_BINDING_MISMATCH,
    )

    _assert_branch(
        tmp_path=tmp_path,
        baseline=baseline,
        candidate=assessment_request(
            fixture,
            assessment_request_id="ebs036-contract-id",
            work_order=work_order_variant(fixture.work_order, destination_contract_id="different-contract"),
            timestamp=baseline.timestamp,
        ),
        changed_field="destination_contract_id",
        assessment_id="ebs036-contract-id-result",
        disposition=ConstructionWorkOrderDisposition.NOT_ATTESTED,
        finding=ConstructionWorkOrderFindingCode.CONTRACT_BINDING_MISMATCH,
    )
    _assert_branch(
        tmp_path=tmp_path,
        baseline=baseline,
        candidate=assessment_request(
            fixture,
            assessment_request_id="ebs036-contract-digest",
            work_order=work_order_variant(fixture.work_order, destination_contract_digest="d" * 64),
            timestamp=baseline.timestamp,
        ),
        changed_field="destination_contract_digest",
        assessment_id="ebs036-contract-digest-result",
        disposition=ConstructionWorkOrderDisposition.NOT_ATTESTED,
        finding=ConstructionWorkOrderFindingCode.CONTRACT_BINDING_MISMATCH,
    )
    _assert_branch(
        tmp_path=tmp_path,
        baseline=baseline,
        candidate=assessment_request(
            fixture,
            assessment_request_id="ebs036-contract-assessment-id",
            work_order=work_order_variant(
                fixture.work_order,
                destination_contract_assessment_id="different-contract-assessment",
            ),
            timestamp=baseline.timestamp,
        ),
        changed_field="destination_contract_assessment_id",
        assessment_id="ebs036-contract-assessment-id-result",
        disposition=ConstructionWorkOrderDisposition.NOT_ATTESTED,
        finding=ConstructionWorkOrderFindingCode.CONTRACT_BINDING_MISMATCH,
    )
    _assert_branch(
        tmp_path=tmp_path,
        baseline=baseline,
        candidate=assessment_request(
            fixture,
            assessment_request_id="ebs036-contract-assessment-digest",
            work_order=work_order_variant(
                fixture.work_order,
                destination_contract_assessment_digest="e" * 64,
            ),
            timestamp=baseline.timestamp,
        ),
        changed_field="destination_contract_assessment_digest",
        assessment_id="ebs036-contract-assessment-digest-result",
        disposition=ConstructionWorkOrderDisposition.NOT_ATTESTED,
        finding=ConstructionWorkOrderFindingCode.CONTRACT_BINDING_MISMATCH,
    )

    _assert_branch(
        tmp_path=tmp_path,
        baseline=baseline,
        candidate=assessment_request(
            fixture,
            assessment_request_id="ebs036-outcome-id",
            work_order=work_order_variant(fixture.work_order, outcome_policy_id="different-outcome-policy"),
            timestamp=baseline.timestamp,
        ),
        changed_field="outcome_policy_id",
        assessment_id="ebs036-outcome-id-result",
        disposition=ConstructionWorkOrderDisposition.NOT_ATTESTED,
        finding=ConstructionWorkOrderFindingCode.OUTCOME_POLICY_BINDING_MISMATCH,
    )
    _assert_branch(
        tmp_path=tmp_path,
        baseline=baseline,
        candidate=assessment_request(
            fixture,
            assessment_request_id="ebs036-outcome-digest",
            work_order=work_order_variant(fixture.work_order, outcome_policy_digest="f" * 64),
            timestamp=baseline.timestamp,
        ),
        changed_field="outcome_policy_digest",
        assessment_id="ebs036-outcome-digest-result",
        disposition=ConstructionWorkOrderDisposition.NOT_ATTESTED,
        finding=ConstructionWorkOrderFindingCode.OUTCOME_POLICY_BINDING_MISMATCH,
    )
    _assert_branch(
        tmp_path=tmp_path,
        baseline=baseline,
        candidate=assessment_request(
            fixture,
            assessment_request_id="ebs036-outcome-assessment-id",
            work_order=work_order_variant(
                fixture.work_order,
                outcome_policy_assessment_id="different-outcome-assessment",
            ),
            timestamp=baseline.timestamp,
        ),
        changed_field="outcome_policy_assessment_id",
        assessment_id="ebs036-outcome-assessment-id-result",
        disposition=ConstructionWorkOrderDisposition.NOT_ATTESTED,
        finding=ConstructionWorkOrderFindingCode.OUTCOME_POLICY_BINDING_MISMATCH,
    )
    _assert_branch(
        tmp_path=tmp_path,
        baseline=baseline,
        candidate=assessment_request(
            fixture,
            assessment_request_id="ebs036-outcome-assessment-digest",
            work_order=work_order_variant(
                fixture.work_order,
                outcome_policy_assessment_digest="a" * 64,
            ),
            timestamp=baseline.timestamp,
        ),
        changed_field="outcome_policy_assessment_digest",
        assessment_id="ebs036-outcome-assessment-digest-result",
        disposition=ConstructionWorkOrderDisposition.NOT_ATTESTED,
        finding=ConstructionWorkOrderFindingCode.OUTCOME_POLICY_BINDING_MISMATCH,
    )

    _assert_branch(
        tmp_path=tmp_path,
        baseline=baseline,
        candidate=assessment_request(
            fixture,
            assessment_request_id="ebs036-requirements",
            work_order=work_order_variant(fixture.work_order, construction_requirements_digest="b" * 64),
            timestamp=baseline.timestamp,
        ),
        changed_field="construction_requirements_digest",
        assessment_id="ebs036-requirements-result",
        disposition=ConstructionWorkOrderDisposition.CONSTRUCTION_WORK_ORDER_ATTESTED,
    )
    _assert_branch(
        tmp_path=tmp_path,
        baseline=baseline,
        candidate=assessment_request(
            fixture,
            assessment_request_id="ebs036-architecture",
            work_order=work_order_variant(fixture.work_order, architecture_specification_digest="c" * 64),
            timestamp=baseline.timestamp,
        ),
        changed_field="architecture_specification_digest",
        assessment_id="ebs036-architecture-result",
        disposition=ConstructionWorkOrderDisposition.CONSTRUCTION_WORK_ORDER_ATTESTED,
    )
    _assert_branch(
        tmp_path=tmp_path,
        baseline=baseline,
        candidate=assessment_request(
            fixture,
            assessment_request_id="ebs036-plan",
            work_order=work_order_variant(fixture.work_order, action_plan_digest="d" * 64),
            timestamp=baseline.timestamp,
        ),
        changed_field="action_plan_digest",
        assessment_id="ebs036-plan-result",
        disposition=ConstructionWorkOrderDisposition.CONSTRUCTION_WORK_ORDER_ATTESTED,
    )
    _assert_branch(
        tmp_path=tmp_path,
        baseline=baseline,
        candidate=assessment_request(
            fixture,
            assessment_request_id="ebs036-capabilities",
            work_order=work_order_variant(
                fixture.work_order,
                declared_capability_ids=(
                    "construction_architecture_declaration",
                    "construction_requirements_declaration",
                    "construction_work_order_evidence",
                    "unsafe_workspace_write",
                ),
            ),
            timestamp=baseline.timestamp,
        ),
        changed_field="declared_capability_ids",
        assessment_id="ebs036-capabilities-result",
        disposition=ConstructionWorkOrderDisposition.NOT_ATTESTED,
        finding=ConstructionWorkOrderFindingCode.UNSUPPORTED_CAPABILITY_DECLARATION,
    )
    _assert_branch(
        tmp_path=tmp_path,
        baseline=baseline,
        candidate=assessment_request(
            fixture,
            assessment_request_id="ebs036-file-limit",
            work_order=work_order_variant(fixture.work_order, max_file_actions=5),
            timestamp=baseline.timestamp,
        ),
        changed_field="max_file_actions",
        assessment_id="ebs036-file-limit-result",
        disposition=ConstructionWorkOrderDisposition.CONSTRUCTION_WORK_ORDER_ATTESTED,
    )
    _assert_branch(
        tmp_path=tmp_path,
        baseline=baseline,
        candidate=assessment_request(
            fixture,
            assessment_request_id="ebs036-byte-limit",
            work_order=work_order_variant(fixture.work_order, max_total_bytes=20_000),
            timestamp=baseline.timestamp,
        ),
        changed_field="max_total_bytes",
        assessment_id="ebs036-byte-limit-result",
        disposition=ConstructionWorkOrderDisposition.CONSTRUCTION_WORK_ORDER_ATTESTED,
    )
    _assert_branch(
        tmp_path=tmp_path,
        baseline=baseline,
        candidate=assessment_request(
            fixture,
            assessment_request_id="ebs036-command-limit",
            work_order=work_order_variant(fixture.work_order, max_command_actions=1),
            timestamp=baseline.timestamp,
        ),
        changed_field="max_command_actions",
        assessment_id="ebs036-command-limit-result",
        disposition=ConstructionWorkOrderDisposition.NOT_ATTESTED,
        finding=ConstructionWorkOrderFindingCode.INVALID_STATIC_LIMITS,
    )
    _assert_branch(
        tmp_path=tmp_path,
        baseline=baseline,
        candidate=assessment_request(
            fixture,
            assessment_request_id="ebs036-profile",
            work_order=work_order_variant(fixture.work_order, construction_profile="unsupported-profile"),
            timestamp=baseline.timestamp,
        ),
        changed_field="construction_profile",
        assessment_id="ebs036-profile-result",
        disposition=ConstructionWorkOrderDisposition.UNSUPPORTED_CONSTRUCTION_PROFILE,
        finding=ConstructionWorkOrderFindingCode.UNSUPPORTED_CONSTRUCTION_PROFILE,
    )
    _assert_branch(
        tmp_path=tmp_path,
        baseline=baseline,
        candidate=assessment_request(
            fixture,
            assessment_request_id="ebs036-issued-at",
            work_order=work_order_variant(fixture.work_order, issued_at=fixture.timestamp - timedelta(minutes=1)),
            timestamp=baseline.timestamp,
        ),
        changed_field="policy_issued_at",
        assessment_id="ebs036-issued-at-result",
        disposition=ConstructionWorkOrderDisposition.CONSTRUCTION_WORK_ORDER_ATTESTED,
    )
    _assert_branch(
        tmp_path=tmp_path,
        baseline=baseline,
        candidate=assessment_request(
            fixture,
            assessment_request_id="ebs036-expires-at",
            work_order=work_order_variant(fixture.work_order, expires_at=fixture.timestamp + timedelta(seconds=1)),
            timestamp=baseline.timestamp,
        ),
        changed_field="policy_expires_at",
        assessment_id="ebs036-expires-at-result",
        disposition=ConstructionWorkOrderDisposition.NOT_ATTESTED,
        finding=ConstructionWorkOrderFindingCode.WORK_ORDER_EXPIRED,
    )
    _assert_branch(
        tmp_path=tmp_path,
        baseline=baseline,
        candidate=assessment_request(
            fixture,
            assessment_request_id="ebs036-request-time",
            work_order=fixture.work_order,
            timestamp=baseline.timestamp + timedelta(seconds=1),
        ),
        changed_field="request_timestamp",
        assessment_id="ebs036-request-time-result",
        disposition=ConstructionWorkOrderDisposition.CONSTRUCTION_WORK_ORDER_ATTESTED,
    )

    # Equivalent offset reconstruction retains the same canonical UTC work-order declaration.
    offset_work_order = work_order_variant(
        fixture.work_order,
        issued_at=fixture.work_order.issued_at.astimezone(timezone(timedelta(hours=3))),
        expires_at=fixture.work_order.expires_at.astimezone(timezone(timedelta(hours=3))),
    )
    assert offset_work_order.to_payload() == fixture.work_order.to_payload()
    assert LocalConstructionWorkOrderEvidence.from_payload(offset_work_order.to_payload()) == fixture.work_order

    # Real strict public parser branches preserve raw payload and test-owned state.
    raw_payload = fixture.work_order.to_payload()
    root_before = _tree_state(tmp_path)
    for altered in (
        {**raw_payload, "issued_at": "malformed-timestamp"},
        {**raw_payload, "schema_version": "g2.4.21.unsupported"},
        {**raw_payload, "work_order_digest": "0" * 64},
        {**raw_payload, "unexpected_field": "unexpected"},
    ):
        supplied_before = dict(altered)
        with pytest.raises(ConstructionWorkOrderEvidenceError):
            LocalConstructionWorkOrderEvidence.from_payload(altered)
        assert altered == supplied_before
        assert _tree_state(tmp_path) == root_before

    # Strict constructor omission is distinct from an assessor refusal; no result is fabricated.
    request_kwargs = dict(
        assessment_request_id="ebs036-missing-upstream",
        workspace_custody_attestation=fixture.custody_attestation,
        runtime_composition_attestation=fixture.composition_attestation,
        destination_contract_request=fixture.outcome_fixture.destination_request,
        destination_contract_assessment=fixture.outcome_fixture.destination_assessment,
        outcome_policy_request=fixture.outcome_request,
        outcome_policy_assessment=fixture.outcome_assessment,
        work_order=fixture.work_order,
        timestamp=baseline.timestamp,
    )
    for omitted in (
        "workspace_custody_attestation",
        "runtime_composition_attestation",
        "destination_contract_assessment",
        "outcome_policy_assessment",
    ):
        incomplete = {name: value for name, value in request_kwargs.items() if name != omitted}
        before = _tree_state(tmp_path)
        with pytest.raises(TypeError):
            ConstructionWorkOrderAssessmentRequest(**incomplete)
        assert _tree_state(tmp_path) == before

    # Returned evidence and findings are immutable, slotted, and container-free.
    assert not hasattr(baseline_assessment, "__dict__")
    assert all(not hasattr(finding, "__dict__") for finding in baseline_assessment.findings)
    assert isinstance(baseline_assessment.findings, tuple)
    assert isinstance(baseline_assessment.evidence_refs, tuple)
    assert isinstance(baseline_assessment.recommendations, tuple)
    for value in (fixture.work_order, baseline, baseline_assessment):
        with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
            value.work_order_id = "tampered"

    # Direct capability-absence proof: no public effect surface and no effectful imports/calls.
    prohibited_public_names = (
        "create_workspace",
        "lease_workspace",
        "write_file",
        "mutate_file",
        "execute_command",
        "start_process",
        "install_dependency",
        "runtime",
        "provider",
        "client",
        "receipt",
        "retry",
        "rollback",
        "recover",
        "reconcile",
        "publish",
        "deploy",
        "session",
        "permit",
        "ledger",
    )
    for name in prohibited_public_names:
        assert not hasattr(boundary, name)

    source_modules = (
        boundary,
        __import__("eag.governed_construction_work_order.assessor", fromlist=["*"]),
        __import__("eag.governed_construction_work_order.models", fromlist=["*"]),
        __import__("eag.governed_construction_work_order.canonical", fromlist=["*"]),
    )
    prohibited_import_roots = {
        "asyncio",
        "http",
        "requests",
        "socket",
        "subprocess",
        "urllib",
        "eag.governed_transition_control",
    }
    prohibited_call_names = {
        "claim",
        "connect",
        "create_workspace",
        "execute",
        "mkdir",
        "open",
        "popen",
        "read",
        "write",
    }
    for module in source_modules:
        tree = ast.parse(inspect.getsource(module))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module_name = node.module if isinstance(node, ast.ImportFrom) and node.module else ""
                imported_modules = (module_name, *(alias.name for alias in node.names))
                for imported in imported_modules:
                    assert not any(
                        imported == prohibited or imported.startswith(f"{prohibited}.")
                        for prohibited in prohibited_import_roots
                    )
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    assert node.func.id not in prohibited_call_names
                if isinstance(node.func, ast.Attribute):
                    assert node.func.attr not in prohibited_call_names

    # Attestation evidence does not expose or claim any local or external execution fact.
    prohibited_claim_names = (
        "workspace_created",
        "workspace_leased",
        "files_changed",
        "command_authorized",
        "command_executed",
        "process_started",
        "build_succeeded",
        "test_succeeded",
        "application_working",
        "deployment_permitted",
        "publication_permitted",
        "retry_authorized",
        "rollback_authorized",
        "recovery_authorized",
        "reconciliation_authorized",
    )
    for name in prohibited_claim_names:
        assert not hasattr(baseline_assessment, name)
        assert name not in baseline_assessment.__dataclass_fields__
