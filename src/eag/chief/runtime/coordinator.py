"""Coordinator for EAG Chief Runtime."""

import time
from eag.capability import CapabilityContext, CapabilityRequest, CapabilityRuntime
from eag.chief.runtime.enums import RunOutcome, RunPhase, RunState, StepState, ValidationDecision
from eag.chief.runtime.errors import CoordinationError, RunStateError
from eag.chief.runtime.events import (
    ExecutionCompleted,
    ExecutionStarted,
    PlanningCompleted,
    PlanningStarted,
    RunFailed,
    RunFinished,
    ValidationCompleted,
    ValidationStarted,
)
from eag.chief.runtime.models import (
    ChiefRun,
    Plan,
    PlanStep,
    RunContext,
    RunMetrics,
    RunResult,
    StepResult,
)
from eag.chief.runtime.scheduler import TaskScheduler
from eag.events import EventBus


class Coordinator:
    """Orchestrates the full run lifecycle: plan -> execute -> validate."""

    def __init__(
        self,
        planner,
        capability_runtime: CapabilityRuntime,
        validator,
        scheduler: TaskScheduler | None = None,
        event_bus: EventBus | None = None
    ) -> None:
        self._planner = planner
        self._capability_runtime = capability_runtime
        self._validator = validator
        self._scheduler = scheduler or TaskScheduler()
        self._event_bus = event_bus or EventBus()

    def run(self, context: RunContext) -> RunResult:
        """Execute the full coordination pipeline."""
        start_time = time.monotonic()
        run = ChiefRun(context=context, state=RunState.RECEIVED)
        
        try:
            # 1. Planning
            run = self._transition(run, RunState.PLANNING, RunPhase.PLANNING)
            self._event_bus.publish(PlanningStarted(run_id=run.run_id))
            plan_start = time.monotonic()
            plan = self._planner.create_plan(context)
            planning_time = (time.monotonic() - plan_start) * 1000
            run = self._update_run(run, plan=plan, state=RunState.READY)
            self._event_bus.publish(PlanningCompleted(run_id=run.run_id, plan_id=plan.plan_id, step_count=len(plan.steps)))

            # 2. Execution + Validation
            run = self._transition(run, RunState.EXECUTING, RunPhase.EXECUTION)
            
            # Create CapabilityContext
            cap_context = CapabilityContext(
                workspace_path=context.metadata.get("workspace_path"),
                repository_path=context.metadata.get("repository_path"),
                metadata=context.metadata
            )
            
            step_results, checkpoints = self._execute_plan(run, plan, cap_context)
            
            exec_time = sum(r.duration_ms for r in step_results)
            run = self._update_run(run, step_results=step_results, checkpoints=checkpoints)

            # 3. Completion
            all_success = all(r.success for r in step_results)
            outcome = RunOutcome.SUCCESS if all_success else RunOutcome.FAILURE
            
            if outcome == RunOutcome.SUCCESS:
                run = self._transition(run, RunState.COMPLETED, RunPhase.COMPLETION)
                self._event_bus.publish(RunFinished(run_id=run.run_id, outcome=outcome.value))
            else:
                run = self._transition(run, RunState.FAILED, RunPhase.COMPLETION)
                self._event_bus.publish(RunFailed(run_id=run.run_id, error="One or more steps failed validation"))
                
            run = self._update_run(run, outcome=outcome)
            
            total_time = (time.monotonic() - start_time) * 1000
            metrics = RunMetrics(
                planning_time_ms=planning_time,
                execution_time_ms=exec_time,
                total_duration_ms=total_time,
                steps_total=len(plan.steps),
                steps_completed=sum(1 for r in step_results if r.success),
                failures=sum(1 for r in step_results if not r.success)
            )
            
            return RunResult(
                run_id=run.run_id,
                outcome=outcome,
                plan=plan,
                step_results=step_results,
                summary=f"Completed {len(step_results)} steps. Outcome: {outcome.value}",
                duration_ms=total_time
            )
            
        except Exception as e:
            run = self._update_run(run, state=RunState.FAILED, error=str(e))
            self._event_bus.publish(RunFailed(run_id=run.run_id, error=str(e)))
            return RunResult(
                run_id=run.run_id,
                outcome=RunOutcome.FAILURE,
                summary=f"Run failed: {e}",
                duration_ms=(time.monotonic() - start_time) * 1000
            )

    def _execute_plan(self, run: ChiefRun, plan: Plan, cap_context: CapabilityContext) -> tuple[tuple[StepResult, ...], tuple]:
        results: list[StepResult] = []
        checkpoints: list = []
        completed: set[str] = set()
        
        while not self._scheduler.is_complete(plan, completed):
            step = self._scheduler.get_next_step(plan, completed)
            if step is None:
                break
                
            self._event_bus.publish(ExecutionStarted(run_id=run.run_id, step_id=step.step_id))
            step_start = time.monotonic()
            
            # Create CapabilityRequest
            cap_request = CapabilityRequest(
                capability_id=step.capability_id,
                goal_text=step.name,
                parameters=step.metadata
            )
            
            # Execute via CapabilityRuntime
            cap_result = self._capability_runtime.execute(cap_request, cap_context)
            
            result = StepResult(
                step_id=step.step_id,
                success=cap_result.success,
                output=cap_result.output,
                error=cap_result.error,
                duration_ms=(time.monotonic() - step_start) * 1000,
                metadata=cap_result.metadata
            )
            
            self._event_bus.publish(ExecutionCompleted(run_id=run.run_id, step_id=step.step_id, success=result.success))
            
            # Validation
            self._event_bus.publish(ValidationStarted(run_id=run.run_id, step_id=step.step_id))
            decision = self._validator.validate(step, result, run)
            self._event_bus.publish(ValidationCompleted(run_id=run.run_id, step_id=step.step_id, decision=decision.value))
            
            if decision == ValidationDecision.CONTINUE:
                results.append(result)
                completed.add(step.step_id)
            elif decision == ValidationDecision.RETRY:
                continue
            elif decision == ValidationDecision.ABORT:
                results.append(result)
                break
            else:
                results.append(result)
                break
                
        return tuple(results), tuple(checkpoints)

    def _transition(self, run: ChiefRun, target: RunState, phase: RunPhase) -> ChiefRun:
        if not run.state.can_transition_to(target):
            raise RunStateError(f"Cannot transition from {run.state.value} to {target.value}")
        return ChiefRun(
            context=run.context, state=target, phase=phase,
            plan=run.plan, step_results=run.step_results, checkpoints=run.checkpoints,
            metrics=run.metrics, outcome=run.outcome, error=run.error,
            created_at=run.created_at
        )

    def _update_run(self, run: ChiefRun, **kwargs) -> ChiefRun:
        data = {
            "context": run.context, "state": run.state, "phase": run.phase,
            "plan": run.plan, "step_results": run.step_results, "checkpoints": run.checkpoints,
            "metrics": run.metrics, "outcome": run.outcome, "error": run.error,
            "created_at": run.created_at
        }
        data.update(kwargs)
        return ChiefRun(**data)