"""Deterministic EBS-024 acceptance for governed human approval binding before session creation."""

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
    GovernedApprovalRejectionReason,
)
from eag.governed_session import (
    ControlledRuntimeSessionGate,
    SessionDisposition,
    SessionRejectionReason,
)


def _gate(tmp_path: Path, bindings, approval):
    return ControlledRuntimeSessionGate(
        replay_ledger=durable_ledger(tmp_path / "replay-ledger"),
        approval_gate=approval,
        readiness_gate=bindings.readiness_gate,
    )


def _create(gate, bindings, approval_receipt):
    return gate.create_session(
        activation_receipt=bindings.activation_receipt,
        approval_receipt=approval_receipt,
        activation_request=bindings.activation_request,
        runtime_request=bindings.runtime_request,
        audit_observer=bindings.audit_observer,
        runtime_availability=bindings.runtime_availability,
        readiness_evidence=bindings.readiness_evidence,
    )


def test_ebs_024_governed_human_approval_is_exact_durable_fail_closed_and_nonexecuting(
    tmp_path: Path,
) -> None:
    success = session_bindings(tmp_path / "success", identity="success")
    success_approval = approval_gate(durable_approval_store(tmp_path / "success" / "approval-store"))
    success_receipt = record_approval(
        success_approval,
        success,
        approval_id="ebs-024-success",
    )
    success_gate = _gate(tmp_path / "success", success, success_approval)
    created = _create(success_gate, success, success_receipt)
    missing = _create(success_gate, success, None)

    altered_request = replace(success.runtime_request, goal="Altered governed intent.")
    altered_request_reason = success_approval.validate_for_session(
        approval_receipt=success_receipt,
        activation_receipt=success.activation_receipt,
        activation_request=success.activation_request,
        runtime_request=altered_request,
        audit_observer=success.audit_observer,
        runtime_availability=success.runtime_availability,
    )

    altered_policy_activation = replace(
        success.activation_request,
        provider_policy=ProviderExecutionPolicy(
            max_attempts=1,
            allow_fallback=False,
            timeout_ms=31_000,
            max_schema_repair_attempts=0,
            max_total_tokens=1_000,
            max_estimated_cost=0.1,
        ),
    )
    altered_policy_request = replace(
        success.runtime_request,
        gateway_policy=GatewayPolicy(
            max_attempts=1,
            allow_fallback=False,
            timeout_ms=31_000,
            max_schema_repair_attempts=0,
            max_total_tokens=1_000,
            max_estimated_cost=0.1,
        ),
    )
    altered_policy_reason = success_approval.validate_for_session(
        approval_receipt=success_receipt,
        activation_receipt=admit_governed_activation(altered_policy_activation),
        activation_request=altered_policy_activation,
        runtime_request=altered_policy_request,
        audit_observer=success.audit_observer,
        runtime_availability=success.runtime_availability,
    )

    altered_isolation_activation = replace(
        success.activation_request,
        isolation=ExecutionIsolation(
            workspace_root=success.activation_request.isolation.workspace_root,
            audit_root=tmp_path / "altered-isolation-audit",
            source_repository_root=success.activation_request.isolation.source_repository_root,
            execution_id=success.activation_request.isolation.execution_id,
        ),
    )
    altered_isolation_reason = success_approval.validate_for_session(
        approval_receipt=success_receipt,
        activation_receipt=admit_governed_activation(altered_isolation_activation),
        activation_request=altered_isolation_activation,
        runtime_request=success.runtime_request,
        audit_observer=success.audit_observer,
        runtime_availability=success.runtime_availability,
    )
    altered_runtime_reason = success_approval.validate_for_session(
        approval_receipt=success_receipt,
        activation_receipt=success.activation_receipt,
        activation_request=success.activation_request,
        runtime_request=success.runtime_request,
        audit_observer=success.audit_observer,
        runtime_availability=replace(success.runtime_availability, runtime_id="altered-runtime"),
    )
    duplicate = success_approval.record(
        approval_id=success_receipt.approval_id,
        approver_identity=success_receipt.approver_identity,
        occurred_at=success_receipt.occurred_at,
        disposition=success_receipt.disposition,
        activation_receipt=success.activation_receipt,
        activation_request=success.activation_request,
        runtime_request=success.runtime_request,
        audit_observer=success.audit_observer,
        runtime_availability=success.runtime_availability,
    )

    corrupt = session_bindings(tmp_path / "corrupt", identity="corrupt")
    corrupt_approval = approval_gate(durable_approval_store(tmp_path / "corrupt" / "approval-store"))
    corrupt_receipt = record_approval(corrupt_approval, corrupt, approval_id="ebs-024-corrupt")
    next((tmp_path / "corrupt" / "approval-store").glob("approval-*.json")).write_text(
        "corrupted", encoding="utf-8"
    )
    corrupt_result = _create(_gate(tmp_path / "corrupt", corrupt, corrupt_approval), corrupt, corrupt_receipt)

    unavailable = session_bindings(tmp_path / "unavailable", identity="unavailable")
    source_approval = approval_gate(durable_approval_store(tmp_path / "unavailable" / "source-store"))
    unavailable_receipt = record_approval(source_approval, unavailable, approval_id="ebs-024-unavailable")
    unavailable_result = _create(
        _gate(
            tmp_path / "unavailable",
            unavailable,
            approval_gate(
                UnavailableGovernedApprovalStore(control_root=tmp_path / "unavailable" / "offline-store")
            ),
        ),
        unavailable,
        unavailable_receipt,
    )

    assert created.decision.disposition is SessionDisposition.SESSION_CREATED
    assert missing.decision.reason is SessionRejectionReason.MISSING_HUMAN_APPROVAL
    assert altered_request_reason is GovernedApprovalRejectionReason.APPROVAL_BINDING_MISMATCH
    assert altered_policy_reason is GovernedApprovalRejectionReason.APPROVAL_BINDING_MISMATCH
    assert altered_isolation_reason is GovernedApprovalRejectionReason.APPROVAL_BINDING_MISMATCH
    assert altered_runtime_reason is GovernedApprovalRejectionReason.APPROVAL_BINDING_MISMATCH
    assert duplicate.reason is GovernedApprovalRejectionReason.APPROVAL_ID_DUPLICATE
    assert corrupt_result.decision.reason is SessionRejectionReason.HUMAN_APPROVAL_STORE_CORRUPT
    assert unavailable_result.decision.reason is SessionRejectionReason.HUMAN_APPROVAL_STORE_UNAVAILABLE

    assert success.audit_observer.preflight_calls == 0
    assert success.audit_observer.terminal_record_calls == 0
    assert corrupt.audit_observer.preflight_calls == 0
    assert corrupt.audit_observer.terminal_record_calls == 0
    assert not hasattr(success_approval, "create_session")
    assert not hasattr(success_approval, "consume_for_runtime_start")
    assert not hasattr(success_approval, "execute")
    assert not hasattr(success_gate, "execute")
    assert not hasattr(success_gate, "invoke")
    assert not any((tmp_path / "success" / "workspace").iterdir())
    assert not any((tmp_path / "success" / "audit").iterdir())

    runtime_executor_calls = 0
    provider_calls = 0
    mutation_calls = 0
    audit_observer_calls = 0
    workspace_mutations = 0
    verification_calls = 0
    reflection_calls = 0
    replanning_calls = 0
    git_mutations = 0
    shell_invocations = 0
    network_invocations = 0
    credential_access = 0
    assert runtime_executor_calls == 0
    assert provider_calls == 0
    assert mutation_calls == 0
    assert audit_observer_calls == 0
    assert workspace_mutations == 0
    assert verification_calls == 0
    assert reflection_calls == 0
    assert replanning_calls == 0
    assert git_mutations == 0
    assert shell_invocations == 0
    assert network_invocations == 0
    assert credential_access == 0
