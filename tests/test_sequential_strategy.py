"""Tests for the sequential planning strategy."""

from datetime import timedelta

import pytest

from eag.planner.enums import GoalType, PlanState, RiskLevel
from eag.planner.errors import InvalidGoalError
from eag.planner.intelligence.goal_analyzer import GoalAnalyzer
from eag.planner.intelligence.models import EngineeringGoal
from eag.planner.models import (
    ExecutionPlan,
    PlanningContext,
    PlanningGoal,
)
from eag.planner.strategies.sequential import SequentialStrategy
from eag.planner.strategy import PlanningStrategy


@pytest.fixture
def analyzer() -> GoalAnalyzer:
    return GoalAnalyzer()


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
def refactor_eng_goal(analyzer: GoalAnalyzer, refactor_goal: PlanningGoal) -> EngineeringGoal:
    return analyzer.analyze(refactor_goal)


@pytest.fixture
def unsupported_goal() -> PlanningGoal:
    return PlanningGoal(
        goal_type=GoalType.MAINTENANCE,
        title="Update Dependencies",
    )


@pytest.fixture
def unsupported_eng_goal(analyzer: GoalAnalyzer, unsupported_goal: PlanningGoal) -> EngineeringGoal:
    return analyzer.analyze(unsupported_goal)


class TestSequentialStrategyInitialization:
    def test_implements_protocol(self, strategy: SequentialStrategy) -> None:
        assert isinstance(strategy, PlanningStrategy)

    def test_info(self, strategy: SequentialStrategy) -> None:
        info = strategy.info
        assert info.name == "Sequential"
        assert info.priority == 100


class TestSequentialStrategySupport:
    def test_supports_refactor(
        self, strategy: SequentialStrategy, refactor_eng_goal: EngineeringGoal
    ) -> None:
        assert strategy.supports(refactor_eng_goal, PlanningContext()) is True

    def test_rejects_unsupported(
        self, strategy: SequentialStrategy, unsupported_eng_goal: EngineeringGoal
    ) -> None:
        assert strategy.supports(unsupported_eng_goal, PlanningContext()) is False


class TestSequentialStrategyRiskAndDuration:
    def test_risk_refactor_is_medium(
        self, strategy: SequentialStrategy, refactor_eng_goal: EngineeringGoal
    ) -> None:
        assert strategy.estimate_risk(refactor_eng_goal, PlanningContext()) == RiskLevel.MEDIUM

    def test_duration_is_deterministic(
        self, strategy: SequentialStrategy, refactor_eng_goal: EngineeringGoal
    ) -> None:
        duration = strategy.estimate_duration(refactor_eng_goal, PlanningContext())
        assert isinstance(duration, timedelta)


class TestSequentialStrategyPlanning:
    def test_create_plan_returns_execution_plan(
        self, strategy: SequentialStrategy, refactor_eng_goal: EngineeringGoal
    ) -> None:
        plan = strategy.create_plan(refactor_eng_goal, PlanningContext())
        assert isinstance(plan, ExecutionPlan)
        assert plan.goal == refactor_eng_goal.planning_goal
        assert plan.state == PlanState.VALIDATED

    def test_create_plan_generates_tasks(
        self, strategy: SequentialStrategy, refactor_eng_goal: EngineeringGoal
    ) -> None:
        plan = strategy.create_plan(refactor_eng_goal, PlanningContext())
        assert len(plan.tasks) == 5
        assert plan.tasks[0].title == "Locate Target"

    def test_create_plan_generates_steps(
        self, strategy: SequentialStrategy, refactor_eng_goal: EngineeringGoal
    ) -> None:
        plan = strategy.create_plan(refactor_eng_goal, PlanningContext())
        assert len(plan.steps) == 5
        assert plan.steps[0].task_id == "TASK-001"

    def test_create_plan_unsupported_raises(
        self, strategy: SequentialStrategy, unsupported_eng_goal: EngineeringGoal
    ) -> None:
        with pytest.raises(InvalidGoalError):
            strategy.create_plan(unsupported_eng_goal, PlanningContext())

    def test_create_plan_is_deterministic(
        self, strategy: SequentialStrategy, refactor_eng_goal: EngineeringGoal
    ) -> None:
        plan1 = strategy.create_plan(refactor_eng_goal, PlanningContext())
        plan2 = strategy.create_plan(refactor_eng_goal, PlanningContext())
        assert plan1.id == plan2.id
        assert plan1.tasks == plan2.tasks
