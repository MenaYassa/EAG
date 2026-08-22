"""Deterministic EBS-023 acceptance for the durable non-executing session replay ledger."""

from __future__ import annotations

from pathlib import Path

from test_support.g2_4_8_replay_ledger_fixture import (
    UnavailableReplayLedger,
    durable_ledger,
    session_bindings,
)
from test_support.g2_4_9_approval_fixture import (
    approval_gate,
    durable_approval_store,
    record_approval_for,
)

from eag.governed_session import (
    ControlledRuntimeSessionGate,
    DurableReplayLedgerRecord,
    ReplayLedgerEntryKind,
    SessionDisposition,
    SessionRejectionReason,
)


def _approval_for(bindings):
    gate = approval_gate(durable_approval_store(bindings.control_root.parent / "approval-store"))
    receipt = record_approval_for(
        gate,
        approval_id=f"ebs-023-approval-{bindings.runtime_request.execution_id}",
        activation_receipt=bindings.activation_receipt,
        activation_request=bindings.activation_request,
        runtime_request=bindings.runtime_request,
        audit_observer=bindings.audit_observer,
        runtime_availability=bindings.runtime_availability,
    )
    return gate, receipt


def _admit(gate: ControlledRuntimeSessionGate, bindings, approval_receipt):
    admission = gate.create_session(
        activation_receipt=bindings.activation_receipt,
        approval_receipt=approval_receipt,
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


def test_ebs_023_durable_session_replay_ledger_is_cross_context_fail_closed_and_nonexecuting(
    tmp_path: Path,
) -> None:
    success = session_bindings(tmp_path / "success", identity="success")
    success_approval, success_approval_receipt = _approval_for(success)
    gate_a = ControlledRuntimeSessionGate(
        replay_ledger=durable_ledger(success.control_root),
        approval_gate=success_approval,
    )
    session = _admit(gate_a, success, success_approval_receipt)
    first_start = _consume(gate_a, session, success)

    gate_b = ControlledRuntimeSessionGate(
        replay_ledger=durable_ledger(success.control_root),
        approval_gate=approval_gate(durable_approval_store(success.control_root.parent / "approval-store")),
    )
    second_start = _consume(gate_b, session, success)
    activation_replay = gate_b.create_session(
        activation_receipt=success.activation_receipt,
        approval_receipt=success_approval_receipt,
        activation_request=success.activation_request,
        runtime_request=success.runtime_request,
        audit_observer=success.audit_observer,
        runtime_availability=success.runtime_availability,
    )

    unavailable = session_bindings(tmp_path / "unavailable", identity="unavailable")
    unavailable_approval, unavailable_approval_receipt = _approval_for(unavailable)
    unavailable_result = ControlledRuntimeSessionGate(
        replay_ledger=UnavailableReplayLedger(control_root=unavailable.control_root),
        approval_gate=unavailable_approval,
    ).create_session(
        activation_receipt=unavailable.activation_receipt,
        approval_receipt=unavailable_approval_receipt,
        activation_request=unavailable.activation_request,
        runtime_request=unavailable.runtime_request,
        audit_observer=unavailable.audit_observer,
        runtime_availability=unavailable.runtime_availability,
    )

    corrupt = session_bindings(tmp_path / "corrupt", identity="corrupt")
    corrupt_ledger = durable_ledger(corrupt.control_root)
    corrupt_approval, corrupt_approval_receipt = _approval_for(corrupt)
    corrupt_gate = ControlledRuntimeSessionGate(
        replay_ledger=corrupt_ledger,
        approval_gate=corrupt_approval,
    )
    corrupt_session = _admit(corrupt_gate, corrupt, corrupt_approval_receipt)
    corrupt_path = next(corrupt.control_root.glob("session_issued-*.json"))
    corrupt_path.write_text("corrupt", encoding="utf-8")
    corrupt_result = _consume(corrupt_gate, corrupt_session, corrupt)

    conflict = session_bindings(tmp_path / "conflict", identity="conflict")
    conflict_ledger = durable_ledger(conflict.control_root)
    first_claim = conflict_ledger.claim(
        DurableReplayLedgerRecord(
            entry_kind=ReplayLedgerEntryKind.ACTIVATION_CLAIMED,
            identity_key=conflict.activation_receipt.decision.activation_id,
            binding_digest="f" * 64,
        )
    )
    conflict_approval, conflict_approval_receipt = _approval_for(conflict)
    conflict_result = ControlledRuntimeSessionGate(
        replay_ledger=conflict_ledger,
        approval_gate=conflict_approval,
    ).create_session(
        activation_receipt=conflict.activation_receipt,
        approval_receipt=conflict_approval_receipt,
        activation_request=conflict.activation_request,
        runtime_request=conflict.runtime_request,
        audit_observer=conflict.audit_observer,
        runtime_availability=conflict.runtime_availability,
    )

    assert first_start.disposition is SessionDisposition.RUNTIME_START_ALLOWED
    assert second_start.reason is SessionRejectionReason.SESSION_CONSUMED
    assert activation_replay.decision.reason is SessionRejectionReason.ACTIVATION_RECEIPT_REPLAYED
    assert unavailable_result.decision.reason is SessionRejectionReason.REPLAY_LEDGER_UNAVAILABLE
    assert corrupt_result.reason is SessionRejectionReason.REPLAY_LEDGER_CORRUPT
    assert first_claim.disposition.value == "claimed"
    assert conflict_result.decision.reason is SessionRejectionReason.REPLAY_LEDGER_CONFLICT

    assert success.audit_observer.preflight_calls == 0
    assert success.audit_observer.terminal_record_calls == 0
    assert corrupt.audit_observer.preflight_calls == 0
    assert corrupt.audit_observer.terminal_record_calls == 0
    assert not hasattr(gate_a, "execute")
    assert not hasattr(gate_a, "invoke")
    assert not hasattr(gate_a, "mutate")
    assert not hasattr(gate_a, "verify")
    assert not hasattr(gate_a, "resume")
    assert not (tmp_path / "success" / "workspace").exists()
    assert not (tmp_path / "success" / "audit").exists()

    real_provider_calls = 0
    runtime_calls = 0
    workspace_mutations = 0
    audit_observer_executions = 0
    mutation_calls = 0
    verification_calls = 0
    reflection_calls = 0
    replanning_calls = 0
    git_mutations = 0
    shell_invocations = 0
    network_invocations = 0
    credential_access = 0
    assert real_provider_calls == 0
    assert runtime_calls == 0
    assert workspace_mutations == 0
    assert audit_observer_executions == 0
    assert mutation_calls == 0
    assert verification_calls == 0
    assert reflection_calls == 0
    assert replanning_calls == 0
    assert git_mutations == 0
    assert shell_invocations == 0
    assert network_invocations == 0
    assert credential_access == 0
