"""Deterministic non-executing fixtures for G2.4.9 governed human approval tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from eag.governed_activation import GovernedActivationReceipt, GovernedActivationRequest
from eag.governed_approval import (
    DurableGovernedApprovalStore,
    FileDurableGovernedApprovalStore,
    GovernedApprovalClaim,
    GovernedApprovalDisposition,
    GovernedApprovalGate,
    GovernedApprovalReceipt,
    GovernedApprovalStoreUnavailableError,
)
from eag.governed_runtime.models import GovernedExecutionRequest
from eag.governed_session.models import RuntimeAvailability
from test_support.g2_4_8_replay_ledger_fixture import SessionBindings


class UnavailableGovernedApprovalStore:
    """Structural durable-store double that deterministically demonstrates fail-closed approval handling."""

    def __init__(self, *, control_root: Path) -> None:
        self._control_root = control_root

    @property
    def control_root(self) -> Path:
        return self._control_root

    def claim(self, receipt: GovernedApprovalReceipt) -> GovernedApprovalClaim:
        del receipt
        raise GovernedApprovalStoreUnavailableError("deterministic unavailable approval store")

    def read(self, *, approval_id: str) -> GovernedApprovalReceipt | None:
        del approval_id
        raise GovernedApprovalStoreUnavailableError("deterministic unavailable approval store")


def durable_approval_store(control_root: Path) -> FileDurableGovernedApprovalStore:
    control_root.mkdir(parents=True, exist_ok=True)
    return FileDurableGovernedApprovalStore(control_root=control_root)


def approval_gate(store: DurableGovernedApprovalStore) -> GovernedApprovalGate:
    return GovernedApprovalGate(approval_store=store)


def record_approval_for(
    gate: GovernedApprovalGate,
    *,
    approval_id: str,
    activation_receipt: GovernedActivationReceipt,
    activation_request: GovernedActivationRequest,
    runtime_request: GovernedExecutionRequest,
    audit_observer: object,
    runtime_availability: RuntimeAvailability,
    disposition: GovernedApprovalDisposition = GovernedApprovalDisposition.APPROVED,
) -> GovernedApprovalReceipt:
    admission = gate.record(
        approval_id=approval_id,
        approver_identity="deterministic-operator",
        occurred_at=datetime(2026, 8, 22, 0, 0, tzinfo=UTC),
        disposition=disposition,
        activation_receipt=activation_receipt,
        activation_request=activation_request,
        runtime_request=runtime_request,
        audit_observer=audit_observer,
        runtime_availability=runtime_availability,
    )
    assert admission.receipt is not None
    return admission.receipt


def record_approval(
    gate: GovernedApprovalGate,
    bindings: SessionBindings,
    *,
    approval_id: str,
    disposition: GovernedApprovalDisposition = GovernedApprovalDisposition.APPROVED,
) -> GovernedApprovalReceipt:
    return record_approval_for(
        gate,
        approval_id=approval_id,
        activation_receipt=bindings.activation_receipt,
        activation_request=bindings.activation_request,
        runtime_request=bindings.runtime_request,
        audit_observer=bindings.audit_observer,
        runtime_availability=bindings.runtime_availability,
        disposition=disposition,
    )


__all__ = [
    "UnavailableGovernedApprovalStore",
    "approval_gate",
    "durable_approval_store",
    "record_approval",
    "record_approval_for",
]
