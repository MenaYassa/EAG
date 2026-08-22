"""Non-executing governed human approval evidence creation and exact binding validation."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from eag.chief.intelligence.gateway.models import GatewayPolicy, MutationIntentPolicy
from eag.governed_activation import (
    GovernedActivationReceipt,
    GovernedActivationRequest,
)
from eag.governed_approval.models import (
    GovernedApprovalAdmission,
    GovernedApprovalDisposition,
    GovernedApprovalReceipt,
    GovernedApprovalRejectionReason,
)
from eag.governed_approval.store import (
    DurableGovernedApprovalStore,
    GovernedApprovalClaimDisposition,
    GovernedApprovalStoreCorruptionError,
    GovernedApprovalStoreUnavailableError,
)
from eag.governed_runtime.models import GovernedExecutionRequest

if TYPE_CHECKING:
    from eag.governed_session.models import RuntimeAvailability


class GovernedApprovalGate:
    """Record and validate human approval evidence without issuing sessions, permits, or execution."""

    def __init__(self, *, approval_store: DurableGovernedApprovalStore) -> None:
        if not callable(getattr(approval_store, "claim", None)) or not callable(
            getattr(approval_store, "read", None)
        ):
            raise TypeError("approval_store must expose claim(receipt) and read(approval_id)")
        if not isinstance(getattr(approval_store, "control_root", None), Path):
            raise TypeError("approval_store must expose a Path control_root")
        self._approval_store = approval_store

    def record(
        self,
        *,
        approval_id: str,
        approver_identity: str,
        occurred_at: datetime,
        disposition: GovernedApprovalDisposition,
        activation_receipt: GovernedActivationReceipt,
        activation_request: GovernedActivationRequest,
        runtime_request: GovernedExecutionRequest,
        audit_observer: object,
        runtime_availability: RuntimeAvailability,
    ) -> GovernedApprovalAdmission:
        """Persist one immutable human decision evidence record; no session or permit is created."""
        isolation_rejection = _store_isolation_rejection(self._approval_store, activation_request)
        if isolation_rejection is not None:
            return _rejected(isolation_rejection)
        receipt = _receipt_for(
            approval_id=approval_id,
            approver_identity=approver_identity,
            occurred_at=occurred_at,
            disposition=disposition,
            activation_receipt=activation_receipt,
            activation_request=activation_request,
            runtime_request=runtime_request,
            audit_observer=audit_observer,
            runtime_availability=runtime_availability,
        )
        try:
            claim = self._approval_store.claim(receipt)
        except GovernedApprovalStoreCorruptionError:
            return _rejected(GovernedApprovalRejectionReason.APPROVAL_STORE_CORRUPT)
        except GovernedApprovalStoreUnavailableError:
            return _rejected(GovernedApprovalRejectionReason.APPROVAL_STORE_UNAVAILABLE)
        if claim.disposition is GovernedApprovalClaimDisposition.CLAIMED:
            return GovernedApprovalAdmission(receipt=receipt)
        if claim.disposition is GovernedApprovalClaimDisposition.DUPLICATE:
            return _rejected(GovernedApprovalRejectionReason.APPROVAL_ID_DUPLICATE)
        return _rejected(GovernedApprovalRejectionReason.APPROVAL_ID_CONFLICT)

    def validate_for_session(
        self,
        *,
        approval_receipt: GovernedApprovalReceipt | None,
        activation_receipt: GovernedActivationReceipt,
        activation_request: GovernedActivationRequest,
        runtime_request: GovernedExecutionRequest,
        audit_observer: object,
        runtime_availability: RuntimeAvailability,
    ) -> GovernedApprovalRejectionReason | None:
        """Validate stored approval evidence before an existing session gate creates its own session."""
        if approval_receipt is None:
            return GovernedApprovalRejectionReason.MISSING_APPROVAL
        if not isinstance(approval_receipt, GovernedApprovalReceipt):
            return GovernedApprovalRejectionReason.APPROVAL_BINDING_MISMATCH
        isolation_rejection = _store_isolation_rejection(self._approval_store, activation_request)
        if isolation_rejection is not None:
            return isolation_rejection
        try:
            stored = self._approval_store.read(approval_id=approval_receipt.approval_id)
        except GovernedApprovalStoreCorruptionError:
            return GovernedApprovalRejectionReason.APPROVAL_STORE_CORRUPT
        except GovernedApprovalStoreUnavailableError:
            return GovernedApprovalRejectionReason.APPROVAL_STORE_UNAVAILABLE
        if stored is None:
            return GovernedApprovalRejectionReason.APPROVAL_UNKNOWN
        if stored != approval_receipt:
            return GovernedApprovalRejectionReason.APPROVAL_ID_CONFLICT
        expected = _receipt_for(
            approval_id=approval_receipt.approval_id,
            approver_identity=approval_receipt.approver_identity,
            occurred_at=approval_receipt.occurred_at,
            disposition=approval_receipt.disposition,
            activation_receipt=activation_receipt,
            activation_request=activation_request,
            runtime_request=runtime_request,
            audit_observer=audit_observer,
            runtime_availability=runtime_availability,
        )
        if expected != approval_receipt:
            return GovernedApprovalRejectionReason.APPROVAL_BINDING_MISMATCH
        if approval_receipt.disposition is GovernedApprovalDisposition.DENIED:
            return GovernedApprovalRejectionReason.APPROVAL_DENIED
        return None


def _rejected(reason: GovernedApprovalRejectionReason) -> GovernedApprovalAdmission:
    return GovernedApprovalAdmission(receipt=None, reason=reason)


def _store_isolation_rejection(
    store: DurableGovernedApprovalStore,
    activation_request: GovernedActivationRequest,
) -> GovernedApprovalRejectionReason | None:
    try:
        control_root = store.control_root.resolve()
        isolation = activation_request.isolation
        workspace_root = isolation.workspace_root.resolve() if isolation.workspace_root is not None else None
        source_root = (
            isolation.source_repository_root.resolve()
            if isolation.source_repository_root is not None
            else None
        )
        audit_root = isolation.audit_root.resolve() if isolation.audit_root is not None else None
    except OSError:
        return GovernedApprovalRejectionReason.APPROVAL_STORE_UNAVAILABLE
    if workspace_root is None or source_root is None or audit_root is None:
        return GovernedApprovalRejectionReason.APPROVAL_BINDING_MISMATCH
    if control_root in (workspace_root, source_root, audit_root) or any(
        control_root.is_relative_to(root) for root in (workspace_root, source_root, audit_root)
    ):
        return GovernedApprovalRejectionReason.APPROVAL_BINDING_MISMATCH
    return None


def _receipt_for(
    *,
    approval_id: str,
    approver_identity: str,
    occurred_at: datetime,
    disposition: GovernedApprovalDisposition,
    activation_receipt: GovernedActivationReceipt,
    activation_request: GovernedActivationRequest,
    runtime_request: GovernedExecutionRequest,
    audit_observer: object,
    runtime_availability: RuntimeAvailability,
) -> GovernedApprovalReceipt:
    return GovernedApprovalReceipt.issue(
        approval_id=approval_id,
        approver_identity=approver_identity,
        occurred_at=occurred_at,
        disposition=disposition,
        activation_id=activation_receipt.decision.activation_id,
        activation_receipt_digest=_activation_receipt_digest(activation_receipt),
        execution_id=runtime_request.execution_id,
        run_id=runtime_request.run_id,
        runtime_request_digest=_runtime_request_digest(runtime_request),
        provider_policy_digest=activation_receipt.policy_digest,
        isolation_binding_digest=_isolation_binding_digest(activation_request),
        audit_observer_identity=_observer_identity(audit_observer),
        runtime_id=runtime_availability.runtime_id,
    )


def _activation_receipt_digest(receipt: GovernedActivationReceipt) -> str:
    return _digest(
        {
            "activation_id": receipt.decision.activation_id,
            "disposition": receipt.decision.disposition.value,
            "execution_id": receipt.decision.execution_id,
            "policy_digest": receipt.policy_digest,
            "reason": receipt.decision.reason.value if receipt.decision.reason is not None else None,
        }
    )


def _isolation_binding_digest(request: GovernedActivationRequest) -> str:
    isolation = request.isolation
    assert isolation.workspace_root is not None
    assert isolation.audit_root is not None
    assert isolation.source_repository_root is not None
    return _digest(
        {
            "audit_root": str(isolation.audit_root.resolve()),
            "execution_id": isolation.execution_id,
            "source_repository_root": str(isolation.source_repository_root.resolve()),
            "workspace_root": str(isolation.workspace_root.resolve()),
        }
    )


def _runtime_request_digest(request: GovernedExecutionRequest) -> str:
    mutation_policy: MutationIntentPolicy = request.mutation_intent_policy
    return _digest(
        {
            "available_capability_ids": request.available_capability_ids,
            "budget": {
                "max_iterations": request.budget.max_iterations,
                "max_mutations": request.budget.max_mutations,
                "max_verifications": request.budget.max_verifications,
            },
            "contract_version": request.contract_version,
            "execution_id": request.execution_id,
            "goal_digest": hashlib.sha256(request.goal.encode()).hexdigest(),
            "known_constraints_digest": hashlib.sha256(
                "\n".join(request.known_constraints).encode()
            ).hexdigest(),
            "mutation_intent_policy": {
                "allowed_operations": mutation_policy.allowed_operations,
                "capability_id": mutation_policy.capability_id,
                "max_content_bytes": mutation_policy.max_content_bytes,
                "preservation_requirements": tuple(
                    (item.requirement_id, item.fingerprint)
                    for item in mutation_policy.preservation_requirements
                ),
                "schema_version": mutation_policy.schema_version,
            },
            "provider_policy_digest": _runtime_policy_digest(request.gateway_policy),
            "recovery_rule_representations": tuple(repr(item) for item in request.recovery_rules),
            "repository_path": str(request.repository_path.resolve()),
            "run_id": request.run_id,
            "workspace_root": str(request.workspace_root.resolve()),
        }
    )


def _runtime_policy_digest(policy: GatewayPolicy) -> str:
    return _digest(
        {
            "allow_fallback": policy.allow_fallback,
            "max_attempts": policy.max_attempts,
            "max_estimated_cost": policy.max_estimated_cost,
            "max_schema_repair_attempts": policy.max_schema_repair_attempts,
            "max_total_tokens": policy.max_total_tokens,
            "timeout_ms": policy.timeout_ms,
        }
    )


def _observer_identity(observer: object) -> str:
    return f"{type(observer).__module__}.{type(observer).__qualname__}:{id(observer)}"


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, separators=(",", ":"), sort_keys=True).encode()).hexdigest()


__all__ = ["GovernedApprovalGate"]
