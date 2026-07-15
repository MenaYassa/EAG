"""Tests for the planner runtime."""

from dataclasses import dataclass, field
from typing import Any

import pytest

from eag.planner.enums import GoalType, PlannerRuntimeState
from eag.planner.errors import (
    PlannerError,
    PlanningStrategyUnavailableError,
)
from eag.planner.events import (
    PlanGenerated,
    PlanningCompleted,
    PlanningFailed,
    PlanningStarted,
    StrategySelected,
)
from eag.planner.models import (
    PlanningGoal,
    PlanningResult,
)
from eag.planner.registry import PlanningStrategyRegistry
from eag.planner.runtime import PlannerRuntime
from eag.planner.strategies.sequential import SequentialStrategy


@dataclass
class MockEventBus:
    published_events: list[Any] = field(default_factory=list)

    def publish(self, event: Any) -> None:
        self.published_events.append(event)


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
        title="Rename EventBus",
        description="Rename EventBus to EventHub",
    )


@pytest.fixture
def unsupported_goal() -> PlanningGoal:
    return PlanningGoal(
        goal_type=GoalType.MAINTENANCE,
        title="Update Dependencies",
    )


class TestRuntimeInitialization:
    def test_constructs_successfully(
        self, event_bus: MockEventBus, registry: PlanningStrategyRegistry
    ) -> None:
        rt = PlannerRuntime(event_bus=event_bus, strategy_registry=registry)
        assert isinstance(rt, PlannerRuntime)

    def test_initial_state_is_ready(self, runtime: PlannerRuntime) -> None:
        assert runtime.state == PlannerRuntimeState.READY

    def test_supported_strategies(self, runtime: PlannerRuntime) -> None:
        assert runtime.supported_strategies() == ("Sequential",)

    def test_strategy_info(self, runtime: PlannerRuntime) -> None:
        info = runtime.strategy_info("Sequential")
        assert info.name == "Sequential"

    def test_strategy_info_not_found(self, runtime: PlannerRuntime) -> None:
        with pytest.raises(PlannerError):
            runtime.strategy_info("Ghost")


class TestRuntimePlanning:
    def test_plan_success(self, runtime: PlannerRuntime, refactor_goal: PlanningGoal) -> None:
        result = runtime.plan(refactor_goal)
        assert isinstance(result, PlanningResult)
        assert result.plan.goal == refactor_goal
        assert len(result.plan.tasks) > 0

    def test_plan_unsupported_goal_raises(
        self, runtime: PlannerRuntime, unsupported_goal: PlanningGoal
    ) -> None:
        with pytest.raises(PlanningStrategyUnavailableError):
            runtime.plan(unsupported_goal)

    def test_validate_goal_success(
        self, runtime: PlannerRuntime, refactor_goal: PlanningGoal
    ) -> None:
        runtime.validate(refactor_goal)  # Should not raise

    def test_validate_goal_failure(self, runtime: PlannerRuntime) -> None:
        # Fix: Intercept the ValueError thrown during initialization
        with pytest.raises(ValueError, match="title cannot be empty or whitespace"):
            PlanningGoal(goal_type=GoalType.REFACTOR, title="")


class TestRuntimeEvents:
    def test_events_published_on_success(
        self,
        runtime: PlannerRuntime,
        event_bus: MockEventBus,
        refactor_goal: PlanningGoal,
    ) -> None:
        runtime.plan(refactor_goal)

        event_types = [type(e) for e in event_bus.published_events]
        assert PlanningStarted in event_types
        assert StrategySelected in event_types
        assert PlanGenerated in event_types
        assert PlanningCompleted in event_types

    def test_failure_event_published_on_unsupported(
        self,
        runtime: PlannerRuntime,
        event_bus: MockEventBus,
        unsupported_goal: PlanningGoal,
    ) -> None:
        with pytest.raises(PlannerError):
            runtime.plan(unsupported_goal)

        event_types = [type(e) for e in event_bus.published_events]
        assert PlanningStarted in event_types
        assert PlanningFailed in event_types
        assert PlanningCompleted not in event_types


class TestRuntimeExplain:
    def test_explain_returns_string(
        self, runtime: PlannerRuntime, refactor_goal: PlanningGoal
    ) -> None:
        result = runtime.plan(refactor_goal)
        explanation = runtime.explain(result.plan)
        assert isinstance(explanation, str)
        assert "Rename EventBus" in explanation


class TestRuntimeLifecycle:
    def test_state_transitions_to_completed(
        self, runtime: PlannerRuntime, refactor_goal: PlanningGoal
    ) -> None:
        runtime.plan(refactor_goal)
        assert runtime.state == PlannerRuntimeState.COMPLETED

    def test_state_transitions_to_failed(
        self, runtime: PlannerRuntime, unsupported_goal: PlanningGoal
    ) -> None:
        with pytest.raises(PlannerError):
            runtime.plan(unsupported_goal)
        assert runtime.state == PlannerRuntimeState.FAILED

    def test_caches_last_plan_and_context(
        self, runtime: PlannerRuntime, refactor_goal: PlanningGoal
    ) -> None:
        runtime.plan(refactor_goal)
        assert runtime.last_plan is not None
        assert runtime.last_plan.goal == refactor_goal
        assert runtime.last_context is not None


class TestRuntimeMetrics:
    def test_metrics_increment_on_success(
        self, runtime: PlannerRuntime, refactor_goal: PlanningGoal
    ) -> None:
        runtime.plan(refactor_goal)
        m = runtime.metrics()
        assert m.plans_generated == 1
        assert m.successful_plans == 1
        assert m.failed_plans == 0
        assert m.last_strategy == "Sequential"
        assert m.last_goal_type == GoalType.REFACTOR

    def test_metrics_increment_on_failure(
        self, runtime: PlannerRuntime, unsupported_goal: PlanningGoal
    ) -> None:
        with pytest.raises(PlannerError):
            runtime.plan(unsupported_goal)
        m = runtime.metrics()
        assert m.plans_generated == 1
        assert m.successful_plans == 0
        assert m.failed_plans == 1
        assert m.last_strategy is None


class TestRuntimeDiagnostics:
    def test_health_report(self, runtime: PlannerRuntime, refactor_goal: PlanningGoal) -> None:
        runtime.plan(refactor_goal)
        health = runtime.health()
        assert health.state == PlannerRuntimeState.COMPLETED
        assert health.strategies_registered == 1
        assert health.default_strategy == "Sequential"
        assert health.last_planning_time is not None
        assert health.metrics.successful_plans == 1

    def test_explain_formatted_output(
        self, runtime: PlannerRuntime, refactor_goal: PlanningGoal
    ) -> None:
        result = runtime.plan(refactor_goal)
        explanation = runtime.explain(result.plan)
        assert "Planning Goal" in explanation
        assert "Rename EventBus" in explanation
        assert "Strategy" in explanation
        assert "Sequential" in explanation
        assert "Tasks" in explanation
        assert "Risk" in explanation
        assert "MEDIUM" in explanation
