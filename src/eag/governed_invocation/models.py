"""Immutable contracts for one controlled dispatch into a supplied governed runtime."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from eag.governed_activation import GovernedActivationReceipt, GovernedActivationRequest
from eag.governed_runtime.models import GovernedExecutionRequest, GovernedExecutionResult
from eag.governed_session import ControlledRuntimeSession, RuntimeAvailability


class GovernedInvocationError(ValueError):
    """Raised when an invocation contract is structurally incomplete."""


class InvocationDisposition(StrEnum):
    """One controlled invocation outcome without a retry or continuation handle."""

    RUNTIME_INVOKED = "runtime_invoked"
    SESSION_REFUSED = "session_refused"
    RUNTIME_FAILED_AFTER_CONSUMPTION = "runtime_failed_after_consumption"


class InvocationRejectionReason(StrEnum):
    """Typed refusal reasons evaluated before the supplied runtime is called."""

    MISSING_SESSION = "missing_session"
    EXECUTION_ID_MISMATCH = "execution_id_mismatch"
    RUN_ID_MISMATCH = "run_id_mismatch"
    RUNTIME_BINDING_MISMATCH = "runtime_binding_mismatch"
    INVALID_RUNTIME_EXECUTOR = "invalid_runtime_executor"


class GovernedRuntimeExecutor(Protocol):
    """Narrow protocol fulfilled by the existing G2.4.4 runtime or a deterministic test double."""

    def execute(self, request: GovernedExecutionRequest) -> GovernedExecutionResult: ...


def _require_non_empty(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GovernedInvocationError(f"{field_name} cannot be empty")
    return value


@dataclass(frozen=True, slots=True, kw_only=True)
class RuntimeExecutorBinding:
    """Identity-bound reference to a supplied runtime executor; it does not grant lifecycle authority."""

    runtime_id: str
    executor: GovernedRuntimeExecutor

    def __post_init__(self) -> None:
        object.__setattr__(self, "runtime_id", _require_non_empty(self.runtime_id, "runtime_id"))
        if not callable(getattr(self.executor, "execute", None)):
            raise TypeError("executor must expose callable execute(request)")


@dataclass(frozen=True, slots=True, kw_only=True)
class ControlledRuntimeInvocationRequest:
    """Exact activation/session/runtime bindings required for one controlled dispatch."""

    session: ControlledRuntimeSession | None
    activation_receipt: GovernedActivationReceipt | None
    activation_request: GovernedActivationRequest
    runtime_request: GovernedExecutionRequest
    # Opaque identity binding forwarded only to the existing session gate; never invoked here.
    audit_observer: object | None
    runtime_availability: RuntimeAvailability | None
    runtime_binding: RuntimeExecutorBinding

    def __post_init__(self) -> None:
        if not isinstance(self.activation_request, GovernedActivationRequest):
            raise TypeError("activation_request must be a GovernedActivationRequest")
        if not isinstance(self.runtime_request, GovernedExecutionRequest):
            raise TypeError("runtime_request must be a GovernedExecutionRequest")
        if not isinstance(self.runtime_binding, RuntimeExecutorBinding):
            raise TypeError("runtime_binding must be a RuntimeExecutorBinding")


@dataclass(frozen=True, slots=True, kw_only=True)
class ControlledRuntimeInvocationResult:
    """Immutable result of exactly one attempted controlled invocation."""

    disposition: InvocationDisposition
    session_id: str | None = None
    execution_id: str | None = None
    run_id: str | None = None
    runtime_result: GovernedExecutionResult | None = None
    refusal_reason: InvocationRejectionReason | None = None
    session_refusal_reason: str | None = None
    failure_type: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.disposition, InvocationDisposition):
            raise TypeError("disposition must be an InvocationDisposition")
        if self.disposition is InvocationDisposition.RUNTIME_INVOKED:
            if not isinstance(self.runtime_result, GovernedExecutionResult):
                raise GovernedInvocationError("invoked result requires a GovernedExecutionResult")
            if self.refusal_reason is not None or self.session_refusal_reason is not None:
                raise GovernedInvocationError("invoked result cannot carry refusal data")
            return
        if self.disposition is InvocationDisposition.SESSION_REFUSED:
            if self.refusal_reason is None and self.session_refusal_reason is None:
                raise GovernedInvocationError("session refusal requires a typed reason")
            if self.runtime_result is not None:
                raise GovernedInvocationError("session refusal cannot expose a runtime result")
            return
        if self.disposition is InvocationDisposition.RUNTIME_FAILED_AFTER_CONSUMPTION:
            if not self.failure_type:
                raise GovernedInvocationError("runtime failure requires a failure_type")
            if self.runtime_result is not None:
                raise GovernedInvocationError("runtime failure cannot expose a runtime result")
            if self.refusal_reason is not None or self.session_refusal_reason is not None:
                raise GovernedInvocationError("runtime failure cannot carry refusal data")
            return
        raise GovernedInvocationError("unsupported invocation disposition")


__all__ = [
    "ControlledRuntimeInvocationRequest",
    "ControlledRuntimeInvocationResult",
    "GovernedInvocationError",
    "GovernedRuntimeExecutor",
    "InvocationDisposition",
    "InvocationRejectionReason",
    "RuntimeExecutorBinding",
]
