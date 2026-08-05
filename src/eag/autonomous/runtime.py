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
from eag.chief.runtime.coordinator import Coordinator
from eag.chief.runtime import RunContext
from eag.events import EventBus
from eag.memory import MemoryRuntime
from eag.reflection import ReflectionRuntime
from eag.reflection.models import ReflectionContext


class AutonomousLoopRuntime:
    """Orchestrates the continuous autonomous engineering loop with approval, recovery, and oscillation detection."""

    def __init__(
        self,
        coordinator: Coordinator,
        reflection_runtime: ReflectionRuntime,
        memory_runtime: MemoryRuntime,
        completion_engine: CompletionEngine | None = None,
        recovery_engine: RecoveryEngine | None = None,
        approval_runtime: ApprovalRuntime | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self._coordinator = coordinator
        self._reflection = reflection_runtime
        self._memory = memory_runtime
        self._completion = completion_engine or CompletionEngine()
        self._recovery = recovery_engine or RecoveryEngine()
        self._approval = approval_runtime or ApprovalRuntime()
        self._event_bus = event_bus or EventBus()
        self._plan_history: list[str] = []  # Reset per execution

    def execute(self, context: LoopContext) -> LoopResult:
        """Executes the autonomous loop until completion, max iterations, approval pause, or oscillation abort."""
        start_time = time.monotonic()
        iterations: list[LoopIteration] = []
        state = LoopState.RUNNING
        outcome = LoopOutcome.CONTINUE
        final_decision: LoopDecision | None = None
        pending_approval_id: str | None = None
        self._plan_history = []  # Reset history for this execution

        # Ensure Coordinator has access to memory for adaptive planning
        self._coordinator._memory = self._memory

        for i in range(1, context.max_iterations + 1):
            iter_start = time.monotonic()

            # 1. Execute via Coordinator (no capability_runtime argument)
            chief_ctx = RunContext(goal_text=context.goal, metadata=context.metadata)
            run_result = self._coordinator.run(chief_ctx)
            print(f"Iteration {i}: outcome={run_result.outcome}, plan_steps={len(run_result.plan.steps) if run_result.plan else 0}")
            # 2. Reflect
            state = LoopState.REFLECTING
            ref_ctx = ReflectionContext(run_id=run_result.run_id, run_result=run_result)
            ref_report = self._reflection.reflect(ref_ctx)

            # 3. Remember
            mem_entry = self._memory.store_reflection(ref_ctx, ref_report)

            # 4. Track plan signature for oscillation detection
            plan_signature = self._get_plan_signature(run_result.plan)
            self._plan_history.append(plan_signature)

            # 5. Check for oscillation BEFORE evaluating completion
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
                # Record the iteration that caused the abort
                iter_finish = datetime.now(UTC)
                is_success = self._is_success(run_result.outcome)
                iteration = LoopIteration(
                    iteration_number=i,
                    run_id=run_result.run_id,
                    plan_id=run_result.plan.plan_id if run_result.plan else "",
                    reflection_id=ref_report.id,
                    memory_id=mem_entry.id,
                    planning_decision_id=run_result.planning_decision.id
                    if getattr(run_result, "planning_decision", None)
                    else None,
                    finished_at=iter_finish,
                    duration_ms=(time.monotonic() - iter_start) * 1000,
                    success=is_success,
                )
                iterations.append(iteration)
                break

            # 6. Evaluate Completion
            state = LoopState.REPLANNING
            decision = self._completion.evaluate(run_result, ref_report, i, context.max_iterations)
            print(f"Decision: continue={decision.continue_loop}, action={decision.action.value}, reason={decision.reason}")
            # 7. Check for Human Approval Requirement
            if decision.requires_human:
                state = LoopState.WAITING_APPROVAL
                outcome = LoopOutcome.WAITING_APPROVAL
                approval_req = self._approval.request_approval(
                    loop_id=context.loop_id, iteration=i, reason=decision.reason
                )
                pending_approval_id = approval_req.id

                # Record the iteration
                iter_finish = datetime.now(UTC)
                is_success = self._is_success(run_result.outcome)
                iteration = LoopIteration(
                    iteration_number=i,
                    run_id=run_result.run_id,
                    plan_id=run_result.plan.plan_id if run_result.plan else "",
                    reflection_id=ref_report.id,
                    memory_id=mem_entry.id,
                    planning_decision_id=run_result.planning_decision.id
                    if getattr(run_result, "planning_decision", None)
                    else None,
                    finished_at=iter_finish,
                    duration_ms=(time.monotonic() - iter_start) * 1000,
                    success=is_success,
                )
                iterations.append(iteration)
                final_decision = decision

                total_duration = (time.monotonic() - start_time) * 1000
                return LoopResult(
                    loop_id=context.loop_id,
                    state=state,
                    outcome=outcome,
                    iterations=tuple(iterations),
                    final_decision=final_decision,
                    metrics=self._calculate_metrics(iterations, total_duration),
                    summary=f"Loop paused for human approval: {decision.reason}",
                    duration_ms=total_duration,
                    pending_approval_id=pending_approval_id,
                )

            # 8. Recovery handling
            if decision.action.value == "replan":
                recovery_action = self._recovery.evaluate(run_result, decision)
                if recovery_action.action_type == RecoveryActionType.ABORT:
                    state = LoopState.ABORTED
                    outcome = LoopOutcome.FAILED
                    final_decision = decision
                    # Record the iteration and break
                    iter_finish = datetime.now(UTC)
                    is_success = self._is_success(run_result.outcome)
                    iteration = LoopIteration(
                        iteration_number=i,
                        run_id=run_result.run_id,
                        plan_id=run_result.plan.plan_id if run_result.plan else "",
                        reflection_id=ref_report.id,
                        memory_id=mem_entry.id,
                        planning_decision_id=run_result.planning_decision.id
                        if getattr(run_result, "planning_decision", None)
                        else None,
                        finished_at=iter_finish,
                        duration_ms=(time.monotonic() - iter_start) * 1000,
                        success=is_success,
                    )
                    iterations.append(iteration)
                    break

            # Record the iteration (normal flow)
            iter_finish = datetime.now(UTC)
            is_success = self._is_success(run_result.outcome)
            iteration = LoopIteration(
                iteration_number=i,
                run_id=run_result.run_id,
                plan_id=run_result.plan.plan_id if run_result.plan else "",
                reflection_id=ref_report.id,
                memory_id=mem_entry.id,
                planning_decision_id=run_result.planning_decision.id
                if getattr(run_result, "planning_decision", None)
                else None,
                finished_at=iter_finish,
                duration_ms=(time.monotonic() - iter_start) * 1000,
                success=is_success,
            )
            iterations.append(iteration)

            # 9. Check termination
            if not decision.continue_loop:
                if decision.action.value == "stop":
                    state = LoopState.COMPLETED
                    outcome = LoopOutcome.FINISHED
                else:
                    state = LoopState.FAILED
                    outcome = LoopOutcome.FAILED
                final_decision = decision
                break

            final_decision = decision

        # If loop exits without a terminal decision (max iterations)
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
        metrics = self._calculate_metrics(iterations, total_duration)

        return LoopResult(
            loop_id=context.loop_id,
            state=state,
            outcome=outcome,
            iterations=tuple(iterations),
            final_decision=final_decision,
            metrics=metrics,
            summary=f"Loop finished with outcome: {outcome.value}",
            duration_ms=total_duration,
        )

    def resume(
        self, loop_result: LoopResult, approved: bool, reviewer: str = "human"
    ) -> LoopResult:
        """Resumes a paused loop after human approval."""
        if loop_result.state != LoopState.WAITING_APPROVAL:
            raise ValueError("Can only resume a loop waiting for approval.")

        # Record the approval decision
        self._approval.record_decision(
            approval_id=loop_result.pending_approval_id, approved=approved, reviewer=reviewer
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
        else:
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

    def _get_plan_signature(self, plan: Any) -> str:
        """Creates a deterministic signature of a plan to detect cycles."""
        if not plan or not hasattr(plan, 'steps'):
            return "no_plan"
        return "|".join(sorted([step.capability_id for step in plan.steps]))

    def _is_oscillating(self) -> bool:
        """Detects if the last 4 plans form an A -> B -> A -> B cycle."""
        if len(self._plan_history) < 4:
            return False
        return (self._plan_history[-1] == self._plan_history[-3] and
                self._plan_history[-2] == self._plan_history[-4])

    def _is_success(self, outcome: Any) -> bool:
        """Helper to check if run outcome indicates success."""
        return (outcome == "success"
                or getattr(outcome, "value", None) == "success"
                or str(outcome).lower().endswith("success"))

    def _calculate_metrics(
        self, iterations: list[LoopIteration], total_duration: float
    ) -> LoopMetrics:
        return LoopMetrics(
            total_iterations=len(iterations),
            successful_iterations=sum(1 for i in iterations if i.success),
            failed_iterations=sum(1 for i in iterations if not i.success),
            total_duration_ms=total_duration,
            replans_triggered=sum(1 for i in iterations if i.planning_decision_id is not None),
        )