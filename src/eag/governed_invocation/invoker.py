"""Single-dispatch bridge from a consumed controlled session permit to a supplied runtime."""

from __future__ import annotations

from typing import Any, cast

from eag.governed_invocation.models import (
    ControlledRuntimeInvocationRequest,
    ControlledRuntimeInvocationResult,
    InvocationDisposition,
    InvocationRejectionReason,
)
from eag.governed_session import ControlledRuntimeSessionGate, SessionDisposition


class ControlledRuntimeInvoker:
    """Invoke a supplied runtime once only after the existing session gate admits its exact bindings."""

    def __init__(self, *, session_gate: ControlledRuntimeSessionGate) -> None:
        if not isinstance(session_gate, ControlledRuntimeSessionGate):
            raise TypeError("session_gate must be a ControlledRuntimeSessionGate")
        self._session_gate = session_gate

    def invoke(self, request: ControlledRuntimeInvocationRequest) -> ControlledRuntimeInvocationResult:
        """Consume one valid session permit and dispatch the exact bound runtime request once."""
        if not isinstance(request, ControlledRuntimeInvocationRequest):
            raise TypeError("request must be a ControlledRuntimeInvocationRequest")
        rejection = _pre_dispatch_rejection(request)
        if rejection is not None:
            return _refused(request, refusal_reason=rejection)
        assert request.session is not None
        assert request.runtime_availability is not None
        session_decision = self._session_gate.consume_for_runtime_start(
            session=request.session,
            activation_receipt=request.activation_receipt,
            activation_request=request.activation_request,
            runtime_request=request.runtime_request,
            audit_observer=cast(Any, request.audit_observer),
            runtime_availability=request.runtime_availability,
        )
        if session_decision.disposition is not SessionDisposition.RUNTIME_START_ALLOWED:
            reason = session_decision.reason
            return _refused(
                request,
                session_refusal_reason=reason.value if reason is not None else "session_refused",
            )
        try:
            result = request.runtime_binding.executor.execute(request.runtime_request)
        except Exception as error:
            return ControlledRuntimeInvocationResult(
                disposition=InvocationDisposition.RUNTIME_FAILED_AFTER_CONSUMPTION,
                session_id=request.session.session_id,
                execution_id=request.session.execution_id,
                run_id=request.session.run_id,
                failure_type=type(error).__name__,
            )
        return ControlledRuntimeInvocationResult(
            disposition=InvocationDisposition.RUNTIME_INVOKED,
            session_id=request.session.session_id,
            execution_id=request.session.execution_id,
            run_id=request.session.run_id,
            runtime_result=result,
        )


def _pre_dispatch_rejection(
    request: ControlledRuntimeInvocationRequest,
) -> InvocationRejectionReason | None:
    session = request.session
    if session is None:
        return InvocationRejectionReason.MISSING_SESSION
    if session.execution_id != request.runtime_request.execution_id:
        return InvocationRejectionReason.EXECUTION_ID_MISMATCH
    if session.run_id != request.runtime_request.run_id:
        return InvocationRejectionReason.RUN_ID_MISMATCH
    availability = request.runtime_availability
    if availability is None or availability.runtime_id != session.runtime_id:
        return InvocationRejectionReason.RUNTIME_BINDING_MISMATCH
    if request.runtime_binding.runtime_id != session.runtime_id:
        return InvocationRejectionReason.RUNTIME_BINDING_MISMATCH
    return None


def _refused(
    request: ControlledRuntimeInvocationRequest,
    *,
    refusal_reason: InvocationRejectionReason | None = None,
    session_refusal_reason: str | None = None,
) -> ControlledRuntimeInvocationResult:
    session = request.session
    return ControlledRuntimeInvocationResult(
        disposition=InvocationDisposition.SESSION_REFUSED,
        session_id=session.session_id if session is not None else None,
        execution_id=session.execution_id if session is not None else request.runtime_request.execution_id,
        run_id=session.run_id if session is not None else request.runtime_request.run_id,
        refusal_reason=refusal_reason,
        session_refusal_reason=session_refusal_reason,
    )


__all__ = ["ControlledRuntimeInvoker"]
