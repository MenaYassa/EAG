"""Integration tests for the Planner Runtime pipeline."""

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

import pytest

from eag.planner.enums import GoalType, PlannerRuntimeState, RiskLevel
from eag.planner.errors import PlannerError, PlanningStrategyUnavailableError
from eag.planner.events import (
    PlanGenerated,
    PlanningCompleted,
    PlanningStarted,
    StrategySelected,
)
from eag.planner.intelligence.goal_analyzer import GoalAnalyzer
from eag.planner.intelligence.models import EngineeringGoal, EngineeringOperation
from eag.planner.models import (
    EngineeringTask,
    ExecutionAction,
    ExecutionPlan,
    ExecutionStep,
    PlanningContext,
    PlanningGoal,
    PlanningResult,
    PlanningStrategyInfo,
)
from eag.planner.registry import PlanningStrategyRegistry
from eag.planner.runtime import PlannerRuntime
from eag.planner.strategies.sequential import SequentialStrategy


@dataclass
class MockEventBus:
    published_events: list[Any] = field(default_factory=list)

    def publish(self, event: Any) -> None:
        self.published_events.append(event)


class DummyHighPriorityStrategy:
    @property
    def info(self) -> PlanningStrategyInfo:
        return PlanningStrategyInfo(
            name="DummyHighPriority",
            priority=200,
            supported_goal_types=(GoalType.REFACTOR,),
        )

    def supports(self, eng_goal: EngineeringGoal, context: PlanningContext) -> bool:
        return eng_goal.operation == EngineeringOperation.REFACTOR

    def create_plan(self, eng_goal: EngineeringGoal, context: PlanningContext) -> ExecutionPlan:
        return ExecutionPlan(
            goal=eng_goal.planning_goal,
            strategy=self.info.name,
            tasks=(EngineeringTask(id="d-task", title="Dummy Task"),),
            steps=(
                ExecutionStep(
                    id="d-step",
                    task_id="d-task",
                    action=ExecutionAction(kind="Dummy", target="dummy"),
                ),
            ),
        )

    def estimate_risk(self, eng_goal: EngineeringGoal, context: PlanningContext) -> RiskLevel:
        return RiskLevel.NONE

    def estimate_duration(self, eng_goal: EngineeringGoal, context: PlanningContext) -> timedelta:
        return timedelta(seconds=0)


@pytest.fixture
def event_bus() -> MockEventBus:
    return MockEventBus()


@pytest.fixture
def analyzer() -> GoalAnalyzer:
    return GoalAnalyzer()


@pytest.fixture
def registry() -> PlanningStrategyRegistry:
    reg = PlanningStrategyRegistry()
    reg.register(SequentialStrategy())
    return reg


@pytest.fixture
def runtime(
    event_bus: MockEventBus, registry: PlanningStrategyRegistry, analyzer: GoalAnalyzer
) -> PlannerRuntime:
    return PlannerRuntime(event_bus=event_bus, strategy_registry=registry, goal_analyzer=analyzer)


@pytest.fixture
def refactor_goal() -> PlanningGoal:
    return PlanningGoal(
        goal_type=GoalType.REFACTOR,
        title="Rename EventBus to EventHub",
        description="Rename EventBus to EventHub everywhere",
    )


@pytest.fixture
def unsupported_goal() -> PlanningGoal:
    return PlanningGoal(
        goal_type=GoalType.MAINTENANCE,
        title="Update Dependencies",
    )


class TestPlannerIntegration:
    def test_happy_path(self, runtime: PlannerRuntime, refactor_goal: PlanningGoal) -> None:
        result = runtime.plan(refactor_goal)

        assert isinstance(result, PlanningResult)
        assert result.plan.goal == refactor_goal
        assert result.plan.strategy == "Sequential"
        assert len(result.plan.tasks) == 5
        assert len(result.plan.steps) > 0
        assert result.plan.statistics.task_count == 5
        assert runtime.state == PlannerRuntimeState.COMPLETED

    def test_unsupported_goal(
        self, runtime: PlannerRuntime, unsupported_goal: PlanningGoal
    ) -> None:
        with pytest.raises(PlanningStrategyUnavailableError):
            runtime.plan(unsupported_goal)

        assert runtime.state == PlannerRuntimeState.FAILED

    def test_events_order(
        self, runtime: PlannerRuntime, event_bus: MockEventBus, refactor_goal: PlanningGoal
    ) -> None:
        runtime.plan(refactor_goal)

        event_types = [type(e) for e in event_bus.published_events]
        assert event_types == [
            PlanningStarted,
            StrategySelected,
            PlanGenerated,
            PlanningCompleted,
        ]

    def test_metrics_tracking(
        self, runtime: PlannerRuntime, refactor_goal: PlanningGoal, unsupported_goal: PlanningGoal
    ) -> None:
        runtime.plan(refactor_goal)
        runtime.plan(refactor_goal)
        with pytest.raises(PlannerError):
            runtime.plan(unsupported_goal)

        metrics = runtime.metrics()
        assert metrics.plans_generated == 3
        assert metrics.successful_plans == 2
        assert metrics.failed_plans == 1

    def test_determinism(self, runtime: PlannerRuntime) -> None:
        goal1 = PlanningGoal(goal_type=GoalType.REFACTOR, title="Rename X to Y")
        goal2 = PlanningGoal(goal_type=GoalType.REFACTOR, title="Rename X to Y")

        plan1 = runtime.plan(goal1).plan
        plan2 = runtime.plan(goal2).plan

        assert [t.title for t in plan1.tasks] == [t.title for t in plan2.tasks]
        assert [s.description for s in plan1.steps] == [s.description for s in plan2.steps]
        assert plan1.statistics == plan2.statistics
        assert plan1.risk == plan2.risk

    def test_registry_independence(
        self,
        event_bus: MockEventBus,
        registry: PlanningStrategyRegistry,
        analyzer: GoalAnalyzer,
        refactor_goal: PlanningGoal,
    ) -> None:
        runtime = PlannerRuntime(
            event_bus=event_bus, strategy_registry=registry, goal_analyzer=analyzer
        )

        result1 = runtime.plan(refactor_goal)
        assert result1.plan.strategy == "Sequential"

        registry.register(DummyHighPriorityStrategy())

        result2 = runtime.plan(refactor_goal)
        assert result2.plan.strategy == "DummyHighPriority"
