"""Tests for the engineering intelligence pipeline."""

import pytest

from eag.planner.enums import GoalType
from eag.planner.intelligence.goal_analyzer import GoalAnalyzer
from eag.planner.intelligence.models import EngineeringPlanningArtifact
from eag.planner.intelligence.pipeline import EngineeringIntelligencePipeline
from eag.planner.models import PlanningGoal


@pytest.fixture
def analyzer() -> GoalAnalyzer:
    return GoalAnalyzer()


@pytest.fixture
def pipeline() -> EngineeringIntelligencePipeline:
    return EngineeringIntelligencePipeline()


class TestIntelligencePipeline:
    def test_pipeline_produces_artifact(
        self, analyzer: GoalAnalyzer, pipeline: EngineeringIntelligencePipeline
    ) -> None:
        goal = analyzer.analyze(PlanningGoal(goal_type=GoalType.REFACTOR, title="Rename X"))
        artifact = pipeline.analyze(goal)

        assert isinstance(artifact, EngineeringPlanningArtifact)
        assert artifact.goal.goal_type == GoalType.REFACTOR
        assert len(artifact.tasks) == 5
        assert artifact.graph.statistics.task_count == 5
        assert artifact.risk.overall_risk is not None
        assert artifact.execution_profile.total_engineering_time > 0

    def test_pipeline_determinism(
        self, analyzer: GoalAnalyzer, pipeline: EngineeringIntelligencePipeline
    ) -> None:
        goal = analyzer.analyze(PlanningGoal(goal_type=GoalType.REFACTOR, title="Rename X"))
        artifact1 = pipeline.analyze(goal)
        artifact2 = pipeline.analyze(goal)

        assert artifact1 == artifact2
        assert artifact1.tasks == artifact2.tasks
        assert artifact1.execution_profile == artifact2.execution_profile

    def test_pipeline_preserves_goal(
        self, analyzer: GoalAnalyzer, pipeline: EngineeringIntelligencePipeline
    ) -> None:
        goal = analyzer.analyze(PlanningGoal(goal_type=GoalType.FEATURE, title="Add Export"))
        artifact = pipeline.analyze(goal)

        assert artifact.engineering_goal == goal
        assert artifact.goal == goal.planning_goal
