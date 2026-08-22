"""Deterministic contracts for the G2.4.6.2 controlled runtime-session gate."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from test_support.g2_4_9_approval_fixture import (
    approval_gate,
    durable_approval_store,
    record_approval_for,
)

from eag.chief.intelligence.gateway.models import GatewayPolicy, MutationIntentPolicy
from eag.governed_activation import (
    CallerActivationConfirmation,
    ExecutionIsolation,
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
class _AuditObserver:
    preflight_calls: int = 0
    terminal_record_calls: int = 0

    def preflight(self, workspace_root: Path) -> None:
        del workspace_root
        self.preflight_calls += 1

    def record_terminal_result(self, result: object) -> object:
        del result
        self.terminal_record_calls += 1
        return object()


def _bindings(tmp_path: Path) -> tuple[
    GovernedActivationRequest,
    GovernedExecutionRequest,
    _AuditObserver,
    RuntimeAvailability,
]:
    source_root = tmp_path / "source"
    source_root.mkdir()
    workspace_root = tmp_path / "workspace"
    observer = _AuditObserver()
    execution_id = f"session-execution-{tmp_path.name}"
    policy = ProviderExecutionPolicy(
        max_attempts=1,
        allow_fallback=False,
        timeout_ms=30_000,
        max_schema_repair_attempts=0,
        max_total_tokens=1_000,
        max_estimated_cost=0.1,
    )
    activation = GovernedActivationRequest(
        confirmation=CallerActivationConfirmation(
            confirmation_id=f"session-confirmation-{tmp_path.name}",
            execution_id=execution_id,
            affirmed=True,
        ),
        provider_policy=policy,
        isolation=ExecutionIsolation(
            workspace_root=workspace_root,
            audit_root=tmp_path / "audit",
            source_repository_root=source_root,
            execution_id=execution_id,
        ),
        audit_observer=observer,
    )
    runtime_request = GovernedExecutionRequest(
        goal="Apply the deterministic fixture change.",
        workspace_root=workspace_root,
        repository_path=workspace_root,
        available_capability_ids=("governed_mutation",),
        mutation_intent_policy=MutationIntentPolicy(),
        execution_id=execution_id,
        run_id="session-run",
        gateway_policy=GatewayPolicy(
            max_attempts=1,
            allow_fallback=False,
            timeout_ms=30_000,
            max_schema_repair_attempts=0,
            max_total_tokens=1_000,
            max_estimated_cost=0.1,
        ),
    )
    return activation, runtime_request, observer, RuntimeAvailability(runtime_id="governed-runtime", available=True)


def _ledger(tmp_path: Path) -> FileDurableSessionReplayLedger:
    ledger_root = tmp_path / "replay-ledger"
    ledger_root.mkdir(exist_ok=True)
    return FileDurableSessionReplayLedger(control_root=ledger_root)


def _approved_session(tmp_path: Path):
    activation, request, observer, availability = _bindings(tmp_path)
    receipt = admit_governed_activation(activation)
    approval = approval_gate(durable_approval_store(tmp_path / "approval-store"))
    approval_receipt = record_approval_for(
        approval,
        approval_id=f"session-approval-{tmp_path.name}",
        activation_receipt=receipt,
        activation_request=activation,
        runtime_request=request,
        audit_observer=observer,
        runtime_availability=availability,
    )
    gate = ControlledRuntimeSessionGate(
        replay_ledger=_ledger(tmp_path),
        approval_gate=approval,
    )
    admission = gate.create_session(
        activation_receipt=receipt,
        approval_receipt=approval_receipt,
        activation_request=activation,
        runtime_request=request,
        audit_observer=observer,
        runtime_availability=availability,
    )
    assert admission.session is not None
    return gate, admission.session, receipt, approval_receipt, activation, request, observer, availability


def test_approved_activation_creates_and_consumes_one_nonexecuting_runtime_start_permit(tmp_path: Path) -> None:
    gate, session, receipt, approval_receipt, activation, request, observer, availability = _approved_session(tmp_path)

    start = gate.consume_for_runtime_start(
        session=session,
        activation_receipt=receipt,
        activation_request=activation,
        runtime_request=request,
        audit_observer=observer,
        runtime_availability=availability,
    )

    assert start.disposition is SessionDisposition.RUNTIME_START_ALLOWED
    assert start.execution_id == request.execution_id
    assert start.run_id == request.run_id
    assert observer.preflight_calls == 0
    assert observer.terminal_record_calls == 0
    assert not hasattr(gate, "execute")
    assert not hasattr(gate, "mutate")
    assert not hasattr(gate, "verify")
    assert not hasattr(gate, "resume")


def test_missing_receipt_and_unavailable_runtime_are_refused_before_session_creation(tmp_path: Path) -> None:
    activation, request, observer, availability = _bindings(tmp_path)
    receipt = admit_governed_activation(activation)
    approval = approval_gate(durable_approval_store(tmp_path / "approval-store"))
    gate = ControlledRuntimeSessionGate(
        replay_ledger=_ledger(tmp_path),
        approval_gate=approval,
    )

    missing = gate.create_session(
        activation_receipt=None,
        approval_receipt=None,
        activation_request=activation,
        runtime_request=request,
        audit_observer=observer,
        runtime_availability=availability,
    )
    unavailable = gate.create_session(
        activation_receipt=receipt,
        approval_receipt=None,
        activation_request=activation,
        runtime_request=request,
        audit_observer=observer,
        runtime_availability=RuntimeAvailability(runtime_id="governed-runtime", available=False),
    )

    assert missing.decision.reason is SessionRejectionReason.MISSING_ACTIVATION_RECEIPT
    assert unavailable.decision.reason is SessionRejectionReason.RUNTIME_UNAVAILABLE
    assert observer.preflight_calls == 0


def test_session_reuse_and_activation_replay_are_refused(tmp_path: Path) -> None:
    gate, session, receipt, approval_receipt, activation, request, observer, availability = _approved_session(tmp_path)

    first = gate.consume_for_runtime_start(
        session=session,
        activation_receipt=receipt,
        activation_request=activation,
        runtime_request=request,
        audit_observer=observer,
        runtime_availability=availability,
    )
    replay = gate.consume_for_runtime_start(
        session=session,
        activation_receipt=receipt,
        activation_request=activation,
        runtime_request=request,
        audit_observer=observer,
        runtime_availability=availability,
    )
    second_session = gate.create_session(
        activation_receipt=receipt,
        approval_receipt=approval_receipt,
        activation_request=activation,
        runtime_request=request,
        audit_observer=observer,
        runtime_availability=availability,
    )

    assert first.disposition is SessionDisposition.RUNTIME_START_ALLOWED
    assert replay.reason is SessionRejectionReason.SESSION_CONSUMED
    assert second_session.decision.reason is SessionRejectionReason.ACTIVATION_RECEIPT_REPLAYED


def test_changed_policy_isolation_or_audit_binding_is_refused_before_runtime_start(tmp_path: Path) -> None:
    gate, session, receipt, approval_receipt, activation, request, observer, availability = _approved_session(tmp_path)
    changed_policy = GovernedExecutionRequest(
        goal=request.goal,
        workspace_root=request.workspace_root,
        repository_path=request.repository_path,
        available_capability_ids=request.available_capability_ids,
        mutation_intent_policy=request.mutation_intent_policy,
        execution_id=request.execution_id,
        run_id=request.run_id,
        gateway_policy=GatewayPolicy(
            max_attempts=1,
            allow_fallback=False,
            timeout_ms=31_000,
            max_schema_repair_attempts=0,
            max_total_tokens=1_000,
            max_estimated_cost=0.1,
        ),
    )
    changed_isolation = GovernedActivationRequest(
        confirmation=activation.confirmation,
        provider_policy=activation.provider_policy,
        isolation=ExecutionIsolation(
            workspace_root=activation.isolation.workspace_root,
            audit_root=tmp_path / "other-audit",
            source_repository_root=activation.isolation.source_repository_root,
            execution_id=activation.isolation.execution_id,
        ),
        audit_observer=observer,
    )
    replacement_observer = _AuditObserver()

    policy_refusal = gate.consume_for_runtime_start(
        session=session,
        activation_receipt=receipt,
        activation_request=activation,
        runtime_request=changed_policy,
        audit_observer=observer,
        runtime_availability=availability,
    )
    isolation_refusal = gate.consume_for_runtime_start(
        session=session,
        activation_receipt=receipt,
        activation_request=changed_isolation,
        runtime_request=request,
        audit_observer=observer,
        runtime_availability=availability,
    )
    audit_refusal = gate.consume_for_runtime_start(
        session=session,
        activation_receipt=receipt,
        activation_request=activation,
        runtime_request=request,
        audit_observer=replacement_observer,
        runtime_availability=availability,
    )

    assert policy_refusal.reason is SessionRejectionReason.PROVIDER_POLICY_MISMATCH
    assert isolation_refusal.reason is SessionRejectionReason.ISOLATION_BINDING_MISMATCH
    assert audit_refusal.reason is SessionRejectionReason.AUDIT_BINDING_MISMATCH
    assert observer.preflight_calls == 0
    assert replacement_observer.preflight_calls == 0
