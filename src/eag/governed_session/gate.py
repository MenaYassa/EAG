"""Single-use admission gate for a future existing governed-runtime start with durable replay claims."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from eag.chief.intelligence.gateway.models import GatewayPolicy, MutationIntentPolicy
from eag.governed_activation import (
    ActivationDisposition,
    GovernedActivationReceipt,
    GovernedActivationRequest,
    ProviderExecutionPolicy,
)
from eag.governed_audit.recorder import GovernedExecutionAuditObserver
from eag.governed_runtime.models import GovernedExecutionRequest
from eag.governed_session.ledger import (
    DurableReplayLedgerRecord,
    DurableSessionReplayLedger,
    ReplayLedgerClaim,
    ReplayLedgerClaimDisposition,
    ReplayLedgerCorruptionError,
    ReplayLedgerEntryKind,
    ReplayLedgerUnavailableError,
)
from eag.governed_session.models import (
    ControlledRuntimeSession,
    ControlledSessionAdmission,
    ControlledSessionDecision,
    RuntimeAvailability,
    SessionDisposition,
    SessionRejectionReason,
)


class ControlledRuntimeSessionGate:
    """Bind one approved activation to one durable, non-executing runtime-start permit."""

    def __init__(self, *, replay_ledger: DurableSessionReplayLedger) -> None:
        if not callable(getattr(replay_ledger, "claim", None)) or not callable(
            getattr(replay_ledger, "read", None)
        ):
            raise TypeError("replay_ledger must expose claim(record) and read(entry_kind, identity_key)")
        if not isinstance(getattr(replay_ledger, "control_root", None), Path):
            raise TypeError("replay_ledger must expose a Path control_root")
        self._replay_ledger = replay_ledger

    def create_session(
        self,
        *,
        activation_receipt: GovernedActivationReceipt | None,
        activation_request: GovernedActivationRequest,
        runtime_request: GovernedExecutionRequest,
        audit_observer: GovernedExecutionAuditObserver | None,
        runtime_availability: RuntimeAvailability | None,
    ) -> ControlledSessionAdmission:
        """Create one immutable start session after validation and durable activation claim; no runtime runs."""
        rejection = _binding_rejection(
            activation_receipt=activation_receipt,
            activation_request=activation_request,
            runtime_request=runtime_request,
            audit_observer=audit_observer,
            runtime_availability=runtime_availability,
        )
        if rejection is not None:
            return _rejected(rejection)
        ledger_rejection = _ledger_isolation_rejection(self._replay_ledger, activation_request)
        if ledger_rejection is not None:
            return _rejected(ledger_rejection)
        assert activation_receipt is not None
        assert audit_observer is not None
        assert runtime_availability is not None
        activation_record = _activation_record_for(activation_receipt)
        activation_claim, claim_rejection = _claim(self._replay_ledger, activation_record)
        if claim_rejection is not None:
            return _rejected(claim_rejection)
        assert activation_claim is not None
        if activation_claim.disposition is ReplayLedgerClaimDisposition.ALREADY_CLAIMED:
            return _rejected(SessionRejectionReason.ACTIVATION_RECEIPT_REPLAYED)
        if activation_claim.disposition is ReplayLedgerClaimDisposition.CONFLICT:
            return _rejected(SessionRejectionReason.REPLAY_LEDGER_CONFLICT)

        session = _session_for(
            activation_receipt,
            activation_request,
            runtime_request,
            audit_observer,
            runtime_availability,
        )
        session_claim, claim_rejection = _claim(self._replay_ledger, _issued_record_for(session))
        if claim_rejection is not None:
            return _rejected(claim_rejection)
        assert session_claim is not None
        if session_claim.disposition is not ReplayLedgerClaimDisposition.CLAIMED:
            return _rejected(SessionRejectionReason.REPLAY_LEDGER_CONFLICT)
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
        """Consume a bound durable session once and return only a start decision or refusal."""
        if not isinstance(session, ControlledRuntimeSession):
            raise TypeError("session must be a ControlledRuntimeSession")
        rejection = _binding_rejection(
            activation_receipt=activation_receipt,
            activation_request=activation_request,
            runtime_request=runtime_request,
            audit_observer=audit_observer,
            runtime_availability=runtime_availability,
        )
        if rejection is not None:
            return _rejected(rejection).decision
        ledger_rejection = _ledger_isolation_rejection(self._replay_ledger, activation_request)
        if ledger_rejection is not None:
            return _rejected(ledger_rejection).decision
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
        issued_record = _issued_record_for(session)
        stored_issue, read_rejection = _read(self._replay_ledger, issued_record)
        if read_rejection is not None:
            return _rejected(read_rejection).decision
        if stored_issue is None:
            return _rejected(SessionRejectionReason.SESSION_UNKNOWN).decision
        if stored_issue != issued_record:
            return _rejected(SessionRejectionReason.REPLAY_LEDGER_CONFLICT).decision
        consumed_claim, claim_rejection = _claim(self._replay_ledger, _consumed_record_for(session))
        if claim_rejection is not None:
            return _rejected(claim_rejection).decision
        assert consumed_claim is not None
        if consumed_claim.disposition is ReplayLedgerClaimDisposition.ALREADY_CLAIMED:
            return _rejected(SessionRejectionReason.SESSION_CONSUMED).decision
        if consumed_claim.disposition is ReplayLedgerClaimDisposition.CONFLICT:
            return _rejected(SessionRejectionReason.REPLAY_LEDGER_CONFLICT).decision
        return ControlledSessionDecision(
            disposition=SessionDisposition.RUNTIME_START_ALLOWED,
            session_id=session.session_id,
            execution_id=session.execution_id,
            run_id=session.run_id,
        )


def _claim(
    ledger: DurableSessionReplayLedger,
    record: DurableReplayLedgerRecord,
) -> tuple[ReplayLedgerClaim | None, SessionRejectionReason | None]:
    try:
        return ledger.claim(record), None
    except ReplayLedgerCorruptionError:
        return None, SessionRejectionReason.REPLAY_LEDGER_CORRUPT
    except ReplayLedgerUnavailableError:
        return None, SessionRejectionReason.REPLAY_LEDGER_UNAVAILABLE


def _read(
    ledger: DurableSessionReplayLedger,
    expected: DurableReplayLedgerRecord,
) -> tuple[DurableReplayLedgerRecord | None, SessionRejectionReason | None]:
    try:
        return ledger.read(entry_kind=expected.entry_kind, identity_key=expected.identity_key), None
    except ReplayLedgerCorruptionError:
        return None, SessionRejectionReason.REPLAY_LEDGER_CORRUPT
    except ReplayLedgerUnavailableError:
        return None, SessionRejectionReason.REPLAY_LEDGER_UNAVAILABLE


def _ledger_isolation_rejection(
    ledger: DurableSessionReplayLedger,
    activation_request: GovernedActivationRequest,
) -> SessionRejectionReason | None:
    try:
        control_root = ledger.control_root.resolve()
        isolation = activation_request.isolation
        workspace_root = isolation.workspace_root.resolve() if isolation.workspace_root is not None else None
        source_root = (
            isolation.source_repository_root.resolve()
            if isolation.source_repository_root is not None
            else None
        )
        audit_root = isolation.audit_root.resolve() if isolation.audit_root is not None else None
    except OSError:
        return SessionRejectionReason.REPLAY_LEDGER_UNAVAILABLE
    if workspace_root is None or source_root is None or audit_root is None:
        return SessionRejectionReason.ISOLATION_BINDING_MISMATCH
    if control_root in (workspace_root, source_root, audit_root) or any(
        control_root.is_relative_to(root) for root in (workspace_root, source_root, audit_root)
    ):
        return SessionRejectionReason.REPLAY_LEDGER_ISOLATION_MISMATCH
    return None


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


def _activation_record_for(receipt: GovernedActivationReceipt) -> DurableReplayLedgerRecord:
    return DurableReplayLedgerRecord(
        entry_kind=ReplayLedgerEntryKind.ACTIVATION_CLAIMED,
        identity_key=receipt.decision.activation_id,
        binding_digest=_receipt_digest(receipt),
    )


def _issued_record_for(session: ControlledRuntimeSession) -> DurableReplayLedgerRecord:
    return DurableReplayLedgerRecord(
        entry_kind=ReplayLedgerEntryKind.SESSION_ISSUED,
        identity_key=session.session_id,
        binding_digest=_session_binding_digest(session),
    )


def _consumed_record_for(session: ControlledRuntimeSession) -> DurableReplayLedgerRecord:
    return DurableReplayLedgerRecord(
        entry_kind=ReplayLedgerEntryKind.SESSION_CONSUMED,
        identity_key=session.session_id,
        binding_digest=_session_binding_digest(session),
    )


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


def _session_binding_digest(session: ControlledRuntimeSession) -> str:
    return _digest(
        {
            "activation_id": session.activation_id,
            "activation_receipt_digest": session.activation_receipt_digest,
            "audit_observer_identity": session.audit_observer_identity,
            "execution_id": session.execution_id,
            "isolation_binding_digest": session.isolation_binding_digest,
            "provider_policy_digest": session.provider_policy_digest,
            "request_digest": session.request_digest,
            "run_id": session.run_id,
            "runtime_id": session.runtime_id,
            "session_id": session.session_id,
        }
    )


def _observer_identity(observer: GovernedExecutionAuditObserver) -> str:
    return f"{type(observer).__module__}.{type(observer).__qualname__}:{id(observer)}"


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, separators=(",", ":"), sort_keys=True).encode()).hexdigest()


__all__ = ["ControlledRuntimeSessionGate"]
