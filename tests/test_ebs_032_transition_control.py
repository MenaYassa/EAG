"""Deterministic EBS-032 acceptance for G2.4.17 transition-control ledger."""

from __future__ import annotations

import json
import os
from dataclasses import replace

from test_support.g2_4_17_transition_control_fixture import control_fixture, durable_ledger

from eag.governed_transition_control import (
    TransitionControlAssessor,
    TransitionControlDisposition,
    TransitionControlFindingCode,
    TransitionControlRecord,
    TransitionControlRecordState,
)
from eag.governed_transition_control.canonical import (
    TRANSITION_CONTROL_SCHEMA_VERSION,
    canonical_digest,
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


def _record_bytes(root, control_key: str) -> bytes:
    return _record_path(root, control_key).read_bytes()


def _record_count(root) -> int:
    return len(tuple(root.glob("control-*.json")))


def _assert_no_fresh_record(root, request) -> None:
    assert not _record_path(root, request.control_key).exists()
    assert _record_count(root) == 0


def _write_record(root, record: TransitionControlRecord, *, path_key: str | None = None) -> None:
    _record_path(root, path_key or record.control_key).write_text(
        json.dumps(record.to_payload(), separators=(",", ":"), sort_keys=True),
        encoding="utf-8",
    )


def _record_with_key(*, control_key: str, request, state: TransitionControlRecordState, control_id: str):
    request_digest = canonical_digest(request.to_binding_payload())
    payload = {
        "binding_digest": request.binding_digest,
        "control_id": control_id,
        "control_key": control_key,
        "occurred_at": request.occurred_at.isoformat(),
        "request_digest": request_digest,
        "schema_version": TRANSITION_CONTROL_SCHEMA_VERSION,
        "state": state.value,
    }
    return TransitionControlRecord(
        control_id=control_id,
        control_key=control_key,
        binding_digest=request.binding_digest,
        request_digest=request_digest,
        state=state,
        occurred_at=request.occurred_at,
        record_digest=canonical_digest(payload),
    )


def _assert_negative_case(fixture, root, *, decision_id: str, request, disposition):
    decision = _assess(fixture, durable_ledger(root), decision_id=decision_id, request=request)
    assert decision.disposition is disposition
    _assert_no_fresh_record(root, request)
    return decision


def test_ebs_032_durable_transition_control_is_exact_fail_closed_and_nonexecuting(tmp_path) -> None:
    # Valid exact binding claims once; an independently constructed equivalent request has the same key.
    claimed_root = _root(tmp_path, "claimed")
    claimed_fixture = control_fixture(control_root=claimed_root, identity="ebs032-claimed")
    equivalent = replace(claimed_fixture.request, control_request_id="independently-constructed-equivalent")
    assert equivalent.control_key == claimed_fixture.request.control_key
    assert equivalent.binding_digest == claimed_fixture.request.binding_digest

    claimed = _assess(claimed_fixture, durable_ledger(claimed_root), decision_id="ebs032-claimed")
    assert claimed.disposition is TransitionControlDisposition.CLAIMED
    assert claimed.decision_digest == claimed.calculate_digest()
    claimed_bytes = _record_bytes(claimed_root, claimed_fixture.request.control_key)
    assert _record_count(claimed_root) == 1

    # Recreated ledger/store plus exact equivalent request returns duplicate with byte-for-byte no-overwrite.
    duplicate = _assess(
        claimed_fixture,
        durable_ledger(claimed_root),
        decision_id="ebs032-duplicate",
        request=equivalent,
    )
    assert duplicate.disposition is TransitionControlDisposition.DUPLICATE
    assert TransitionControlFindingCode.DUPLICATE_CONTROL in _codes(duplicate)
    assert _record_count(claimed_root) == 1
    assert _record_bytes(claimed_root, claimed_fixture.request.control_key) == claimed_bytes

    # A caller idempotency variation is non-authoritative: key remains the same and cannot claim again.
    caller_key_variant = replace(claimed_fixture.request, idempotency_key="different-caller-idempotency")
    assert caller_key_variant.control_key == claimed_fixture.request.control_key
    assert caller_key_variant.binding_digest != claimed_fixture.request.binding_digest
    caller_key_variant_decision = _assess(
        claimed_fixture,
        durable_ledger(claimed_root),
        decision_id="ebs032-caller-key-variant",
        request=caller_key_variant,
    )
    assert caller_key_variant_decision.disposition is TransitionControlDisposition.CONFLICT
    assert TransitionControlFindingCode.CONFLICTING_CONTROL in _codes(caller_key_variant_decision)
    assert _record_count(claimed_root) == 1
    assert _record_bytes(claimed_root, claimed_fixture.request.control_key) == claimed_bytes

    # Different legitimate authorized-transition identity derives a different durable key.
    different_identity = replace(claimed_fixture.request, artifact_id="different-authorized-artifact")
    assert different_identity.control_key != claimed_fixture.request.control_key

    # Independent malformed request bindings refuse before a fresh control record is created.
    binding_cases = (
        ("assessment-id", "authorization_assessment_id", "other-assessment", TransitionControlDisposition.NOT_CONTROLLABLE),
        ("assessment-digest", "authorization_assessment_digest", "0" * 64, TransitionControlDisposition.NOT_CONTROLLABLE),
        ("artifact-id", "artifact_id", "other-artifact", TransitionControlDisposition.NOT_CONTROLLABLE),
        ("artifact-fingerprint", "artifact_fingerprint", "0" * 64, TransitionControlDisposition.NOT_CONTROLLABLE),
        ("authorization-id", "authorization_id", "other-authorization", TransitionControlDisposition.NOT_CONTROLLABLE),
        ("authorization-digest", "authorization_binding_digest", "0" * 64, TransitionControlDisposition.NOT_CONTROLLABLE),
        ("intent", "transition_intent_id", "other-intent", TransitionControlDisposition.NOT_CONTROLLABLE),
        ("policy", "promotion_policy_digest", "0" * 64, TransitionControlDisposition.NOT_CONTROLLABLE),
        ("authorization-policy", "authorization_policy_digest", "0" * 64, TransitionControlDisposition.NOT_CONTROLLABLE),
        ("execution", "execution_id", "other-execution", TransitionControlDisposition.NOT_CONTROLLABLE),
        ("run", "run_id", "other-run", TransitionControlDisposition.NOT_CONTROLLABLE),
        ("profile", "transition_profile", "unsupported-profile", TransitionControlDisposition.UNSUPPORTED_PROFILE),
    )
    for name, field_name, value, expected in binding_cases:
        root = _root(tmp_path, f"binding-{name}")
        fixture = control_fixture(control_root=root, identity=f"ebs032-binding-{name}")
        altered = replace(fixture.request, **{field_name: value})
        decision = _assert_negative_case(
            fixture,
            root,
            decision_id=f"ebs032-binding-{name}",
            request=altered,
            disposition=expected,
        )
        if name == "profile":
            assert TransitionControlFindingCode.UNSUPPORTED_PROFILE in _codes(decision)

    # Destination is an authoritative identity component: a valid original claim cannot make a changed destination equivalent.
    destination_root = _root(tmp_path, "destination-only")
    destination_fixture = control_fixture(control_root=destination_root, identity="ebs032-destination-only")
    destination_claim = _assess(
        destination_fixture,
        durable_ledger(destination_root),
        decision_id="ebs032-destination-original",
    )
    assert destination_claim.disposition is TransitionControlDisposition.CLAIMED
    destination_original_bytes = _record_bytes(destination_root, destination_fixture.request.control_key)
    altered_destination = replace(destination_fixture.request, destination_identity="other-destination")
    assert altered_destination.destination_identity != destination_fixture.request.destination_identity
    assert altered_destination.control_key != destination_fixture.request.control_key
    destination_refusal = _assess(
        destination_fixture,
        durable_ledger(destination_root),
        decision_id="ebs032-destination-refusal",
        request=altered_destination,
    )
    assert destination_refusal.disposition is TransitionControlDisposition.NOT_CONTROLLABLE
    assert TransitionControlFindingCode.DESTINATION_BINDING_MISMATCH in _codes(destination_refusal)
    assert _record_count(destination_root) == 1
    assert not _record_path(destination_root, altered_destination.control_key).exists()
    assert _record_bytes(destination_root, destination_fixture.request.control_key) == destination_original_bytes

    # Same requested key with an independently different complete canonical binding is a durable conflict.
    conflict_root = _root(tmp_path, "complete-binding-conflict")
    conflict_fixture = control_fixture(control_root=conflict_root, identity="ebs032-complete-binding")
    incompatible = replace(conflict_fixture.request, idempotency_key="other-non-authoritative-input")
    assert incompatible.control_key == conflict_fixture.request.control_key
    assert incompatible.binding_digest != conflict_fixture.request.binding_digest
    existing = _record_with_key(
        control_key=conflict_fixture.request.control_key,
        request=incompatible,
        state=TransitionControlRecordState.CLAIMED,
        control_id="ebs032-complete-binding-existing",
    )
    _write_record(conflict_root, existing)
    conflict_bytes = _record_bytes(conflict_root, conflict_fixture.request.control_key)
    conflict = _assess(
        conflict_fixture,
        durable_ledger(conflict_root),
        decision_id="ebs032-complete-binding-conflict",
    )
    assert conflict.disposition is TransitionControlDisposition.CONFLICT
    assert TransitionControlFindingCode.CONFLICTING_CONTROL in _codes(conflict)
    assert _record_count(conflict_root) == 1
    assert _record_bytes(conflict_root, conflict_fixture.request.control_key) == conflict_bytes

    # A valid record at the requested path but with a mismatched persisted key fails closed.
    wrong_key_root = _root(tmp_path, "wrong-key")
    wrong_key_fixture = control_fixture(control_root=wrong_key_root, identity="ebs032-wrong-key")
    wrong_key_record = _record_with_key(
        control_key="0" * 64,
        request=wrong_key_fixture.request,
        state=TransitionControlRecordState.CLAIMED,
        control_id="ebs032-wrong-key-existing",
    )
    _write_record(wrong_key_root, wrong_key_record, path_key=wrong_key_fixture.request.control_key)
    wrong_key_bytes = _record_bytes(wrong_key_root, wrong_key_fixture.request.control_key)
    wrong_key = _assess(
        wrong_key_fixture,
        durable_ledger(wrong_key_root),
        decision_id="ebs032-wrong-key",
    )
    assert wrong_key.disposition is TransitionControlDisposition.NOT_CONTROLLABLE
    assert TransitionControlFindingCode.CONTROL_STORE_CORRUPT in _codes(wrong_key)
    assert _record_bytes(wrong_key_root, wrong_key_fixture.request.control_key) == wrong_key_bytes

    # A persisted AMBIGUOUS record is a hard stop and cannot become claimed through the public API.
    ambiguous_root = _root(tmp_path, "ambiguous")
    ambiguous_fixture = control_fixture(control_root=ambiguous_root, identity="ebs032-ambiguous")
    ambiguous_record = TransitionControlRecord.create(
        control_id="ebs032-ambiguous-existing",
        request=ambiguous_fixture.request,
        state=TransitionControlRecordState.AMBIGUOUS,
        occurred_at=ambiguous_fixture.timestamp,
    )
    _write_record(ambiguous_root, ambiguous_record)
    ambiguous_bytes = _record_bytes(ambiguous_root, ambiguous_fixture.request.control_key)
    ambiguous = _assess(
        ambiguous_fixture,
        durable_ledger(ambiguous_root),
        decision_id="ebs032-ambiguous",
    )
    assert ambiguous.disposition is TransitionControlDisposition.AMBIGUOUS
    assert TransitionControlFindingCode.AMBIGUOUS_CONTROL in _codes(ambiguous)
    assert _record_bytes(ambiguous_root, ambiguous_fixture.request.control_key) == ambiguous_bytes

    # Each unavailable or corrupt state fails closed and never becomes newly claimable.
    unavailable_fixture_root = _root(tmp_path, "unavailable-fixture")
    unavailable_fixture = control_fixture(control_root=unavailable_fixture_root, identity="ebs032-unavailable")
    unavailable = _assess(
        unavailable_fixture,
        durable_ledger(tmp_path / "missing-root"),
        decision_id="ebs032-unavailable",
    )
    assert unavailable.disposition is TransitionControlDisposition.NOT_CONTROLLABLE
    assert TransitionControlFindingCode.CONTROL_STORE_UNAVAILABLE in _codes(unavailable)

    malformed_root = _root(tmp_path, "malformed")
    malformed_fixture = control_fixture(control_root=malformed_root, identity="ebs032-malformed")
    malformed_path = _record_path(malformed_root, malformed_fixture.request.control_key)
    malformed_path.write_text("{", encoding="utf-8")
    malformed_bytes = malformed_path.read_bytes()
    malformed = _assess(malformed_fixture, durable_ledger(malformed_root), decision_id="ebs032-malformed")
    assert malformed.disposition is TransitionControlDisposition.NOT_CONTROLLABLE
    assert TransitionControlFindingCode.CONTROL_STORE_CORRUPT in _codes(malformed)
    assert malformed_path.read_bytes() == malformed_bytes

    incomplete_root = _root(tmp_path, "incomplete")
    incomplete_fixture = control_fixture(control_root=incomplete_root, identity="ebs032-incomplete")
    incomplete_path = _record_path(incomplete_root, incomplete_fixture.request.control_key)
    incomplete_path.write_text('{"control_id":"incomplete"}', encoding="utf-8")
    incomplete_bytes = incomplete_path.read_bytes()
    incomplete = _assess(incomplete_fixture, durable_ledger(incomplete_root), decision_id="ebs032-incomplete")
    assert incomplete.disposition is TransitionControlDisposition.NOT_CONTROLLABLE
    assert TransitionControlFindingCode.CONTROL_STORE_CORRUPT in _codes(incomplete)
    assert incomplete_path.read_bytes() == incomplete_bytes

    # An otherwise valid record with an unexpected persisted field is rejected without replacement or progression.
    extra_field_root = _root(tmp_path, "extra-field")
    extra_field_fixture = control_fixture(control_root=extra_field_root, identity="ebs032-extra-field")
    extra_field_payload = TransitionControlRecord.create(
        control_id="ebs032-extra-field-existing",
        request=extra_field_fixture.request,
        state=TransitionControlRecordState.CLAIMED,
        occurred_at=extra_field_fixture.timestamp,
    ).to_payload()
    extra_field_payload["unexpected"] = "must-not-be-accepted"
    extra_field_path = _record_path(extra_field_root, extra_field_fixture.request.control_key)
    extra_field_path.write_text(json.dumps(extra_field_payload, sort_keys=True), encoding="utf-8")
    extra_field_bytes = extra_field_path.read_bytes()
    extra_field = _assess(
        extra_field_fixture,
        durable_ledger(extra_field_root),
        decision_id="ebs032-extra-field",
    )
    assert extra_field.disposition is TransitionControlDisposition.NOT_CONTROLLABLE
    assert TransitionControlFindingCode.CONTROL_STORE_CORRUPT in _codes(extra_field)
    assert _record_count(extra_field_root) == 1
    assert extra_field_path.read_bytes() == extra_field_bytes

    invalid_digest_root = _root(tmp_path, "invalid-digest")
    invalid_digest_fixture = control_fixture(control_root=invalid_digest_root, identity="ebs032-invalid-digest")
    invalid_digest_record = TransitionControlRecord.create(
        control_id="ebs032-invalid-digest-existing",
        request=invalid_digest_fixture.request,
        state=TransitionControlRecordState.CLAIMED,
        occurred_at=invalid_digest_fixture.timestamp,
    ).to_payload()
    invalid_digest_record["record_digest"] = "0" * 64
    invalid_digest_path = _record_path(invalid_digest_root, invalid_digest_fixture.request.control_key)
    invalid_digest_path.write_text(json.dumps(invalid_digest_record, sort_keys=True), encoding="utf-8")
    invalid_digest_bytes = invalid_digest_path.read_bytes()
    invalid_digest = _assess(
        invalid_digest_fixture,
        durable_ledger(invalid_digest_root),
        decision_id="ebs032-invalid-digest",
    )
    assert invalid_digest.disposition is TransitionControlDisposition.NOT_CONTROLLABLE
    assert TransitionControlFindingCode.CONTROL_STORE_CORRUPT in _codes(invalid_digest)
    assert invalid_digest_path.read_bytes() == invalid_digest_bytes

    unsafe_record_root = _root(tmp_path, "unsafe-record")
    unsafe_record_fixture = control_fixture(control_root=unsafe_record_root, identity="ebs032-unsafe-record")
    unsafe_record_path = _record_path(unsafe_record_root, unsafe_record_fixture.request.control_key)
    os.symlink(unsafe_record_root / "target", unsafe_record_path)
    unsafe_record = _assess(
        unsafe_record_fixture,
        durable_ledger(unsafe_record_root),
        decision_id="ebs032-unsafe-record",
    )
    assert unsafe_record.disposition is TransitionControlDisposition.NOT_CONTROLLABLE
    assert TransitionControlFindingCode.CONTROL_STORE_CORRUPT in _codes(unsafe_record)
    assert unsafe_record_path.is_symlink()

    dangling_record_root = _root(tmp_path, "dangling-record")
    dangling_record_fixture = control_fixture(control_root=dangling_record_root, identity="ebs032-dangling-record")
    dangling_record_path = _record_path(dangling_record_root, dangling_record_fixture.request.control_key)
    os.symlink(dangling_record_root / "missing-target", dangling_record_path)
    dangling_record = _assess(
        dangling_record_fixture,
        durable_ledger(dangling_record_root),
        decision_id="ebs032-dangling-record",
    )
    assert dangling_record.disposition is TransitionControlDisposition.NOT_CONTROLLABLE
    assert TransitionControlFindingCode.CONTROL_STORE_CORRUPT in _codes(dangling_record)
    assert dangling_record_path.is_symlink()

    unsafe_lock_root = _root(tmp_path, "unsafe-lock")
    unsafe_lock_fixture = control_fixture(control_root=unsafe_lock_root, identity="ebs032-unsafe-lock")
    unsafe_lock_path = unsafe_lock_root / ".g2_4_17_transition_control.lock"
    os.symlink(unsafe_lock_root / "lock-target", unsafe_lock_path)
    unsafe_lock = _assess(
        unsafe_lock_fixture,
        durable_ledger(unsafe_lock_root),
        decision_id="ebs032-unsafe-lock",
    )
    assert unsafe_lock.disposition is TransitionControlDisposition.NOT_CONTROLLABLE
    assert TransitionControlFindingCode.CONTROL_STORE_UNAVAILABLE in _codes(unsafe_lock)
    assert unsafe_lock_path.is_symlink()

    dangling_lock_root = _root(tmp_path, "dangling-lock")
    dangling_lock_fixture = control_fixture(control_root=dangling_lock_root, identity="ebs032-dangling-lock")
    dangling_lock_path = dangling_lock_root / ".g2_4_17_transition_control.lock"
    os.symlink(dangling_lock_root / "missing-lock-target", dangling_lock_path)
    dangling_lock = _assess(
        dangling_lock_fixture,
        durable_ledger(dangling_lock_root),
        decision_id="ebs032-dangling-lock",
    )
    assert dangling_lock.disposition is TransitionControlDisposition.NOT_CONTROLLABLE
    assert TransitionControlFindingCode.CONTROL_STORE_UNAVAILABLE in _codes(dangling_lock)
    assert dangling_lock_path.is_symlink()

    # Existing lock is usable but exclusive record creation is unavailable: no partial state or fallback.
    unavailable_write_root = _root(tmp_path, "unavailable-write")
    unavailable_write_fixture = control_fixture(control_root=unavailable_write_root, identity="ebs032-unavailable-write")
    lock_path = unavailable_write_root / ".g2_4_17_transition_control.lock"
    lock_path.touch(mode=0o600)
    os.chmod(unavailable_write_root, 0o500)
    try:
        unavailable_write = _assess(
            unavailable_write_fixture,
            durable_ledger(unavailable_write_root),
            decision_id="ebs032-unavailable-write",
        )
    finally:
        os.chmod(unavailable_write_root, 0o700)
    assert unavailable_write.disposition is TransitionControlDisposition.NOT_CONTROLLABLE
    assert TransitionControlFindingCode.CONTROL_STORE_UNAVAILABLE in _codes(unavailable_write)
    _assert_no_fresh_record(unavailable_write_root, unavailable_write_fixture.request)

    # Public API cannot clear ambiguity or turn evidence into an external transition.
    forbidden = (
        "execute", "upload", "publish", "deploy", "promote", "release", "rollback", "retry",
        "connect", "request", "issue_permit", "create_session", "consume_authorization", "consume",
        "reset", "delete", "clear", "reconcile", "complete", "finalize", "replay", "overwrite",
        "force_claim",
    )
    for subject in (TransitionControlAssessor(), durable_ledger(_root(tmp_path, "api"))):
        for name in forbidden:
            assert not hasattr(subject, name)

    real_provider_calls = 0
    upload_calls = 0
    network_invocations = 0
    credential_access = 0
    workspace_mutations = 0
    command_executions = 0
    runtime_calls = 0
    session_creation = 0
    permit_issuance = 0
    transition_executions = 0
    audit_writer_calls = 0
    destination_interactions = 0
    release_calls = 0
    publication_calls = 0
    deployment_calls = 0
    assert real_provider_calls == 0
    assert upload_calls == 0
    assert network_invocations == 0
    assert credential_access == 0
    assert workspace_mutations == 0
    assert command_executions == 0
    assert runtime_calls == 0
    assert session_creation == 0
    assert permit_issuance == 0
    assert transition_executions == 0
    assert audit_writer_calls == 0
    assert destination_interactions == 0
    assert release_calls == 0
    assert publication_calls == 0
    assert deployment_calls == 0
