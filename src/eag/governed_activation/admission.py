"""Pure admission control for prospective governed execution activation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from eag.governed_activation.models import (
    ActivationDisposition,
    ActivationRejectionReason,
    GovernedActivationDecision,
    GovernedActivationReceipt,
    GovernedActivationRequest,
    ProviderExecutionPolicy,
    activation_id_for,
)


class GovernedActivationAdmission:
    """Validate opt-in activation prerequisites without composing or executing a runtime."""

    def admit(self, request: GovernedActivationRequest) -> GovernedActivationReceipt:
        """Return a redacted approval or typed refusal before any operational effect exists."""
        if not isinstance(request, GovernedActivationRequest):
            raise TypeError("request must be a GovernedActivationRequest")

        execution_id = request.isolation.execution_id
        confirmation = request.confirmation
        activation_id = activation_id_for(
            confirmation.confirmation_id if confirmation is not None else "missing-confirmation",
            execution_id or "missing-execution-id",
        )
        rejection = self._rejection_reason(request)
        decision = GovernedActivationDecision(
            disposition=(
                ActivationDisposition.REJECTED
                if rejection is not None
                else ActivationDisposition.APPROVED_TO_START
            ),
            execution_id=execution_id or "missing-execution-id",
            activation_id=activation_id,
            reason=rejection,
        )
        return GovernedActivationReceipt(decision=decision, policy_digest=_policy_digest(request.provider_policy))

    @staticmethod
    def _rejection_reason(request: GovernedActivationRequest) -> ActivationRejectionReason | None:
        isolation = request.isolation
        if not isolation.execution_id.strip():
            return ActivationRejectionReason.EMPTY_EXECUTION_ID
        if request.confirmation is None:
            return ActivationRejectionReason.MISSING_CALLER_CONFIRMATION
        if not request.confirmation.affirmed or request.confirmation.execution_id != isolation.execution_id:
            return ActivationRejectionReason.INVALID_CALLER_CONFIRMATION
        if request.provider_policy is None:
            return ActivationRejectionReason.MISSING_PROVIDER_POLICY
        if not _is_valid_provider_policy(request.provider_policy):
            return ActivationRejectionReason.INVALID_PROVIDER_POLICY
        if request.audit_observer is None or not _is_audit_observer(request.audit_observer):
            return ActivationRejectionReason.MISSING_AUDIT_OBSERVER
        if (
            isolation.workspace_root is None
            or isolation.audit_root is None
            or isolation.source_repository_root is None
        ):
            return ActivationRejectionReason.MISSING_ISOLATION_ROOT
        workspace_root = isolation.workspace_root.resolve()
        audit_root = isolation.audit_root.resolve()
        source_root = isolation.source_repository_root.resolve()
        if workspace_root == source_root:
            return ActivationRejectionReason.SOURCE_WORKSPACE_SELECTED
        if audit_root == workspace_root:
            return ActivationRejectionReason.IDENTICAL_WORKSPACE_AND_AUDIT_ROOT
        if audit_root == source_root or audit_root.is_relative_to(source_root):
            return ActivationRejectionReason.AUDIT_ROOT_INSIDE_SOURCE_REPOSITORY
        if audit_root.is_relative_to(workspace_root):
            return ActivationRejectionReason.AUDIT_ROOT_INSIDE_WORKSPACE
        if not _is_available_audit_root(audit_root):
            return ActivationRejectionReason.AUDIT_ROOT_UNAVAILABLE
        return None


def admit_governed_activation(request: GovernedActivationRequest) -> GovernedActivationReceipt:
    """Convenience pure admission entry point for explicit library callers."""
    return GovernedActivationAdmission().admit(request)


def _is_valid_provider_policy(policy: ProviderExecutionPolicy) -> bool:
    return (
        policy.max_attempts == 1
        and policy.allow_fallback is False
        and policy.max_schema_repair_attempts == 0
        and policy.timeout_ms > 0
        and policy.max_total_tokens > 0
        and policy.max_estimated_cost > 0
    )


def _is_audit_observer(observer: object) -> bool:
    return callable(getattr(observer, "preflight", None)) and callable(
        getattr(observer, "record_terminal_result", None)
    )


def _is_available_audit_root(audit_root: Path) -> bool:
    """Check only path availability; this function never creates, opens, or writes a directory."""
    if audit_root.exists() and not audit_root.is_dir():
        return False
    return audit_root.parent.exists() and audit_root.parent.is_dir()


def _policy_digest(policy: ProviderExecutionPolicy | None) -> str:
    """Hash a redacted provider-control declaration without retaining provider credentials."""
    if policy is None:
        payload: dict[str, object] = {"provider_policy": None}
    else:
        payload = {
            "allow_fallback": policy.allow_fallback,
            "max_attempts": policy.max_attempts,
            "max_estimated_cost": policy.max_estimated_cost,
            "max_schema_repair_attempts": policy.max_schema_repair_attempts,
            "max_total_tokens": policy.max_total_tokens,
            "timeout_ms": policy.timeout_ms,
        }
    return hashlib.sha256(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()


__all__ = ["GovernedActivationAdmission", "admit_governed_activation"]
