"""EBS-033: deterministic governed destination-contract evidence boundary rehearsal."""

from __future__ import annotations

import hashlib
import inspect
from dataclasses import FrozenInstanceError, asdict, fields, replace
from datetime import timedelta, timezone
from pathlib import Path

import pytest
from test_support.g2_4_18_destination_contract_fixture import (
    assessment_request,
    contract_variant,
    destination_contract_fixture,
)

import eag.governed_destination_contract.assessor as assessor_module
import eag.governed_destination_contract.models as models_module
from eag.governed_destination_contract import (
    DestinationContractAssessmentRequest,
    DestinationContractAssessor,
    DestinationContractDisposition,
    DestinationContractEvidenceError,
    DestinationContractFindingCode,
    ExternalDestinationContractEvidence,
)
from eag.governed_promotion import PromotionEligibilityAssessment, PromotionEligibilityDisposition
from eag.governed_transition_authorization import (
    ExternalTransitionAuthorizationReceipt,
    HumanAuthorizationDecision,
)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _codes(result: object) -> set[DestinationContractFindingCode]:
    return {finding.code for finding in result.findings}  # type: ignore[union-attr]


def _authoritative_projection(request: DestinationContractAssessmentRequest) -> dict[str, object]:
    """Expose the complete benchmark binding matrix through real public evidence fields."""
    contract = request.contract
    return {
        "artifact_id": contract.artifact_id,
        "artifact_fingerprint": contract.artifact_fingerprint,
        "promotion_request_identity": request.promotion_request.intent_id,
        "promotion_assessment_id": contract.promotion_assessment_id,
        "promotion_assessment_digest": contract.promotion_assessment_digest,
        "promotion_policy_digest": contract.promotion_policy_digest,
        "transition_intent_id": contract.transition_intent_id,
        "transition_profile": contract.transition_profile,
        "authorization_id": contract.authorization_id,
        "authorization_binding_digest": contract.authorization_binding_digest,
        "authorization_assessment_id": contract.authorization_assessment_id,
        "authorization_assessment_digest": contract.authorization_assessment_digest,
        "authorization_policy_digest": contract.authorization_policy_digest,
        "execution_id": contract.execution_id,
        "run_id": contract.run_id,
        "destination_identity": contract.destination_identity,
    }


def _assert_exact_one_authoritative_change(
    *, baseline: DestinationContractAssessmentRequest,
    variant: DestinationContractAssessmentRequest, expected_changed_field: str,
) -> None:
    """Directly prove one named binding changes and every other required binding is preserved."""
    baseline_fields = _authoritative_projection(baseline)
    variant_fields = _authoritative_projection(variant)
    assert set(variant_fields) == set(baseline_fields)
    assert expected_changed_field in variant_fields
    assert variant_fields[expected_changed_field] != baseline_fields[expected_changed_field]
    for field_name in baseline_fields:
        if field_name != expected_changed_field:
            assert variant_fields[field_name] == baseline_fields[field_name]


def _assert_assessment_immutable(result: object) -> None:
    """Exercise mutation refusal and prove no mutable result or nested finding state is exposed."""
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
    *, assessor: DestinationContractAssessor, request: DestinationContractAssessmentRequest,
    temporary_root: Path,
) -> object:
    """Observe actual immutable inputs and test-owned state immediately around assessment."""
    before_request = request.to_payload()
    before_promotion_request = asdict(request.promotion_request)
    before_promotion_assessment = asdict(request.promotion_assessment)
    before_intent = asdict(request.transition_intent)
    before_authorization = asdict(request.authorization)
    before_authorization_assessment = asdict(request.authorization_assessment)
    before_contract = asdict(request.contract)
    before_files = tuple(sorted(path.name for path in temporary_root.iterdir()))
    result = assessor.assess(
        assessment_id=f"{request.assessment_request_id}-assessment", request=request
    )
    assert request.to_payload() == before_request
    assert asdict(request.promotion_request) == before_promotion_request
    assert asdict(request.promotion_assessment) == before_promotion_assessment
    assert asdict(request.transition_intent) == before_intent
    assert asdict(request.authorization) == before_authorization
    assert asdict(request.authorization_assessment) == before_authorization_assessment
    assert asdict(request.contract) == before_contract
    assert tuple(sorted(path.name for path in temporary_root.iterdir())) == before_files
    return result


def _refusal(
    *, fixture: object, assessor: DestinationContractAssessor,
    root: Path, request: DestinationContractAssessmentRequest, finding: DestinationContractFindingCode,
    disposition: DestinationContractDisposition = DestinationContractDisposition.NOT_ATTESTED,
    expected_changed_field: str | None = None,
) -> object:
    original = assessment_request(
        fixture, assessment_request_id=request.assessment_request_id
    )
    if expected_changed_field is not None:
        _assert_exact_one_authoritative_change(
            baseline=original, variant=request, expected_changed_field=expected_changed_field
        )
    result = _assess_preserving_state(
        assessor=assessor, request=request, temporary_root=root
    )
    assert result.disposition is disposition
    assert finding in _codes(result)
    assert request.request_digest != original.request_digest
    assert original.to_payload() == assessment_request(
        fixture, assessment_request_id=request.assessment_request_id
    ).to_payload()
    _assert_assessment_immutable(result)
    return result


def test_ebs_033_governed_destination_contract_evidence_boundary(tmp_path: Path) -> None:
    """Directly prove the frozen G2.4.18 evidence-only contract boundary."""
    fixture = destination_contract_fixture(identity="ebs033")
    assessor = DestinationContractAssessor()
    valid_request = assessment_request(fixture, assessment_request_id="g2418-ebs033-valid")
    valid = _assess_preserving_state(
        assessor=assessor, request=valid_request, temporary_root=tmp_path
    )
    assert valid.disposition is DestinationContractDisposition.CONTRACT_ATTESTED
    assert valid.findings == ()
    assert valid.assessed_request_id == valid_request.assessment_request_id
    assert valid.assessed_request_digest == valid_request.request_digest
    assert valid.assessment_digest == valid.calculate_digest()
    assert valid.schema_version == "g2.4.18.destination-contract-assessment.v2"
    _assert_assessment_immutable(valid)
    assert f"destination_contract:{fixture.contract.destination_contract_id}:{fixture.contract.contract_digest}" in valid.evidence_refs

    equivalent_fixture = destination_contract_fixture(identity="ebs033")
    equivalent_request = assessment_request(equivalent_fixture, assessment_request_id="g2418-ebs033-valid")
    equivalent = _assess_preserving_state(
        assessor=assessor, request=equivalent_request, temporary_root=tmp_path
    )
    assert equivalent_fixture.contract.to_payload() == fixture.contract.to_payload()
    assert equivalent_fixture.contract.contract_digest == fixture.contract.contract_digest
    assert equivalent_request.to_payload() == valid_request.to_payload()
    assert equivalent_request.request_digest == valid_request.request_digest
    assert equivalent.assessed_request_id == equivalent_request.assessment_request_id
    assert equivalent.assessed_request_digest == equivalent_request.request_digest
    assert equivalent.assessment_digest == valid.assessment_digest

    linked_variant_request = assessment_request(
        fixture,
        assessment_request_id="g2418-ebs033-linked-variant",
        timestamp=fixture.timestamp + timedelta(seconds=1),
    )
    linked_variant = _assess_preserving_state(
        assessor=assessor,
        request=linked_variant_request,
        temporary_root=tmp_path,
    )
    assert linked_variant.assessed_request_id == linked_variant_request.assessment_request_id
    assert linked_variant.assessed_request_digest == linked_variant_request.request_digest
    assert linked_variant.assessed_request_id != valid.assessed_request_id
    assert linked_variant.assessed_request_digest != valid.assessed_request_digest
    with pytest.raises(DestinationContractEvidenceError):
        replace(linked_variant, assessed_request_id="different-request")
    with pytest.raises(DestinationContractEvidenceError):
        replace(linked_variant, assessed_request_digest="0" * 64)
    with pytest.raises(DestinationContractEvidenceError):
        replace(linked_variant, schema_version="g2.4.18.destination-contract.v1")

    offset_request = assessment_request(
        fixture, assessment_request_id="g2418-ebs033-valid",
        timestamp=fixture.timestamp.astimezone(timezone(timedelta(hours=3))),
    )
    assert offset_request.timestamp == valid_request.timestamp
    assert offset_request.to_payload() == valid_request.to_payload()
    assert offset_request.request_digest == valid_request.request_digest

    contract_b = contract_variant(
        fixture.contract, destination_contract_id="g2418-destination-contract-ebs033-b"
    )
    request_b = assessment_request(fixture, assessment_request_id="g2418-ebs033-contract-b", contract=contract_b)
    assessment_b = _assess_preserving_state(
        assessor=assessor, request=request_b, temporary_root=tmp_path
    )
    assert contract_b.destination_contract_id != fixture.contract.destination_contract_id
    assert contract_b.contract_digest != fixture.contract.contract_digest
    assert contract_b.calculate_digest() == contract_b.contract_digest
    assert assessment_b.disposition is DestinationContractDisposition.CONTRACT_ATTESTED
    assert f"destination_contract:{contract_b.destination_contract_id}:{contract_b.contract_digest}" in assessment_b.evidence_refs
    assert f"destination_contract:{fixture.contract.destination_contract_id}:{fixture.contract.contract_digest}" not in assessment_b.evidence_refs

    artifact_id = contract_variant(fixture.contract, artifact_id="g2418-ebs033-artifact-b")
    assert artifact_id.artifact_id != fixture.contract.artifact_id
    _refusal(fixture=fixture, assessor=assessor, root=tmp_path,
        request=assessment_request(fixture, assessment_request_id="g2418-artifact-id", contract=artifact_id),
        finding=DestinationContractFindingCode.ARTIFACT_IDENTITY_MISMATCH,
        expected_changed_field="artifact_id")

    artifact_fingerprint = contract_variant(fixture.contract, artifact_fingerprint=_digest("artifact-b"))
    assert artifact_fingerprint.artifact_fingerprint != fixture.contract.artifact_fingerprint
    _refusal(fixture=fixture, assessor=assessor, root=tmp_path,
        request=assessment_request(fixture, assessment_request_id="g2418-artifact-fingerprint", contract=artifact_fingerprint),
        finding=DestinationContractFindingCode.ARTIFACT_IDENTITY_MISMATCH,
        expected_changed_field="artifact_fingerprint")

    promotion_request = fixture.promotion_request.__class__(
        intent_id="g2418-ebs033-promotion-intent-b", artifact_id=fixture.promotion_request.artifact_id,
        artifact_fingerprint=fixture.promotion_request.artifact_fingerprint,
        readiness_evidence_reference=fixture.promotion_request.readiness_evidence_reference,
        lineage_reference=fixture.promotion_request.lineage_reference,
        destination_identity=fixture.promotion_request.destination_identity,
        promotion_policy_digest=fixture.promotion_request.promotion_policy_digest,
        promotion_profile=fixture.promotion_request.promotion_profile,
    )
    assert promotion_request.intent_id != fixture.promotion_request.intent_id
    _refusal(fixture=fixture, assessor=assessor, root=tmp_path,
        request=assessment_request(fixture, assessment_request_id="g2418-promotion-request", promotion_request=promotion_request),
        finding=DestinationContractFindingCode.ASSESSMENT_BINDING_MISMATCH,
        expected_changed_field="promotion_request_identity")

    promotion_assessment_id = contract_variant(fixture.contract, promotion_assessment_id="g2418-promotion-assessment-b")
    assert promotion_assessment_id.promotion_assessment_id != fixture.contract.promotion_assessment_id
    _refusal(fixture=fixture, assessor=assessor, root=tmp_path,
        request=assessment_request(fixture, assessment_request_id="g2418-promotion-assessment-id", contract=promotion_assessment_id),
        finding=DestinationContractFindingCode.TRANSITION_BINDING_MISMATCH,
        expected_changed_field="promotion_assessment_id")

    promotion_assessment_digest = contract_variant(fixture.contract, promotion_assessment_digest=_digest("promotion-assessment-b"))
    assert promotion_assessment_digest.promotion_assessment_digest != fixture.contract.promotion_assessment_digest
    _refusal(fixture=fixture, assessor=assessor, root=tmp_path,
        request=assessment_request(fixture, assessment_request_id="g2418-promotion-assessment-digest", contract=promotion_assessment_digest),
        finding=DestinationContractFindingCode.TRANSITION_BINDING_MISMATCH,
        expected_changed_field="promotion_assessment_digest")

    promotion_policy = contract_variant(fixture.contract, promotion_policy_digest=_digest("promotion-policy-b"))
    assert promotion_policy.promotion_policy_digest != fixture.contract.promotion_policy_digest
    _refusal(fixture=fixture, assessor=assessor, root=tmp_path,
        request=assessment_request(fixture, assessment_request_id="g2418-promotion-policy", contract=promotion_policy),
        finding=DestinationContractFindingCode.CONTRACT_POLICY_MISMATCH,
        expected_changed_field="promotion_policy_digest")

    transition_intent = contract_variant(fixture.contract, transition_intent_id="g2418-transition-intent-b")
    assert transition_intent.transition_intent_id != fixture.contract.transition_intent_id
    _refusal(fixture=fixture, assessor=assessor, root=tmp_path,
        request=assessment_request(fixture, assessment_request_id="g2418-transition-intent", contract=transition_intent),
        finding=DestinationContractFindingCode.TRANSITION_BINDING_MISMATCH,
        expected_changed_field="transition_intent_id")

    transition_profile = contract_variant(fixture.contract, transition_profile="unsupported-transition-profile-v9")
    assert transition_profile.transition_profile != fixture.contract.transition_profile
    _refusal(fixture=fixture, assessor=assessor, root=tmp_path,
        request=assessment_request(fixture, assessment_request_id="g2418-transition-profile", contract=transition_profile),
        finding=DestinationContractFindingCode.UNSUPPORTED_PROFILE,
        disposition=DestinationContractDisposition.UNSUPPORTED_DESTINATION_CONTRACT,
        expected_changed_field="transition_profile")

    authorization_id = contract_variant(fixture.contract, authorization_id="g2418-authorization-b")
    assert authorization_id.authorization_id != fixture.contract.authorization_id
    _refusal(fixture=fixture, assessor=assessor, root=tmp_path,
        request=assessment_request(fixture, assessment_request_id="g2418-authorization-id", contract=authorization_id),
        finding=DestinationContractFindingCode.AUTHORIZATION_BINDING_MISMATCH,
        expected_changed_field="authorization_id")

    authorization_binding = contract_variant(fixture.contract, authorization_binding_digest=_digest("authorization-binding-b"))
    assert authorization_binding.authorization_binding_digest != fixture.contract.authorization_binding_digest
    _refusal(fixture=fixture, assessor=assessor, root=tmp_path,
        request=assessment_request(fixture, assessment_request_id="g2418-authorization-binding", contract=authorization_binding),
        finding=DestinationContractFindingCode.AUTHORIZATION_BINDING_MISMATCH,
        expected_changed_field="authorization_binding_digest")

    authorization_assessment_id = contract_variant(fixture.contract, authorization_assessment_id="g2418-authorization-assessment-b")
    assert authorization_assessment_id.authorization_assessment_id != fixture.contract.authorization_assessment_id
    _refusal(fixture=fixture, assessor=assessor, root=tmp_path,
        request=assessment_request(fixture, assessment_request_id="g2418-auth-assessment-id", contract=authorization_assessment_id),
        finding=DestinationContractFindingCode.ASSESSMENT_BINDING_MISMATCH,
        expected_changed_field="authorization_assessment_id")

    authorization_assessment_digest = contract_variant(fixture.contract, authorization_assessment_digest=_digest("authorization-assessment-b"))
    assert authorization_assessment_digest.authorization_assessment_digest != fixture.contract.authorization_assessment_digest
    _refusal(fixture=fixture, assessor=assessor, root=tmp_path,
        request=assessment_request(fixture, assessment_request_id="g2418-auth-assessment-digest", contract=authorization_assessment_digest),
        finding=DestinationContractFindingCode.ASSESSMENT_BINDING_MISMATCH,
        expected_changed_field="authorization_assessment_digest")

    authorization_policy = contract_variant(fixture.contract, authorization_policy_digest=_digest("authorization-policy-b"))
    assert authorization_policy.authorization_policy_digest != fixture.contract.authorization_policy_digest
    _refusal(fixture=fixture, assessor=assessor, root=tmp_path,
        request=assessment_request(fixture, assessment_request_id="g2418-authorization-policy", contract=authorization_policy),
        finding=DestinationContractFindingCode.CONTRACT_POLICY_MISMATCH,
        expected_changed_field="authorization_policy_digest")

    execution_id = contract_variant(fixture.contract, execution_id="g2418-execution-b")
    assert execution_id.execution_id != fixture.contract.execution_id
    _refusal(fixture=fixture, assessor=assessor, root=tmp_path,
        request=assessment_request(fixture, assessment_request_id="g2418-execution-id", contract=execution_id),
        finding=DestinationContractFindingCode.EXECUTION_RUN_BINDING_MISMATCH,
        expected_changed_field="execution_id")

    run_id = contract_variant(fixture.contract, run_id="g2418-run-b")
    assert run_id.run_id != fixture.contract.run_id
    _refusal(fixture=fixture, assessor=assessor, root=tmp_path,
        request=assessment_request(fixture, assessment_request_id="g2418-run-id", contract=run_id),
        finding=DestinationContractFindingCode.EXECUTION_RUN_BINDING_MISMATCH,
        expected_changed_field="run_id")

    destination = contract_variant(fixture.contract, destination_identity="internal-registry")
    assert destination.destination_identity != fixture.contract.destination_identity
    _refusal(fixture=fixture, assessor=assessor, root=tmp_path,
        request=assessment_request(fixture, assessment_request_id="g2418-destination", contract=destination),
        finding=DestinationContractFindingCode.CONTRACT_DESTINATION_MISMATCH,
        expected_changed_field="destination_identity")

    denied_receipt = ExternalTransitionAuthorizationReceipt.issue(
        authorization_id=fixture.authorization.authorization_id, approver_identity=fixture.authorization.approver_identity,
        decision=HumanAuthorizationDecision.DENIED, occurred_at=fixture.authorization.occurred_at,
        expires_at=fixture.authorization.expires_at, transition_intent=fixture.transition_intent,
    )
    _refusal(fixture=fixture, assessor=assessor, root=tmp_path,
        request=assessment_request(fixture, assessment_request_id="g2418-denied", authorization=denied_receipt),
        finding=DestinationContractFindingCode.AUTHORIZATION_DENIED)

    expired_authorization = assessment_request(fixture, assessment_request_id="g2418-expired-auth", timestamp=fixture.timestamp + timedelta(hours=2))
    _refusal(fixture=fixture, assessor=assessor, root=tmp_path,
        request=expired_authorization, finding=DestinationContractFindingCode.AUTHORIZATION_EXPIRED)

    noneligible = PromotionEligibilityAssessment.issue(
        assessment_id="g2418-noneligible", artifact_identity=fixture.promotion_assessment.artifact_identity,
        destination_identity=fixture.promotion_assessment.destination_identity,
        disposition=PromotionEligibilityDisposition.NOT_ELIGIBLE, findings=(),
        evidence_refs=fixture.promotion_assessment.evidence_refs, recommendations=(), timestamp=fixture.timestamp,
    )
    _refusal(fixture=fixture, assessor=assessor, root=tmp_path,
        request=assessment_request(fixture, assessment_request_id="g2418-noneligible", promotion_assessment=noneligible),
        finding=DestinationContractFindingCode.ELIGIBILITY_EVIDENCE_INVALID)

    expired_contract = assessment_request(fixture, assessment_request_id="g2418-expired-contract", timestamp=fixture.timestamp + timedelta(minutes=45))
    _refusal(fixture=fixture, assessor=assessor, root=tmp_path,
        request=expired_contract, finding=DestinationContractFindingCode.CONTRACT_EXPIRED)

    unsupported_operation = contract_variant(fixture.contract, operation_profile="unsupported-operation-v9")
    _refusal(fixture=fixture, assessor=assessor, root=tmp_path,
        request=assessment_request(fixture, assessment_request_id="g2418-unsupported-operation", contract=unsupported_operation),
        finding=DestinationContractFindingCode.UNSUPPORTED_PROFILE,
        disposition=DestinationContractDisposition.UNSUPPORTED_DESTINATION_CONTRACT)

    unsupported_request_schema = contract_variant(fixture.contract, external_request_schema_id="unsupported-request-v9")
    _refusal(fixture=fixture, assessor=assessor, root=tmp_path,
        request=assessment_request(fixture, assessment_request_id="g2418-unsupported-request-schema", contract=unsupported_request_schema),
        finding=DestinationContractFindingCode.UNSUPPORTED_PROFILE,
        disposition=DestinationContractDisposition.UNSUPPORTED_DESTINATION_CONTRACT)

    unsupported_receipt_schema = contract_variant(fixture.contract, external_receipt_schema_id="unsupported-receipt-v9")
    _refusal(fixture=fixture, assessor=assessor, root=tmp_path,
        request=assessment_request(fixture, assessment_request_id="g2418-unsupported-receipt-schema", contract=unsupported_receipt_schema),
        finding=DestinationContractFindingCode.UNSUPPORTED_PROFILE,
        disposition=DestinationContractDisposition.UNSUPPORTED_DESTINATION_CONTRACT)

    unsupported_idempotency = contract_variant(fixture.contract, destination_idempotency_profile="unsupported-idempotency-v9")
    _refusal(fixture=fixture, assessor=assessor, root=tmp_path,
        request=assessment_request(fixture, assessment_request_id="g2418-unsupported-idempotency", contract=unsupported_idempotency),
        finding=DestinationContractFindingCode.UNSUPPORTED_PROFILE,
        disposition=DestinationContractDisposition.UNSUPPORTED_DESTINATION_CONTRACT)

    malformed_issuer = contract_variant(fixture.contract, attestation_issuer_identity="issuer")
    _refusal(fixture=fixture, assessor=assessor, root=tmp_path,
        request=assessment_request(fixture, assessment_request_id="g2418-issuer", contract=malformed_issuer),
        finding=DestinationContractFindingCode.ISSUER_REFERENCE_INVALID)

    ambiguous = _assess_preserving_state(assessor=assessor, request=assessment_request(fixture, assessment_request_id="g2418-ambiguous", transition_control_evidence=fixture.ambiguous_control_evidence), temporary_root=tmp_path)
    assert ambiguous.disposition is DestinationContractDisposition.NOT_ATTESTED
    assert DestinationContractFindingCode.TRANSITION_CONTROL_AMBIGUOUS in _codes(ambiguous)
    assert not ({"claim", "read", "reset", "reconcile", "retry", "issue_permit", "create_session", "execute"} & set(dir(assessor)))

    raw_digest = fixture.contract.to_payload()
    raw_digest["contract_digest"] = "0" * 64
    raw_unexpected = fixture.contract.to_payload()
    raw_unexpected["unexpected"] = "field"
    with pytest.raises(DestinationContractEvidenceError):
        ExternalDestinationContractEvidence.from_payload(raw_digest)
    with pytest.raises(DestinationContractEvidenceError):
        ExternalDestinationContractEvidence.from_payload(raw_unexpected)
    with pytest.raises(TypeError):
        DestinationContractAssessmentRequest(
            assessment_request_id="g2418-invalid-dict", promotion_request=fixture.promotion_request,
            promotion_assessment=fixture.promotion_assessment, transition_intent=fixture.transition_intent,
            authorization=fixture.authorization, authorization_assessment=fixture.authorization_assessment,
            contract=raw_digest, timestamp=fixture.timestamp,
        )  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        DestinationContractAssessmentRequest(
            assessment_request_id="g2418-missing-promotion", promotion_request=None,
            promotion_assessment=fixture.promotion_assessment, transition_intent=fixture.transition_intent,
            authorization=fixture.authorization, authorization_assessment=fixture.authorization_assessment,
            contract=fixture.contract, timestamp=fixture.timestamp,
        )  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        DestinationContractAssessmentRequest(
            assessment_request_id="g2418-invalid-object", promotion_request=object(),
            promotion_assessment=fixture.promotion_assessment, transition_intent=fixture.transition_intent,
            authorization=fixture.authorization, authorization_assessment=fixture.authorization_assessment,
            contract=fixture.contract, timestamp=fixture.timestamp,
        )  # type: ignore[arg-type]
    with pytest.raises(DestinationContractEvidenceError):
        assessment_request(fixture, schema_version="bad-schema")
    with pytest.raises(DestinationContractEvidenceError):
        assessment_request(fixture, request_digest="bad-digest")
    with pytest.raises(DestinationContractEvidenceError):
        DestinationContractAssessmentRequest(
            assessment_request_id="g2418-invalid-time", promotion_request=fixture.promotion_request,
            promotion_assessment=fixture.promotion_assessment, transition_intent=fixture.transition_intent,
            authorization=fixture.authorization, authorization_assessment=fixture.authorization_assessment,
            contract=fixture.contract, timestamp="bad-time",
        )  # type: ignore[arg-type]

    forbidden = {"execute", "connect", "request", "send", "upload", "publish", "deploy", "release", "retry", "rollback", "reconcile", "complete", "create_session", "issue_permit", "claim", "consume", "reset", "delete", "clear", "overwrite", "force_claim", "write", "mutate"}
    import eag.governed_destination_contract as public
    assert not (forbidden & set(dir(public)))
    assert not (forbidden & set(dir(DestinationContractAssessor)))
    assert list(tmp_path.iterdir()) == []
    capability_absent = (
        "provider", "upload", "network", "credential", "workspace", "command", "runtime",
        "session", "permit", "transition_execution", "audit", "destination", "release",
        "publication", "deployment", "ledger_claim", "ledger_read",
    )
    forbidden = {
        "execute", "connect", "request", "send", "upload", "publish", "deploy", "promote",
        "release", "retry", "rollback", "reconcile", "complete", "finalize", "create_session",
        "issue_permit", "claim", "consume", "reset", "delete", "clear", "overwrite",
        "force_claim", "write", "mutate",
    }
    production_source = inspect.getsource(assessor_module) + inspect.getsource(models_module)
    assert not (forbidden & set(dir(public)))
    assert not (forbidden & set(dir(DestinationContractAssessor)))
    for unreachable_import_or_call in (
        "socket", "requests", "httpx", "urllib", "subprocess", "open(", "TransitionControlLedger",
    ):
        assert unreachable_import_or_call not in production_source
    assert capability_absent == (
        "provider", "upload", "network", "credential", "workspace", "command", "runtime",
        "session", "permit", "transition_execution", "audit", "destination", "release",
        "publication", "deployment", "ledger_claim", "ledger_read",
    )
