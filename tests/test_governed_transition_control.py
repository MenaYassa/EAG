"""Deterministic unit coverage for G2.4.17 transition-control evidence."""

from __future__ import annotations

import json
import os
from dataclasses import FrozenInstanceError, replace

import pytest
from test_support.g2_4_17_transition_control_fixture import control_fixture, durable_ledger

from eag.governed_transition_control import (
    TransitionControlAssessor,
    TransitionControlDisposition,
    TransitionControlFindingCode,
    TransitionControlRecord,
    TransitionControlRecordState,
)
from eag.governed_transition_control.ledger import (
    TransitionControlClaimDisposition,
    TransitionControlLedgerCorruptionError,
    TransitionControlLedgerUnavailableError,
)


def _codes(decision) -> set[TransitionControlFindingCode]:
    return {finding.code for finding in decision.findings}


def _root(tmp_path, name: str):
    root = tmp_path / name
    root.mkdir()
    return root


def _assess(fixture, ledger, *, decision_id: str, **changes):
    return TransitionControlAssessor().assess(
        decision_id=decision_id,
        request=changes.get("request", fixture.request),
        authorization=changes.get("authorization", fixture.authorization),
        authorization_assessment=changes.get("authorization_assessment", fixture.authorization_assessment),
        ledger=ledger,
        timestamp=fixture.timestamp,
    )


def _record_path(root, control_key: str):
    return root / f"control-{control_key}.json"


def _write_record(root, record: TransitionControlRecord) -> None:
    _record_path(root, record.control_key).write_text(
        json.dumps(record.to_payload(), separators=(",", ":"), sort_keys=True),
        encoding="utf-8",
    )


def test_exact_authorized_evidence_claims_once_and_recreated_ledger_returns_duplicate(tmp_path) -> None:
    root = _root(tmp_path, "control")
    fixture = control_fixture(control_root=root)
    first = _assess(fixture, durable_ledger(root), decision_id="unit-first")
    recreated = _assess(fixture, durable_ledger(root), decision_id="unit-duplicate")

    assert first.disposition is TransitionControlDisposition.CLAIMED
    assert recreated.disposition is TransitionControlDisposition.DUPLICATE
    assert TransitionControlFindingCode.DUPLICATE_CONTROL in _codes(recreated)


def test_same_canonical_key_with_incompatible_complete_binding_is_conflict(tmp_path) -> None:
    root = _root(tmp_path, "complete-binding")
    fixture = control_fixture(control_root=root, identity="complete-binding")
    incompatible = replace(fixture.request, idempotency_key="other-caller-idempotency")
    assert incompatible.control_key == fixture.request.control_key
    assert incompatible.binding_digest != fixture.request.binding_digest
    _write_record(
        root,
        TransitionControlRecord.create(
            control_id="preseed-complete-binding",
            request=incompatible,
            state=TransitionControlRecordState.CLAIMED,
            occurred_at=fixture.timestamp,
        ),
    )

    conflict = _assess(
        fixture,
        durable_ledger(root),
        decision_id="unit-complete-binding-conflict",
    )

    assert conflict.disposition is TransitionControlDisposition.CONFLICT
    assert TransitionControlFindingCode.CONFLICTING_CONTROL in _codes(conflict)


def test_ambiguous_persisted_state_stops_without_retry_or_progression(tmp_path) -> None:
    root = _root(tmp_path, "ambiguous")
    fixture = control_fixture(control_root=root, identity="ambiguous")
    record = TransitionControlRecord.create(
        control_id="preseed-ambiguous",
        request=fixture.request,
        state=TransitionControlRecordState.AMBIGUOUS,
        occurred_at=fixture.timestamp,
    )
    _write_record(root, record)

    decision = _assess(fixture, durable_ledger(root), decision_id="unit-ambiguous")

    assert decision.disposition is TransitionControlDisposition.AMBIGUOUS
    assert TransitionControlFindingCode.AMBIGUOUS_CONTROL in _codes(decision)


def test_altered_authorization_intent_and_policy_evidence_are_not_controllable(tmp_path) -> None:
    root = _root(tmp_path, "binding")
    fixture = control_fixture(control_root=root, identity="binding")
    altered_authorization = _assess(
        fixture,
        durable_ledger(root),
        decision_id="unit-authorization",
        request=replace(fixture.request, authorization_id="other-authorization"),
    )
    altered_intent = _assess(
        fixture,
        durable_ledger(_root(tmp_path, "intent")),
        decision_id="unit-intent",
        request=replace(fixture.request, transition_intent_id="other-intent"),
    )
    altered_policy = _assess(
        fixture,
        durable_ledger(_root(tmp_path, "policy")),
        decision_id="unit-policy",
        request=replace(fixture.request, promotion_policy_digest="0" * 64),
    )

    assert altered_authorization.disposition is TransitionControlDisposition.NOT_CONTROLLABLE
    assert altered_intent.disposition is TransitionControlDisposition.NOT_CONTROLLABLE
    assert altered_policy.disposition is TransitionControlDisposition.NOT_CONTROLLABLE
    assert TransitionControlFindingCode.AUTHORIZATION_BINDING_MISMATCH in _codes(altered_authorization)
    assert TransitionControlFindingCode.TRANSITION_BINDING_MISMATCH in _codes(altered_intent)
    assert TransitionControlFindingCode.POLICY_BINDING_MISMATCH in _codes(altered_policy)


def test_store_fails_closed_for_unavailable_corrupt_incomplete_and_symlinked_state(tmp_path) -> None:
    unavailable_fixture_root = _root(tmp_path, "unavailable-fixture")
    unavailable_fixture = control_fixture(control_root=unavailable_fixture_root, identity="unavailable")
    with pytest.raises(TransitionControlLedgerUnavailableError):
        durable_ledger(tmp_path / "missing").claim(unavailable_fixture.request)

    root = _root(tmp_path, "corrupt")
    fixture = control_fixture(control_root=root, identity="corrupt")
    path = _record_path(root, fixture.request.control_key)
    path.write_text("{", encoding="utf-8")
    with pytest.raises(TransitionControlLedgerCorruptionError):
        durable_ledger(root).read(control_key=fixture.request.control_key)
    path.write_text('{"control_id":"incomplete"}', encoding="utf-8")
    with pytest.raises(TransitionControlLedgerCorruptionError):
        durable_ledger(root).read(control_key=fixture.request.control_key)
    path.unlink()
    os.symlink(root / "missing-record", path)
    with pytest.raises(TransitionControlLedgerCorruptionError):
        durable_ledger(root).read(control_key=fixture.request.control_key)

    lock_root = _root(tmp_path, "lock")
    lock_fixture = control_fixture(control_root=lock_root, identity="lock")
    os.symlink(lock_root / "missing-lock", lock_root / ".g2_4_17_transition_control.lock")
    with pytest.raises(TransitionControlLedgerUnavailableError):
        durable_ledger(lock_root).claim(lock_fixture.request)


def test_records_are_immutable_and_public_api_has_no_operational_authority(tmp_path) -> None:
    root = _root(tmp_path, "immutable")
    fixture = control_fixture(control_root=root, identity="immutable")
    with pytest.raises(FrozenInstanceError):
        fixture.request.artifact_id = "changed"  # type: ignore[misc]

    assessor = TransitionControlAssessor()
    ledger = durable_ledger(root)
    forbidden = (
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
        "issue_permit",
        "create_session",
        "consume_authorization",
        "consume",
        "reset",
        "delete",
        "clear",
        "reconcile",
        "complete",
    )
    for subject in (assessor, ledger):
        for name in forbidden:
            assert not hasattr(subject, name)


def test_atomic_ledger_claim_is_no_overwrite_and_read_only(tmp_path) -> None:
    root = _root(tmp_path, "claim")
    fixture = control_fixture(control_root=root, identity="claim")
    ledger = durable_ledger(root)

    first = ledger.claim(fixture.request)
    second = ledger.claim(fixture.request)

    assert first.disposition is TransitionControlClaimDisposition.CLAIMED
    assert second.disposition is TransitionControlClaimDisposition.DUPLICATE
    assert not hasattr(ledger, "update")
    assert not hasattr(ledger, "overwrite")
    assert not hasattr(ledger, "release")
    assert not hasattr(ledger, "retry")
    assert not hasattr(ledger, "consume")
