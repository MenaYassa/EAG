"""Planner runtime for EAG."""

import time
from typing import Any

from eag.events import EventBus
from eag.planner.enums import PlannerRuntimeState
from eag.planner.errors import PlannerError, PlanningValidationError
from eag.planner.events import (
    PlanGenerated,
    PlanningCompleted,
    PlanningFailed,
    PlanningStarted,
    StrategySelected,
)
from eag.planner.intelligence.goal_analyzer import GoalAnalyzer
from eag.planner.intelligence.models import EngineeringGoal
from eag.planner.models import (
    ExecutionPlan,
    PlanningContext,
    PlanningGoal,
    PlanningResult,
    PlanningRuntimeHealth,
    PlanningRuntimeMetrics,
)
from eag.planner.registry import PlanningStrategyRegistry
from eag.planner.strategy import PlanningStrategy


class PlannerRuntime:
    """Orchestrates the planning lifecycle."""

    def __init__(
        self,
        event_bus: EventBus,
        strategy_registry: PlanningStrategyRegistry,
        goal_analyzer: GoalAnalyzer,
    ) -> None:
        self._event_bus = event_bus
        self._registry = strategy_registry
        self._analyzer = goal_analyzer
        self._state = PlannerRuntimeState.CREATED

        self._metrics = PlanningRuntimeMetrics()
        self._total_duration = 0.0
        self._last_planning_time: float | None = None
        self._last_context: PlanningContext | None = None
        self._last_plan: ExecutionPlan | None = None

        if self._registry.all():
            self._state = PlannerRuntimeState.READY

    @property
    def state(self) -> PlannerRuntimeState:
        return self._state

    @property
    def last_plan(self) -> ExecutionPlan | None:
        return self._last_plan

    @property
    def last_context(self) -> PlanningContext | None:
        return self._last_context

    def metrics(self) -> PlanningRuntimeMetrics:
        return self._metrics

    def health(self) -> PlanningRuntimeHealth:
        default = self._registry.default().info.name if self._registry.all() else None
        return PlanningRuntimeHealth(
            state=self._state,
            strategies_registered=len(self._registry.all()),
            default_strategy=default,
            last_planning_time=self._last_planning_time,
            metrics=self._metrics,
        )

    def plan(
        self,
        goal: PlanningGoal,
        context: PlanningContext | None = None,
    ) -> PlanningResult:
        """Generate a planning result for a given goal."""
        ctx = context or PlanningContext()
        self._last_context = ctx
        start_time = time.monotonic()

        self._state = PlannerRuntimeState.PLANNING
        self._event_bus.publish(PlanningStarted(goal_id=goal.id, goal_type=goal.goal_type))

        try:
            self._validate_goal(goal)

            eng_goal = self._analyzer.analyze(goal)

            strategy = self._select_strategy(eng_goal, ctx)
            self._event_bus.publish(StrategySelected(goal_id=goal.id, strategy=strategy.info.name))

            execution_plan = self._generate_plan(strategy, eng_goal, ctx)
            self._last_plan = execution_plan

            self._state = PlannerRuntimeState.VALIDATING
            self._validate_plan(execution_plan, goal)

            duration = time.monotonic() - start_time
            self._last_planning_time = duration
            self._update_metrics(True, duration, strategy.info.name, goal.goal_type)

            self._event_bus.publish(
                PlanGenerated(
                    goal_id=goal.id,
                    plan_id=execution_plan.id,
                    strategy=strategy.info.name,
                    task_count=len(execution_plan.tasks),
                    step_count=len(execution_plan.steps),
                    risk=execution_plan.risk,
                )
            )

            result = PlanningResult(
                plan=execution_plan,
                risk=execution_plan.risk,
                statistics=execution_plan.statistics,
            )

            self._event_bus.publish(
                PlanningCompleted(
                    goal_id=goal.id,
                    plan_id=execution_plan.id,
                    strategy=strategy.info.name,
                    task_count=len(execution_plan.tasks),
                    step_count=len(execution_plan.steps),
                    risk=execution_plan.risk,
                    duration=duration,
                )
            )

            self._state = PlannerRuntimeState.COMPLETED
            return result

        except PlannerError as e:
            duration = time.monotonic() - start_time
            self._last_planning_time = duration
            self._update_metrics(False, duration, None, goal.goal_type)

            self._event_bus.publish(
                PlanningFailed(
                    goal_id=goal.id,
                    goal_type=goal.goal_type,
                    error=str(e),
                )
            )
            self._state = PlannerRuntimeState.FAILED
            raise

    def validate(self, goal: PlanningGoal) -> None:
        self._validate_goal(goal)

    def supported_strategies(self) -> tuple[str, ...]:
        return self._registry.supported()

    def strategy_info(self, name: str) -> Any:
        for strategy in self._registry.all():
            if strategy.info.name == name:
                return strategy.info
        raise PlannerError(f"Strategy '{name}' not found.")

    def explain(self, plan: ExecutionPlan) -> str:
        return (
            f"Planning Goal\n"
            f"────────────────────────\n\n"
            f"{plan.goal.title}\n\n"
            f"Strategy\n\n"
            f"{plan.strategy}\n\n"
            f"Tasks\n\n"
            f"{len(plan.tasks)}\n\n"
            f"Execution Steps\n\n"
            f"{len(plan.steps)}\n\n"
            f"Risk\n\n"
            f"{plan.risk.value.upper()}\n\n"
            f"Estimated Duration\n\n"
            f"{plan.statistics.estimated_minutes} minutes\n\n"
            f"Status\n\n"
            f"{plan.state.value.capitalize()}\n"
        )

    def _update_metrics(
        self, success: bool, duration: float, strategy_name: str | None, goal_type: Any
    ) -> None:
        generated = self._metrics.plans_generated + 1
        successful = self._metrics.successful_plans + (1 if success else 0)
        failed = self._metrics.failed_plans + (0 if success else 1)

        self._total_duration += duration
        avg_duration = self._total_duration / generated if generated > 0 else 0.0

        self._metrics = PlanningRuntimeMetrics(
            plans_generated=generated,
            successful_plans=successful,
            failed_plans=failed,
            average_duration=avg_duration,
            last_strategy=strategy_name,
            last_goal_type=goal_type,
        )

    def _validate_goal(self, goal: PlanningGoal) -> None:
        if not isinstance(goal, PlanningGoal):
            raise PlanningValidationError("Invalid goal type provided.")
        if not goal.title.strip():
            raise PlanningValidationError("Goal title cannot be empty.")

    def _select_strategy(
        self, eng_goal: EngineeringGoal, context: PlanningContext
    ) -> PlanningStrategy:
        return self._registry.find(eng_goal, context)

    def _generate_plan(
        self,
        strategy: PlanningStrategy,
        eng_goal: EngineeringGoal,
        context: PlanningContext,
    ) -> ExecutionPlan:
        return strategy.create_plan(eng_goal, context)

    def _validate_plan(self, plan: ExecutionPlan, original_goal: PlanningGoal) -> None:
        if not plan.tasks:
            raise PlanningValidationError("Plan must contain at least one task.")
        if not plan.steps:
            raise PlanningValidationError("Plan must contain at least one step.")
        if plan.goal.id != original_goal.id:
            raise PlanningValidationError("Generated plan goal does not match original goal.")
