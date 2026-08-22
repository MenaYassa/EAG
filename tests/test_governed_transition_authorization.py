"""Deterministic unit coverage for G2.4.16 transition authorization evidence."""

from __future__ import annotations

import hashlib
import os
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta

import pytest
from test_support.g2_4_16_transition_authorization_fixture import (
    authorization_fixture,
    durable_store,
)

from eag.governed_promotion import (
    PromotionEligibilityAssessment,
    PromotionEligibilityDisposition,
)
from eag.governed_transition_authorization import (
    ExternalTransitionAuthorizationReceipt,
    HumanAuthorizationDecision,
    TransitionAuthorizationAssessor,
    TransitionAuthorizationDisposition,
    TransitionAuthorizationFindingCode,
)
from eag.governed_transition_authorization.store import (
    AuthorizationClaimDisposition,
    TransitionAuthorizationStoreCorruptionError,
    TransitionAuthorizationStoreUnavailableError,
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


def test_exact_eligible_evidence_and_authorization_are_durably_authorized(tmp_path) -> None:
    fixture = authorization_fixture()
    control_root = tmp_path / "control"
    control_root.mkdir()
    store = durable_store(control_root)

    assessment = _assess(fixture, store, assessment_id="unit-authorized")

    assert assessment.disposition is TransitionAuthorizationDisposition.AUTHORIZED
    assert assessment.assessment_digest == assessment.calculate_digest()
    assert store.read(authorization_id=fixture.authorization.authorization_id) == fixture.authorization


def test_missing_non_eligible_and_altered_bindings_are_not_authorized(tmp_path) -> None:
    fixture = authorization_fixture(identity="bindings")
    control_root = tmp_path / "control"
    control_root.mkdir()
    store = durable_store(control_root)
    missing = _assess(fixture, store, assessment_id="unit-missing", authorization=None)
    non_eligible = PromotionEligibilityAssessment.issue(
        assessment_id="non-eligible",
        artifact_identity=fixture.promotion_assessment.artifact_identity,
        destination_identity=fixture.promotion_assessment.destination_identity,
        disposition=PromotionEligibilityDisposition.NOT_ELIGIBLE,
        findings=(),
        evidence_refs=fixture.promotion_assessment.evidence_refs,
        recommendations=(),
        timestamp=fixture.timestamp,
    )
    not_eligible = _assess(
        fixture,
        store,
        assessment_id="unit-not-eligible",
        promotion_assessment=non_eligible,
    )
    changed_artifact = _assess(
        fixture,
        store,
        assessment_id="unit-artifact",
        intent=replace(fixture.intent, artifact_fingerprint="0" * 64),
    )
    changed_destination = _assess(
        fixture,
        store,
        assessment_id="unit-destination",
        intent=replace(fixture.intent, destination_identity="internal-registry"),
    )
    changed_transition = _assess(
        fixture,
        store,
        assessment_id="unit-transition",
        intent=replace(fixture.intent, transition_intent_id="other-transition"),
    )

    assert TransitionAuthorizationFindingCode.AUTHORIZATION_MISSING in _codes(missing)
    assert TransitionAuthorizationFindingCode.ELIGIBILITY_EVIDENCE_INVALID in _codes(not_eligible)
    assert TransitionAuthorizationFindingCode.ARTIFACT_IDENTITY_MISMATCH in _codes(changed_artifact)
    assert TransitionAuthorizationFindingCode.DESTINATION_BINDING_MISMATCH in _codes(changed_destination)
    assert TransitionAuthorizationFindingCode.TRANSITION_INTENT_BINDING_MISMATCH in _codes(changed_transition)


def test_denied_expired_and_unsupported_profile_fail_closed(tmp_path) -> None:
    fixture = authorization_fixture(identity="decision")
    control_root = tmp_path / "control"
    control_root.mkdir()
    store = durable_store(control_root)
    denied = ExternalTransitionAuthorizationReceipt.issue(
        authorization_id="denied-auth",
        approver_identity="operator@example.invalid",
        decision=HumanAuthorizationDecision.DENIED,
        occurred_at=fixture.timestamp,
        expires_at=fixture.timestamp + timedelta(hours=1),
        transition_intent=fixture.intent,
    )
    expired = ExternalTransitionAuthorizationReceipt.issue(
        authorization_id="expired-auth",
        approver_identity="operator@example.invalid",
        decision=HumanAuthorizationDecision.AUTHORIZED,
        occurred_at=fixture.timestamp - timedelta(hours=2),
        expires_at=fixture.timestamp - timedelta(hours=1),
        transition_intent=fixture.intent,
    )
    denied_assessment = _assess(fixture, store, assessment_id="unit-denied", authorization=denied)
    expired_assessment = _assess(fixture, store, assessment_id="unit-expired", authorization=expired)
    unsupported = _assess(
        fixture,
        store,
        assessment_id="unit-unsupported",
        intent=replace(fixture.intent, transition_profile="unsupported_profile"),
    )

    assert TransitionAuthorizationFindingCode.AUTHORIZATION_DENIED in _codes(denied_assessment)
    assert TransitionAuthorizationFindingCode.AUTHORIZATION_EXPIRED in _codes(expired_assessment)
    assert unsupported.disposition is TransitionAuthorizationDisposition.UNSUPPORTED_TRANSITION
    assert TransitionAuthorizationFindingCode.UNSUPPORTED_TRANSITION_PROFILE in _codes(unsupported)


def test_duplicate_and_conflicting_authorization_identity_are_refused(tmp_path) -> None:
    fixture = authorization_fixture(identity="duplicates")
    control_root = tmp_path / "control"
    control_root.mkdir()
    store = durable_store(control_root)
    first = _assess(fixture, store, assessment_id="unit-first")
    duplicate = _assess(fixture, store, assessment_id="unit-duplicate")
    conflict_receipt = ExternalTransitionAuthorizationReceipt.issue(
        authorization_id=fixture.authorization.authorization_id,
        approver_identity="other-operator@example.invalid",
        decision=HumanAuthorizationDecision.AUTHORIZED,
        occurred_at=fixture.timestamp,
        expires_at=fixture.timestamp + timedelta(hours=1),
        transition_intent=fixture.intent,
    )
    conflict = _assess(
        fixture,
        store,
        assessment_id="unit-conflict",
        authorization=conflict_receipt,
    )

    assert first.disposition is TransitionAuthorizationDisposition.AUTHORIZED
    assert TransitionAuthorizationFindingCode.AUTHORIZATION_DUPLICATE in _codes(duplicate)
    assert TransitionAuthorizationFindingCode.AUTHORIZATION_CONFLICT in _codes(conflict)


def test_store_rejects_corrupt_incomplete_symlinked_and_unavailable_state(tmp_path) -> None:
    fixture = authorization_fixture(identity="store")
    missing_store = durable_store(tmp_path / "missing")
    with pytest.raises(TransitionAuthorizationStoreUnavailableError):
        missing_store.claim(fixture.authorization)

    unsafe_target = tmp_path / "target"
    unsafe_target.mkdir()
    unsafe_root = tmp_path / "unsafe-root"
    os.symlink(unsafe_target, unsafe_root)
    with pytest.raises(TransitionAuthorizationStoreUnavailableError):
        durable_store(unsafe_root).claim(fixture.authorization)

    control_root = tmp_path / "control"
    control_root.mkdir()
    store = durable_store(control_root)
    record_path = control_root / f"authorization-{hashlib.sha256(fixture.authorization.authorization_id.encode()).hexdigest()}.json"
    record_path.write_text("{", encoding="utf-8")
    with pytest.raises(TransitionAuthorizationStoreCorruptionError):
        store.read(authorization_id=fixture.authorization.authorization_id)
    record_path.write_text('{"authorization_id":"incomplete"}', encoding="utf-8")
    with pytest.raises(TransitionAuthorizationStoreCorruptionError):
        store.read(authorization_id=fixture.authorization.authorization_id)
    record_path.unlink()
    os.symlink(control_root / "other", record_path)
    with pytest.raises(TransitionAuthorizationStoreCorruptionError):
        store.read(authorization_id=fixture.authorization.authorization_id)


def test_receipts_are_immutable_and_public_assessor_has_no_execution_authority() -> None:
    fixture = authorization_fixture(identity="immutable")
    with pytest.raises(FrozenInstanceError):
        fixture.authorization.authorization_id = "changed"  # type: ignore[misc]

    assessor = TransitionAuthorizationAssessor()
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
    ):
        assert not hasattr(assessor, forbidden_name)


def test_store_claim_is_immutable_claim_read_only(tmp_path) -> None:
    fixture = authorization_fixture(identity="claim")
    control_root = tmp_path / "control"
    control_root.mkdir()
    store = durable_store(control_root)

    first = store.claim(fixture.authorization)
    second = store.claim(fixture.authorization)

    assert first.disposition is AuthorizationClaimDisposition.CLAIMED
    assert second.disposition is AuthorizationClaimDisposition.DUPLICATE
    assert not hasattr(store, "update")
    assert not hasattr(store, "delete")
    assert not hasattr(store, "reset")
    assert not hasattr(store, "consume")
    assert not hasattr(store, "release")
