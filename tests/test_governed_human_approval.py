"""Deterministic contracts for G2.4.9 governed human approval evidence."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from test_support.g2_4_8_replay_ledger_fixture import durable_ledger, session_bindings
from test_support.g2_4_9_approval_fixture import (
    UnavailableGovernedApprovalStore,
    approval_gate,
    durable_approval_store,
    record_approval,
)

from eag.chief.intelligence.gateway.models import GatewayPolicy
from eag.governed_activation import (
    ExecutionIsolation,
    ProviderExecutionPolicy,
    admit_governed_activation,
)
from eag.governed_approval import (
    GovernedApprovalDisposition,
    GovernedApprovalRejectionReason,
)
from eag.governed_session import (
    ControlledRuntimeSessionGate,
    SessionDisposition,
    SessionRejectionReason,
)


def _session_gate(tmp_path: Path, bindings):
    approval = approval_gate(durable_approval_store(tmp_path / "approval-store"))
    receipt = record_approval(
        approval,
        bindings,
        approval_id=f"approval-{bindings.runtime_request.execution_id}",
    )
    gate = ControlledRuntimeSessionGate(
        replay_ledger=durable_ledger(tmp_path / "replay-ledger"),
        approval_gate=approval,
    )
    return gate, approval, receipt


def _create(gate, bindings, approval_receipt):
    return gate.create_session(
        activation_receipt=bindings.activation_receipt,
        approval_receipt=approval_receipt,
        activation_request=bindings.activation_request,
        runtime_request=bindings.runtime_request,
        audit_observer=bindings.audit_observer,
        runtime_availability=bindings.runtime_availability,
    )


def test_approved_immutable_receipt_is_durable_and_allows_only_existing_session_creation(
    tmp_path: Path,
) -> None:
    bindings = session_bindings(tmp_path, identity="approval-success")
    gate, _, receipt = _session_gate(tmp_path, bindings)
    recreated_approval = approval_gate(durable_approval_store(tmp_path / "approval-store"))
    recreated_gate = ControlledRuntimeSessionGate(
        replay_ledger=durable_ledger(tmp_path / "replay-ledger"),
        approval_gate=recreated_approval,
    )

    validation = recreated_approval.validate_for_session(
        approval_receipt=receipt,
        activation_receipt=bindings.activation_receipt,
        activation_request=bindings.activation_request,
        runtime_request=bindings.runtime_request,
        audit_observer=bindings.audit_observer,
        runtime_availability=bindings.runtime_availability,
    )
    created = _create(gate, bindings, receipt)
    missing = _create(recreated_gate, bindings, None)

    assert validation is None
    assert created.decision.disposition is SessionDisposition.SESSION_CREATED
    assert missing.decision.reason is SessionRejectionReason.MISSING_HUMAN_APPROVAL
    assert bindings.audit_observer.preflight_calls == 0
    assert bindings.audit_observer.terminal_record_calls == 0


def test_denial_and_exact_request_policy_isolation_and_runtime_bindings_fail_closed(tmp_path: Path) -> None:
    bindings = session_bindings(tmp_path / "bindings", identity="bindings")
    gate, approval, receipt = _session_gate(tmp_path / "bindings", bindings)

    changed_request = replace(bindings.runtime_request, goal="Changed request intent.")
    changed_request_reason = approval.validate_for_session(
        approval_receipt=receipt,
        activation_receipt=bindings.activation_receipt,
        activation_request=bindings.activation_request,
        runtime_request=changed_request,
        audit_observer=bindings.audit_observer,
        runtime_availability=bindings.runtime_availability,
    )

    changed_policy = ProviderExecutionPolicy(
        max_attempts=1,
        allow_fallback=False,
        timeout_ms=31_000,
        max_schema_repair_attempts=0,
        max_total_tokens=1_000,
        max_estimated_cost=0.1,
    )
    changed_policy_activation = replace(bindings.activation_request, provider_policy=changed_policy)
    changed_policy_request = replace(
        bindings.runtime_request,
        gateway_policy=GatewayPolicy(
            max_attempts=1,
            allow_fallback=False,
            timeout_ms=31_000,
            max_schema_repair_attempts=0,
            max_total_tokens=1_000,
            max_estimated_cost=0.1,
        ),
    )
    changed_policy_reason = approval.validate_for_session(
        approval_receipt=receipt,
        activation_receipt=admit_governed_activation(changed_policy_activation),
        activation_request=changed_policy_activation,
        runtime_request=changed_policy_request,
        audit_observer=bindings.audit_observer,
        runtime_availability=bindings.runtime_availability,
    )

    changed_isolation_activation = replace(
        bindings.activation_request,
        isolation=ExecutionIsolation(
            workspace_root=bindings.activation_request.isolation.workspace_root,
            audit_root=tmp_path / "changed-audit",
            source_repository_root=bindings.activation_request.isolation.source_repository_root,
            execution_id=bindings.activation_request.isolation.execution_id,
        ),
    )
    changed_isolation_reason = approval.validate_for_session(
        approval_receipt=receipt,
        activation_receipt=admit_governed_activation(changed_isolation_activation),
        activation_request=changed_isolation_activation,
        runtime_request=bindings.runtime_request,
        audit_observer=bindings.audit_observer,
        runtime_availability=bindings.runtime_availability,
    )
    changed_runtime_reason = approval.validate_for_session(
        approval_receipt=receipt,
        activation_receipt=bindings.activation_receipt,
        activation_request=bindings.activation_request,
        runtime_request=bindings.runtime_request,
        audit_observer=bindings.audit_observer,
        runtime_availability=replace(bindings.runtime_availability, runtime_id="changed-runtime"),
    )

    denied_bindings = session_bindings(tmp_path / "denied", identity="denied")
    denied_approval = approval_gate(durable_approval_store(tmp_path / "denied" / "approval-store"))
    denied_receipt = record_approval(
        denied_approval,
        denied_bindings,
        approval_id="denied-approval",
        disposition=GovernedApprovalDisposition.DENIED,
    )
    denied_gate = ControlledRuntimeSessionGate(
        replay_ledger=durable_ledger(tmp_path / "denied" / "replay-ledger"),
        approval_gate=denied_approval,
    )
    denied = denied_gate.create_session(
        activation_receipt=denied_bindings.activation_receipt,
        approval_receipt=denied_receipt,
        activation_request=denied_bindings.activation_request,
        runtime_request=denied_bindings.runtime_request,
        audit_observer=denied_bindings.audit_observer,
        runtime_availability=denied_bindings.runtime_availability,
    )

    assert changed_request_reason is GovernedApprovalRejectionReason.APPROVAL_BINDING_MISMATCH
    assert changed_policy_reason is GovernedApprovalRejectionReason.APPROVAL_BINDING_MISMATCH
    assert changed_isolation_reason is GovernedApprovalRejectionReason.APPROVAL_BINDING_MISMATCH
    assert changed_runtime_reason is GovernedApprovalRejectionReason.APPROVAL_BINDING_MISMATCH
    assert denied.decision.reason is SessionRejectionReason.HUMAN_APPROVAL_DENIED
    assert not hasattr(gate, "execute")
    assert not hasattr(approval, "create_session")
    assert not hasattr(approval, "invoke")


def test_duplicate_corrupt_and_unavailable_approval_storage_fail_closed(tmp_path: Path) -> None:
    bindings = session_bindings(tmp_path / "duplicate", identity="duplicate")
    _, approval, receipt = _session_gate(tmp_path / "duplicate", bindings)
    duplicate = approval.record(
        approval_id=receipt.approval_id,
        approver_identity=receipt.approver_identity,
        occurred_at=receipt.occurred_at,
        disposition=receipt.disposition,
        activation_receipt=bindings.activation_receipt,
        activation_request=bindings.activation_request,
        runtime_request=bindings.runtime_request,
        audit_observer=bindings.audit_observer,
        runtime_availability=bindings.runtime_availability,
    )

    corrupt_bindings = session_bindings(tmp_path / "corrupt", identity="corrupt")
    corrupt_gate, corrupt_approval, corrupt_receipt = _session_gate(tmp_path / "corrupt", corrupt_bindings)
    corrupt_path = next((tmp_path / "corrupt" / "approval-store").glob("approval-*.json"))
    corrupt_path.write_text("partial", encoding="utf-8")
    corrupt = _create(corrupt_gate, corrupt_bindings, corrupt_receipt)

    unavailable_bindings = session_bindings(tmp_path / "unavailable", identity="unavailable")
    source_approval = approval_gate(durable_approval_store(tmp_path / "unavailable" / "source-store"))
    unavailable_receipt = record_approval(
        source_approval,
        unavailable_bindings,
        approval_id="unavailable-approval",
    )
    unavailable_gate = ControlledRuntimeSessionGate(
        replay_ledger=durable_ledger(tmp_path / "unavailable" / "replay-ledger"),
        approval_gate=approval_gate(
            UnavailableGovernedApprovalStore(control_root=tmp_path / "unavailable" / "offline-store")
        ),
    )
    unavailable = unavailable_gate.create_session(
        activation_receipt=unavailable_bindings.activation_receipt,
        approval_receipt=unavailable_receipt,
        activation_request=unavailable_bindings.activation_request,
        runtime_request=unavailable_bindings.runtime_request,
        audit_observer=unavailable_bindings.audit_observer,
        runtime_availability=unavailable_bindings.runtime_availability,
    )

    assert duplicate.reason is GovernedApprovalRejectionReason.APPROVAL_ID_DUPLICATE
    assert corrupt.decision.reason is SessionRejectionReason.HUMAN_APPROVAL_STORE_CORRUPT
    assert unavailable.decision.reason is SessionRejectionReason.HUMAN_APPROVAL_STORE_UNAVAILABLE
    assert corrupt_approval.validate_for_session(
        approval_receipt=corrupt_receipt,
        activation_receipt=corrupt_bindings.activation_receipt,
        activation_request=corrupt_bindings.activation_request,
        runtime_request=corrupt_bindings.runtime_request,
        audit_observer=corrupt_bindings.audit_observer,
        runtime_availability=corrupt_bindings.runtime_availability,
    ) is GovernedApprovalRejectionReason.APPROVAL_STORE_CORRUPT
