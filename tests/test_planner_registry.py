"""Tests for the planning strategy registry."""

import pytest

from eag.planner.enums import GoalType
from eag.planner.errors import (
    DuplicatePlanningStrategyError,
    PlanningStrategyNotFoundError,
    PlanningStrategyUnavailableError,
)
from eag.planner.models import PlanningContext, PlanningGoal, PlanningStrategyInfo
from eag.planner.registry import PlanningStrategyRegistry


class DummyLowPriorityStrategy:
    @property
    def info(self) -> PlanningStrategyInfo:
        return PlanningStrategyInfo(name="Low", priority=10)

    def supports(self, goal: PlanningGoal, context: PlanningContext) -> bool:
        return True


class DummyHighPriorityStrategy:
    @property
    def info(self) -> PlanningStrategyInfo:
        return PlanningStrategyInfo(name="High", priority=100)

    def supports(self, goal: PlanningGoal, context: PlanningContext) -> bool:
        return True


class DummySelectiveStrategy:
    @property
    def info(self) -> PlanningStrategyInfo:
        return PlanningStrategyInfo(name="Selective", priority=50)

    def supports(self, goal: PlanningGoal, context: PlanningContext) -> bool:
        return goal.goal_type == GoalType.ANALYSIS


@pytest.fixture
def registry() -> PlanningStrategyRegistry:
    return PlanningStrategyRegistry()


class TestRegistryInitialization:
    def test_empty_registry_supported(self, registry: PlanningStrategyRegistry) -> None:
        assert registry.supported() == ()

    def test_empty_registry_all(self, registry: PlanningStrategyRegistry) -> None:
        assert registry.all() == ()

    def test_empty_registry_default_raises(self, registry: PlanningStrategyRegistry) -> None:
        with pytest.raises(PlanningStrategyNotFoundError):
            registry.default()


class TestRegistryRegistration:
    def test_register_single_strategy(self, registry: PlanningStrategyRegistry) -> None:
        strategy = DummyLowPriorityStrategy()
        registry.register(strategy)
        assert registry.supported() == ("Low",)
        assert registry.all() == (strategy,)

    def test_register_duplicate_raises(self, registry: PlanningStrategyRegistry) -> None:
        registry.register(DummyLowPriorityStrategy())
        with pytest.raises(DuplicatePlanningStrategyError):
            registry.register(DummyLowPriorityStrategy())

    def test_unregister_existing(self, registry: PlanningStrategyRegistry) -> None:
        registry.register(DummyLowPriorityStrategy())
        assert registry.unregister("Low") is True
        assert registry.supported() == ()

    def test_unregister_nonexistent_returns_false(self, registry: PlanningStrategyRegistry) -> None:
        assert registry.unregister("Ghost") is False


class TestRegistryLookup:
    def test_find_no_match_raises(self, registry: PlanningStrategyRegistry) -> None:
        registry.register(DummySelectiveStrategy())
        goal = PlanningGoal(goal_type=GoalType.FEATURE, title="Test")
        with pytest.raises(PlanningStrategyUnavailableError):
            registry.find(goal, PlanningContext())

    def test_find_returns_match(self, registry: PlanningStrategyRegistry) -> None:
        registry.register(DummySelectiveStrategy())
        goal = PlanningGoal(goal_type=GoalType.ANALYSIS, title="Test")
        found = registry.find(goal, PlanningContext())
        assert found.info.name == "Selective"

    def test_find_returns_highest_priority(self, registry: PlanningStrategyRegistry) -> None:
        registry.register(DummyLowPriorityStrategy())
        registry.register(DummyHighPriorityStrategy())
        goal = PlanningGoal(goal_type=GoalType.FEATURE, title="Test")
        found = registry.find(goal, PlanningContext())
        assert found.info.name == "High"

    def test_default_returns_highest_priority(self, registry: PlanningStrategyRegistry) -> None:
        registry.register(DummyLowPriorityStrategy())
        registry.register(DummyHighPriorityStrategy())
        default = registry.default()
        assert default.info.name == "High"

    def test_supported_returns_sorted_names(self, registry: PlanningStrategyRegistry) -> None:
        registry.register(DummyLowPriorityStrategy())
        registry.register(DummyHighPriorityStrategy())
        assert registry.supported() == ("High", "Low")
