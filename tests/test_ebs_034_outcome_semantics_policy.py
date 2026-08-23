"""EBS-034: deterministic governed external outcome-semantics policy evidence rehearsal."""

from __future__ import annotations

import hashlib
import inspect
from dataclasses import FrozenInstanceError, asdict, fields
from datetime import timedelta, timezone
from pathlib import Path

import pytest
from test_support.g2_4_19_outcome_policy_fixture import (
    outcome_assessment_request,
    outcome_policy_fixture,
    policy_variant,
)

import eag.governed_outcome_policy.assessor as assessor_module
import eag.governed_outcome_policy.models as models_module
from eag.governed_outcome_policy import (
    ExternalOutcomeSemanticsPolicyEvidence,
    OutcomePolicyDisposition,
    OutcomePolicyEvidenceError,
    OutcomePolicyFindingCode,
    OutcomeSemanticsAssessmentRequest,
    OutcomeSemanticsAssessor,
)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _codes(result: object) -> set[OutcomePolicyFindingCode]:
    return {finding.code for finding in result.findings}  # type: ignore[union-attr]


def _projection(request: OutcomeSemanticsAssessmentRequest) -> dict[str, object]:
    """Expose every authoritative policy binding through real public evidence."""
    policy = request.policy
    return {
        "destination_contract_id": policy.destination_contract_id,
        "destination_contract_digest": policy.destination_contract_digest,
        "destination_contract_assessment_id": policy.destination_contract_assessment_id,
        "destination_contract_assessment_digest": policy.destination_contract_assessment_digest,
        "destination_identity": policy.destination_identity,
        "destination_operation_profile": policy.destination_operation_profile,
        "external_receipt_schema_id": policy.external_receipt_schema_id,
        "destination_idempotency_profile": policy.destination_idempotency_profile,
        "operation_profile": policy.operation_profile,
        "future_receipt_classes": policy.future_receipt_classes,
        "unknown_outcome_disposition": policy.unknown_outcome_disposition,
        "automatic_retry_disposition": policy.automatic_retry_disposition,
        "automatic_rollback_disposition": policy.automatic_rollback_disposition,
        "completion_verification_requirement": policy.completion_verification_requirement,
        "outcome_policy_id": policy.outcome_policy_id,
        "policy_issued_at": policy.issued_at,
        "policy_expires_at": policy.expires_at,
        "request_timestamp": request.timestamp,
    }


def _assert_exact_one_change(
    *, baseline: OutcomeSemanticsAssessmentRequest,
    variant: OutcomeSemanticsAssessmentRequest, expected_changed_field: str,
) -> None:
    before = _projection(baseline)
    after = _projection(variant)
    assert set(before) == set(after)
    assert after[expected_changed_field] != before[expected_changed_field]
    for field_name in before:
        if field_name != expected_changed_field:
            assert after[field_name] == before[field_name]


def _assert_assessment_immutable(result: object) -> None:
    """Exercise real returned policy assessment and nested finding immutability."""
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
    *, assessor: OutcomeSemanticsAssessor, request: OutcomeSemanticsAssessmentRequest,
    temporary_root: Path,
) -> object:
    """Directly preserve immutable inputs and test-owned filesystem state around real assessment."""
    before_request = request.to_payload()
    before_destination_request = request.destination_contract_request.to_payload()
    before_destination_assessment = asdict(request.destination_contract_assessment)
    before_policy = request.policy.to_payload()
    before_files = tuple(sorted(path.name for path in temporary_root.iterdir()))
    result = assessor.assess(assessment_id=f"{request.assessment_request_id}-assessment", request=request)
    assert request.to_payload() == before_request
    assert request.destination_contract_request.to_payload() == before_destination_request
    assert asdict(request.destination_contract_assessment) == before_destination_assessment
    assert request.policy.to_payload() == before_policy
    assert tuple(sorted(path.name for path in temporary_root.iterdir())) == before_files
    return result


def _refusal(
    *, fixture: object, assessor: OutcomeSemanticsAssessor, root: Path,
    request: OutcomeSemanticsAssessmentRequest, finding: OutcomePolicyFindingCode,
    disposition: OutcomePolicyDisposition = OutcomePolicyDisposition.NOT_ATTESTED,
    expected_changed_field: str | None = None,
) -> object:
    original = outcome_assessment_request(
        fixture,
        assessment_request_id=request.assessment_request_id,
        timestamp=request.timestamp,
    )
    if expected_changed_field is not None:
        _assert_exact_one_change(
            baseline=original, variant=request, expected_changed_field=expected_changed_field
        )
    result = _assess_preserving_state(assessor=assessor, request=request, temporary_root=root)
    assert result.disposition is disposition
    assert finding in _codes(result)
    assert request.request_digest != original.request_digest
    assert original.to_payload() == outcome_assessment_request(
        fixture,
        assessment_request_id=request.assessment_request_id,
        timestamp=request.timestamp,
    ).to_payload()
    _assert_assessment_immutable(result)
    return result


def test_ebs_034_governed_outcome_semantics_policy_boundary(tmp_path: Path) -> None:
    """Directly prove policy evidence only, not an attempt, receipt, outcome, or completion."""
    fixture = outcome_policy_fixture(identity="ebs034")
    assessor = OutcomeSemanticsAssessor()
    valid_request = outcome_assessment_request(fixture, assessment_request_id="g2419-ebs034-valid")
    valid = _assess_preserving_state(assessor=assessor, request=valid_request, temporary_root=tmp_path)
    assert valid.disposition is OutcomePolicyDisposition.OUTCOME_POLICY_ATTESTED
    assert valid.findings == ()
    _assert_assessment_immutable(valid)
    assert f"outcome_policy:{fixture.policy.outcome_policy_id}:{fixture.policy.policy_digest}" in valid.evidence_refs

    public_names = set(dir(__import__("eag.governed_outcome_policy", fromlist=["*"])))
    forbidden_outcome_or_effect_claims = {
        "outcome_attempted", "outcome_succeeded", "outcome_failed", "receipt_received",
        "receipt_verified", "destination_state_changed", "completed", "published", "released",
        "deployed",
    }
    assert not (forbidden_outcome_or_effect_claims & public_names)
    assert not (forbidden_outcome_or_effect_claims & set(dir(valid)))

    equivalent_fixture = outcome_policy_fixture(identity="ebs034")
    equivalent_request = outcome_assessment_request(equivalent_fixture, assessment_request_id="g2419-ebs034-valid")
    equivalent = _assess_preserving_state(assessor=assessor, request=equivalent_request, temporary_root=tmp_path)
    assert equivalent_fixture.policy.to_payload() == fixture.policy.to_payload()
    assert equivalent_fixture.policy.policy_digest == fixture.policy.policy_digest
    assert equivalent_request.to_payload() == valid_request.to_payload()
    assert equivalent_request.request_digest == valid_request.request_digest
    assert equivalent.assessment_digest == valid.assessment_digest

    offset_request = outcome_assessment_request(
        fixture, assessment_request_id="g2419-ebs034-valid",
        timestamp=fixture.timestamp.astimezone(timezone(timedelta(hours=3))),
    )
    assert offset_request.timestamp == valid_request.timestamp
    assert offset_request.to_payload() == valid_request.to_payload()
    assert offset_request.request_digest == valid_request.request_digest

    policy_b = policy_variant(fixture.policy, outcome_policy_id="g2419-outcome-policy-ebs034-b")
    policy_b_request = outcome_assessment_request(
        fixture, assessment_request_id="g2419-policy-self-identity", policy=policy_b
    )
    policy_b_result = _assess_preserving_state(
        assessor=assessor, request=policy_b_request, temporary_root=tmp_path
    )
    _assert_exact_one_change(
        baseline=valid_request,
        variant=policy_b_request,
        expected_changed_field="outcome_policy_id",
    )
    assert policy_b.outcome_policy_id != fixture.policy.outcome_policy_id
    assert policy_b.policy_digest != fixture.policy.policy_digest
    assert policy_b.calculate_digest() == policy_b.policy_digest
    assert policy_b_result.disposition is OutcomePolicyDisposition.OUTCOME_POLICY_ATTESTED
    assert policy_b_result.policy_id == policy_b.outcome_policy_id
    assert not ({"select", "precedence", "reconcile"} & set(dir(assessor)))

    cases = (
        ("destination_contract_id", "g2419-contract-b", OutcomePolicyFindingCode.CONTRACT_BINDING_MISMATCH, OutcomePolicyDisposition.NOT_ATTESTED),
        ("destination_contract_digest", _digest("contract-b"), OutcomePolicyFindingCode.CONTRACT_BINDING_MISMATCH, OutcomePolicyDisposition.NOT_ATTESTED),
        ("destination_contract_assessment_id", "g2419-contract-assessment-b", OutcomePolicyFindingCode.CONTRACT_BINDING_MISMATCH, OutcomePolicyDisposition.NOT_ATTESTED),
        ("destination_contract_assessment_digest", _digest("contract-assessment-b"), OutcomePolicyFindingCode.CONTRACT_BINDING_MISMATCH, OutcomePolicyDisposition.NOT_ATTESTED),
        ("destination_identity", "internal-registry", OutcomePolicyFindingCode.DESTINATION_BINDING_MISMATCH, OutcomePolicyDisposition.NOT_ATTESTED),
        ("destination_operation_profile", "unsupported-operation-v9", OutcomePolicyFindingCode.PROFILE_BINDING_MISMATCH, OutcomePolicyDisposition.NOT_ATTESTED),
        ("external_receipt_schema_id", "unsupported-receipt-v9", OutcomePolicyFindingCode.PROFILE_BINDING_MISMATCH, OutcomePolicyDisposition.NOT_ATTESTED),
        ("destination_idempotency_profile", "unsupported-idempotency-v9", OutcomePolicyFindingCode.PROFILE_BINDING_MISMATCH, OutcomePolicyDisposition.NOT_ATTESTED),
        ("operation_profile", "unsupported-outcome-v9", OutcomePolicyFindingCode.UNSUPPORTED_OUTCOME_PROFILE, OutcomePolicyDisposition.UNSUPPORTED_OUTCOME_POLICY),
        ("future_receipt_classes", ("outcome_unknown_v1",), OutcomePolicyFindingCode.UNSUPPORTED_OUTCOME_PROFILE, OutcomePolicyDisposition.UNSUPPORTED_OUTCOME_POLICY),
        ("unknown_outcome_disposition", "automatic_progress_allowed", OutcomePolicyFindingCode.UNSAFE_UNKNOWN_OUTCOME_SEMANTICS, OutcomePolicyDisposition.NOT_ATTESTED),
        ("automatic_retry_disposition", "allowed", OutcomePolicyFindingCode.AUTOMATIC_RETRY_FORBIDDEN, OutcomePolicyDisposition.NOT_ATTESTED),
        ("automatic_rollback_disposition", "allowed", OutcomePolicyFindingCode.AUTOMATIC_ROLLBACK_FORBIDDEN, OutcomePolicyDisposition.NOT_ATTESTED),
        ("completion_verification_requirement", "unverified_completion_allowed", OutcomePolicyFindingCode.UNVERIFIED_COMPLETION_FORBIDDEN, OutcomePolicyDisposition.NOT_ATTESTED),
    )
    for index, (field, value, finding, disposition) in enumerate(cases):
        policy = policy_variant(fixture.policy, **{field: value})
        request = outcome_assessment_request(
            fixture, assessment_request_id=f"g2419-{field}-{index}", policy=policy
        )
        _refusal(
            fixture=fixture, assessor=assessor, root=tmp_path, request=request,
            finding=finding, disposition=disposition, expected_changed_field=field,
        )

    expired = policy_variant(fixture.policy, expires_at=fixture.timestamp + timedelta(minutes=1))
    expired_request = outcome_assessment_request(
        fixture,
        assessment_request_id="g2419-expired",
        policy=expired,
        timestamp=fixture.timestamp + timedelta(minutes=2),
    )
    _refusal(
        fixture=fixture,
        assessor=assessor,
        root=tmp_path,
        request=expired_request,
        finding=OutcomePolicyFindingCode.POLICY_EXPIRED,
        expected_changed_field="policy_expires_at",
    )

    nonattested = fixture.destination_assessment.__class__.issue(
        assessment_id="g2419-nonattested", destination_identity=fixture.destination_assessment.destination_identity,
        contract_id=fixture.destination_assessment.contract_id,
        disposition=fixture.destination_assessment.disposition.NOT_ATTESTED,
        findings=(), evidence_refs=fixture.destination_assessment.evidence_refs,
        recommendations=(), timestamp=fixture.timestamp,
    )
    _refusal(
        fixture=fixture, assessor=assessor, root=tmp_path,
        request=outcome_assessment_request(
            fixture, assessment_request_id="g2419-nonattested", destination_assessment=nonattested
        ),
        finding=OutcomePolicyFindingCode.CONTRACT_ASSESSMENT_INVALID,
    )

    ambiguous_request = outcome_assessment_request(
        fixture, assessment_request_id="g2419-ambiguous",
        transition_control_evidence=fixture.destination_fixture.ambiguous_control_evidence,
    )
    ambiguous = _assess_preserving_state(assessor=assessor, request=ambiguous_request, temporary_root=tmp_path)
    assert ambiguous.disposition is OutcomePolicyDisposition.NOT_ATTESTED
    assert OutcomePolicyFindingCode.TRANSITION_CONTROL_AMBIGUOUS in _codes(ambiguous)
    _assert_assessment_immutable(ambiguous)
    assert not ({"claim", "read", "consume", "reset", "release", "reconcile", "retry", "execute"} & set(dir(assessor)))

    before_files = tuple(sorted(path.name for path in tmp_path.iterdir()))
    raw_digest = fixture.policy.to_payload()
    raw_digest["policy_digest"] = "0" * 64
    raw_unexpected = fixture.policy.to_payload()
    raw_unexpected["unexpected"] = "field"
    raw_schema = fixture.policy.to_payload()
    raw_schema["schema_version"] = "unsupported-outcome-policy-schema"
    raw_timestamp = fixture.policy.to_payload()
    raw_timestamp["issued_at"] = "malformed-issued-at"
    for invalid_payload in (raw_digest, raw_unexpected, raw_schema, raw_timestamp):
        snapshot = dict(invalid_payload)
        with pytest.raises(OutcomePolicyEvidenceError):
            ExternalOutcomeSemanticsPolicyEvidence.from_payload(invalid_payload)
        assert invalid_payload == snapshot
        assert tuple(sorted(path.name for path in tmp_path.iterdir())) == before_files
    with pytest.raises(TypeError):
        OutcomeSemanticsAssessmentRequest(
            assessment_request_id="g2419-invalid-request", destination_contract_request=object(),
            destination_contract_assessment=fixture.destination_assessment, policy=fixture.policy,
            timestamp=fixture.timestamp,
        )
    with pytest.raises(TypeError):
        OutcomeSemanticsAssessmentRequest(
            assessment_request_id="g2419-missing-policy",
            destination_contract_request=fixture.destination_request,
            destination_contract_assessment=fixture.destination_assessment,
            timestamp=fixture.timestamp,
        )
    assert tuple(sorted(path.name for path in tmp_path.iterdir())) == before_files

    forbidden = {
        "execute", "connect", "request", "send", "upload", "publish", "deploy", "promote",
        "release", "retry", "rollback", "reconcile", "complete", "finalize", "create_session",
        "issue_permit", "claim", "read", "consume", "reset", "delete", "clear", "overwrite",
        "force_claim", "write", "mutate",
    }
    source = inspect.getsource(assessor_module) + inspect.getsource(models_module)
    public = __import__("eag.governed_outcome_policy", fromlist=["*"])
    assert not (forbidden & set(dir(public)))
    assert not (forbidden & set(dir(OutcomeSemanticsAssessor)))
    for unreachable_import_or_call in (
        "socket", "requests", "httpx", "urllib", "subprocess", "open(", "TransitionControlLedger",
    ):
        assert unreachable_import_or_call not in source
    assert list(tmp_path.iterdir()) == []
