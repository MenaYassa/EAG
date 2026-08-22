"""Deterministic non-executing fixtures for G2.4.8 durable session replay-ledger tests."""

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
    DurableReplayLedgerRecord,
    FileDurableSessionReplayLedger,
    ReplayLedgerClaim,
    ReplayLedgerEntryKind,
    ReplayLedgerUnavailableError,
    RuntimeAvailability,
)


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


@dataclass(frozen=True, slots=True)
class SessionBindings:
    activation_request: GovernedActivationRequest
    activation_receipt: GovernedActivationReceipt
    runtime_request: GovernedExecutionRequest
    audit_observer: CountingAuditObserver
    runtime_availability: RuntimeAvailability
    control_root: Path


class UnavailableReplayLedger:
    """Structural durable-store double that demonstrates fail-closed gate behavior."""

    def __init__(self, *, control_root: Path) -> None:
        self._control_root = control_root

    @property
    def control_root(self) -> Path:
        return self._control_root

    def claim(self, record: DurableReplayLedgerRecord) -> ReplayLedgerClaim:
        del record
        raise ReplayLedgerUnavailableError("deterministic unavailable durable store")

    def read(
        self,
        *,
        entry_kind: ReplayLedgerEntryKind,
        identity_key: str,
    ) -> DurableReplayLedgerRecord | None:
        del entry_kind, identity_key
        raise ReplayLedgerUnavailableError("deterministic unavailable durable store")


def durable_ledger(control_root: Path) -> FileDurableSessionReplayLedger:
    control_root.mkdir(parents=True, exist_ok=True)
    return FileDurableSessionReplayLedger(control_root=control_root)


def session_bindings(tmp_path: Path, *, identity: str) -> SessionBindings:
    source_root = tmp_path / "source"
    source_root.mkdir(parents=True)
    workspace_root = tmp_path / "workspace"
    execution_id = f"g248-execution-{identity}"
    observer = CountingAuditObserver()
    activation_request = GovernedActivationRequest(
        confirmation=CallerActivationConfirmation(
            confirmation_id=f"g248-confirmation-{identity}",
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
        goal="Prove deterministic durable replay protection without runtime execution.",
        workspace_root=workspace_root,
        repository_path=workspace_root,
        available_capability_ids=("governed_mutation",),
        mutation_intent_policy=MutationIntentPolicy(),
        execution_id=execution_id,
        run_id=f"g248-run-{identity}",
        gateway_policy=GatewayPolicy(
            max_attempts=1,
            allow_fallback=False,
            timeout_ms=30_000,
            max_schema_repair_attempts=0,
            max_total_tokens=1_000,
            max_estimated_cost=0.1,
        ),
    )
    return SessionBindings(
        activation_request=activation_request,
        activation_receipt=admit_governed_activation(activation_request),
        runtime_request=runtime_request,
        audit_observer=observer,
        runtime_availability=RuntimeAvailability(runtime_id="g248-runtime", available=True),
        control_root=tmp_path / "control-plane",
    )


__all__ = [
    "CountingAuditObserver",
    "SessionBindings",
    "UnavailableReplayLedger",
    "durable_ledger",
    "session_bindings",
]
