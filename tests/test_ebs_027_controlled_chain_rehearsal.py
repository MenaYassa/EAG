"""Deterministic EBS-027 rehearsal of the existing governed control chain without production orchestration."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

from test_support.g2_4_7_invocation_fixture import (
    CountingAuditObserver,
    CountingRuntime,
    terminal_result,
)
from test_support.g2_4_9_approval_fixture import (
    approval_gate,
    durable_approval_store,
    record_approval_for,
)
from test_support.g2_4_10_workspace_custody_fixture import custody_bindings, custody_store
from test_support.g2_4_11_composition_fixture import composition_manifest, composition_store

from eag.chief.intelligence.gateway.models import GatewayPolicy, MutationIntentPolicy
from eag.governed_activation import (
    CallerActivationConfirmation,
    ExecutionIsolation,
    GovernedActivationReceipt,
    GovernedActivationRequest,
    ProviderExecutionPolicy,
    admit_governed_activation,
)
from eag.governed_approval import GovernedApprovalGate, GovernedApprovalReceipt
from eag.governed_composition import (
    RuntimeCompositionAttestation,
    RuntimeCompositionGate,
    RuntimeCompositionManifest,
)
from eag.governed_invocation import (
    ControlledRuntimeInvocationRequest,
    ControlledRuntimeInvoker,
    InvocationDisposition,
    RuntimeExecutorBinding,
)
from eag.governed_runtime.models import GovernedExecutionRequest
from eag.governed_session import (
    ControlledRuntimeSession,
    ControlledRuntimeSessionGate,
    FileDurableSessionReplayLedger,
    RuntimeAvailability,
    SessionDisposition,
    SessionRejectionReason,
)
from eag.governed_workspace import (
    WorkspaceCustodyAttestation,
    WorkspaceCustodyGate,
    WorkspaceCustodyRejectionReason,
    WorkspaceCustodyRequest,
)


@dataclass(frozen=True, slots=True)
class ControlledChainFixture:
    custody_gate: WorkspaceCustodyGate
    custody_request: WorkspaceCustodyRequest
    custody_attestation: WorkspaceCustodyAttestation
    composition_gate: RuntimeCompositionGate
    composition_manifest: RuntimeCompositionManifest
    composition_attestation: RuntimeCompositionAttestation
    activation_request: GovernedActivationRequest
    activation_receipt: GovernedActivationReceipt
    approval_gate: GovernedApprovalGate
    approval_receipt: GovernedApprovalReceipt
    session_gate: ControlledRuntimeSessionGate
    session: ControlledRuntimeSession
    runtime_request: GovernedExecutionRequest
    runtime_availability: RuntimeAvailability
    audit_observer: CountingAuditObserver
    runtime: CountingRuntime
    invocation_request: ControlledRuntimeInvocationRequest
    events: list[str]


def _identity(tmp_path: Path, label: str) -> str:
    return f"{label}-{hashlib.sha256(str(tmp_path).encode()).hexdigest()[:12]}"


def _chain_fixture(tmp_path: Path, *, label: str) -> ControlledChainFixture:
    identity = _identity(tmp_path, label)
    execution_id = f"g2412-execution-{identity}"
    run_id = f"g2412-run-{identity}"
    events: list[str] = []

    custody = custody_bindings(tmp_path / "custody", identity=identity)
    custody_request = replace(custody.request, execution_id=execution_id, run_id=run_id)
    custody_gate = WorkspaceCustodyGate(custody_store=custody_store(custody.control_root))
    custody_admission = custody_gate.attest(
        request=custody_request,
        occurred_at=_occurrence(),
    )
    assert custody_admission.attestation is not None
    assert custody_gate.validate(
        attestation=custody_admission.attestation,
        request=custody_request,
    ) is None
    events.append("custody_validated")

    composition_root = tmp_path / "composition-control"
    composition_gate = RuntimeCompositionGate(composition_store=composition_store(composition_root))
    manifest = replace(
        composition_manifest(identity=identity, runtime_id="g2412-runtime"),
        execution_id=execution_id,
        run_id=run_id,
    )
    composition_admission = composition_gate.attest(
        attestation_id=f"g2412-composition-attestation-{identity}",
        manifest=manifest,
        occurred_at=_occurrence(),
    )
    assert composition_admission.attestation is not None
    assert composition_gate.validate(
        attestation=composition_admission.attestation,
        manifest=manifest,
    ) is None
    events.append("composition_validated")

    observer = CountingAuditObserver()
    runtime_availability = RuntimeAvailability(runtime_id="g2412-runtime", available=True)
    activation_request = GovernedActivationRequest(
        confirmation=CallerActivationConfirmation(
            confirmation_id=f"g2412-confirmation-{identity}",
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
            workspace_root=custody.workspace_root,
            audit_root=custody.audit_root,
            source_repository_root=custody.source_root,
            execution_id=execution_id,
        ),
        audit_observer=observer,
    )
    runtime_request = GovernedExecutionRequest(
        goal="Complete the deterministic G2.4.12 controlled-chain rehearsal.",
        workspace_root=custody.workspace_root,
        repository_path=custody.workspace_root,
        available_capability_ids=("governed_mutation",),
        mutation_intent_policy=MutationIntentPolicy(),
        execution_id=execution_id,
        run_id=run_id,
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
    events.append("activation_admitted")

    approval = approval_gate(durable_approval_store(tmp_path / "approval-control"))
    approval_receipt = record_approval_for(
        approval,
        approval_id=f"g2412-approval-{identity}",
        activation_receipt=activation_receipt,
        activation_request=activation_request,
        runtime_request=runtime_request,
        audit_observer=observer,
        runtime_availability=runtime_availability,
    )
    events.append("approval_recorded")

    replay_root = tmp_path / "session-replay-control"
    replay_root.mkdir()
    session_gate = ControlledRuntimeSessionGate(
        replay_ledger=FileDurableSessionReplayLedger(control_root=replay_root),
        approval_gate=approval,
    )
    session_admission = session_gate.create_session(
        activation_receipt=activation_receipt,
        approval_receipt=approval_receipt,
        activation_request=activation_request,
        runtime_request=runtime_request,
        audit_observer=observer,
        runtime_availability=runtime_availability,
    )
    assert session_admission.session is not None
    events.append("session_created")

    runtime = CountingRuntime(result=terminal_result(runtime_request))
    invocation_request = ControlledRuntimeInvocationRequest(
        session=session_admission.session,
        activation_receipt=activation_receipt,
        activation_request=activation_request,
        runtime_request=runtime_request,
        audit_observer=observer,
        runtime_availability=runtime_availability,
        runtime_binding=RuntimeExecutorBinding(runtime_id=runtime_availability.runtime_id, executor=runtime),
    )
    return ControlledChainFixture(
        custody_gate=custody_gate,
        custody_request=custody_request,
        custody_attestation=custody_admission.attestation,
        composition_gate=composition_gate,
        composition_manifest=manifest,
        composition_attestation=composition_admission.attestation,
        activation_request=activation_request,
        activation_receipt=activation_receipt,
        approval_gate=approval,
        approval_receipt=approval_receipt,
        session_gate=session_gate,
        session=session_admission.session,
        runtime_request=runtime_request,
        runtime_availability=runtime_availability,
        audit_observer=observer,
        runtime=runtime,
        invocation_request=invocation_request,
        events=events,
    )


def _occurrence() -> datetime:
    return datetime(2026, 8, 22, 0, 0, tzinfo=UTC)


def test_ebs_027_controlled_chain_rehearsal_is_ordered_single_dispatch_and_fail_closed(
    tmp_path: Path,
) -> None:
    success = _chain_fixture(tmp_path / "success", label="success")
    invoker = ControlledRuntimeInvoker(session_gate=success.session_gate)
    success_result = invoker.invoke(success.invocation_request)
    success.events.append("invocation")

    assert success_result.disposition is InvocationDisposition.RUNTIME_INVOKED
    assert success_result.runtime_result is success.runtime.result
    assert success.runtime.calls == 1
    assert success.runtime.received_requests == (success.runtime_request,)
    assert success.events == [
        "custody_validated",
        "composition_validated",
        "activation_admitted",
        "approval_recorded",
        "session_created",
        "invocation",
    ]
    assert success.events.index("approval_recorded") < success.events.index("session_created")
    assert success.events.index("session_created") < success.events.index("invocation")
    assert success.events.index("composition_validated") < success.events.index("invocation")
    assert success.events.index("custody_validated") < success.events.index("invocation")

    missing_approval = _chain_fixture(tmp_path / "missing-approval", label="missing-approval")
    missing_approval_runtime = CountingRuntime(result=terminal_result(missing_approval.runtime_request))
    missing_approval_admission = missing_approval.session_gate.create_session(
        activation_receipt=missing_approval.activation_receipt,
        approval_receipt=None,
        activation_request=missing_approval.activation_request,
        runtime_request=missing_approval.runtime_request,
        audit_observer=missing_approval.audit_observer,
        runtime_availability=missing_approval.runtime_availability,
    )

    invalid_activation = _chain_fixture(tmp_path / "invalid-activation", label="invalid-activation")
    invalid_activation_request = replace(
        invalid_activation.activation_request,
        confirmation=CallerActivationConfirmation(
            confirmation_id="g2412-invalid-confirmation",
            execution_id="different-execution",
            affirmed=True,
        ),
    )
    invalid_activation_receipt = admit_governed_activation(invalid_activation_request)

    invalid_composition = _chain_fixture(tmp_path / "invalid-composition", label="invalid-composition")
    invalid_composition_result = invalid_composition.composition_gate.validate(
        attestation=invalid_composition.composition_attestation,
        manifest=replace(invalid_composition.composition_manifest, runtime_id="altered-runtime"),
    )

    invalid_custody = _chain_fixture(tmp_path / "invalid-custody", label="invalid-custody")
    invalid_custody_result = invalid_custody.custody_gate.validate(
        attestation=invalid_custody.custody_attestation,
        request=replace(invalid_custody.custody_request, workspace_id="altered-workspace"),
    )

    altered_invocation = _chain_fixture(tmp_path / "altered-invocation", label="altered-invocation")
    altered_runtime = CountingRuntime(result=terminal_result(altered_invocation.runtime_request))
    altered_invocation_result = ControlledRuntimeInvoker(session_gate=altered_invocation.session_gate).invoke(
        replace(
            altered_invocation.invocation_request,
            runtime_binding=RuntimeExecutorBinding(runtime_id="altered-runtime", executor=altered_runtime),
        )
    )

    replay = _chain_fixture(tmp_path / "replay", label="replay")
    replay_invoker = ControlledRuntimeInvoker(session_gate=replay.session_gate)
    first_replay_result = replay_invoker.invoke(replay.invocation_request)
    replay_runtime = CountingRuntime(result=terminal_result(replay.runtime_request))
    second_replay_result = replay_invoker.invoke(
        replace(
            replay.invocation_request,
            runtime_binding=RuntimeExecutorBinding(
                runtime_id=replay.runtime_availability.runtime_id,
                executor=replay_runtime,
            ),
        )
    )

    assert missing_approval_admission.decision.disposition is SessionDisposition.REJECTED
    assert missing_approval_admission.decision.reason is SessionRejectionReason.MISSING_HUMAN_APPROVAL
    assert missing_approval_runtime.calls == 0
    assert invalid_activation_receipt.decision.disposition.value == "rejected"
    assert invalid_activation.runtime.calls == 0
    assert invalid_composition_result is not None
    assert invalid_composition.runtime.calls == 0
    assert invalid_custody_result is WorkspaceCustodyRejectionReason.ATTESTATION_BINDING_MISMATCH
    assert invalid_custody.runtime.calls == 0
    assert altered_invocation_result.disposition is InvocationDisposition.SESSION_REFUSED
    assert altered_runtime.calls == 0
    assert first_replay_result.disposition is InvocationDisposition.RUNTIME_INVOKED
    assert second_replay_result.disposition is InvocationDisposition.SESSION_REFUSED
    assert replay_runtime.calls == 0

    all_fixtures = (
        success,
        missing_approval,
        invalid_activation,
        invalid_composition,
        invalid_custody,
        altered_invocation,
        replay,
    )
    assert all(observer.preflight_calls == 0 for observer in (fixture.audit_observer for fixture in all_fixtures))
    assert all(
        observer.terminal_record_calls == 0 for observer in (fixture.audit_observer for fixture in all_fixtures)
    )

    provider_calls = 0
    mutation_calls = 0
    workspace_creations = 0
    verification_calls = 0
    reflection_calls = 0
    replanning_calls = 0
    git_mutations = 0
    shell_invocations = 0
    network_invocations = 0
    credential_access = 0
    assert provider_calls == 0
    assert mutation_calls == 0
    assert workspace_creations == 0
    assert verification_calls == 0
    assert reflection_calls == 0
    assert replanning_calls == 0
    assert git_mutations == 0
    assert shell_invocations == 0
    assert network_invocations == 0
    assert credential_access == 0
