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
from eag.planner.models import (
    EngineeringTask,  # <-- ADDED
    ExecutionAction,  # <-- ADDED
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
    """A simple event bus mock to record published events in order."""

    published_events: list[Any] = field(default_factory=list)

    def publish(self, event: Any) -> None:
        self.published_events.append(event)


class DummyHighPriorityStrategy:
    """A dummy strategy with high priority to test registry independence."""

    @property
    def info(self) -> PlanningStrategyInfo:
        return PlanningStrategyInfo(
            name="DummyHighPriority",
            priority=200,
            supported_goal_types=(GoalType.REFACTOR,),
        )

    def supports(self, goal: PlanningGoal, context: PlanningContext) -> bool:
        return goal.goal_type in self.info.supported_goal_types

    def create_plan(self, goal: PlanningGoal, context: PlanningContext) -> ExecutionPlan:
        return ExecutionPlan(
            goal=goal,
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

    def estimate_risk(self, goal: PlanningGoal, context: PlanningContext) -> RiskLevel:
        return RiskLevel.NONE

    def estimate_duration(self, goal: PlanningGoal, context: PlanningContext) -> timedelta:
        return timedelta(seconds=0)


# Fixtures
@pytest.fixture
def event_bus() -> MockEventBus:
    return MockEventBus()


@pytest.fixture
def registry() -> PlanningStrategyRegistry:
    reg = PlanningStrategyRegistry()
    reg.register(SequentialStrategy())
    return reg


@pytest.fixture
def runtime(event_bus: MockEventBus, registry: PlanningStrategyRegistry) -> PlannerRuntime:
    return PlannerRuntime(event_bus=event_bus, strategy_registry=registry)


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
    """End-to-end integration tests for the planning pipeline."""

    def test_happy_path(self, runtime: PlannerRuntime, refactor_goal: PlanningGoal) -> None:
        """Test 1: Goal -> Runtime -> Registry -> Strategy -> Plan -> Result."""
        result = runtime.plan(refactor_goal)

        assert isinstance(result, PlanningResult)
        assert result.plan.goal == refactor_goal
        assert result.plan.strategy == "Sequential"
        assert len(result.plan.tasks) == 5
        assert len(result.plan.steps) > 0
        assert result.plan.statistics.task_count == 5
        assert result.plan.statistics.step_count == len(result.plan.steps)
        assert runtime.state == PlannerRuntimeState.COMPLETED

    def test_unsupported_goal(
        self, runtime: PlannerRuntime, unsupported_goal: PlanningGoal
    ) -> None:
        """Test 2: Unsupported goal raises exception and marks runtime failed."""
        with pytest.raises(PlanningStrategyUnavailableError):
            runtime.plan(unsupported_goal)

        assert runtime.state == PlannerRuntimeState.FAILED

    def test_events_order(
        self, runtime: PlannerRuntime, event_bus: MockEventBus, refactor_goal: PlanningGoal
    ) -> None:
        """Test 3: Verify exact event sequence on success."""
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
        """Test 4: Run success, success, failure and verify metrics."""
        runtime.plan(refactor_goal)
        runtime.plan(refactor_goal)
        with pytest.raises(PlannerError):
            runtime.plan(unsupported_goal)

        metrics = runtime.metrics()
        assert metrics.plans_generated == 3
        assert metrics.successful_plans == 2
        assert metrics.failed_plans == 1

    def test_determinism(self, runtime: PlannerRuntime) -> None:
        """Test 5: Identical goals must produce identical plans."""
        goal1 = PlanningGoal(goal_type=GoalType.REFACTOR, title="Rename X to Y")
        goal2 = PlanningGoal(goal_type=GoalType.REFACTOR, title="Rename X to Y")

        plan1 = runtime.plan(goal1).plan
        plan2 = runtime.plan(goal2).plan

        # Plan IDs will differ because Goal IDs differ, but structure must be identical
        assert [t.title for t in plan1.tasks] == [t.title for t in plan2.tasks]
        assert [s.description for s in plan1.steps] == [s.description for s in plan2.steps]
        assert plan1.statistics == plan2.statistics
        assert plan1.risk == plan2.risk

    def test_registry_independence(
        self,
        event_bus: MockEventBus,
        registry: PlanningStrategyRegistry,
        refactor_goal: PlanningGoal,
    ) -> None:
        """Test 6: Runtime dynamically adapts to newly registered high-priority strategies."""
        runtime = PlannerRuntime(event_bus=event_bus, strategy_registry=registry)

        # Initially uses Sequential
        result1 = runtime.plan(refactor_goal)
        assert result1.plan.strategy == "Sequential"

        # Register dummy strategy with higher priority
        registry.register(DummyHighPriorityStrategy())

        # Runtime immediately uses it without modification
        result2 = runtime.plan(refactor_goal)
        assert result2.plan.strategy == "DummyHighPriority"
