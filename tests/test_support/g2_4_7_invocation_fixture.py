"""Deterministic fixtures for G2.4.7.1 controlled invocation tests and EBS-022."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from eag.chief.intelligence.gateway.models import GatewayPolicy, MutationIntentPolicy
from eag.governed_activation import (
    CallerActivationConfirmation,
    ExecutionIsolation,
    GovernedActivationRequest,
    ProviderExecutionPolicy,
    admit_governed_activation,
)
from eag.governed_execution.enums import (
    ExecutionEvidenceKind,
    GovernedExecutionState,
    GovernedExecutionStopReason,
)
from eag.governed_execution.models import (
    ExecutionBudget,
    ExecutionEvidenceRef,
    GovernedExecutionContext,
)
from eag.governed_execution.state_machine import GovernedExecutionStateMachine
from eag.governed_invocation import (
    ControlledRuntimeInvocationRequest,
    RuntimeExecutorBinding,
)
from eag.governed_runtime.models import (
    GovernedExecutionRequest,
    GovernedExecutionResult,
    IterationContextArtifact,
)
from eag.governed_session import (
    ControlledRuntimeSession,
    ControlledRuntimeSessionGate,
    FileDurableSessionReplayLedger,
    RuntimeAvailability,
)
from test_support.g2_4_9_approval_fixture import (
    approval_gate,
    durable_approval_store,
    record_approval_for,
)
from test_support.g2_4_13_readiness_fixture import readiness_fixture


@dataclass
class CountingAuditObserver:
    preflight_calls: int = 0
    terminal_record_calls: int = 0

    def preflight(self, workspace_root: Path) -> None:
        del workspace_root
        self.preflight_calls += 1

    def record_terminal_result(self, result: object) -> object:
        del result
        self.terminal_record_calls += 1
        return object()


@dataclass
class CountingRuntime:
    result: GovernedExecutionResult
    calls: int = 0
    received_requests: tuple[GovernedExecutionRequest, ...] = ()
    fail_with: Exception | None = None

    def execute(self, request: GovernedExecutionRequest) -> GovernedExecutionResult:
        self.calls += 1
        self.received_requests += (request,)
        if self.fail_with is not None:
            raise self.fail_with
        return self.result


@dataclass(frozen=True, slots=True)
class InvocationFixture:
    gate: ControlledRuntimeSessionGate
    session: ControlledRuntimeSession
    activation_request: GovernedActivationRequest
    runtime_request: GovernedExecutionRequest
    audit_observer: CountingAuditObserver
    runtime_availability: RuntimeAvailability
    runtime: CountingRuntime
    invocation_request: ControlledRuntimeInvocationRequest


def terminal_result(request: GovernedExecutionRequest) -> GovernedExecutionResult:
    """Construct a valid terminal result through the existing pure state-machine contract."""
    machine = GovernedExecutionStateMachine()
    context = GovernedExecutionContext(
        execution_id=request.execution_id,
        run_id=request.run_id,
        goal=request.goal,
        budget=ExecutionBudget(max_iterations=2, max_mutations=2, max_verifications=2),
    )
    context = machine.transition_or_raise(context, GovernedExecutionState.CONTEXT_ASSEMBLING)
    context = machine.transition_or_raise(
        context,
        GovernedExecutionState.PLANNING,
        evidence=(ExecutionEvidenceRef(kind=ExecutionEvidenceKind.PLAN, reference_id="fixture-plan"),),
    )
    context = machine.transition_or_raise(context, GovernedExecutionState.DECIDING)
    context = machine.transition_or_raise(
        context,
        GovernedExecutionState.PROPOSING,
        evidence=(ExecutionEvidenceRef(kind=ExecutionEvidenceKind.DECISION, reference_id="fixture-decision"),),
    )
    context = machine.transition_or_raise(
        context,
        GovernedExecutionState.AUTHORIZING,
        evidence=(ExecutionEvidenceRef(kind=ExecutionEvidenceKind.PROPOSAL, reference_id="fixture-proposal"),),
    )
    context = machine.transition_or_raise(
        context,
        GovernedExecutionState.MUTATING,
        evidence=(ExecutionEvidenceRef(kind=ExecutionEvidenceKind.AUTHORIZATION, reference_id="fixture-auth"),),
    )
    context = machine.transition_or_raise(
        context,
        GovernedExecutionState.VERIFYING,
        evidence=(
            ExecutionEvidenceRef(
                kind=ExecutionEvidenceKind.MUTATION_RECEIPT,
                reference_id="fixture-receipt",
            ),
        ),
    )
    context = machine.transition_or_raise(
        context,
        GovernedExecutionState.COMPLETED,
        stop_reason=GovernedExecutionStopReason.SUCCESS,
        evidence=(ExecutionEvidenceRef(kind=ExecutionEvidenceKind.VERIFICATION, reference_id="fixture-verification"),),
    )
    return GovernedExecutionResult(
        context=context,
        iteration_artifacts=(
            IterationContextArtifact(
                artifact_id="fixture-context-artifact",
                repository_snapshot_fingerprint="fixture-snapshot",
                context_fingerprint="fixture-context",
                policy_version="fixture-policy",
            ),
        ),
    )


def invocation_fixture(tmp_path: Path, *, identity: str) -> InvocationFixture:
    source_root = tmp_path / "source"
    source_root.mkdir(parents=True)
    workspace_root = tmp_path / "workspace"
    identity_key = f"{identity}-{hashlib.sha256(str(tmp_path).encode()).hexdigest()[:12]}"
    execution_id = f"g247-execution-{identity_key}"
    observer = CountingAuditObserver()
    availability = RuntimeAvailability(runtime_id="fixture-runtime", available=True)
    activation_request = GovernedActivationRequest(
        confirmation=CallerActivationConfirmation(
            confirmation_id=f"g247-confirmation-{identity_key}",
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
            audit_root=tmp_path / "audit",
            source_repository_root=source_root,
            execution_id=execution_id,
        ),
        audit_observer=observer,
    )
    runtime_request = GovernedExecutionRequest(
        goal="Complete the deterministic controlled invocation fixture.",
        workspace_root=workspace_root,
        repository_path=workspace_root,
        available_capability_ids=("governed_mutation",),
        mutation_intent_policy=MutationIntentPolicy(),
        execution_id=execution_id,
        run_id=f"g247-run-{identity_key}",
        gateway_policy=GatewayPolicy(
            max_attempts=1,
            allow_fallback=False,
            timeout_ms=30_000,
            max_schema_repair_attempts=0,
            max_total_tokens=1_000,
            max_estimated_cost=0.1,
        ),
    )
    activation_receipt = admit_governed_activation(activation_request)
    approval = approval_gate(durable_approval_store(tmp_path / "approval-store"))
    approval_receipt = record_approval_for(
        approval,
        approval_id=f"g247-approval-{identity_key}",
        activation_receipt=activation_receipt,
        activation_request=activation_request,
        runtime_request=runtime_request,
        audit_observer=observer,
        runtime_availability=availability,
    )
    readiness = readiness_fixture(
        tmp_path,
        identity=f"g247-{identity_key}",
        activation_request=activation_request,
        runtime_request=runtime_request,
        runtime_availability=availability,
    )
    ledger_root = tmp_path / "replay-ledger"
    ledger_root.mkdir()
    gate = ControlledRuntimeSessionGate(
        replay_ledger=FileDurableSessionReplayLedger(control_root=ledger_root),
        approval_gate=approval,
        readiness_gate=readiness.gate,
    )
    admission = gate.create_session(
        activation_receipt=activation_receipt,
        approval_receipt=approval_receipt,
        activation_request=activation_request,
        runtime_request=runtime_request,
        audit_observer=observer,
        runtime_availability=availability,
        readiness_evidence=readiness.evidence,
    )
    assert admission.session is not None
    runtime = CountingRuntime(result=terminal_result(runtime_request))
    invocation_request = ControlledRuntimeInvocationRequest(
        session=admission.session,
        activation_receipt=activation_receipt,
        activation_request=activation_request,
        runtime_request=runtime_request,
        audit_observer=observer,
        runtime_availability=availability,
        runtime_binding=RuntimeExecutorBinding(runtime_id=availability.runtime_id, executor=runtime),
    )
    return InvocationFixture(
        gate=gate,
        session=admission.session,
        activation_request=activation_request,
        runtime_request=runtime_request,
        audit_observer=observer,
        runtime_availability=availability,
        runtime=runtime,
        invocation_request=invocation_request,
    )
