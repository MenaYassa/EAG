"""Tests for the goal analyzer."""

import pytest

from eag.planner.enums import GoalType
from eag.planner.intelligence.goal_analyzer import GoalAnalyzer
from eag.planner.intelligence.models import (
    EngineeringComplexity,
    EngineeringOperation,
    EngineeringScope,
)
from eag.planner.models import PlanningGoal


@pytest.fixture
def analyzer() -> GoalAnalyzer:
    return GoalAnalyzer()


class TestGoalAnalyzerMapping:
    def test_refactor_maps_correctly(self, analyzer: GoalAnalyzer) -> None:
        goal = PlanningGoal(goal_type=GoalType.REFACTOR, title="Rename EventBus")
        eng = analyzer.analyze(goal)
        assert eng.operation == EngineeringOperation.REFACTOR
        assert eng.complexity == EngineeringComplexity.MEDIUM
        assert eng.scope == EngineeringScope.REPOSITORY

    def test_bugfix_maps_correctly(self, analyzer: GoalAnalyzer) -> None:
        goal = PlanningGoal(goal_type=GoalType.BUGFIX, title="Fix null pointer")
        eng = analyzer.analyze(goal)
        assert eng.operation == EngineeringOperation.FIX
        assert eng.complexity == EngineeringComplexity.LOW
        assert eng.scope == EngineeringScope.FILE

    def test_feature_maps_correctly(self, analyzer: GoalAnalyzer) -> None:
        goal = PlanningGoal(goal_type=GoalType.FEATURE, title="Add export")
        eng = analyzer.analyze(goal)
        assert eng.operation == EngineeringOperation.CREATE
        assert eng.complexity == EngineeringComplexity.MEDIUM
        assert eng.scope == EngineeringScope.MODULE


class TestGoalAnalyzerBehavior:
    def test_target_extraction(self, analyzer: GoalAnalyzer) -> None:
        goal = PlanningGoal(goal_type=GoalType.REFACTOR, title="Rename EventBus")
        eng = analyzer.analyze(goal)
        assert eng.target == "Rename EventBus"

    def test_confidence_is_deterministic(self, analyzer: GoalAnalyzer) -> None:
        goal = PlanningGoal(goal_type=GoalType.REFACTOR, title="Rename EventBus")
        eng = analyzer.analyze(goal)
        assert eng.confidence == 1.0

    def test_analyzer_is_deterministic(self, analyzer: GoalAnalyzer) -> None:
        goal = PlanningGoal(goal_type=GoalType.REFACTOR, title="Rename EventBus")
        eng1 = analyzer.analyze(goal)
        eng2 = analyzer.analyze(goal)
        assert eng1 == eng2

    def test_invalid_goal_raises(self, analyzer: GoalAnalyzer) -> None:
        with pytest.raises(ValueError, match="title cannot be empty or whitespace"):
            PlanningGoal(goal_type=GoalType.REFACTOR, title="")

    def test_preserves_planning_goal(self, analyzer: GoalAnalyzer) -> None:
        goal = PlanningGoal(goal_type=GoalType.REFACTOR, title="Rename EventBus")
        eng = analyzer.analyze(goal)
        assert eng.planning_goal == goal
