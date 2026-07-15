"""Tests for the task decomposer."""

import pytest

from eag.planner.enums import GoalType
from eag.planner.intelligence.goal_analyzer import GoalAnalyzer

# Look for the imports from eag.planner.intelligence.models and add EngineeringGoal
from eag.planner.intelligence.models import (
    EngineeringGoal,  # <-- ADDED
)
from eag.planner.intelligence.task_decomposer import TaskDecomposer
from eag.planner.models import PlanningGoal


@pytest.fixture
def analyzer() -> GoalAnalyzer:
    return GoalAnalyzer()


@pytest.fixture
def decomposer() -> TaskDecomposer:
    return TaskDecomposer()


class TestTaskDecomposerTemplates:
    def test_refactor_template(self, analyzer: GoalAnalyzer, decomposer: TaskDecomposer) -> None:
        goal = analyzer.analyze(PlanningGoal(goal_type=GoalType.REFACTOR, title="Rename X"))
        tasks = decomposer.decompose(goal)

        assert len(tasks) == 5
        assert tasks[0].title == "Locate Target"
        assert tasks[0].id == "TASK-001"
        assert tasks[1].dependencies == ("TASK-001",)

    def test_feature_template(self, analyzer: GoalAnalyzer, decomposer: TaskDecomposer) -> None:
        goal = analyzer.analyze(PlanningGoal(goal_type=GoalType.FEATURE, title="Add Export"))
        tasks = decomposer.decompose(goal)

        assert len(tasks) == 5
        assert tasks[0].title == "Analyze Requirement"
        assert tasks[4].title == "Document"

    def test_bugfix_template(self, analyzer: GoalAnalyzer, decomposer: TaskDecomposer) -> None:
        goal = analyzer.analyze(PlanningGoal(goal_type=GoalType.BUGFIX, title="Fix NullPtr"))
        tasks = decomposer.decompose(goal)

        assert len(tasks) == 5
        assert tasks[0].title == "Reproduce Problem"
        assert tasks[2].title == "Implement Fix"

    def test_documentation_template(
        self, analyzer: GoalAnalyzer, decomposer: TaskDecomposer
    ) -> None:
        goal = analyzer.analyze(PlanningGoal(goal_type=GoalType.DOCUMENTATION, title="Update Docs"))
        tasks = decomposer.decompose(goal)

        assert len(tasks) == 3
        assert "Build" not in [t.title for t in tasks]
        assert tasks[2].title == "Review Consistency"


class TestTaskDecomposerBehavior:
    def test_determinism(self, analyzer: GoalAnalyzer, decomposer: TaskDecomposer) -> None:
        goal = analyzer.analyze(PlanningGoal(goal_type=GoalType.REFACTOR, title="Rename X"))
        tasks1 = decomposer.decompose(goal)
        tasks2 = decomposer.decompose(goal)

        assert tasks1 == tasks2
        assert [t.id for t in tasks1] == [
            "TASK-001",
            "TASK-002",
            "TASK-003",
            "TASK-004",
            "TASK-005",
        ]

    def test_unsupported_operation_raises(
        self, analyzer: GoalAnalyzer, decomposer: TaskDecomposer
    ) -> None:
        from unittest.mock import MagicMock

        mock_goal = MagicMock(spec=EngineeringGoal)
        # Give it an operation that does not exist in your templates
        mock_goal.operation = "UNSUPPORTED_RANDOM_OPERATION"

        with pytest.raises(ValueError, match="No decomposition template"):
            decomposer.decompose(mock_goal)

    def test_task_dependencies_chain_correctly(
        self, analyzer: GoalAnalyzer, decomposer: TaskDecomposer
    ) -> None:
        goal = analyzer.analyze(PlanningGoal(goal_type=GoalType.FEATURE, title="Add X"))
        tasks = decomposer.decompose(goal)

        for i in range(1, len(tasks)):
            assert f"TASK-{i:03d}" in tasks[i].dependencies
