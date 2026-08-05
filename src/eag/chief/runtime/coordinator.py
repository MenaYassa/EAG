"""Coordinator for EAG Chief Runtime."""

import time

from eag.capability import CapabilityContext, CapabilityRequest, CapabilityRuntime
from eag.chief.runtime.enums import RunOutcome, RunPhase, RunState, ValidationDecision
from eag.chief.runtime.errors import RunStateError
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
    RunContext,
    RunMetrics,
    RunResult,
    StepResult,
)
from eag.chief.runtime.scheduler import TaskScheduler
from eag.events import EventBus
from eag.memory import MemoryRuntime


class Coordinator:
    """Orchestrates the full run lifecycle: plan -> execute -> validate."""

    def __init__(
        self,
        planner,  # The standard base planner
        capability_runtime: CapabilityRuntime,
        validator,
        scheduler: TaskScheduler | None = None,
        event_bus: EventBus | None = None,
        memory_runtime: MemoryRuntime | None = None,
        adaptive_planner=None,  # Inject adaptive planner separately without strict type hint
    ) -> None:
        self._planner = planner
        self._adaptive_planner = adaptive_planner
        self._capability_runtime = capability_runtime
        self._validator = validator
        self._scheduler = scheduler or TaskScheduler()
        self._event_bus = event_bus or EventBus()
        self._memory = memory_runtime

        # Lazy import breaks the circular dependency on startup
        from eag.adaptive.analyzer import ExperienceAnalyzer

        self._analyzer = ExperienceAnalyzer()

    def run(self, context: RunContext) -> RunResult:
        """Execute the full coordination pipeline."""
        start_time = time.monotonic()
        run = ChiefRun(context=context, state=RunState.RECEIVED)

        try:
            # 1. Planning (Orchestrated)
            run = self._transition(run, RunState.PLANNING, RunPhase.PLANNING)
            self._event_bus.publish(PlanningStarted(run_id=run.run_id))
            plan_start = time.monotonic()

            base_plan = self._planner.create_plan(context)
            final_plan = base_plan
            planning_decision = None

            if self._memory and self._adaptive_planner:
                # Lazy import to avoid circular dependencies
                from eag.adaptive.models import AdaptivePlanningContext

                exp = self._memory.get_relevant_experience(context.goal_text)
                if exp:
                    experiences = (exp,)
                    insights = self._analyzer.analyze(experiences)
                    rules = self._generate_rules_from_insights(insights)

                    adapt_ctx = AdaptivePlanningContext(
                        goal=context.goal_text,
                        experiences=experiences,
                        insights=insights,
                        rules=rules,
                    )
                    adaptive_plan, planning_decision = self._adaptive_planner.plan(
                        adapt_ctx, base_plan
                    )
                    final_plan = adaptive_plan.final_plan

            planning_time = (time.monotonic() - plan_start) * 1000
            run = self._update_run(run, plan=final_plan, state=RunState.READY)
            self._event_bus.publish(
                PlanningCompleted(
                    run_id=run.run_id, plan_id=final_plan.plan_id, step_count=len(final_plan.steps)
                )
            )

            # 2. Execution + Validation
            run = self._transition(run, RunState.EXECUTING, RunPhase.EXECUTION)

            cap_context = CapabilityContext(
                workspace_path=context.metadata.get("workspace_path"),
                repository_path=context.metadata.get("repository_path"),
                metadata=context.metadata,
            )

            step_results, checkpoints = self._execute_plan(run, final_plan, cap_context)

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
                self._event_bus.publish(
                    RunFailed(run_id=run.run_id, error="One or more steps failed validation")
                )

            run = self._update_run(run, outcome=outcome)

            total_time = (time.monotonic() - start_time) * 1000
            metrics = RunMetrics(
                planning_time_ms=planning_time,
                execution_time_ms=exec_time,
                total_duration_ms=total_time,
                steps_total=len(final_plan.steps),
                steps_completed=sum(1 for r in step_results if r.success),
                failures=sum(1 for r in step_results if not r.success),
            )

            return RunResult(
                run_id=run.run_id,
                outcome=outcome,
                plan=final_plan,
                step_results=step_results,
                summary=f"Completed {len(step_results)} steps. Outcome: {outcome.value}",
                duration_ms=total_time,
                planning_decision=planning_decision,
            )

        except Exception as e:
            run = self._update_run(run, state=RunState.FAILED, error=str(e))
            self._event_bus.publish(RunFailed(run_id=run.run_id, error=str(e)))
            return RunResult(
                run_id=run.run_id,
                outcome=RunOutcome.FAILURE,
                summary=f"Run failed: {e}",
                duration_ms=(time.monotonic() - start_time) * 1000,
            )

    def _generate_rules_from_insights(self, insights) -> tuple:
        """Converts insights into deterministic planning rules dynamically."""
        from eag.adaptive.enums import RulePriority
        from eag.adaptive.models import PlanningRule

        rules = []
        for insight in insights:
            cap_id = insight.category.value
            rules.append(
                PlanningRule(
                    condition="has_insights == 'true'",
                    action=f"insert_worker:{cap_id}",
                    priority=RulePriority.HIGH,
                )
            )
        return tuple(rules)

    def _execute_plan(
        self, run: ChiefRun, plan: Plan, cap_context: CapabilityContext
    ) -> tuple[tuple[StepResult, ...], tuple]:
        results: list[StepResult] = []
        checkpoints: list = []
        completed: set[str] = set()

        while not self._scheduler.is_complete(plan, completed):
            step = self._scheduler.get_next_step(plan, completed)
            if step is None:
                break

            self._event_bus.publish(ExecutionStarted(run_id=run.run_id, step_id=step.step_id))
            step_start = time.monotonic()

            cap_request = CapabilityRequest(
                capability_id=step.capability_id, goal_text=step.name, parameters=step.metadata
            )

            cap_result = self._capability_runtime.execute(cap_request, cap_context)

            result = StepResult(
                step_id=step.step_id,
                success=cap_result.success,
                output=cap_result.output,
                error=cap_result.error,
                duration_ms=(time.monotonic() - step_start) * 1000,
                metadata=cap_result.metadata,
            )

            self._event_bus.publish(
                ExecutionCompleted(run_id=run.run_id, step_id=step.step_id, success=result.success)
            )

            self._event_bus.publish(ValidationStarted(run_id=run.run_id, step_id=step.step_id))
            decision = self._validator.validate(step, result, run)
            self._event_bus.publish(
                ValidationCompleted(
                    run_id=run.run_id, step_id=step.step_id, decision=decision.value
                )
            )

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
            context=run.context,
            state=target,
            phase=phase,
            plan=run.plan,
            step_results=run.step_results,
            checkpoints=run.checkpoints,
            metrics=run.metrics,
            outcome=run.outcome,
            error=run.error,
            created_at=run.created_at,
        )

    def _update_run(self, run: ChiefRun, **kwargs) -> ChiefRun:
        data = {
            "context": run.context,
            "state": run.state,
            "phase": run.phase,
            "plan": run.plan,
            "step_results": run.step_results,
            "checkpoints": run.checkpoints,
            "metrics": run.metrics,
            "outcome": run.outcome,
            "error": run.error,
            "created_at": run.created_at,
        }
        data.update(kwargs)
        return ChiefRun(**data)
