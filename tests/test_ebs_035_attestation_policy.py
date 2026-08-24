"""EBS-035: deterministic G2.4.20 declared attestation-policy evidence boundary."""

from __future__ import annotations

import hashlib
import inspect
from dataclasses import FrozenInstanceError, asdict, fields
from datetime import timedelta, timezone
from pathlib import Path

import pytest
from test_support.g2_4_18_destination_contract_fixture import (
    assessment_request as destination_assessment_request,
)
from test_support.g2_4_19_outcome_policy_fixture import outcome_assessment_request
from test_support.g2_4_20_attestation_policy_fixture import (
    assessment_request,
    attestation_policy_fixture,
    policy_variant,
)

import eag.governed_attestation_policy.assessor as assessor_module
import eag.governed_attestation_policy.models as models_module
from eag.governed_attestation_policy import (
    AttestationPolicyAssessmentRequest,
    AttestationPolicyAssessor,
    AttestationPolicyDisposition,
    AttestationPolicyEvidenceError,
    AttestationPolicyFindingCode,
    DestinationContractAttestationPolicyEvidence,
)
from eag.governed_destination_contract import DestinationContractAssessor
from eag.governed_outcome_policy import OutcomeSemanticsAssessor


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _codes(result: object) -> set[AttestationPolicyFindingCode]:
    return {finding.code for finding in result.findings}  # type: ignore[union-attr]


def _authoritative_projection(request: AttestationPolicyAssessmentRequest) -> dict[str, object]:
    """Expose the complete G2.4.20 policy binding matrix through public evidence fields."""
    policy = request.policy
    return {
        "attestation_policy_id": policy.attestation_policy_id,
        "destination_contract_id": policy.destination_contract_id,
        "destination_contract_digest": policy.destination_contract_digest,
        "destination_contract_assessment_id": policy.destination_contract_assessment_id,
        "destination_contract_assessment_digest": policy.destination_contract_assessment_digest,
        "outcome_policy_id": policy.outcome_policy_id,
        "outcome_policy_digest": policy.outcome_policy_digest,
        "outcome_policy_assessment_id": policy.outcome_policy_assessment_id,
        "outcome_policy_assessment_digest": policy.outcome_policy_assessment_digest,
        "destination_identity": policy.destination_identity,
        "declared_attestation_issuer_identity": policy.declared_attestation_issuer_identity,
        "declared_attestation_reference": policy.declared_attestation_reference,
        "attestation_policy_profile": policy.attestation_policy_profile,
        "policy_issued_at": policy.issued_at,
        "policy_expires_at": policy.expires_at,
        "request_timestamp": request.timestamp,
    }


def _assert_exact_one_change(
    *,
    baseline: AttestationPolicyAssessmentRequest,
    variant: AttestationPolicyAssessmentRequest,
    expected_changed_field: str,
) -> None:
    """Directly prove one named authoritative fact changes and all other facts are preserved."""
    baseline_fields = _authoritative_projection(baseline)
    variant_fields = _authoritative_projection(variant)
    assert set(variant_fields) == set(baseline_fields)
    assert expected_changed_field in variant_fields
    assert variant_fields[expected_changed_field] != baseline_fields[expected_changed_field]
    for field_name in baseline_fields:
        if field_name != expected_changed_field:
            assert variant_fields[field_name] == baseline_fields[field_name]


def _assert_exact_one_payload_change(
    *,
    baseline: dict[str, str],
    variant: dict[str, str],
    expected_changed_field: str,
) -> None:
    """Directly prove a strict-parser payload branch alters only one supplied fact."""
    assert set(variant) == set(baseline)
    assert expected_changed_field in variant
    assert variant[expected_changed_field] != baseline[expected_changed_field]
    for field_name in baseline:
        if field_name != expected_changed_field:
            assert variant[field_name] == baseline[field_name]


def _assert_immutable(result: object) -> None:
    """Prove the public result is frozen/slots based and does not expose mutable state."""
    assert not hasattr(result, "__dict__")
    before = asdict(result)
    before_digest = result.calculate_digest()
    for field in fields(result):
        value = getattr(result, field.name)
        assert not isinstance(value, (dict, list, set))
        with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
            setattr(result, field.name, value)
    for finding in result.findings:
        assert not hasattr(finding, "__dict__")
        assert not isinstance(finding, (dict, list, set))
        with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
            finding.evidence_reference = finding.evidence_reference
    assert asdict(result) == before
    assert result.calculate_digest() == before_digest


def _assess_preserving_state(
    *,
    assessor: AttestationPolicyAssessor,
    request: AttestationPolicyAssessmentRequest,
    temporary_root: Path,
) -> object:
    """Directly observe immutable inputs and test-owned state around the real assessor call."""
    before_request = request.to_payload()
    before_contract_request = request.destination_contract_request.to_payload()
    before_contract_assessment = asdict(request.destination_contract_assessment)
    before_outcome_request = request.outcome_policy_request.to_payload()
    before_outcome_assessment = asdict(request.outcome_policy_assessment)
    before_policy = request.policy.to_payload()
    before_files = tuple(sorted(path.name for path in temporary_root.iterdir()))
    result = assessor.assess(
        assessment_id=f"{request.assessment_request_id}-assessment",
        request=request,
    )
    assert request.to_payload() == before_request
    assert request.destination_contract_request.to_payload() == before_contract_request
    assert asdict(request.destination_contract_assessment) == before_contract_assessment
    assert request.outcome_policy_request.to_payload() == before_outcome_request
    assert asdict(request.outcome_policy_assessment) == before_outcome_assessment
    assert request.policy.to_payload() == before_policy
    assert tuple(sorted(path.name for path in temporary_root.iterdir())) == before_files
    return result


def _refusal(
    *,
    fixture: object,
    assessor: AttestationPolicyAssessor,
    root: Path,
    request: AttestationPolicyAssessmentRequest,
    finding: AttestationPolicyFindingCode,
    disposition: AttestationPolicyDisposition = AttestationPolicyDisposition.NOT_ATTESTED,
    expected_changed_field: str | None = None,
) -> object:
    original = assessment_request(fixture, assessment_request_id=request.assessment_request_id)
    if expected_changed_field is not None:
        _assert_exact_one_change(
            baseline=original,
            variant=request,
            expected_changed_field=expected_changed_field,
        )
    result = _assess_preserving_state(assessor=assessor, request=request, temporary_root=root)
    assert result.disposition is disposition
    assert finding in _codes(result)
    assert request.request_digest != original.request_digest
    assert original.to_payload() == assessment_request(
        fixture,
        assessment_request_id=request.assessment_request_id,
    ).to_payload()
    _assert_immutable(result)
    return result


def test_ebs_035_declared_attestation_policy_evidence_boundary(tmp_path: Path) -> None:
    """Directly prove G2.4.20 is static policy evidence, not trust or execution evidence."""
    fixture = attestation_policy_fixture(identity="ebs035")
    assessor = AttestationPolicyAssessor()
    valid_request = assessment_request(fixture, assessment_request_id="g2420-ebs035-valid")
    valid = _assess_preserving_state(
        assessor=assessor,
        request=valid_request,
        temporary_root=tmp_path,
    )

    assert valid.disposition is AttestationPolicyDisposition.ATTESTATION_POLICY_ATTESTED
    assert valid.findings == ()
    assert valid.recommendations == ("attestation_policy_evidence_only",)
    assert fixture.outcome_assessment.assessed_request_id == fixture.outcome_request.assessment_request_id
    assert fixture.outcome_assessment.assessed_request_digest == fixture.outcome_request.request_digest
    _assert_immutable(valid)

    substituted_destination_request = destination_assessment_request(
        fixture.outcome_fixture.destination_fixture,
        assessment_request_id="g2420-ebs035-substituted-destination-request",
        timestamp=fixture.timestamp + timedelta(seconds=1),
    )
    substituted_destination_assessment = DestinationContractAssessor().assess(
        assessment_id="g2420-ebs035-substituted-destination-assessment",
        request=substituted_destination_request,
    )
    substituted_destination_chain = AttestationPolicyAssessmentRequest(
        assessment_request_id="g2420-ebs035-substituted-destination-chain",
        destination_contract_request=fixture.outcome_fixture.destination_request,
        destination_contract_assessment=substituted_destination_assessment,
        outcome_policy_request=fixture.outcome_request,
        outcome_policy_assessment=fixture.outcome_assessment,
        policy=fixture.policy,
        timestamp=fixture.timestamp,
    )
    assert substituted_destination_chain.policy == valid_request.policy
    assert substituted_destination_chain.destination_contract_request == valid_request.destination_contract_request
    assert substituted_destination_chain.outcome_policy_request == valid_request.outcome_policy_request
    assert substituted_destination_chain.outcome_policy_assessment == valid_request.outcome_policy_assessment
    assert (
        substituted_destination_chain.destination_contract_assessment.assessed_request_id
        != substituted_destination_chain.destination_contract_request.assessment_request_id
    )
    assert (
        substituted_destination_chain.destination_contract_assessment.assessed_request_digest
        != substituted_destination_chain.destination_contract_request.request_digest
    )
    substituted_destination_result = _assess_preserving_state(
        assessor=assessor,
        request=substituted_destination_chain,
        temporary_root=tmp_path,
    )
    assert substituted_destination_result.disposition is AttestationPolicyDisposition.NOT_ATTESTED
    assert AttestationPolicyFindingCode.CONTRACT_BINDING_MISMATCH in _codes(substituted_destination_result)
    _assert_immutable(substituted_destination_result)

    substituted_outcome_request = outcome_assessment_request(
        fixture.outcome_fixture,
        assessment_request_id="g2420-ebs035-substituted-outcome-request",
        timestamp=fixture.timestamp + timedelta(seconds=1),
    )
    substituted_outcome_assessment = OutcomeSemanticsAssessor().assess(
        assessment_id="g2420-ebs035-substituted-outcome-assessment",
        request=substituted_outcome_request,
    )
    substituted_outcome_assessment_request = assessment_request(
        fixture,
        assessment_request_id="g2420-ebs035-substituted-outcome-chain",
        outcome_assessment=substituted_outcome_assessment,
    )
    assert substituted_outcome_assessment_request.policy == valid_request.policy
    assert substituted_outcome_assessment_request.destination_contract_request == valid_request.destination_contract_request
    assert substituted_outcome_assessment_request.destination_contract_assessment == valid_request.destination_contract_assessment
    assert substituted_outcome_assessment_request.outcome_policy_request == valid_request.outcome_policy_request
    assert (
        substituted_outcome_assessment_request.outcome_policy_assessment.assessed_request_id
        != substituted_outcome_assessment_request.outcome_policy_request.assessment_request_id
    )
    assert (
        substituted_outcome_assessment_request.outcome_policy_assessment.assessed_request_digest
        != substituted_outcome_assessment_request.outcome_policy_request.request_digest
    )
    substituted_outcome_result = _assess_preserving_state(
        assessor=assessor,
        request=substituted_outcome_assessment_request,
        temporary_root=tmp_path,
    )
    assert substituted_outcome_result.disposition is AttestationPolicyDisposition.NOT_ATTESTED
    assert AttestationPolicyFindingCode.OUTCOME_POLICY_BINDING_MISMATCH in _codes(substituted_outcome_result)
    _assert_immutable(substituted_outcome_result)
    assert (
        f"destination_contract_assessment:{fixture.outcome_fixture.destination_assessment.assessment_id}:"
        f"{fixture.outcome_fixture.destination_assessment.assessment_digest}"
        in valid.evidence_refs
    )
    assert (
        f"outcome_policy_assessment:{fixture.outcome_assessment.assessment_id}:"
        f"{fixture.outcome_assessment.assessment_digest}"
        in valid.evidence_refs
    )
    assert (
        f"attestation_policy:{fixture.policy.attestation_policy_id}:{fixture.policy.policy_digest}"
        in valid.evidence_refs
    )

    equivalent_fixture = attestation_policy_fixture(identity="ebs035")
    equivalent_request = assessment_request(
        equivalent_fixture,
        assessment_request_id="g2420-ebs035-valid",
    )
    equivalent = _assess_preserving_state(
        assessor=assessor,
        request=equivalent_request,
        temporary_root=tmp_path,
    )
    assert equivalent_fixture.policy.to_payload() == fixture.policy.to_payload()
    assert equivalent_fixture.policy.policy_digest == fixture.policy.policy_digest
    assert equivalent_request.to_payload() == valid_request.to_payload()
    assert equivalent_request.request_digest == valid_request.request_digest
    assert equivalent.assessment_digest == valid.assessment_digest

    offset_request = assessment_request(
        fixture,
        assessment_request_id="g2420-ebs035-valid",
        timestamp=fixture.timestamp.astimezone(timezone(timedelta(hours=3))),
    )
    assert offset_request.timestamp == valid_request.timestamp
    assert offset_request.to_payload() == valid_request.to_payload()
    assert offset_request.request_digest == valid_request.request_digest

    issued_at_policy = policy_variant(
        fixture.policy,
        issued_at=fixture.timestamp - timedelta(minutes=1),
    )
    issued_at_request = assessment_request(
        fixture,
        assessment_request_id="g2420-ebs035-issued-at",
        policy=issued_at_policy,
    )
    _assert_exact_one_change(
        baseline=assessment_request(fixture, assessment_request_id="g2420-ebs035-issued-at"),
        variant=issued_at_request,
        expected_changed_field="policy_issued_at",
    )
    issued_at_result = _assess_preserving_state(
        assessor=assessor,
        request=issued_at_request,
        temporary_root=tmp_path,
    )
    assert issued_at_policy.issued_at < fixture.policy.issued_at
    assert issued_at_policy.policy_digest != fixture.policy.policy_digest
    assert issued_at_result.disposition is AttestationPolicyDisposition.ATTESTATION_POLICY_ATTESTED
    assert issued_at_result.findings == ()
    _assert_immutable(issued_at_result)

    self_identity_policy = policy_variant(
        fixture.policy,
        attestation_policy_id="g2420-attestation-policy-ebs035-b",
    )
    self_identity_request = assessment_request(
        fixture,
        assessment_request_id="g2420-ebs035-self-identity",
        policy=self_identity_policy,
    )
    _assert_exact_one_change(
        baseline=assessment_request(fixture, assessment_request_id="g2420-ebs035-self-identity"),
        variant=self_identity_request,
        expected_changed_field="attestation_policy_id",
    )
    self_identity = _assess_preserving_state(
        assessor=assessor,
        request=self_identity_request,
        temporary_root=tmp_path,
    )
    assert self_identity_policy.policy_digest != fixture.policy.policy_digest
    assert self_identity.disposition is AttestationPolicyDisposition.ATTESTATION_POLICY_ATTESTED
    assert self_identity.policy_id == self_identity_policy.attestation_policy_id
    assert "selection" not in " ".join(self_identity.recommendations)
    assert "precedence" not in " ".join(self_identity.recommendations)
    assert "reconciliation" not in " ".join(self_identity.recommendations)

    issuer_policy = policy_variant(
        fixture.policy,
        declared_attestation_issuer_identity="attester-ebs035-other",
    )
    _refusal(
        fixture=fixture,
        assessor=assessor,
        root=tmp_path,
        request=assessment_request(
            fixture,
            assessment_request_id="g2420-ebs035-issuer",
            policy=issuer_policy,
        ),
        finding=AttestationPolicyFindingCode.ATTESTATION_ISSUER_BINDING_MISMATCH,
        expected_changed_field="declared_attestation_issuer_identity",
    )

    reference_policy = policy_variant(
        fixture.policy,
        declared_attestation_reference="attestation-ebs035-other",
    )
    _refusal(
        fixture=fixture,
        assessor=assessor,
        root=tmp_path,
        request=assessment_request(
            fixture,
            assessment_request_id="g2420-ebs035-reference",
            policy=reference_policy,
        ),
        finding=AttestationPolicyFindingCode.ATTESTATION_REFERENCE_BINDING_MISMATCH,
        expected_changed_field="declared_attestation_reference",
    )

    contract_policy = policy_variant(
        fixture.policy,
        destination_contract_id="g2418-destination-contract-ebs035-other",
    )
    _refusal(
        fixture=fixture,
        assessor=assessor,
        root=tmp_path,
        request=assessment_request(
            fixture,
            assessment_request_id="g2420-ebs035-contract",
            policy=contract_policy,
        ),
        finding=AttestationPolicyFindingCode.CONTRACT_BINDING_MISMATCH,
        expected_changed_field="destination_contract_id",
    )

    contract_digest_policy = policy_variant(
        fixture.policy,
        destination_contract_digest=_digest("ebs035-contract-digest-other"),
    )
    _refusal(
        fixture=fixture,
        assessor=assessor,
        root=tmp_path,
        request=assessment_request(
            fixture,
            assessment_request_id="g2420-ebs035-contract-digest",
            policy=contract_digest_policy,
        ),
        finding=AttestationPolicyFindingCode.CONTRACT_BINDING_MISMATCH,
        expected_changed_field="destination_contract_digest",
    )

    contract_assessment_id_policy = policy_variant(
        fixture.policy,
        destination_contract_assessment_id="g2418-contract-assessment-ebs035-other",
    )
    _refusal(
        fixture=fixture,
        assessor=assessor,
        root=tmp_path,
        request=assessment_request(
            fixture,
            assessment_request_id="g2420-ebs035-contract-assessment-id",
            policy=contract_assessment_id_policy,
        ),
        finding=AttestationPolicyFindingCode.CONTRACT_BINDING_MISMATCH,
        expected_changed_field="destination_contract_assessment_id",
    )

    contract_assessment_digest_policy = policy_variant(
        fixture.policy,
        destination_contract_assessment_digest=_digest("ebs035-contract-assessment-digest-other"),
    )
    _refusal(
        fixture=fixture,
        assessor=assessor,
        root=tmp_path,
        request=assessment_request(
            fixture,
            assessment_request_id="g2420-ebs035-contract-assessment-digest",
            policy=contract_assessment_digest_policy,
        ),
        finding=AttestationPolicyFindingCode.CONTRACT_BINDING_MISMATCH,
        expected_changed_field="destination_contract_assessment_digest",
    )

    outcome_policy = policy_variant(
        fixture.policy,
        outcome_policy_id="g2419-outcome-policy-ebs035-other",
    )
    _refusal(
        fixture=fixture,
        assessor=assessor,
        root=tmp_path,
        request=assessment_request(
            fixture,
            assessment_request_id="g2420-ebs035-outcome",
            policy=outcome_policy,
        ),
        finding=AttestationPolicyFindingCode.OUTCOME_POLICY_BINDING_MISMATCH,
        expected_changed_field="outcome_policy_id",
    )

    outcome_policy_digest = policy_variant(
        fixture.policy,
        outcome_policy_digest=_digest("ebs035-outcome-policy-digest-other"),
    )
    _refusal(
        fixture=fixture,
        assessor=assessor,
        root=tmp_path,
        request=assessment_request(
            fixture,
            assessment_request_id="g2420-ebs035-outcome-digest",
            policy=outcome_policy_digest,
        ),
        finding=AttestationPolicyFindingCode.OUTCOME_POLICY_BINDING_MISMATCH,
        expected_changed_field="outcome_policy_digest",
    )

    outcome_assessment_id_policy = policy_variant(
        fixture.policy,
        outcome_policy_assessment_id="g2419-outcome-assessment-ebs035-other",
    )
    _refusal(
        fixture=fixture,
        assessor=assessor,
        root=tmp_path,
        request=assessment_request(
            fixture,
            assessment_request_id="g2420-ebs035-outcome-assessment-id",
            policy=outcome_assessment_id_policy,
        ),
        finding=AttestationPolicyFindingCode.OUTCOME_POLICY_BINDING_MISMATCH,
        expected_changed_field="outcome_policy_assessment_id",
    )

    outcome_assessment_digest_policy = policy_variant(
        fixture.policy,
        outcome_policy_assessment_digest=_digest("ebs035-outcome-assessment-digest-other"),
    )
    _refusal(
        fixture=fixture,
        assessor=assessor,
        root=tmp_path,
        request=assessment_request(
            fixture,
            assessment_request_id="g2420-ebs035-outcome-assessment-digest",
            policy=outcome_assessment_digest_policy,
        ),
        finding=AttestationPolicyFindingCode.OUTCOME_POLICY_BINDING_MISMATCH,
        expected_changed_field="outcome_policy_assessment_digest",
    )

    destination_policy = policy_variant(
        fixture.policy,
        destination_identity="destination-ebs035-other",
    )
    _refusal(
        fixture=fixture,
        assessor=assessor,
        root=tmp_path,
        request=assessment_request(
            fixture,
            assessment_request_id="g2420-ebs035-destination",
            policy=destination_policy,
        ),
        finding=AttestationPolicyFindingCode.DESTINATION_BINDING_MISMATCH,
        expected_changed_field="destination_identity",
    )

    expiry_policy = policy_variant(
        fixture.policy,
        expires_at=fixture.timestamp + timedelta(minutes=1),
    )
    expiry_request = assessment_request(
        fixture,
        assessment_request_id="g2420-ebs035-expiry",
        policy=expiry_policy,
        timestamp=fixture.timestamp + timedelta(minutes=2),
    )
    _assert_exact_one_change(
        baseline=assessment_request(
            fixture,
            assessment_request_id="g2420-ebs035-expiry",
            timestamp=fixture.timestamp + timedelta(minutes=2),
        ),
        variant=expiry_request,
        expected_changed_field="policy_expires_at",
    )
    expired = _assess_preserving_state(assessor=assessor, request=expiry_request, temporary_root=tmp_path)
    assert expired.disposition is AttestationPolicyDisposition.NOT_ATTESTED
    assert AttestationPolicyFindingCode.POLICY_EXPIRED in _codes(expired)
    _assert_immutable(expired)

    request_time_refusal = assessment_request(
        fixture,
        assessment_request_id="g2420-ebs035-request-time",
        timestamp=fixture.timestamp + timedelta(minutes=11),
    )
    _refusal(
        fixture=fixture,
        assessor=assessor,
        root=tmp_path,
        request=request_time_refusal,
        finding=AttestationPolicyFindingCode.POLICY_EXPIRED,
        expected_changed_field="request_timestamp",
    )

    unsupported_policy = policy_variant(
        fixture.policy,
        attestation_policy_profile="unsupported_attestation_policy_v1",
    )
    _refusal(
        fixture=fixture,
        assessor=assessor,
        root=tmp_path,
        request=assessment_request(
            fixture,
            assessment_request_id="g2420-ebs035-unsupported",
            policy=unsupported_policy,
        ),
        finding=AttestationPolicyFindingCode.UNSUPPORTED_ATTESTATION_PROFILE,
        disposition=AttestationPolicyDisposition.UNSUPPORTED_ATTESTATION_POLICY,
        expected_changed_field="attestation_policy_profile",
    )

    baseline_timestamp_payload = fixture.policy.to_payload()
    malformed_timestamp_payload = fixture.policy.to_payload()
    malformed_timestamp_payload["issued_at"] = "not-a-timestamp"
    _assert_exact_one_payload_change(
        baseline=baseline_timestamp_payload,
        variant=malformed_timestamp_payload,
        expected_changed_field="issued_at",
    )
    with pytest.raises(AttestationPolicyEvidenceError):
        DestinationContractAttestationPolicyEvidence.from_payload(malformed_timestamp_payload)
    assert malformed_timestamp_payload["issued_at"] == "not-a-timestamp"
    assert tuple(sorted(path.name for path in tmp_path.iterdir())) == ()

    schema_payload = fixture.policy.to_payload()
    schema_payload["schema_version"] = "g2.4.20.unsupported"
    with pytest.raises(AttestationPolicyEvidenceError):
        DestinationContractAttestationPolicyEvidence.from_payload(schema_payload)
    assert schema_payload["schema_version"] == "g2.4.20.unsupported"
    assert tuple(sorted(path.name for path in tmp_path.iterdir())) == ()

    digest_payload = fixture.policy.to_payload()
    digest_payload["policy_digest"] = _digest("ebs035-tampered-policy-digest")
    with pytest.raises(AttestationPolicyEvidenceError):
        DestinationContractAttestationPolicyEvidence.from_payload(digest_payload)
    assert digest_payload["policy_digest"] == _digest("ebs035-tampered-policy-digest")
    assert tuple(sorted(path.name for path in tmp_path.iterdir())) == ()

    before_missing_request = valid_request.to_payload()
    before_missing_files = tuple(sorted(path.name for path in tmp_path.iterdir()))
    with pytest.raises(TypeError):
        AttestationPolicyAssessmentRequest(
            assessment_request_id="g2420-ebs035-missing-contract-assessment",
            destination_contract_request=fixture.outcome_fixture.destination_request,
            outcome_policy_request=fixture.outcome_request,
            outcome_policy_assessment=fixture.outcome_assessment,
            policy=fixture.policy,
            timestamp=fixture.timestamp,
        )
    with pytest.raises(TypeError):
        AttestationPolicyAssessmentRequest(
            assessment_request_id="g2420-ebs035-missing-outcome-assessment",
            destination_contract_request=fixture.outcome_fixture.destination_request,
            destination_contract_assessment=fixture.outcome_fixture.destination_assessment,
            outcome_policy_request=fixture.outcome_request,
            policy=fixture.policy,
            timestamp=fixture.timestamp,
        )
    assert valid_request.to_payload() == before_missing_request
    assert tuple(sorted(path.name for path in tmp_path.iterdir())) == before_missing_files

    public_names = set(
        __import__("eag.governed_attestation_policy", fromlist=["*"]).__all__
    )
    forbidden_public_names = {
        "Client",
        "Credential",
        "Executor",
        "Ledger",
        "Permit",
        "Receipt",
        "Registry",
        "Session",
        "Transport",
        "Verifier",
        "TrustRoot",
    }
    assert public_names.isdisjoint(forbidden_public_names)
    assessor_signature = inspect.signature(AttestationPolicyAssessor.assess)
    assert tuple(assessor_signature.parameters) == ("self", "assessment_id", "request")
    assert "AttestationPolicyAssessor" in assessor_module.__all__
    assert set(models_module.__all__) == public_names - {"AttestationPolicyAssessor"}

    forbidden_runtime_fields = {
        "client",
        "credential",
        "executor",
        "ledger",
        "network",
        "receipt",
        "registry",
        "session",
        "transport",
        "verifier",
    }
    for model in (
        DestinationContractAttestationPolicyEvidence,
        AttestationPolicyAssessmentRequest,
        type(valid),
    ):
        assert forbidden_runtime_fields.isdisjoint({field.name for field in fields(model)})

    # B5/B6: immutable evidence/result and test-owned state are direct state proof.
    # Operational categories have no reachable public capability and are capability absent.
    # No literal zero-effect counter, sentinel, callback, hook, observer, or instrumentation is used.
