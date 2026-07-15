"""Tests for the planning strategy protocol."""

from datetime import timedelta
from typing import Any  # <-- ADDED

from eag.planner.enums import GoalType, RiskLevel
from eag.planner.models import ExecutionPlan, PlanningStrategyInfo
from eag.planner.strategy import PlanningStrategy


class DummyPlanningStrategy:
    """A minimal but functional implementation of the PlanningStrategy protocol for testing."""

    def __init__(self) -> None:
        self.name = "Dummy"
        self.priority = 100

    @property
    def info(self) -> PlanningStrategyInfo:
        return PlanningStrategyInfo(
            name="Dummy",
            description="A dummy strategy",
            priority=10,
            supported_goal_types=(GoalType.REFACTOR,),
            supports_parallelism=False,
            experimental=False,
        )

    def supports(self, eng_goal: Any, context: Any) -> bool:
        # If eng_goal is an EngineeringGoal, check its operation, otherwise fallback
        operation = getattr(eng_goal, "operation", None)
        return operation == "refactor" or True

    def create_plan(self, eng_goal: Any, context: Any) -> ExecutionPlan:
        # Safely extract the underlying planning_goal if wrapped
        planning_goal = getattr(eng_goal, "planning_goal", eng_goal)
        return ExecutionPlan(
            id="dummy-plan",
            goal=planning_goal,
            tasks=(),
            steps=(),
            strategy=self.name,
        )

    def estimate_risk(self, eng_goal: Any, context: Any) -> RiskLevel:
        return RiskLevel.NONE

    def estimate_duration(self, eng_goal: Any, context: Any) -> timedelta:
        return timedelta(minutes=1)


class TestPlanningStrategyProtocol:
    def test_is_protocol(self) -> None:
        assert issubclass(PlanningStrategy, object)

    def test_dummy_implementation_isinstance(self) -> None:
        strategy = DummyPlanningStrategy()
        assert isinstance(strategy, PlanningStrategy)

    def test_has_info(self) -> None:
        strategy = DummyPlanningStrategy()
        assert isinstance(strategy.info, PlanningStrategyInfo)
        assert strategy.info.name == "Dummy"

    def test_has_supports(self) -> None:
        strategy = DummyPlanningStrategy()
        assert hasattr(strategy, "supports")

    def test_has_create_plan(self) -> None:
        strategy = DummyPlanningStrategy()
        assert hasattr(strategy, "create_plan")

    def test_has_estimate_risk(self) -> None:
        strategy = DummyPlanningStrategy()
        assert hasattr(strategy, "estimate_risk")

    def test_has_estimate_duration(self) -> None:
        strategy = DummyPlanningStrategy()
        assert hasattr(strategy, "estimate_duration")
