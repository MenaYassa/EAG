"""Pure, single-use admission gate for a future existing governed-runtime start."""

from __future__ import annotations

import hashlib
import json
from threading import RLock

from eag.chief.intelligence.gateway.models import GatewayPolicy, MutationIntentPolicy
from eag.governed_activation import (
    ActivationDisposition,
    GovernedActivationReceipt,
    GovernedActivationRequest,
    ProviderExecutionPolicy,
)
from eag.governed_audit.recorder import GovernedExecutionAuditObserver
from eag.governed_runtime.models import GovernedExecutionRequest
from eag.governed_session.models import (
    ControlledRuntimeSession,
    ControlledSessionAdmission,
    ControlledSessionDecision,
    RuntimeAvailability,
    SessionDisposition,
    SessionRejectionReason,
)

_PROCESS_DOMAIN_LOCK = RLock()
_PROCESS_DOMAIN_SESSIONS: dict[str, ControlledRuntimeSession] = {}
_PROCESS_DOMAIN_ACTIVATION_IDS: set[str] = set()
_PROCESS_DOMAIN_CONSUMED_SESSION_IDS: set[str] = set()


class ControlledRuntimeSessionGate:
    """Bind one approved activation to one process-wide, non-executing start permit."""

    def create_session(
        self,
        *,
        activation_receipt: GovernedActivationReceipt | None,
        activation_request: GovernedActivationRequest,
        runtime_request: GovernedExecutionRequest,
        audit_observer: GovernedExecutionAuditObserver | None,
        runtime_availability: RuntimeAvailability | None,
    ) -> ControlledSessionAdmission:
        """Create one immutable start session after pure binding validation; no runtime is invoked."""
        rejection = _binding_rejection(
            activation_receipt=activation_receipt,
            activation_request=activation_request,
            runtime_request=runtime_request,
            audit_observer=audit_observer,
            runtime_availability=runtime_availability,
        )
        if rejection is not None:
            return _rejected(rejection)
        assert activation_receipt is not None
        assert audit_observer is not None
        assert runtime_availability is not None
        activation_id = activation_receipt.decision.activation_id
        with _PROCESS_DOMAIN_LOCK:
            if activation_id in _PROCESS_DOMAIN_ACTIVATION_IDS:
                return _rejected(SessionRejectionReason.ACTIVATION_RECEIPT_REPLAYED)
            session = _session_for(
                activation_receipt,
                activation_request,
                runtime_request,
                audit_observer,
                runtime_availability,
            )
            _PROCESS_DOMAIN_SESSIONS[session.session_id] = session
            _PROCESS_DOMAIN_ACTIVATION_IDS.add(activation_id)
        return ControlledSessionAdmission(
            session=session,
            decision=ControlledSessionDecision(
                disposition=SessionDisposition.SESSION_CREATED,
                session_id=session.session_id,
                execution_id=session.execution_id,
                run_id=session.run_id,
            ),
        )

    def consume_for_runtime_start(
        self,
        *,
        session: ControlledRuntimeSession,
        activation_receipt: GovernedActivationReceipt | None,
        activation_request: GovernedActivationRequest,
        runtime_request: GovernedExecutionRequest,
        audit_observer: GovernedExecutionAuditObserver | None,
        runtime_availability: RuntimeAvailability | None,
    ) -> ControlledSessionDecision:
        """Consume a bound session once and return only a non-executing start permit or refusal."""
        if not isinstance(session, ControlledRuntimeSession):
            raise TypeError("session must be a ControlledRuntimeSession")
        with _PROCESS_DOMAIN_LOCK:
            stored = _PROCESS_DOMAIN_SESSIONS.get(session.session_id)
            if stored is None:
                return _rejected(SessionRejectionReason.SESSION_UNKNOWN).decision
            if stored != session:
                return _rejected(SessionRejectionReason.REQUEST_IDENTITY_MISMATCH).decision
            if session.session_id in _PROCESS_DOMAIN_CONSUMED_SESSION_IDS:
                return _rejected(SessionRejectionReason.SESSION_CONSUMED).decision
            rejection = _binding_rejection(
                activation_receipt=activation_receipt,
                activation_request=activation_request,
                runtime_request=runtime_request,
                audit_observer=audit_observer,
                runtime_availability=runtime_availability,
            )
            if rejection is not None:
                return _rejected(rejection).decision
            assert activation_receipt is not None
            assert audit_observer is not None
            assert runtime_availability is not None
            expected = _session_for(
                activation_receipt,
                activation_request,
                runtime_request,
                audit_observer,
                runtime_availability,
            )
            if expected != session:
                return _rejected(_session_mismatch_reason(session, expected)).decision
            _PROCESS_DOMAIN_CONSUMED_SESSION_IDS.add(session.session_id)
        return ControlledSessionDecision(
            disposition=SessionDisposition.RUNTIME_START_ALLOWED,
            session_id=session.session_id,
            execution_id=session.execution_id,
            run_id=session.run_id,
        )


def _binding_rejection(
    *,
    activation_receipt: GovernedActivationReceipt | None,
    activation_request: GovernedActivationRequest,
    runtime_request: GovernedExecutionRequest,
    audit_observer: GovernedExecutionAuditObserver | None,
    runtime_availability: RuntimeAvailability | None,
) -> SessionRejectionReason | None:
    if activation_receipt is None:
        return SessionRejectionReason.MISSING_ACTIVATION_RECEIPT
    if activation_receipt.decision.disposition is not ActivationDisposition.APPROVED_TO_START:
        return SessionRejectionReason.ACTIVATION_NOT_APPROVED
    if runtime_availability is None or not runtime_availability.available:
        return SessionRejectionReason.RUNTIME_UNAVAILABLE
    if activation_request.confirmation is None or activation_request.provider_policy is None:
        return SessionRejectionReason.ACTIVATION_RECEIPT_MISMATCH
    if activation_request.audit_observer is None or audit_observer is None:
        return SessionRejectionReason.AUDIT_BINDING_MISMATCH
    if activation_request.audit_observer is not audit_observer:
        return SessionRejectionReason.AUDIT_BINDING_MISMATCH
    if activation_request.isolation.execution_id != runtime_request.execution_id:
        return SessionRejectionReason.EXECUTION_ID_MISMATCH
    if activation_receipt.decision.execution_id != runtime_request.execution_id:
        return SessionRejectionReason.EXECUTION_ID_MISMATCH
    if activation_request.confirmation.execution_id != runtime_request.execution_id:
        return SessionRejectionReason.EXECUTION_ID_MISMATCH
    if activation_receipt.policy_digest != _activation_policy_digest(activation_request.provider_policy):
        return SessionRejectionReason.ACTIVATION_RECEIPT_MISMATCH
    if activation_receipt.policy_digest != _runtime_policy_digest(runtime_request.gateway_policy):
        return SessionRejectionReason.PROVIDER_POLICY_MISMATCH
    workspace_root = activation_request.isolation.workspace_root
    audit_root = activation_request.isolation.audit_root
    source_root = activation_request.isolation.source_repository_root
    if workspace_root is None or audit_root is None or source_root is None:
        return SessionRejectionReason.ISOLATION_BINDING_MISMATCH
    if (
        runtime_request.workspace_root.resolve() != workspace_root.resolve()
        or runtime_request.repository_path.resolve() != workspace_root.resolve()
    ):
        return SessionRejectionReason.ISOLATION_BINDING_MISMATCH
    return None


def _session_for(
    activation_receipt: GovernedActivationReceipt,
    activation_request: GovernedActivationRequest,
    runtime_request: GovernedExecutionRequest,
    audit_observer: GovernedExecutionAuditObserver,
    runtime_availability: RuntimeAvailability,
) -> ControlledRuntimeSession:
    receipt_digest = _receipt_digest(activation_receipt)
    request_digest = _runtime_request_digest(runtime_request)
    isolation_digest = _isolation_digest(activation_request)
    observer_identity = _observer_identity(audit_observer)
    session_id = _digest(
        {
            "activation_receipt_digest": receipt_digest,
            "audit_observer_identity": observer_identity,
            "isolation_binding_digest": isolation_digest,
            "request_digest": request_digest,
            "runtime_id": runtime_availability.runtime_id,
        }
    )
    return ControlledRuntimeSession(
        session_id=session_id,
        activation_id=activation_receipt.decision.activation_id,
        activation_receipt_digest=receipt_digest,
        execution_id=runtime_request.execution_id,
        run_id=runtime_request.run_id,
        request_digest=request_digest,
        provider_policy_digest=activation_receipt.policy_digest,
        isolation_binding_digest=isolation_digest,
        audit_observer_identity=observer_identity,
        runtime_id=runtime_availability.runtime_id,
    )


def _session_mismatch_reason(
    actual: ControlledRuntimeSession,
    expected: ControlledRuntimeSession,
) -> SessionRejectionReason:
    if actual.activation_receipt_digest != expected.activation_receipt_digest:
        return SessionRejectionReason.ACTIVATION_RECEIPT_MISMATCH
    if actual.execution_id != expected.execution_id:
        return SessionRejectionReason.EXECUTION_ID_MISMATCH
    if actual.run_id != expected.run_id:
        return SessionRejectionReason.RUN_ID_MISMATCH
    if actual.provider_policy_digest != expected.provider_policy_digest:
        return SessionRejectionReason.PROVIDER_POLICY_MISMATCH
    if actual.isolation_binding_digest != expected.isolation_binding_digest:
        return SessionRejectionReason.ISOLATION_BINDING_MISMATCH
    if actual.audit_observer_identity != expected.audit_observer_identity:
        return SessionRejectionReason.AUDIT_BINDING_MISMATCH
    return SessionRejectionReason.REQUEST_IDENTITY_MISMATCH


def _rejected(reason: SessionRejectionReason) -> ControlledSessionAdmission:
    return ControlledSessionAdmission(
        session=None,
        decision=ControlledSessionDecision(
            disposition=SessionDisposition.REJECTED,
            reason=reason,
        ),
    )


def _activation_policy_digest(policy: ProviderExecutionPolicy) -> str:
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


def _receipt_digest(receipt: GovernedActivationReceipt) -> str:
    return _digest(
        {
            "activation_id": receipt.decision.activation_id,
            "disposition": receipt.decision.disposition.value,
            "execution_id": receipt.decision.execution_id,
            "policy_digest": receipt.policy_digest,
            "reason": receipt.decision.reason.value if receipt.decision.reason is not None else None,
        }
    )


def _isolation_digest(request: GovernedActivationRequest) -> str:
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


def _observer_identity(observer: GovernedExecutionAuditObserver) -> str:
    return f"{type(observer).__module__}.{type(observer).__qualname__}:{id(observer)}"


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, separators=(",", ":"), sort_keys=True).encode()).hexdigest()


__all__ = ["ControlledRuntimeSessionGate"]
