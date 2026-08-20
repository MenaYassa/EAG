"""Autonomous Loop Runtime for EAG."""

import time
from datetime import UTC, datetime
from typing import Any

from eag.autonomous.approval import ApprovalRuntime
from eag.autonomous.completion import CompletionEngine
from eag.autonomous.enums import (
    CompletionAction,
    LoopOutcome,
    LoopState,
    RecoveryActionType,
    RecoveryPolicy,
)
from eag.autonomous.models import (
    LoopContext,
    LoopDecision,
    LoopIteration,
    LoopMetrics,
    LoopResult,
)
from eag.autonomous.recovery import RecoveryEngine
from eag.chief.runtime import ChiefRuntime, RunContext
from eag.events import EventBus
from eag.memory import MemoryRuntime
from eag.reflection import ReflectionRuntime
from eag.reflection.models import ReflectionContext


class AutonomousLoopRuntime:
    """Run the deterministic autonomous engineering loop through a Chief.

    The loop owns iteration, reflection, memory storage, completion, recovery,
    and approval. The supplied Chief owns the Coordinator that executes a
    single engineering run. This keeps runtime ownership public and stable.
    """

    def __init__(
        self,
        chief_runtime: ChiefRuntime,
        reflection_runtime: ReflectionRuntime,
        memory_runtime: MemoryRuntime,
        completion_engine: CompletionEngine | None = None,
        recovery_engine: RecoveryEngine | None = None,
        approval_runtime: ApprovalRuntime | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self._chief = chief_runtime
        self._reflection = reflection_runtime
        self._memory = memory_runtime
        self._completion = completion_engine or CompletionEngine()
        self._recovery = recovery_engine or RecoveryEngine()
        self._approval = approval_runtime or ApprovalRuntime()
        self._event_bus = event_bus or EventBus()
        self._plan_history: list[str] = []

    @property
    def chief_runtime(self) -> ChiefRuntime:
        """Return the Chief that owns the loop's Coordinator."""
        return self._chief

    @property
    def reflection_runtime(self) -> ReflectionRuntime:
        """Return the loop reflection runtime."""
        return self._reflection

    @property
    def memory_runtime(self) -> MemoryRuntime:
        """Return the loop memory runtime."""
        return self._memory

    @property
    def event_bus(self) -> EventBus:
        """Return the loop event bus."""
        return self._event_bus

    @property
    def completion_engine(self) -> CompletionEngine:
        """Return the loop completion policy."""
        return self._completion

    def execute(self, context: LoopContext) -> LoopResult:
        """Execute until completion, approval pause, recovery abort, or exhaustion."""
        start_time = time.monotonic()
        iterations: list[LoopIteration] = []
        state = LoopState.RUNNING
        outcome = LoopOutcome.CONTINUE
        final_decision: LoopDecision | None = None
        self._plan_history = []

        for iteration_number in range(1, context.max_iterations + 1):
            iteration_started = time.monotonic()
            chief_context = RunContext(goal_text=context.goal, metadata=context.metadata)
            run_result = self._chief.execute_goal(chief_context)

            state = LoopState.REFLECTING
            reflection_context = ReflectionContext(run_id=run_result.run_id, run_result=run_result)
            reflection_report = self._reflection.reflect(reflection_context)
            memory_entry = self._memory.store_reflection(reflection_context, reflection_report)

            plan_signature = self._get_plan_signature(run_result.plan)
            self._plan_history.append(plan_signature)

            if self._is_oscillating():
                state = LoopState.ABORTED
                outcome = LoopOutcome.FAILED
                final_decision = LoopDecision(
                    continue_loop=False,
                    reason="Oscillation detected: The planner is cycling between the same plans without progress.",
                    action=CompletionAction.ESCALATE,
                    recovery_policy=RecoveryPolicy.ABORT,
                    confidence=1.0,
                )
                iterations.append(
                    self._create_iteration(
                        iteration_number,
                        run_result,
                        reflection_report.id,
                        memory_entry.id,
                        iteration_started,
                    )
                )
                break

            state = LoopState.REPLANNING
            decision = self._completion.evaluate(
                run_result, reflection_report, iteration_number, context.max_iterations
            )

            if decision.requires_human:
                state = LoopState.WAITING_APPROVAL
                outcome = LoopOutcome.WAITING_APPROVAL
                approval_request = self._approval.request_approval(
                    loop_id=context.loop_id,
                    iteration=iteration_number,
                    reason=decision.reason,
                )
                iterations.append(
                    self._create_iteration(
                        iteration_number,
                        run_result,
                        reflection_report.id,
                        memory_entry.id,
                        iteration_started,
                    )
                )
                total_duration = (time.monotonic() - start_time) * 1000
                return LoopResult(
                    loop_id=context.loop_id,
                    state=state,
                    outcome=outcome,
                    iterations=tuple(iterations),
                    final_decision=decision,
                    metrics=self._calculate_metrics(iterations, total_duration),
                    summary=f"Loop paused for human approval: {decision.reason}",
                    duration_ms=total_duration,
                    pending_approval_id=approval_request.id,
                )

            if decision.action == CompletionAction.REPLAN:
                recovery_action = self._recovery.evaluate(run_result, decision)
                if recovery_action.action_type == RecoveryActionType.ABORT:
                    state = LoopState.ABORTED
                    outcome = LoopOutcome.FAILED
                    final_decision = decision
                    iterations.append(
                        self._create_iteration(
                            iteration_number,
                            run_result,
                            reflection_report.id,
                            memory_entry.id,
                            iteration_started,
                        )
                    )
                    break

            iterations.append(
                self._create_iteration(
                    iteration_number,
                    run_result,
                    reflection_report.id,
                    memory_entry.id,
                    iteration_started,
                )
            )

            if not decision.continue_loop:
                state = (
                    LoopState.COMPLETED
                    if decision.action == CompletionAction.STOP
                    else LoopState.FAILED
                )
                outcome = (
                    LoopOutcome.FINISHED
                    if decision.action == CompletionAction.STOP
                    else LoopOutcome.FAILED
                )
                final_decision = decision
                break

            final_decision = decision

        if outcome == LoopOutcome.CONTINUE:
            state = LoopState.FAILED
            outcome = LoopOutcome.FAILED
            final_decision = LoopDecision(
                continue_loop=False,
                reason="Max iterations reached without completion.",
                action=CompletionAction.ESCALATE,
                confidence=1.0,
            )

        total_duration = (time.monotonic() - start_time) * 1000
        return LoopResult(
            loop_id=context.loop_id,
            state=state,
            outcome=outcome,
            iterations=tuple(iterations),
            final_decision=final_decision,
            metrics=self._calculate_metrics(iterations, total_duration),
            summary=f"Loop finished with outcome: {outcome.value}",
            duration_ms=total_duration,
        )

    def resume(
        self, loop_result: LoopResult, approved: bool, reviewer: str = "human"
    ) -> LoopResult:
        """Resume a paused loop after a human decision."""
        if loop_result.state != LoopState.WAITING_APPROVAL:
            raise ValueError("Can only resume a loop waiting for approval.")
        if loop_result.pending_approval_id is None:
            raise ValueError("Paused loop result is missing an approval identifier.")

        self._approval.record_decision(
            approval_id=loop_result.pending_approval_id,
            approved=approved,
            reviewer=reviewer,
        )

        if approved:
            return LoopResult(
                loop_id=loop_result.loop_id,
                state=LoopState.COMPLETED,
                outcome=LoopOutcome.FINISHED,
                iterations=loop_result.iterations,
                final_decision=loop_result.final_decision,
                metrics=loop_result.metrics,
                summary="Loop resumed and approved.",
                duration_ms=loop_result.duration_ms,
            )

        return LoopResult(
            loop_id=loop_result.loop_id,
            state=LoopState.ABORTED,
            outcome=LoopOutcome.FAILED,
            iterations=loop_result.iterations,
            final_decision=loop_result.final_decision,
            metrics=loop_result.metrics,
            summary="Loop aborted due to rejection.",
            duration_ms=loop_result.duration_ms,
        )

    def _create_iteration(
        self,
        iteration_number: int,
        run_result: Any,
        reflection_id: str,
        memory_id: str,
        iteration_started: float,
    ) -> LoopIteration:
        plan = getattr(run_result, "plan", None)
        return LoopIteration(
            iteration_number=iteration_number,
            run_id=run_result.run_id,
            plan_id=plan.plan_id if plan is not None else "",
            reflection_id=reflection_id,
            memory_id=memory_id,
            planning_decision_id=self._planning_decision_id(run_result),
            finished_at=datetime.now(UTC),
            duration_ms=(time.monotonic() - iteration_started) * 1000,
            success=self._is_success(run_result.outcome),
        )

    @staticmethod
    def _planning_decision_id(run_result: Any) -> str | None:
        decision = getattr(run_result, "planning_decision", None)
        identifier = getattr(decision, "id", None)
        return identifier if isinstance(identifier, str) else None

    @staticmethod
    def _get_plan_signature(plan: Any) -> str:
        """Create a deterministic plan signature for cycle detection."""
        if not plan or not hasattr(plan, "steps"):
            return "no_plan"
        return "|".join(sorted(step.capability_id for step in plan.steps))

    def _is_oscillating(self) -> bool:
        """Detect a repeating A → B → A → B plan cycle."""
        if len(self._plan_history) < 4:
            return False
        return (
            self._plan_history[-1] != self._plan_history[-2]
            and self._plan_history[-1] == self._plan_history[-3]
            and self._plan_history[-2] == self._plan_history[-4]
        )

    @staticmethod
    def _is_success(outcome: Any) -> bool:
        """Return whether a run outcome represents success."""
        return (
            outcome == "success"
            or getattr(outcome, "value", None) == "success"
            or str(outcome).lower().endswith("success")
        )

    @staticmethod
    def _calculate_metrics(
        iterations: list[LoopIteration], total_duration: float
    ) -> LoopMetrics:
        return LoopMetrics(
            total_iterations=len(iterations),
            successful_iterations=sum(1 for iteration in iterations if iteration.success),
            failed_iterations=sum(1 for iteration in iterations if not iteration.success),
            total_duration_ms=total_duration,
            replans_triggered=sum(
                1 for iteration in iterations if iteration.planning_decision_id is not None
            ),
        )
