"""Deterministic G2.4.1 transition controller with no operational integrations."""

from __future__ import annotations

from dataclasses import replace

from eag.events import EventBus
from eag.governed_execution.enums import (
    GovernedExecutionState,
    GovernedExecutionStopReason,
)
from eag.governed_execution.errors import IllegalTransitionError
from eag.governed_execution.events import (
    GovernedExecutionStarted,
    GovernedExecutionStopped,
    GovernedExecutionTransitioned,
)
from eag.governed_execution.models import (
    LEGAL_TRANSITIONS,
    ExecutionEvidenceRef,
    ExecutionTransitionRecord,
    GovernedExecutionContext,
    TransitionResult,
    _validate_terminal_stop_reason,
)


class GovernedExecutionStateMachine:
    """Own only immutable G2.4.1 state/ledger transitions and transition telemetry.

    The class never calls an LLM, a capability, a mutation runtime, a verifier,
    reflection, replanning, shell, Git, network, or credential service.
    """

    def __init__(self, event_bus: EventBus | None = None) -> None:
        self._event_bus = event_bus

    @staticmethod
    def is_legal(
        from_state: GovernedExecutionState,
        to_state: GovernedExecutionState,
    ) -> bool:
        """Return whether the approved G2.4.1 matrix allows the transition."""
        return to_state in LEGAL_TRANSITIONS[from_state]

    def transition(
        self,
        context: GovernedExecutionContext,
        target: GovernedExecutionState,
        *,
        evidence: tuple[ExecutionEvidenceRef, ...] = (),
        stop_reason: GovernedExecutionStopReason | None = None,
    ) -> TransitionResult:
        """Attempt one transition and return the old immutable context on rejection."""
        if not isinstance(target, GovernedExecutionState):
            raise TypeError("target must be a GovernedExecutionState")
        if not self.is_legal(context.state, target):
            return TransitionResult(
                accepted=False,
                context=context,
                error_code="illegal_transition",
            )
        try:
            next_context = self._advance(
                context,
                target,
                evidence=evidence,
                stop_reason=stop_reason,
            )
        except ValueError as error:
            return TransitionResult(
                accepted=False,
                context=context,
                error_code=_budget_or_validation_code(error),
            )
        self._publish(context, next_context)
        return TransitionResult(accepted=True, context=next_context)

    def transition_or_raise(
        self,
        context: GovernedExecutionContext,
        target: GovernedExecutionState,
        *,
        evidence: tuple[ExecutionEvidenceRef, ...] = (),
        stop_reason: GovernedExecutionStopReason | None = None,
    ) -> GovernedExecutionContext:
        """Strict variant that raises a typed exception for illegal transitions."""
        result = self.transition(
            context,
            target,
            evidence=evidence,
            stop_reason=stop_reason,
        )
        if result.accepted:
            return result.context
        if result.error_code == "illegal_transition":
            raise IllegalTransitionError(context.state, target)
        raise ValueError(result.error_code)

    def _advance(
        self,
        context: GovernedExecutionContext,
        target: GovernedExecutionState,
        *,
        evidence: tuple[ExecutionEvidenceRef, ...],
        stop_reason: GovernedExecutionStopReason | None,
    ) -> GovernedExecutionContext:
        budget = context.budget
        iteration = context.iteration
        exhausted_reason: GovernedExecutionStopReason | None = None
        if target is GovernedExecutionState.CONTEXT_ASSEMBLING:
            try:
                budget = budget.consume_iteration()
                iteration = budget.iterations_used
            except ValueError:
                target = GovernedExecutionState.FAILED
                exhausted_reason = GovernedExecutionStopReason.ITERATION_BUDGET_EXHAUSTED
        elif target is GovernedExecutionState.MUTATING:
            try:
                budget = budget.consume_mutation()
            except ValueError:
                target = GovernedExecutionState.FAILED
                exhausted_reason = GovernedExecutionStopReason.MUTATION_BUDGET_EXHAUSTED
        elif target is GovernedExecutionState.VERIFYING:
            try:
                budget = budget.consume_verification()
            except ValueError:
                target = GovernedExecutionState.FAILED
                exhausted_reason = GovernedExecutionStopReason.VERIFICATION_BUDGET_EXHAUSTED

        resolved_stop_reason = exhausted_reason or stop_reason
        _validate_terminal_stop_reason(target, resolved_stop_reason)
        record = ExecutionTransitionRecord(
            sequence=len(context.history) + 1,
            iteration=iteration,
            from_state=context.state,
            to_state=target,
            reason=resolved_stop_reason,
            evidence=evidence,
        )
        return replace(
            context,
            state=target,
            iteration=iteration,
            budget=budget,
            history=(*context.history, record),
            evidence=(*context.evidence, *evidence),
            stop_reason=resolved_stop_reason,
        )

    def _publish(
        self,
        previous: GovernedExecutionContext,
        current: GovernedExecutionContext,
    ) -> None:
        """Emit best-effort observations; event delivery never determines state correctness."""
        if self._event_bus is None:
            return
        record = current.history[-1]
        try:
            if previous.state is GovernedExecutionState.CREATED:
                self._event_bus.publish(
                    GovernedExecutionStarted(
                        execution_id=current.execution_id,
                        run_id=current.run_id,
                        iteration=current.iteration,
                        sequence=record.sequence,
                        state=current.state,
                    )
                )
            self._event_bus.publish(
                GovernedExecutionTransitioned(
                    execution_id=current.execution_id,
                    run_id=current.run_id,
                    iteration=current.iteration,
                    sequence=record.sequence,
                    from_state=previous.state,
                    to_state=current.state,
                    evidence_count=len(record.evidence),
                )
            )
            if current.state.is_terminal and current.stop_reason is not None:
                self._event_bus.publish(
                    GovernedExecutionStopped(
                        execution_id=current.execution_id,
                        run_id=current.run_id,
                        iteration=current.iteration,
                        sequence=record.sequence,
                        state=current.state,
                        reason=current.stop_reason,
                    )
                )
        except Exception:
            # Existing EventBus handlers execute synchronously and may raise. State
            # evolution is intentionally complete before telemetry is attempted.
            return


def _budget_or_validation_code(error: ValueError) -> str:
    message = str(error)
    if "budget" in message:
        return "budget_exhausted"
    if "stop_reason" in message or "stop reason" in message:
        return "invalid_stop_reason"
    return "invalid_transition_input"


__all__ = ["GovernedExecutionStateMachine", "LEGAL_TRANSITIONS"]
