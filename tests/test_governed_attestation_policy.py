"""Focused tests for G2.4.20 declared attestation-policy evidence."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, asdict
from datetime import timedelta, timezone

import pytest
from test_support.g2_4_20_attestation_policy_fixture import (
    assessment_request,
    attestation_policy_fixture,
    policy_variant,
)

from eag.governed_attestation_policy import (
    AttestationPolicyAssessmentRequest,
    AttestationPolicyAssessor,
    AttestationPolicyDisposition,
    AttestationPolicyEvidenceError,
    AttestationPolicyFindingCode,
    AttestationPolicyProfile,
    DestinationContractAttestationPolicyEvidence,
)


def _codes(result: object) -> set[AttestationPolicyFindingCode]:
    return {finding.code for finding in result.findings}  # type: ignore[union-attr]


def test_policy_is_canonical_self_validating_and_strictly_reconstructable() -> None:
    fixture = attestation_policy_fixture(identity="focused-canonical")
    policy = fixture.policy

    assert policy.calculate_digest() == policy.policy_digest
    assert DestinationContractAttestationPolicyEvidence.from_payload(policy.to_payload()) == policy
    payload = policy.to_payload()
    payload["unexpected"] = "value"
    with pytest.raises(AttestationPolicyEvidenceError):
        DestinationContractAttestationPolicyEvidence.from_payload(payload)

    tampered = policy.to_payload()
    tampered["policy_digest"] = "0" * 64
    with pytest.raises(AttestationPolicyEvidenceError):
        DestinationContractAttestationPolicyEvidence.from_payload(tampered)


def test_policy_timestamp_normalization_and_self_identity_are_deterministic() -> None:
    fixture = attestation_policy_fixture(identity="focused-time")
    policy = fixture.policy
    equivalent = policy_variant(
        policy,
        issued_at=policy.issued_at.astimezone(timezone(timedelta(hours=3))),
        expires_at=policy.expires_at.astimezone(timezone(timedelta(hours=3))),
    )
    distinct = policy_variant(policy, attestation_policy_id="g2420-attestation-policy-focused-time-b")

    assert equivalent.to_payload() == policy.to_payload()
    assert equivalent.policy_digest == policy.policy_digest
    assert distinct.attestation_policy_id != policy.attestation_policy_id
    assert distinct.policy_digest != policy.policy_digest
    assert distinct.calculate_digest() == distinct.policy_digest


def test_request_is_frozen_exact_typed_and_self_validating() -> None:
    fixture = attestation_policy_fixture(identity="focused-request")
    request = assessment_request(fixture, assessment_request_id="g2420-focused-request")

    assert request.request_digest == request.calculate_digest()
    with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
        request.policy = fixture.policy
    with pytest.raises(TypeError):
        AttestationPolicyAssessmentRequest(
            assessment_request_id="g2420-wrong-upstream",
            destination_contract_request=fixture.outcome_fixture.destination_request,
            destination_contract_assessment=fixture.outcome_fixture.destination_assessment,
            outcome_policy_request=fixture.outcome_request,
            outcome_policy_assessment=object(),  # type: ignore[arg-type]
            policy=fixture.policy,
            timestamp=fixture.timestamp,
        )
    with pytest.raises(AttestationPolicyEvidenceError):
        assessment_request(fixture, request_digest="0" * 64)


def test_assessor_attests_only_static_policy_compliance_with_exact_public_evidence() -> None:
    fixture = attestation_policy_fixture(identity="focused-success")
    request = assessment_request(fixture, assessment_request_id="g2420-focused-success")
    result = AttestationPolicyAssessor().assess(assessment_id="g2420-focused-success-result", request=request)

    assert result.disposition is AttestationPolicyDisposition.ATTESTATION_POLICY_ATTESTED
    assert result.findings == ()
    assert result.recommendations == ("attestation_policy_evidence_only",)
    assert (
        f"attestation_policy:{fixture.policy.attestation_policy_id}:{fixture.policy.policy_digest}"
        in result.evidence_refs
    )
    assert result.calculate_digest() == result.assessment_digest


def test_assessor_fails_closed_for_declared_issuer_and_reference_mismatches() -> None:
    fixture = attestation_policy_fixture(identity="focused-metadata")
    assessor = AttestationPolicyAssessor()
    issuer = policy_variant(
        fixture.policy,
        declared_attestation_issuer_identity="attester-focused-metadata-other",
    )
    reference = policy_variant(
        fixture.policy,
        declared_attestation_reference="attestation-focused-metadata-other",
    )

    issuer_result = assessor.assess(
        assessment_id="g2420-focused-issuer-result",
        request=assessment_request(fixture, policy=issuer),
    )
    reference_result = assessor.assess(
        assessment_id="g2420-focused-reference-result",
        request=assessment_request(fixture, policy=reference),
    )

    assert issuer_result.disposition is AttestationPolicyDisposition.NOT_ATTESTED
    assert AttestationPolicyFindingCode.ATTESTATION_ISSUER_BINDING_MISMATCH in _codes(issuer_result)
    assert reference_result.disposition is AttestationPolicyDisposition.NOT_ATTESTED
    assert AttestationPolicyFindingCode.ATTESTATION_REFERENCE_BINDING_MISMATCH in _codes(reference_result)


def test_assessor_fails_closed_for_upstream_binding_expiry_and_unsupported_profile() -> None:
    fixture = attestation_policy_fixture(identity="focused-refusal")
    assessor = AttestationPolicyAssessor()
    contract = policy_variant(fixture.policy, destination_contract_id="g2418-contract-other")
    outcome = policy_variant(fixture.policy, outcome_policy_id="g2419-outcome-policy-other")
    expired = policy_variant(
        fixture.policy,
        issued_at=fixture.timestamp - timedelta(minutes=20),
        expires_at=fixture.timestamp - timedelta(minutes=1),
    )
    unsupported = policy_variant(fixture.policy, attestation_policy_profile="unsupported_attestation_policy_v1")

    contract_result = assessor.assess(assessment_id="g2420-contract-refusal", request=assessment_request(fixture, policy=contract))
    outcome_result = assessor.assess(assessment_id="g2420-outcome-refusal", request=assessment_request(fixture, policy=outcome))
    expired_result = assessor.assess(assessment_id="g2420-expired-refusal", request=assessment_request(fixture, policy=expired))
    unsupported_result = assessor.assess(assessment_id="g2420-unsupported-refusal", request=assessment_request(fixture, policy=unsupported))

    assert AttestationPolicyFindingCode.CONTRACT_BINDING_MISMATCH in _codes(contract_result)
    assert AttestationPolicyFindingCode.OUTCOME_POLICY_BINDING_MISMATCH in _codes(outcome_result)
    assert AttestationPolicyFindingCode.POLICY_EXPIRED in _codes(expired_result)
    assert unsupported_result.disposition is AttestationPolicyDisposition.UNSUPPORTED_ATTESTATION_POLICY
    assert AttestationPolicyFindingCode.UNSUPPORTED_ATTESTATION_PROFILE in _codes(unsupported_result)


def test_assessment_is_immutable_and_contains_no_mutable_public_state() -> None:
    fixture = attestation_policy_fixture(identity="focused-immutable")
    result = AttestationPolicyAssessor().assess(
        assessment_id="g2420-focused-immutable-result",
        request=assessment_request(fixture),
    )
    before = asdict(result)

    assert not hasattr(result, "__dict__")
    assert not isinstance(result.findings, (dict, list, set))
    assert not isinstance(result.evidence_refs, (dict, list, set))
    assert not isinstance(result.recommendations, (dict, list, set))
    with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
        result.disposition = AttestationPolicyDisposition.NOT_ATTESTED
    assert asdict(result) == before


def test_public_surface_has_no_authentication_or_execution_entrypoints() -> None:
    public_names = set(__import__("eag.governed_attestation_policy", fromlist=["*"]).__all__)
    forbidden = {
        "Client",
        "Executor",
        "Credential",
        "Receipt",
        "Permit",
        "Session",
        "Ledger",
        "Registry",
        "Transport",
        "Verifier",
        "TrustRoot",
    }

    assert public_names.isdisjoint(forbidden)
    assert AttestationPolicyProfile.DECLARED_ATTESTATION_POLICY_V1.value == "declared_attestation_policy_v1"
