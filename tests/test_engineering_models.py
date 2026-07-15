"""Tests for the engineering intelligence models."""

from dataclasses import FrozenInstanceError

import pytest

from eag.planner.enums import GoalType
from eag.planner.intelligence.models import (
    EngineeringComplexity,
    EngineeringGoal,
    EngineeringOperation,
    EngineeringScope,
)
from eag.planner.models import PlanningGoal


class TestEngineeringEnums:
    def test_operation_values(self) -> None:
        assert EngineeringOperation.RENAME == "rename"
        assert EngineeringOperation.ANALYZE == "analyze"

    def test_complexity_values(self) -> None:
        assert EngineeringComplexity.TRIVIAL == "trivial"
        assert EngineeringComplexity.EXTREME == "extreme"

    def test_scope_values(self) -> None:
        assert EngineeringScope.SYMBOL == "symbol"
        assert EngineeringScope.SYSTEM == "system"


class TestEngineeringGoal:
    @pytest.fixture
    def valid_goal(self) -> PlanningGoal:
        return PlanningGoal(goal_type=GoalType.REFACTOR, title="Rename EventBus")

    def test_valid_construction(self, valid_goal: PlanningGoal) -> None:
        eng_goal = EngineeringGoal(
            planning_goal=valid_goal,
            operation=EngineeringOperation.RENAME,
            target="EventBus",
            complexity=EngineeringComplexity.LOW,
            scope=EngineeringScope.REPOSITORY,
        )
        with pytest.raises(FrozenInstanceError):
            eng_goal.target = "EventHub"  # type: ignore[misc]
        assert eng_goal.operation == EngineeringOperation.RENAME
        assert eng_goal.confidence == 1.0

    def test_empty_target_raises(self, valid_goal: PlanningGoal) -> None:
        with pytest.raises(ValueError, match="target cannot be empty"):
            EngineeringGoal(
                planning_goal=valid_goal,
                operation=EngineeringOperation.RENAME,
                target="",
                complexity=EngineeringComplexity.LOW,
                scope=EngineeringScope.REPOSITORY,
            )

    def test_invalid_confidence_raises(self, valid_goal: PlanningGoal) -> None:
        with pytest.raises(ValueError, match="confidence must be between 0.0 and 1.0"):
            EngineeringGoal(
                planning_goal=valid_goal,
                operation=EngineeringOperation.RENAME,
                target="EventBus",
                complexity=EngineeringComplexity.LOW,
                scope=EngineeringScope.REPOSITORY,
                confidence=1.5,
            )

    def test_immutability(self, valid_goal: PlanningGoal) -> None:
        eng_goal = EngineeringGoal(
            planning_goal=valid_goal,
            operation=EngineeringOperation.RENAME,
            target="EventBus",
            complexity=EngineeringComplexity.LOW,
            scope=EngineeringScope.REPOSITORY,
        )
        with pytest.raises(FrozenInstanceError):
            eng_goal.target = "EventHub"  # type: ignore[misc]
