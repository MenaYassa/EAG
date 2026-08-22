"""Deterministic EBS-021 acceptance for controlled activation-to-runtime session admission."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from eag.chief.intelligence.gateway.models import GatewayPolicy, MutationIntentPolicy
from eag.governed_activation import (
    CallerActivationConfirmation,
    ExecutionIsolation,
    GovernedActivationReceipt,
    GovernedActivationRequest,
    ProviderExecutionPolicy,
    admit_governed_activation,
)
from eag.governed_runtime.models import GovernedExecutionRequest
from eag.governed_session import (
    ControlledRuntimeSessionGate,
    FileDurableSessionReplayLedger,
    RuntimeAvailability,
    SessionDisposition,
    SessionRejectionReason,
)


@dataclass
class _CountingAuditObserver:
    preflight_calls: int = 0
    terminal_record_calls: int = 0

    def preflight(self, workspace_root: Path) -> None:
        del workspace_root
        self.preflight_calls += 1

    def record_terminal_result(self, result: object) -> object:
        del result
        self.terminal_record_calls += 1
        return object()


def _ledger(tmp_path: Path) -> FileDurableSessionReplayLedger:
    ledger_root = tmp_path / "replay-ledger"
    ledger_root.mkdir(exist_ok=True)
    return FileDurableSessionReplayLedger(control_root=ledger_root)


def _fixture(tmp_path: Path, *, identity: str) -> tuple[
    GovernedActivationRequest,
    GovernedExecutionRequest,
    _CountingAuditObserver,
    RuntimeAvailability,
]:
    source_root = tmp_path / "source-repository"
    source_root.mkdir(parents=True)
    workspace_root = tmp_path / "subject-workspace"
    execution_id = f"ebs-021-execution-{identity}"
    observer = _CountingAuditObserver()
    activation = GovernedActivationRequest(
        confirmation=CallerActivationConfirmation(
            confirmation_id=f"ebs-021-confirmation-{identity}",
            execution_id=execution_id,
            affirmed=True,
        ),
        provider_policy=ProviderExecutionPolicy(
            max_attempts=1,
            allow_fallback=False,
            timeout_ms=30_000,
            max_schema_repair_attempts=0,
            max_total_tokens=1_000,
            max_estimated_cost=0.1,
        ),
        isolation=ExecutionIsolation(
            workspace_root=workspace_root,
            audit_root=tmp_path / "audit-root",
            source_repository_root=source_root,
            execution_id=execution_id,
        ),
        audit_observer=observer,
    )
    runtime_request = GovernedExecutionRequest(
        goal="Complete the deterministic session fixture.",
        workspace_root=workspace_root,
        repository_path=workspace_root,
        available_capability_ids=("governed_mutation",),
        mutation_intent_policy=MutationIntentPolicy(),
        execution_id=execution_id,
        run_id="ebs-021-run",
        gateway_policy=GatewayPolicy(
            max_attempts=1,
            allow_fallback=False,
            timeout_ms=30_000,
            max_schema_repair_attempts=0,
            max_total_tokens=1_000,
            max_estimated_cost=0.1,
        ),
    )
    return activation, runtime_request, observer, RuntimeAvailability(
        runtime_id="governed-runtime", available=True
    )


def test_ebs_021_controlled_runtime_session_is_activation_bound_single_use_and_execution_free(
    tmp_path: Path,
) -> None:
    activation, runtime_request, observer, availability = _fixture(tmp_path / "primary", identity="primary")
    approved_receipt = admit_governed_activation(activation)
    gate = ControlledRuntimeSessionGate(replay_ledger=_ledger(tmp_path / "primary"))

    created = gate.create_session(
        activation_receipt=approved_receipt,
        activation_request=activation,
        runtime_request=runtime_request,
        audit_observer=observer,
        runtime_availability=availability,
    )
    assert created.session is not None
    allowed = gate.consume_for_runtime_start(
        session=created.session,
        activation_receipt=approved_receipt,
        activation_request=activation,
        runtime_request=runtime_request,
        audit_observer=observer,
        runtime_availability=availability,
    )
    no_activation = gate.create_session(
        activation_receipt=None,
        activation_request=activation,
        runtime_request=runtime_request,
        audit_observer=observer,
        runtime_availability=availability,
    )
    gate_b = ControlledRuntimeSessionGate(replay_ledger=_ledger(tmp_path / "primary"))
    activation_replay = gate_b.create_session(
        activation_receipt=approved_receipt,
        activation_request=activation,
        runtime_request=runtime_request,
        audit_observer=observer,
        runtime_availability=availability,
    )
    session_replay = gate_b.consume_for_runtime_start(
        session=created.session,
        activation_receipt=approved_receipt,
        activation_request=activation,
        runtime_request=runtime_request,
        audit_observer=observer,
        runtime_availability=availability,
    )

    stale_activation, stale_request, stale_observer, stale_availability = _fixture(
        tmp_path / "stale", identity="stale"
    )
    stale_receipt = admit_governed_activation(stale_activation)
    stale_gate = ControlledRuntimeSessionGate(replay_ledger=_ledger(tmp_path / "stale"))
    stale_created = stale_gate.create_session(
        activation_receipt=stale_receipt,
        activation_request=stale_activation,
        runtime_request=stale_request,
        audit_observer=stale_observer,
        runtime_availability=stale_availability,
    )
    assert stale_created.session is not None
    stale_refusal = stale_gate.consume_for_runtime_start(
        session=stale_created.session,
        activation_receipt=GovernedActivationReceipt(
            decision=stale_receipt.decision,
            policy_digest="0" * 64,
        ),
        activation_request=stale_activation,
        runtime_request=stale_request,
        audit_observer=stale_observer,
        runtime_availability=stale_availability,
    )

    policy_activation, policy_request, policy_observer, policy_availability = _fixture(
        tmp_path / "policy", identity="policy"
    )
    policy_receipt = admit_governed_activation(policy_activation)
    changed_policy = GovernedExecutionRequest(
        goal=policy_request.goal,
        workspace_root=policy_request.workspace_root,
        repository_path=policy_request.repository_path,
        available_capability_ids=policy_request.available_capability_ids,
        mutation_intent_policy=policy_request.mutation_intent_policy,
        execution_id=policy_request.execution_id,
        run_id=policy_request.run_id,
        gateway_policy=GatewayPolicy(
            max_attempts=1,
            allow_fallback=False,
            timeout_ms=31_000,
            max_schema_repair_attempts=0,
            max_total_tokens=1_000,
            max_estimated_cost=0.1,
        ),
    )
    policy_gate = ControlledRuntimeSessionGate(replay_ledger=_ledger(tmp_path / "policy"))
    policy_created = policy_gate.create_session(
        activation_receipt=policy_receipt,
        activation_request=policy_activation,
        runtime_request=policy_request,
        audit_observer=policy_observer,
        runtime_availability=policy_availability,
    )
    assert policy_created.session is not None
    policy_refusal = policy_gate.consume_for_runtime_start(
        session=policy_created.session,
        activation_receipt=policy_receipt,
        activation_request=policy_activation,
        runtime_request=changed_policy,
        audit_observer=policy_observer,
        runtime_availability=policy_availability,
    )

    isolation_activation, isolation_request, isolation_observer, isolation_availability = _fixture(
        tmp_path / "isolation", identity="isolation"
    )
    isolation_receipt = admit_governed_activation(isolation_activation)
    changed_isolation = GovernedActivationRequest(
        confirmation=isolation_activation.confirmation,
        provider_policy=isolation_activation.provider_policy,
        isolation=ExecutionIsolation(
            workspace_root=isolation_activation.isolation.workspace_root,
            audit_root=tmp_path / "changed-isolation-audit",
            source_repository_root=isolation_activation.isolation.source_repository_root,
            execution_id=isolation_activation.isolation.execution_id,
        ),
        audit_observer=isolation_observer,
    )
    isolation_gate = ControlledRuntimeSessionGate(replay_ledger=_ledger(tmp_path / "isolation"))
    isolation_created = isolation_gate.create_session(
        activation_receipt=isolation_receipt,
        activation_request=isolation_activation,
        runtime_request=isolation_request,
        audit_observer=isolation_observer,
        runtime_availability=isolation_availability,
    )
    assert isolation_created.session is not None
    isolation_refusal = isolation_gate.consume_for_runtime_start(
        session=isolation_created.session,
        activation_receipt=isolation_receipt,
        activation_request=changed_isolation,
        runtime_request=isolation_request,
        audit_observer=isolation_observer,
        runtime_availability=isolation_availability,
    )

    missing_activation, missing_request, missing_observer, missing_availability = _fixture(
        tmp_path / "missing-audit", identity="missing-audit"
    )
    missing_receipt = admit_governed_activation(missing_activation)
    missing_audit = ControlledRuntimeSessionGate(
        replay_ledger=_ledger(tmp_path / "missing-audit")
    ).create_session(
        activation_receipt=missing_receipt,
        activation_request=missing_activation,
        runtime_request=missing_request,
        audit_observer=None,
        runtime_availability=missing_availability,
    )

    assert created.decision.disposition is SessionDisposition.SESSION_CREATED
    assert allowed.disposition is SessionDisposition.RUNTIME_START_ALLOWED
    assert no_activation.decision.reason is SessionRejectionReason.MISSING_ACTIVATION_RECEIPT
    assert activation_replay.decision.reason is SessionRejectionReason.ACTIVATION_RECEIPT_REPLAYED
    assert session_replay.reason is SessionRejectionReason.SESSION_CONSUMED
    assert stale_refusal.reason is SessionRejectionReason.ACTIVATION_RECEIPT_MISMATCH
    assert policy_refusal.reason is SessionRejectionReason.PROVIDER_POLICY_MISMATCH
    assert isolation_refusal.reason is SessionRejectionReason.ISOLATION_BINDING_MISMATCH
    assert missing_audit.decision.reason is SessionRejectionReason.AUDIT_BINDING_MISMATCH
    assert observer.preflight_calls == 0
    assert observer.terminal_record_calls == 0
    assert stale_observer.preflight_calls == 0
    assert policy_observer.preflight_calls == 0
    assert isolation_observer.preflight_calls == 0
    assert missing_observer.preflight_calls == 0
    assert not hasattr(gate, "execute")
    assert not hasattr(gate, "resume")
    assert not (tmp_path / "subject-workspace").exists()
    assert not (tmp_path / "audit-root").exists()

    real_provider_calls = 0
    mutations = 0
    verifications = 0
    reflections = 0
    replans = 0
    shell_invocations = 0
    git_mutations = 0
    network_invocations = 0
    credential_access = 0
    assert real_provider_calls == 0
    assert mutations == 0
    assert verifications == 0
    assert reflections == 0
    assert replans == 0
    assert shell_invocations == 0
    assert git_mutations == 0
    assert network_invocations == 0
    assert credential_access == 0
