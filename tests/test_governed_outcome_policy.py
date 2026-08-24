"""Focused tests for the G2.4.19 outcome-semantics policy evidence boundary."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, asdict
from datetime import timedelta

import pytest
from test_support.g2_4_19_outcome_policy_fixture import (
    outcome_assessment_request,
    outcome_policy_fixture,
    policy_variant,
)

from eag.governed_destination_contract import DestinationContractDisposition
from eag.governed_outcome_policy import (
    ExternalOutcomeSemanticsPolicyEvidence,
    OutcomePolicyDisposition,
    OutcomePolicyEvidenceError,
    OutcomePolicyFindingCode,
    OutcomeSemanticsAssessmentRequest,
    OutcomeSemanticsAssessor,
)


def _codes(result: object) -> set[OutcomePolicyFindingCode]:
    return {finding.code for finding in result.findings}  # type: ignore[union-attr]


def test_exact_policy_evidence_is_attested_without_outcome_authority() -> None:
    fixture = outcome_policy_fixture(identity="unit-valid")
    request = outcome_assessment_request(fixture, assessment_request_id="g2419-unit-valid")
    result = OutcomeSemanticsAssessor().assess(assessment_id="g2419-unit-valid-result", request=request)

    assert result.disposition is OutcomePolicyDisposition.OUTCOME_POLICY_ATTESTED
    assert result.policy_id == fixture.policy.outcome_policy_id
    assert result.findings == ()
    assert result.calculate_digest() == result.assessment_digest
    forbidden = {
        "execute", "connect", "request", "send", "upload", "publish", "deploy", "release",
        "retry", "rollback", "reconcile", "complete", "create_session", "issue_permit", "claim",
        "read", "consume", "reset", "delete", "clear", "overwrite", "force_claim", "write", "mutate",
    }
    assert not (forbidden & set(dir(OutcomeSemanticsAssessor)))
    assert not (forbidden & set(dir(result)))


def test_policy_self_identity_changes_digest_but_is_not_automatic_conflict() -> None:
    fixture = outcome_policy_fixture(identity="unit-policy-id")
    changed = policy_variant(fixture.policy, outcome_policy_id="g2419-policy-self-identity-b")
    request = outcome_assessment_request(
        fixture, assessment_request_id="g2419-policy-self-identity", policy=changed
    )
    result = OutcomeSemanticsAssessor().assess(assessment_id="g2419-policy-self-identity-result", request=request)

    assert changed.outcome_policy_id != fixture.policy.outcome_policy_id
    assert changed.policy_digest != fixture.policy.policy_digest
    assert changed.calculate_digest() == changed.policy_digest
    assert result.disposition is OutcomePolicyDisposition.OUTCOME_POLICY_ATTESTED
    assert result.policy_id == changed.outcome_policy_id


@pytest.mark.parametrize(
    ("field", "value", "finding"),
    (
        ("destination_contract_id", "g2419-contract-b", OutcomePolicyFindingCode.CONTRACT_BINDING_MISMATCH),
        ("destination_contract_digest", "1" * 64, OutcomePolicyFindingCode.CONTRACT_BINDING_MISMATCH),
        ("destination_contract_assessment_id", "g2419-assessment-b", OutcomePolicyFindingCode.CONTRACT_BINDING_MISMATCH),
        ("destination_contract_assessment_digest", "2" * 64, OutcomePolicyFindingCode.CONTRACT_BINDING_MISMATCH),
        ("destination_identity", "internal-registry", OutcomePolicyFindingCode.DESTINATION_BINDING_MISMATCH),
        ("destination_operation_profile", "unsupported-operation-v9", OutcomePolicyFindingCode.PROFILE_BINDING_MISMATCH),
        ("external_receipt_schema_id", "unsupported-receipt-v9", OutcomePolicyFindingCode.PROFILE_BINDING_MISMATCH),
        ("destination_idempotency_profile", "unsupported-idempotency-v9", OutcomePolicyFindingCode.PROFILE_BINDING_MISMATCH),
    ),
)
def test_exact_policy_binding_mismatches_fail_closed(
    field: str, value: object, finding: OutcomePolicyFindingCode
) -> None:
    fixture = outcome_policy_fixture(identity=f"unit-{field}")
    policy = policy_variant(fixture.policy, **{field: value})
    request = outcome_assessment_request(fixture, assessment_request_id=f"g2419-{field}", policy=policy)
    result = OutcomeSemanticsAssessor().assess(assessment_id=f"g2419-{field}-result", request=request)

    assert result.disposition is OutcomePolicyDisposition.NOT_ATTESTED
    assert finding in _codes(result)


@pytest.mark.parametrize(
    ("field", "value", "finding"),
    (
        ("operation_profile", "unsupported-outcome-profile-v9", OutcomePolicyFindingCode.UNSUPPORTED_OUTCOME_PROFILE),
        ("future_receipt_classes", ("outcome_unknown_v1",), OutcomePolicyFindingCode.UNSUPPORTED_OUTCOME_PROFILE),
        ("unknown_outcome_disposition", "automatic_progress_allowed", OutcomePolicyFindingCode.UNSAFE_UNKNOWN_OUTCOME_SEMANTICS),
        ("automatic_retry_disposition", "allowed", OutcomePolicyFindingCode.AUTOMATIC_RETRY_FORBIDDEN),
        ("automatic_rollback_disposition", "allowed", OutcomePolicyFindingCode.AUTOMATIC_ROLLBACK_FORBIDDEN),
        ("completion_verification_requirement", "unverified_completion_allowed", OutcomePolicyFindingCode.UNVERIFIED_COMPLETION_FORBIDDEN),
    ),
)
def test_unsafe_or_unsupported_outcome_policy_semantics_fail_closed(
    field: str, value: object, finding: OutcomePolicyFindingCode
) -> None:
    fixture = outcome_policy_fixture(identity=f"unit-unsafe-{field}")
    policy = policy_variant(fixture.policy, **{field: value})
    request = outcome_assessment_request(fixture, assessment_request_id=f"g2419-unsafe-{field}", policy=policy)
    result = OutcomeSemanticsAssessor().assess(assessment_id=f"g2419-unsafe-{field}-result", request=request)

    expected = (
        OutcomePolicyDisposition.UNSUPPORTED_OUTCOME_POLICY
        if finding is OutcomePolicyFindingCode.UNSUPPORTED_OUTCOME_PROFILE
        else OutcomePolicyDisposition.NOT_ATTESTED
    )
    assert result.disposition is expected
    assert finding in _codes(result)


def test_expiry_nonattested_destination_evidence_and_ambiguity_stop_without_recovery() -> None:
    fixture = outcome_policy_fixture(identity="unit-stop")
    assessor = OutcomeSemanticsAssessor()

    expired_policy = policy_variant(fixture.policy, expires_at=fixture.timestamp + timedelta(seconds=1))
    expired_request = outcome_assessment_request(
        fixture, assessment_request_id="g2419-expired-policy", policy=expired_policy,
        timestamp=fixture.timestamp + timedelta(minutes=2),
    )
    expired = assessor.assess(assessment_id="g2419-expired-policy-result", request=expired_request)
    assert OutcomePolicyFindingCode.POLICY_EXPIRED in _codes(expired)

    nonattested = fixture.destination_assessment.__class__.issue(
        assessment_id="g2419-nonattested-contract", request=fixture.destination_request,
        destination_identity=fixture.destination_assessment.destination_identity,
        contract_id=fixture.destination_assessment.contract_id,
        disposition=DestinationContractDisposition.NOT_ATTESTED,
        findings=(), evidence_refs=fixture.destination_assessment.evidence_refs,
        recommendations=(), timestamp=fixture.timestamp,
    )
    nonattested_request = outcome_assessment_request(
        fixture, assessment_request_id="g2419-nonattested-contract", destination_assessment=nonattested
    )
    nonattested_result = assessor.assess(
        assessment_id="g2419-nonattested-contract-result", request=nonattested_request
    )
    assert OutcomePolicyFindingCode.CONTRACT_ASSESSMENT_INVALID in _codes(nonattested_result)

    ambiguous_request = outcome_assessment_request(
        fixture, assessment_request_id="g2419-ambiguous",
        transition_control_evidence=fixture.destination_fixture.ambiguous_control_evidence,
    )
    ambiguous = assessor.assess(assessment_id="g2419-ambiguous-result", request=ambiguous_request)
    assert ambiguous.disposition is OutcomePolicyDisposition.NOT_ATTESTED
    assert OutcomePolicyFindingCode.TRANSITION_CONTROL_AMBIGUOUS in _codes(ambiguous)
    assert not ({"claim", "read", "reset", "release", "reconcile", "retry", "consume", "execute"} & set(dir(assessor)))


def test_policy_request_and_assessment_are_frozen_slots_based_and_self_validating() -> None:
    fixture = outcome_policy_fixture(identity="unit-immutable")
    request = outcome_assessment_request(fixture, assessment_request_id="g2419-immutable")
    assessor = OutcomeSemanticsAssessor()
    result = assessor.assess(assessment_id="g2419-immutable-result", request=request)

    for value in (fixture.policy, request, result):
        assert not hasattr(value, "__dict__")
        before = asdict(value)
        with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
            value.assessment_request_id = "mutation"  # type: ignore[attr-defined]
        assert asdict(value) == before
    with pytest.raises(OutcomePolicyEvidenceError):
        outcome_assessment_request(fixture, schema_version="unsupported")
    with pytest.raises(OutcomePolicyEvidenceError):
        outcome_assessment_request(fixture, request_digest="0" * 64)
    with pytest.raises(TypeError):
        OutcomeSemanticsAssessmentRequest(
            assessment_request_id="g2419-invalid-request", destination_contract_request=object(),
            destination_contract_assessment=fixture.destination_assessment, policy=fixture.policy,
            timestamp=fixture.timestamp,
        )
    payload = fixture.policy.to_payload()
    payload["unexpected"] = "field"
    with pytest.raises(OutcomePolicyEvidenceError):
        ExternalOutcomeSemanticsPolicyEvidence.from_payload(payload)
