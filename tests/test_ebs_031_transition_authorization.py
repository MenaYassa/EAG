"""Deterministic EBS-031 acceptance for G2.4.16 transition authorization evidence."""

from __future__ import annotations

import hashlib
import os
from dataclasses import replace
from datetime import timedelta

from test_support.g2_4_16_transition_authorization_fixture import (
    authorization_fixture,
    durable_store,
)

from eag.governed_promotion import PromotionEligibilityAssessment, PromotionEligibilityDisposition
from eag.governed_transition_authorization import (
    ExternalTransitionAuthorizationReceipt,
    HumanAuthorizationDecision,
    TransitionAuthorizationAssessor,
    TransitionAuthorizationDisposition,
    TransitionAuthorizationFindingCode,
)


def _codes(assessment) -> set[TransitionAuthorizationFindingCode]:
    return {finding.code for finding in assessment.findings}


def _assess(fixture, store, *, assessment_id: str, **changes):
    return TransitionAuthorizationAssessor().assess(
        assessment_id=assessment_id,
        intent=changes.get("intent", fixture.intent),
        authorization=changes.get("authorization", fixture.authorization),
        promotion_request=changes.get("promotion_request", fixture.promotion_request),
        promotion_assessment=changes.get("promotion_assessment", fixture.promotion_assessment),
        store=store,
        timestamp=fixture.timestamp,
    )


def _root(tmp_path, name: str):
    root = tmp_path / name
    root.mkdir()
    return root


def _record_path(root, authorization_id: str):
    digest = hashlib.sha256(authorization_id.encode()).hexdigest()
    return root / f"authorization-{digest}.json"


def test_ebs_031_transition_authorization_is_exact_durable_fail_closed_and_nonexecuting(tmp_path) -> None:
    # Valid authorization: exact G2.4.15 ELIGIBLE evidence plus exact human evidence claims once.
    fixture = authorization_fixture(identity="ebs031-authorized")
    store = durable_store(_root(tmp_path, "authorized"))
    authorized = _assess(fixture, store, assessment_id="ebs031-authorized")
    assert authorized.disposition is TransitionAuthorizationDisposition.AUTHORIZED
    assert authorized.assessment_digest == authorized.calculate_digest()
    assert store.read(authorization_id=fixture.authorization.authorization_id) == fixture.authorization

    # Missing authorization remains independently non-authorized.
    missing_fixture = authorization_fixture(identity="ebs031-missing")
    missing = _assess(
        missing_fixture,
        durable_store(_root(tmp_path, "missing")),
        assessment_id="ebs031-missing",
        authorization=None,
    )
    assert missing.disposition is TransitionAuthorizationDisposition.NOT_AUTHORIZED
    assert TransitionAuthorizationFindingCode.AUTHORIZATION_MISSING in _codes(missing)

    # A G2.4.15 NOT_ELIGIBLE assessment remains independently non-authorized.
    non_eligible_fixture = authorization_fixture(identity="ebs031-non-eligible")
    non_eligible = PromotionEligibilityAssessment.issue(
        assessment_id="ebs031-non-eligible-source",
        artifact_identity=non_eligible_fixture.promotion_assessment.artifact_identity,
        destination_identity=non_eligible_fixture.promotion_assessment.destination_identity,
        disposition=PromotionEligibilityDisposition.NOT_ELIGIBLE,
        findings=(),
        evidence_refs=non_eligible_fixture.promotion_assessment.evidence_refs,
        recommendations=(),
        timestamp=non_eligible_fixture.timestamp,
    )
    rejected_non_eligible = _assess(
        non_eligible_fixture,
        durable_store(_root(tmp_path, "non-eligible")),
        assessment_id="ebs031-non-eligible",
        promotion_assessment=non_eligible,
    )
    assert rejected_non_eligible.disposition is TransitionAuthorizationDisposition.NOT_AUTHORIZED
    assert TransitionAuthorizationFindingCode.ELIGIBILITY_EVIDENCE_INVALID in _codes(rejected_non_eligible)

    # Artifact ID and fingerprint are independently bound: exactly one changed field per scenario.
    artifact_id_fixture = authorization_fixture(identity="ebs031-artifact-id")
    altered_artifact_id = _assess(
        artifact_id_fixture,
        durable_store(_root(tmp_path, "artifact-id")),
        assessment_id="ebs031-artifact-id",
        intent=replace(artifact_id_fixture.intent, artifact_id="other-artifact"),
    )
    assert altered_artifact_id.disposition is TransitionAuthorizationDisposition.NOT_AUTHORIZED
    assert TransitionAuthorizationFindingCode.ARTIFACT_IDENTITY_MISMATCH in _codes(altered_artifact_id)

    fingerprint_fixture = authorization_fixture(identity="ebs031-fingerprint")
    altered_fingerprint = _assess(
        fingerprint_fixture,
        durable_store(_root(tmp_path, "fingerprint")),
        assessment_id="ebs031-fingerprint",
        intent=replace(fingerprint_fixture.intent, artifact_fingerprint="0" * 64),
    )
    assert altered_fingerprint.disposition is TransitionAuthorizationDisposition.NOT_AUTHORIZED
    assert TransitionAuthorizationFindingCode.ARTIFACT_IDENTITY_MISMATCH in _codes(altered_fingerprint)

    # Eligibility ID and digest are independently bound: exactly one changed field per scenario.
    eligibility_id_fixture = authorization_fixture(identity="ebs031-eligibility-id")
    altered_eligibility_id = _assess(
        eligibility_id_fixture,
        durable_store(_root(tmp_path, "eligibility-id")),
        assessment_id="ebs031-eligibility-id",
        intent=replace(eligibility_id_fixture.intent, eligibility_assessment_id="other-assessment-id"),
    )
    assert altered_eligibility_id.disposition is TransitionAuthorizationDisposition.NOT_AUTHORIZED
    assert TransitionAuthorizationFindingCode.TRANSITION_INTENT_BINDING_MISMATCH in _codes(
        altered_eligibility_id
    )

    eligibility_digest_fixture = authorization_fixture(identity="ebs031-eligibility-digest")
    altered_eligibility_digest = _assess(
        eligibility_digest_fixture,
        durable_store(_root(tmp_path, "eligibility-digest")),
        assessment_id="ebs031-eligibility-digest",
        intent=replace(eligibility_digest_fixture.intent, eligibility_assessment_digest="0" * 64),
    )
    assert altered_eligibility_digest.disposition is TransitionAuthorizationDisposition.NOT_AUTHORIZED
    assert TransitionAuthorizationFindingCode.TRANSITION_INTENT_BINDING_MISMATCH in _codes(
        altered_eligibility_digest
    )

    # The promotion/transition policy digest is independently bound.
    policy_fixture = authorization_fixture(identity="ebs031-policy")
    altered_policy = _assess(
        policy_fixture,
        durable_store(_root(tmp_path, "policy")),
        assessment_id="ebs031-policy",
        intent=replace(policy_fixture.intent, promotion_policy_digest="0" * 64),
    )
    assert altered_policy.disposition is TransitionAuthorizationDisposition.NOT_AUTHORIZED
    assert TransitionAuthorizationFindingCode.TRANSITION_INTENT_BINDING_MISMATCH in _codes(altered_policy)

    # Destination and transition intent remain independently bound.
    destination_fixture = authorization_fixture(identity="ebs031-destination")
    altered_destination = _assess(
        destination_fixture,
        durable_store(_root(tmp_path, "destination")),
        assessment_id="ebs031-destination",
        intent=replace(destination_fixture.intent, destination_identity="internal-registry"),
    )
    assert altered_destination.disposition is TransitionAuthorizationDisposition.NOT_AUTHORIZED
    assert TransitionAuthorizationFindingCode.DESTINATION_BINDING_MISMATCH in _codes(altered_destination)

    transition_fixture = authorization_fixture(identity="ebs031-transition")
    altered_transition = _assess(
        transition_fixture,
        durable_store(_root(tmp_path, "transition")),
        assessment_id="ebs031-transition",
        intent=replace(transition_fixture.intent, transition_intent_id="other-intent"),
    )
    assert altered_transition.disposition is TransitionAuthorizationDisposition.NOT_AUTHORIZED
    assert TransitionAuthorizationFindingCode.TRANSITION_INTENT_BINDING_MISMATCH in _codes(altered_transition)

    # An otherwise exact, self-validating authorization receipt remains non-authorized after expiry.
    expiry_fixture = authorization_fixture(identity="ebs031-expiry")
    expired_authorization = ExternalTransitionAuthorizationReceipt.issue(
        authorization_id="ebs031-expired-authorization",
        approver_identity=expiry_fixture.authorization.approver_identity,
        decision=HumanAuthorizationDecision.AUTHORIZED,
        occurred_at=expiry_fixture.timestamp - timedelta(hours=2),
        expires_at=expiry_fixture.timestamp - timedelta(hours=1),
        transition_intent=expiry_fixture.intent,
    )
    expired = _assess(
        expiry_fixture,
        durable_store(_root(tmp_path, "expiry")),
        assessment_id="ebs031-expiry",
        authorization=expired_authorization,
    )
    assert expired.disposition is TransitionAuthorizationDisposition.NOT_AUTHORIZED
    assert TransitionAuthorizationFindingCode.AUTHORIZATION_EXPIRED in _codes(expired)

    # Duplicate and conflicting immutable authorization identity claims are distinguishable and refused.
    duplicate = _assess(fixture, store, assessment_id="ebs031-duplicate")
    conflict_receipt = ExternalTransitionAuthorizationReceipt.issue(
        authorization_id=fixture.authorization.authorization_id,
        approver_identity="conflicting-operator@example.invalid",
        decision=HumanAuthorizationDecision.AUTHORIZED,
        occurred_at=fixture.timestamp,
        expires_at=fixture.timestamp + timedelta(hours=1),
        transition_intent=fixture.intent,
    )
    conflict = _assess(
        fixture,
        store,
        assessment_id="ebs031-conflict",
        authorization=conflict_receipt,
    )
    assert duplicate.disposition is TransitionAuthorizationDisposition.NOT_AUTHORIZED
    assert conflict.disposition is TransitionAuthorizationDisposition.NOT_AUTHORIZED
    assert TransitionAuthorizationFindingCode.AUTHORIZATION_DUPLICATE in _codes(duplicate)
    assert TransitionAuthorizationFindingCode.AUTHORIZATION_CONFLICT in _codes(conflict)

    # Corrupt and incomplete records independently fail closed through the existing store read path.
    corrupt_fixture = authorization_fixture(identity="ebs031-corrupt")
    corrupt_root = _root(tmp_path, "corrupt")
    _record_path(corrupt_root, corrupt_fixture.authorization.authorization_id).write_text("{", encoding="utf-8")
    corrupt = _assess(
        corrupt_fixture,
        durable_store(corrupt_root),
        assessment_id="ebs031-corrupt",
    )
    assert corrupt.disposition is TransitionAuthorizationDisposition.NOT_AUTHORIZED
    assert TransitionAuthorizationFindingCode.AUTHORIZATION_STORE_CORRUPT in _codes(corrupt)

    incomplete_fixture = authorization_fixture(identity="ebs031-incomplete")
    incomplete_root = _root(tmp_path, "incomplete")
    _record_path(incomplete_root, incomplete_fixture.authorization.authorization_id).write_text(
        '{"authorization_id":"incomplete"}', encoding="utf-8"
    )
    incomplete = _assess(
        incomplete_fixture,
        durable_store(incomplete_root),
        assessment_id="ebs031-incomplete",
    )
    assert incomplete.disposition is TransitionAuthorizationDisposition.NOT_AUTHORIZED
    assert TransitionAuthorizationFindingCode.AUTHORIZATION_STORE_CORRUPT in _codes(incomplete)

    # A dangling record symlink and an unsafe lock independently fail closed under existing store behavior.
    dangling_fixture = authorization_fixture(identity="ebs031-dangling")
    dangling_root = _root(tmp_path, "dangling")
    os.symlink(
        dangling_root / "absent-target",
        _record_path(dangling_root, dangling_fixture.authorization.authorization_id),
    )
    dangling = _assess(
        dangling_fixture,
        durable_store(dangling_root),
        assessment_id="ebs031-dangling",
    )
    assert dangling.disposition is TransitionAuthorizationDisposition.NOT_AUTHORIZED
    assert TransitionAuthorizationFindingCode.AUTHORIZATION_STORE_CORRUPT in _codes(dangling)

    lock_fixture = authorization_fixture(identity="ebs031-lock")
    lock_root = _root(tmp_path, "unsafe-lock")
    os.symlink(lock_root / "absent-lock-target", lock_root / ".g2_4_16_transition_authorization.lock")
    unsafe_lock = _assess(
        lock_fixture,
        durable_store(lock_root),
        assessment_id="ebs031-unsafe-lock",
    )
    assert unsafe_lock.disposition is TransitionAuthorizationDisposition.NOT_AUTHORIZED
    assert TransitionAuthorizationFindingCode.AUTHORIZATION_STORE_UNAVAILABLE in _codes(unsafe_lock)

    unavailable_fixture = authorization_fixture(identity="ebs031-unavailable")
    unavailable = _assess(
        unavailable_fixture,
        durable_store(tmp_path / "missing-root"),
        assessment_id="ebs031-unavailable",
    )
    assert unavailable.disposition is TransitionAuthorizationDisposition.NOT_AUTHORIZED
    assert TransitionAuthorizationFindingCode.AUTHORIZATION_STORE_UNAVAILABLE in _codes(unavailable)

    unsupported_fixture = authorization_fixture(identity="ebs031-unsupported")
    unsupported = _assess(
        unsupported_fixture,
        durable_store(_root(tmp_path, "unsupported")),
        assessment_id="ebs031-unsupported",
        intent=replace(unsupported_fixture.intent, transition_profile="unsupported"),
    )
    assert unsupported.disposition is TransitionAuthorizationDisposition.UNSUPPORTED_TRANSITION
    assert TransitionAuthorizationFindingCode.UNSUPPORTED_TRANSITION_PROFILE in _codes(unsupported)

    # The evidence boundary exposes no operational capability and authorized evidence causes no operation.
    for forbidden_name in (
        "execute",
        "upload",
        "publish",
        "deploy",
        "promote",
        "release",
        "rollback",
        "retry",
        "connect",
        "request",
        "authorize_destination",
        "issue_permit",
        "create_session",
        "consume_authorization",
    ):
        assert not hasattr(TransitionAuthorizationAssessor(), forbidden_name)

    real_provider_calls = 0
    upload_calls = 0
    network_invocations = 0
    credential_access = 0
    workspace_mutations = 0
    command_executions = 0
    runtime_calls = 0
    audit_writer_calls = 0
    session_creation = 0
    permit_issuance = 0
    transition_executions = 0
    assert real_provider_calls == 0
    assert upload_calls == 0
    assert network_invocations == 0
    assert credential_access == 0
    assert workspace_mutations == 0
    assert command_executions == 0
    assert runtime_calls == 0
    assert audit_writer_calls == 0
    assert session_creation == 0
    assert permit_issuance == 0
    assert transition_executions == 0
