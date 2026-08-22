"""Deterministic contracts for the G2.4.8 durable single-use session replay ledger."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from test_support.g2_4_8_replay_ledger_fixture import (
    UnavailableReplayLedger,
    durable_ledger,
    session_bindings,
)

from eag.governed_session import (
    ControlledRuntimeSessionGate,
    DurableReplayLedgerRecord,
    ReplayLedgerEntryKind,
    SessionDisposition,
    SessionRejectionReason,
)


def _create_session(gate: ControlledRuntimeSessionGate, bindings):
    admission = gate.create_session(
        activation_receipt=bindings.activation_receipt,
        activation_request=bindings.activation_request,
        runtime_request=bindings.runtime_request,
        audit_observer=bindings.audit_observer,
        runtime_availability=bindings.runtime_availability,
    )
    assert admission.session is not None
    return admission.session


def _consume(gate: ControlledRuntimeSessionGate, session, bindings):
    return gate.consume_for_runtime_start(
        session=session,
        activation_receipt=bindings.activation_receipt,
        activation_request=bindings.activation_request,
        runtime_request=bindings.runtime_request,
        audit_observer=bindings.audit_observer,
        runtime_availability=bindings.runtime_availability,
    )


def test_consumed_session_and_activation_receipt_remain_refused_after_gate_recreation(
    tmp_path: Path,
) -> None:
    bindings = session_bindings(tmp_path, identity="durable-replay")
    gate_a = ControlledRuntimeSessionGate(replay_ledger=durable_ledger(bindings.control_root))
    session = _create_session(gate_a, bindings)
    allowed = _consume(gate_a, session, bindings)

    gate_b = ControlledRuntimeSessionGate(replay_ledger=durable_ledger(bindings.control_root))
    consumed_replay = _consume(gate_b, session, bindings)
    activation_replay = gate_b.create_session(
        activation_receipt=bindings.activation_receipt,
        activation_request=bindings.activation_request,
        runtime_request=bindings.runtime_request,
        audit_observer=bindings.audit_observer,
        runtime_availability=bindings.runtime_availability,
    )

    assert allowed.disposition is SessionDisposition.RUNTIME_START_ALLOWED
    assert consumed_replay.reason is SessionRejectionReason.SESSION_CONSUMED
    assert activation_replay.decision.reason is SessionRejectionReason.ACTIVATION_RECEIPT_REPLAYED
    assert bindings.audit_observer.preflight_calls == 0
    assert bindings.audit_observer.terminal_record_calls == 0


def test_unavailable_corrupt_and_conflicting_durable_store_state_fail_closed(tmp_path: Path) -> None:
    unavailable_bindings = session_bindings(tmp_path / "unavailable", identity="unavailable")
    unavailable = ControlledRuntimeSessionGate(
        replay_ledger=UnavailableReplayLedger(control_root=unavailable_bindings.control_root)
    ).create_session(
        activation_receipt=unavailable_bindings.activation_receipt,
        activation_request=unavailable_bindings.activation_request,
        runtime_request=unavailable_bindings.runtime_request,
        audit_observer=unavailable_bindings.audit_observer,
        runtime_availability=unavailable_bindings.runtime_availability,
    )

    corrupt_bindings = session_bindings(tmp_path / "corrupt", identity="corrupt")
    corrupt_ledger = durable_ledger(corrupt_bindings.control_root)
    corrupt_gate = ControlledRuntimeSessionGate(replay_ledger=corrupt_ledger)
    corrupt_session = _create_session(corrupt_gate, corrupt_bindings)
    issued_record = corrupt_ledger.read(
        entry_kind=ReplayLedgerEntryKind.SESSION_ISSUED,
        identity_key=corrupt_session.session_id,
    )
    assert issued_record is not None
    issued_path = next(corrupt_bindings.control_root.glob("session_issued-*.json"))
    issued_path.write_text("not-json", encoding="utf-8")
    corruption_refusal = _consume(corrupt_gate, corrupt_session, corrupt_bindings)

    conflict_bindings = session_bindings(tmp_path / "conflict", identity="conflict")
    conflict_ledger = durable_ledger(conflict_bindings.control_root)
    conflict_claim = conflict_ledger.claim(
        DurableReplayLedgerRecord(
            entry_kind=ReplayLedgerEntryKind.ACTIVATION_CLAIMED,
            identity_key=conflict_bindings.activation_receipt.decision.activation_id,
            binding_digest="0" * 64,
        )
    )
    conflict = ControlledRuntimeSessionGate(replay_ledger=conflict_ledger).create_session(
        activation_receipt=conflict_bindings.activation_receipt,
        activation_request=conflict_bindings.activation_request,
        runtime_request=conflict_bindings.runtime_request,
        audit_observer=conflict_bindings.audit_observer,
        runtime_availability=conflict_bindings.runtime_availability,
    )

    assert unavailable.decision.reason is SessionRejectionReason.REPLAY_LEDGER_UNAVAILABLE
    assert corruption_refusal.reason is SessionRejectionReason.REPLAY_LEDGER_CORRUPT
    assert conflict_claim.disposition.value == "claimed"
    assert conflict.decision.reason is SessionRejectionReason.REPLAY_LEDGER_CONFLICT


def test_altered_session_and_control_root_inside_workspace_are_refused(tmp_path: Path) -> None:
    bindings = session_bindings(tmp_path / "altered", identity="altered")
    gate = ControlledRuntimeSessionGate(replay_ledger=durable_ledger(bindings.control_root))
    session = _create_session(gate, bindings)
    altered = _consume(gate, replace(session, runtime_id="altered-runtime"), bindings)

    isolated = session_bindings(tmp_path / "isolated", identity="isolated")
    workspace_root = isolated.activation_request.isolation.workspace_root
    assert workspace_root is not None
    unsafe_gate = ControlledRuntimeSessionGate(
        replay_ledger=durable_ledger(workspace_root)
    )
    unsafe = unsafe_gate.create_session(
        activation_receipt=isolated.activation_receipt,
        activation_request=isolated.activation_request,
        runtime_request=isolated.runtime_request,
        audit_observer=isolated.audit_observer,
        runtime_availability=isolated.runtime_availability,
    )

    assert altered.reason is SessionRejectionReason.REQUEST_IDENTITY_MISMATCH
    assert unsafe.decision.reason is SessionRejectionReason.REPLAY_LEDGER_ISOLATION_MISMATCH
    assert bindings.audit_observer.preflight_calls == 0
    assert bindings.audit_observer.terminal_record_calls == 0
