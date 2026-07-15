"""Tests for the sequential planning strategy."""

from datetime import timedelta

import pytest

from eag.planner.enums import GoalType, PlanState, RiskLevel

# ADDED: InvalidGoalError included in the errors import block
from eag.planner.errors import InvalidGoalError
from eag.planner.models import (
    ExecutionPlan,
    PlanningContext,
    PlanningGoal,
)
from eag.planner.strategies.sequential import SequentialStrategy
from eag.planner.strategy import PlanningStrategy


@pytest.fixture
def strategy() -> SequentialStrategy:
    return SequentialStrategy()


@pytest.fixture
def refactor_goal() -> PlanningGoal:
    return PlanningGoal(
        goal_type=GoalType.REFACTOR,
        title="Rename EventBus",
        description="Rename EventBus to EventHub",
    )


@pytest.fixture
def analysis_goal() -> PlanningGoal:
    return PlanningGoal(
        goal_type=GoalType.ANALYSIS,
        title="Understand Graph",
    )


@pytest.fixture
def unsupported_goal() -> PlanningGoal:
    return PlanningGoal(
        goal_type=GoalType.MAINTENANCE,
        title="Update Dependencies",
    )


class TestSequentialStrategyInitialization:
    def test_implements_protocol(self, strategy: SequentialStrategy) -> None:
        assert isinstance(strategy, PlanningStrategy)
        assert hasattr(strategy, "name")
        assert hasattr(strategy, "priority")
        assert hasattr(strategy, "create_plan")
        assert hasattr(strategy, "estimate_risk")

    def test_info(self, strategy: SequentialStrategy) -> None:
        info = strategy.info
        assert info.name == "Sequential"
        assert info.priority == 100
        assert GoalType.REFACTOR in info.supported_goal_types
        assert info.supports_parallelism is False


class TestSequentialStrategySupport:
    def test_supports_refactor(
        self, strategy: SequentialStrategy, refactor_goal: PlanningGoal
    ) -> None:
        assert strategy.supports(refactor_goal, PlanningContext()) is True

    def test_supports_analysis(
        self, strategy: SequentialStrategy, analysis_goal: PlanningGoal
    ) -> None:
        assert strategy.supports(analysis_goal, PlanningContext()) is True

    def test_rejects_unsupported(
        self, strategy: SequentialStrategy, unsupported_goal: PlanningGoal
    ) -> None:
        assert strategy.supports(unsupported_goal, PlanningContext()) is False


class TestSequentialStrategyRiskAndDuration:
    def test_risk_analysis_is_none(
        self, strategy: SequentialStrategy, analysis_goal: PlanningGoal
    ) -> None:
        assert strategy.estimate_risk(analysis_goal, PlanningContext()) == RiskLevel.NONE

    def test_risk_refactor_is_medium(
        self, strategy: SequentialStrategy, refactor_goal: PlanningGoal
    ) -> None:
        assert strategy.estimate_risk(refactor_goal, PlanningContext()) == RiskLevel.MEDIUM

    def test_duration_is_deterministic(
        self, strategy: SequentialStrategy, refactor_goal: PlanningGoal
    ) -> None:
        duration = strategy.estimate_duration(refactor_goal, PlanningContext())
        assert isinstance(duration, timedelta)
        assert duration.total_seconds() > 0


class TestSequentialStrategyPlanning:
    def test_create_plan_returns_execution_plan(
        self, strategy: SequentialStrategy, refactor_goal: PlanningGoal
    ) -> None:
        plan = strategy.create_plan(refactor_goal, PlanningContext())
        assert isinstance(plan, ExecutionPlan)
        assert plan.goal == refactor_goal
        assert plan.state == PlanState.VALIDATED

    def test_create_plan_generates_tasks(
        self, strategy: SequentialStrategy, refactor_goal: PlanningGoal
    ) -> None:
        plan = strategy.create_plan(refactor_goal, PlanningContext())
        assert len(plan.tasks) == 5
        assert plan.tasks[0].title == "Locate Target"

    def test_create_plan_orders_dependencies(
        self, strategy: SequentialStrategy, refactor_goal: PlanningGoal
    ) -> None:
        plan = strategy.create_plan(refactor_goal, PlanningContext())
        # Task 2 depends on Task 1
        assert plan.tasks[1].dependencies == ("task-1",)

    def test_create_plan_generates_steps(
        self, strategy: SequentialStrategy, refactor_goal: PlanningGoal
    ) -> None:
        plan = strategy.create_plan(refactor_goal, PlanningContext())
        assert len(plan.steps) > 0
        # Check that steps reference tasks
        assert plan.steps[0].task_id == "task-1"

    def test_create_plan_generates_statistics(
        self, strategy: SequentialStrategy, refactor_goal: PlanningGoal
    ) -> None:
        plan = strategy.create_plan(refactor_goal, PlanningContext())
        assert plan.statistics.task_count == 5
        assert plan.statistics.step_count > 0
        assert plan.statistics.risk_score == 0.5  # MEDIUM risk

    def test_create_plan_unsupported_raises(
        self, strategy: SequentialStrategy, unsupported_goal: PlanningGoal
    ) -> None:
        with pytest.raises(InvalidGoalError):
            strategy.create_plan(unsupported_goal, PlanningContext())

    def test_create_plan_is_deterministic(
        self, strategy: SequentialStrategy, refactor_goal: PlanningGoal
    ) -> None:
        plan1 = strategy.create_plan(refactor_goal, PlanningContext())
        plan2 = strategy.create_plan(refactor_goal, PlanningContext())

        # Since IDs are deterministic based on goal ID
        assert plan1.id == plan2.id
        assert plan1.tasks == plan2.tasks
        assert plan1.steps == plan2.steps
