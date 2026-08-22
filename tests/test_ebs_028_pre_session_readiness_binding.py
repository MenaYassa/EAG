"""Deterministic EBS-028 acceptance for G2.4.13 pre-session readiness binding."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from test_support.g2_4_8_replay_ledger_fixture import durable_ledger, session_bindings
from test_support.g2_4_9_approval_fixture import (
    approval_gate,
    durable_approval_store,
    record_approval,
)

from eag.governed_invocation import (
    ControlledRuntimeInvocationRequest,
    ControlledRuntimeInvoker,
    InvocationDisposition,
    InvocationRejectionReason,
    RuntimeExecutorBinding,
)
from eag.governed_session import (
    ControlledRuntimeSessionGate,
    ReadinessDisposition,
    ReplayLedgerEntryKind,
    SessionDisposition,
    SessionRejectionReason,
)


@dataclass
class _CountingExecutor:
    calls: int = 0

    def execute(self, request: object) -> object:
        del request
        self.calls += 1
        raise AssertionError("EBS-028 altered invocation binding must refuse before dispatch")


def _session_gate(tmp_path: Path, bindings, approval):
    ledger = durable_ledger(tmp_path / "replay-ledger")
    gate = ControlledRuntimeSessionGate(
        replay_ledger=ledger,
        approval_gate=approval,
        readiness_gate=bindings.readiness_gate,
    )
    return gate, ledger


def _create(gate, bindings, approval_receipt, readiness_evidence):
    return gate.create_session(
        activation_receipt=bindings.activation_receipt,
        approval_receipt=approval_receipt,
        activation_request=bindings.activation_request,
        runtime_request=bindings.runtime_request,
        audit_observer=bindings.audit_observer,
        runtime_availability=bindings.runtime_availability,
        readiness_evidence=readiness_evidence,
    )


def _assert_activation_unclaimed(ledger, bindings) -> None:
    assert ledger.read(
        entry_kind=ReplayLedgerEntryKind.ACTIVATION_CLAIMED,
        identity_key=bindings.activation_receipt.decision.activation_id,
    ) is None


def test_ebs_028_pre_session_readiness_is_required_fail_closed_and_nonexecuting(
    tmp_path: Path,
) -> None:
    bindings = session_bindings(tmp_path / "readiness", identity="ebs-028")
    approval = approval_gate(durable_approval_store(tmp_path / "readiness" / "approval-store"))
    approval_receipt = record_approval(approval, bindings, approval_id="ebs-028-approval")
    gate, ledger = _session_gate(tmp_path / "readiness", bindings, approval)
    evidence = bindings.readiness_evidence
    custody_request = evidence.custody_request
    composition_manifest = evidence.composition_manifest
    assert custody_request is not None
    assert composition_manifest is not None
    valid_readiness = bindings.readiness_gate.validate_for_session(
        evidence=evidence,
        activation_request=bindings.activation_request,
        runtime_request=bindings.runtime_request,
        runtime_availability=bindings.runtime_availability,
    )
    assert valid_readiness.decision.disposition is ReadinessDisposition.READY
    assert valid_readiness.evidence is evidence

    missing_custody = _create(
        gate,
        bindings,
        approval_receipt,
        replace(evidence, custody_request=None, custody_attestation=None),
    )
    altered_custody = _create(
        gate,
        bindings,
        approval_receipt,
        replace(evidence, custody_request=replace(custody_request, run_id="altered-run")),
    )
    missing_composition = _create(
        gate,
        bindings,
        approval_receipt,
        replace(evidence, composition_manifest=None, composition_attestation=None),
    )
    altered_composition = _create(
        gate,
        bindings,
        approval_receipt,
        replace(evidence, composition_manifest=replace(composition_manifest, runtime_id="altered-runtime")),
    )

    assert missing_custody.decision.reason is SessionRejectionReason.MISSING_WORKSPACE_CUSTODY_EVIDENCE
    assert altered_custody.decision.reason is SessionRejectionReason.WORKSPACE_CUSTODY_BINDING_MISMATCH
    assert missing_composition.decision.reason is SessionRejectionReason.MISSING_RUNTIME_COMPOSITION_EVIDENCE
    assert altered_composition.decision.reason is SessionRejectionReason.RUNTIME_COMPOSITION_BINDING_MISMATCH
    for refusal in (missing_custody, altered_custody, missing_composition, altered_composition):
        assert refusal.session is None
        assert refusal.decision.disposition is SessionDisposition.REJECTED
        _assert_activation_unclaimed(ledger, bindings)

    created = _create(gate, bindings, approval_receipt, evidence)
    assert created.decision.disposition is SessionDisposition.SESSION_CREATED
    assert created.session is not None
    assert ledger.read(
        entry_kind=ReplayLedgerEntryKind.ACTIVATION_CLAIMED,
        identity_key=bindings.activation_receipt.decision.activation_id,
    ) is not None
    assert ledger.read(
        entry_kind=ReplayLedgerEntryKind.SESSION_ISSUED,
        identity_key=created.session.session_id,
    ) is not None

    replay = _create(gate, bindings, approval_receipt, evidence)
    assert replay.session is None
    assert replay.decision.reason is SessionRejectionReason.ACTIVATION_RECEIPT_REPLAYED

    executor = _CountingExecutor()
    unchanged_invocation = ControlledRuntimeInvoker(session_gate=gate).invoke(
        ControlledRuntimeInvocationRequest(
            session=created.session,
            activation_receipt=bindings.activation_receipt,
            activation_request=bindings.activation_request,
            runtime_request=bindings.runtime_request,
            audit_observer=bindings.audit_observer,
            runtime_availability=bindings.runtime_availability,
            runtime_binding=RuntimeExecutorBinding(runtime_id="altered-runtime", executor=executor),
        )
    )
    assert unchanged_invocation.disposition is InvocationDisposition.SESSION_REFUSED
    assert unchanged_invocation.refusal_reason is InvocationRejectionReason.RUNTIME_BINDING_MISMATCH
    assert ledger.read(
        entry_kind=ReplayLedgerEntryKind.SESSION_CONSUMED,
        identity_key=created.session.session_id,
    ) is None
    assert executor.calls == 0

    assert bindings.audit_observer.preflight_calls == 0
    assert bindings.audit_observer.terminal_record_calls == 0
    assert not hasattr(bindings.readiness_gate, "create_session")
    assert not hasattr(bindings.readiness_gate, "issue_permit")
    assert not hasattr(bindings.readiness_gate, "consume_for_runtime_start")
    assert not hasattr(bindings.readiness_gate, "execute")
    workspace_root = bindings.activation_request.isolation.workspace_root
    audit_root = bindings.activation_request.isolation.audit_root
    assert workspace_root is not None
    assert audit_root is not None
    assert not any(workspace_root.iterdir())
    assert not any(audit_root.iterdir())

    runtime_executor_calls = executor.calls
    provider_calls = 0
    mutation_calls = 0
    audit_observer_executions = 0
    workspace_mutations = 0
    git_mutations = 0
    shell_invocations = 0
    network_invocations = 0
    credential_access = 0
    assert runtime_executor_calls == 0
    assert provider_calls == 0
    assert mutation_calls == 0
    assert audit_observer_executions == 0
    assert workspace_mutations == 0
    assert git_mutations == 0
    assert shell_invocations == 0
    assert network_invocations == 0
    assert credential_access == 0
