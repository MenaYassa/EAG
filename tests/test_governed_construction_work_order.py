"""Focused deterministic tests for G2.4.21 construction work-order evidence only."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import timedelta

import pytest
from test_support.g2_4_21_construction_work_order_fixture import (
    assessment_request,
    construction_work_order_fixture,
    work_order_variant,
)

from eag.governed_construction_work_order import (
    ConstructionWorkOrderAssessmentRequest,
    ConstructionWorkOrderAssessor,
    ConstructionWorkOrderDisposition,
    ConstructionWorkOrderEvidenceError,
    ConstructionWorkOrderFindingCode,
    ConstructionWorkOrderProfile,
    LocalConstructionWorkOrderEvidence,
)


def _codes(assessment: object) -> set[ConstructionWorkOrderFindingCode]:
    return {finding.code for finding in assessment.findings}


def test_valid_work_order_attests_exact_public_evidence(tmp_path) -> None:
    fixture = construction_work_order_fixture(tmp_path)
    request = assessment_request(fixture)

    assessment = ConstructionWorkOrderAssessor().assess(
        assessment_id="g2421-focused-valid",
        request=request,
    )

    assert assessment.disposition is ConstructionWorkOrderDisposition.CONSTRUCTION_WORK_ORDER_ATTESTED
    assert assessment.findings == ()
    assert assessment.work_order_id == fixture.work_order.work_order_id
    assert assessment.workspace_id == fixture.work_order.workspace_id
    assert assessment.assessment_digest == assessment.calculate_digest()


def test_exact_upstream_binding_mismatches_fail_closed(tmp_path) -> None:
    fixture = construction_work_order_fixture(tmp_path)
    assessor = ConstructionWorkOrderAssessor()
    cases = (
        (
            work_order_variant(fixture.work_order, destination_contract_id="different-contract"),
            ConstructionWorkOrderFindingCode.CONTRACT_BINDING_MISMATCH,
        ),
        (
            work_order_variant(fixture.work_order, outcome_policy_id="different-policy"),
            ConstructionWorkOrderFindingCode.OUTCOME_POLICY_BINDING_MISMATCH,
        ),
        (
            work_order_variant(fixture.work_order, workspace_id="different-workspace"),
            ConstructionWorkOrderFindingCode.WORKSPACE_BINDING_MISMATCH,
        ),
        (
            work_order_variant(
                fixture.work_order,
                runtime_composition_attestation_id="different-composition-attestation",
            ),
            ConstructionWorkOrderFindingCode.RUNTIME_COMPOSITION_BINDING_MISMATCH,
        ),
    )

    for work_order, expected in cases:
        assessment = assessor.assess(
            assessment_id=f"g2421-focused-{expected.value}",
            request=assessment_request(fixture, work_order=work_order),
        )
        assert assessment.disposition is ConstructionWorkOrderDisposition.NOT_ATTESTED
        assert expected in _codes(assessment)


def test_expiry_unsupported_capabilities_and_limits_fail_closed(tmp_path) -> None:
    fixture = construction_work_order_fixture(tmp_path)
    assessor = ConstructionWorkOrderAssessor()
    cases = (
        (
            work_order_variant(fixture.work_order, expires_at=fixture.timestamp + timedelta(seconds=1)),
            fixture.timestamp + timedelta(minutes=1),
            ConstructionWorkOrderDisposition.NOT_ATTESTED,
            ConstructionWorkOrderFindingCode.WORK_ORDER_EXPIRED,
        ),
        (
            work_order_variant(
                fixture.work_order,
                declared_capability_ids=(
                    "construction_architecture_declaration",
                    "construction_requirements_declaration",
                    "construction_work_order_evidence",
                    "unsafe_workspace_write",
                ),
            ),
            fixture.timestamp,
            ConstructionWorkOrderDisposition.NOT_ATTESTED,
            ConstructionWorkOrderFindingCode.UNSUPPORTED_CAPABILITY_DECLARATION,
        ),
        (
            work_order_variant(fixture.work_order, max_command_actions=1),
            fixture.timestamp,
            ConstructionWorkOrderDisposition.NOT_ATTESTED,
            ConstructionWorkOrderFindingCode.INVALID_STATIC_LIMITS,
        ),
        (
            work_order_variant(fixture.work_order, construction_profile="unsupported_construction_profile"),
            fixture.timestamp,
            ConstructionWorkOrderDisposition.UNSUPPORTED_CONSTRUCTION_PROFILE,
            ConstructionWorkOrderFindingCode.UNSUPPORTED_CONSTRUCTION_PROFILE,
        ),
    )

    for work_order, timestamp, disposition, code in cases:
        assessment = assessor.assess(
            assessment_id=f"g2421-focused-{code.value}",
            request=assessment_request(fixture, work_order=work_order, timestamp=timestamp),
        )
        assert assessment.disposition is disposition
        assert code in _codes(assessment)


def test_valid_self_identity_and_valid_static_variations_remain_evidence_only(tmp_path) -> None:
    fixture = construction_work_order_fixture(tmp_path)
    assessor = ConstructionWorkOrderAssessor()
    cases = (
        work_order_variant(fixture.work_order, work_order_id="g2421-distinct-work-order"),
        work_order_variant(fixture.work_order, max_file_actions=5),
        work_order_variant(fixture.work_order, max_total_bytes=20_000),
        work_order_variant(fixture.work_order, issued_at=fixture.timestamp - timedelta(minutes=1)),
    )

    for index, work_order in enumerate(cases):
        assessment = assessor.assess(
            assessment_id=f"g2421-focused-valid-variation-{index}",
            request=assessment_request(fixture, work_order=work_order),
        )
        assert assessment.disposition is ConstructionWorkOrderDisposition.CONSTRUCTION_WORK_ORDER_ATTESTED
        assert assessment.findings == ()


def test_payload_parser_is_strict_and_self_validating(tmp_path) -> None:
    fixture = construction_work_order_fixture(tmp_path)
    payload = fixture.work_order.to_payload()
    assert LocalConstructionWorkOrderEvidence.from_payload(payload) == fixture.work_order

    malformed_timestamp = {**payload, "issued_at": "not-a-timestamp"}
    tampered_digest = {**payload, "work_order_digest": "0" * 64}
    unexpected_field = {**payload, "unexpected": "value"}
    unsupported_schema = {**payload, "schema_version": "g2.4.21.unsupported"}
    for invalid in (malformed_timestamp, tampered_digest, unexpected_field, unsupported_schema):
        with pytest.raises(ConstructionWorkOrderEvidenceError):
            LocalConstructionWorkOrderEvidence.from_payload(invalid)


def test_request_strictly_requires_every_public_upstream_type(tmp_path) -> None:
    fixture = construction_work_order_fixture(tmp_path)
    kwargs = dict(
        assessment_request_id="g2421-missing-upstream",
        workspace_custody_attestation=fixture.custody_attestation,
        runtime_composition_attestation=fixture.composition_attestation,
        destination_contract_request=fixture.outcome_fixture.destination_request,
        destination_contract_assessment=fixture.outcome_fixture.destination_assessment,
        outcome_policy_request=fixture.outcome_request,
        outcome_policy_assessment=fixture.outcome_assessment,
        work_order=fixture.work_order,
        timestamp=fixture.timestamp,
    )
    without_contract = {key: value for key, value in kwargs.items() if key != "destination_contract_assessment"}
    without_outcome = {key: value for key, value in kwargs.items() if key != "outcome_policy_assessment"}
    for missing in (without_contract, without_outcome):
        with pytest.raises(TypeError):
            ConstructionWorkOrderAssessmentRequest(**missing)


def test_public_contracts_are_immutable_slots_only_and_container_free(tmp_path) -> None:
    fixture = construction_work_order_fixture(tmp_path)
    request = assessment_request(fixture)
    assessment = ConstructionWorkOrderAssessor().assess(
        assessment_id="g2421-focused-immutable",
        request=request,
    )
    for value in (fixture.work_order, request, assessment):
        assert not hasattr(value, "__dict__")
        with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
            value.work_order_id = "tampered"
    assert isinstance(fixture.work_order.declared_capability_ids, tuple)
    assert isinstance(assessment.findings, tuple)
    assert isinstance(assessment.evidence_refs, tuple)
    assert isinstance(assessment.recommendations, tuple)


def test_public_surface_has_no_construction_effect_methods() -> None:
    import eag.governed_construction_work_order as boundary

    prohibited = (
        "create_workspace",
        "lease_workspace",
        "write_file",
        "mutate_file",
        "execute_command",
        "start_process",
        "install_dependency",
        "retry",
        "rollback",
        "recover",
        "reconcile",
        "publish",
        "deploy",
    )
    for name in prohibited:
        assert not hasattr(boundary, name)
    assert ConstructionWorkOrderProfile.DISPOSABLE_LOCAL_CONSTRUCTION_WORK_ORDER_V1.value
