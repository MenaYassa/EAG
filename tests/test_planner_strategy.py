"""Tests for the planning strategy protocol."""

from datetime import timedelta

from eag.planner.enums import GoalType, RiskLevel
from eag.planner.models import ExecutionPlan, PlanningContext, PlanningGoal, PlanningStrategyInfo
from eag.planner.strategy import PlanningStrategy


class DummyPlanningStrategy:
    """A minimal implementation of the PlanningStrategy protocol for testing."""

    @property
    def info(self) -> PlanningStrategyInfo:
        return PlanningStrategyInfo(
            name="Dummy",
            description="A dummy strategy",
            priority=10,
            supported_goal_types=(GoalType.REFACTOR,),
        )

    @property
    def name(self) -> str:
        return "Dummy"

    @property
    def priority(self) -> int:
        return 0

    def supports(self, goal: PlanningGoal, context: PlanningContext) -> bool:
        return goal.goal_type in self.info.supported_goal_types

    def create_plan(self, goal: PlanningGoal, context: PlanningContext) -> ExecutionPlan:
        return ExecutionPlan(goal=goal)

    def estimate_risk(self, goal: PlanningGoal, context: PlanningContext) -> RiskLevel:
        return RiskLevel.NONE

    def estimate_duration(self, goal: PlanningGoal, context: PlanningContext) -> timedelta:
        return timedelta(minutes=1)


class TestPlanningStrategyProtocol:
    def test_is_protocol(self) -> None:
        assert issubclass(PlanningStrategy, object)

    def test_dummy_implementation_isinstance(self) -> None:
        """A class implementing the interface should be recognized as a strategy."""
        strategy = DummyPlanningStrategy()
        assert isinstance(strategy, PlanningStrategy)

    def test_has_info(self) -> None:
        strategy = DummyPlanningStrategy()
        assert isinstance(strategy.info, PlanningStrategyInfo)
        assert strategy.info.name == "Dummy"

    def test_has_name(self) -> None:
        strategy = DummyPlanningStrategy()
        assert strategy.name == "Dummy"

    def test_has_priority(self) -> None:
        strategy = DummyPlanningStrategy()
        assert strategy.priority == 0

    def test_has_supports(self) -> None:
        strategy = DummyPlanningStrategy()
        goal = PlanningGoal(goal_type=GoalType.REFACTOR, title="Test")
        context = PlanningContext()
        assert strategy.supports(goal, context) is True

    def test_has_create_plan(self) -> None:
        strategy = DummyPlanningStrategy()
        goal = PlanningGoal(goal_type=GoalType.REFACTOR, title="Test")
        context = PlanningContext()
        plan = strategy.create_plan(goal, context)
        assert isinstance(plan, ExecutionPlan)

    def test_has_estimate_risk(self) -> None:
        strategy = DummyPlanningStrategy()
        goal = PlanningGoal(goal_type=GoalType.REFACTOR, title="Test")
        context = PlanningContext()
        risk = strategy.estimate_risk(goal, context)
        assert risk == RiskLevel.NONE

    def test_has_estimate_duration(self) -> None:
        strategy = DummyPlanningStrategy()
        goal = PlanningGoal(goal_type=GoalType.REFACTOR, title="Test")
        context = PlanningContext()
        duration = strategy.estimate_duration(goal, context)
        assert duration == timedelta(minutes=1)
