"""Tests for the plan simulation engine."""

import pytest

from eag.planner.enums import GoalType
from eag.planner.intelligence.goal_analyzer import GoalAnalyzer
from eag.planner.intelligence.pipeline import EngineeringIntelligencePipeline
from eag.planner.models import PlanningGoal
from eag.planner.simulation.models import SimulationStatus
from eag.planner.simulation.simulator import PlanSimulator


@pytest.fixture
def analyzer() -> GoalAnalyzer:
    return GoalAnalyzer()


@pytest.fixture
def pipeline() -> EngineeringIntelligencePipeline:
    return EngineeringIntelligencePipeline()


@pytest.fixture
def simulator() -> PlanSimulator:
    return PlanSimulator()


class TestPlanSimulator:
    def test_simulate_ready_status(
        self,
        analyzer: GoalAnalyzer,
        pipeline: EngineeringIntelligencePipeline,
        simulator: PlanSimulator,
    ) -> None:
        goal = analyzer.analyze(PlanningGoal(goal_type=GoalType.FEATURE, title="Add Export"))
        artifact = pipeline.analyze(goal)
        report = simulator.simulate(artifact)

        assert report.status == SimulationStatus.READY
        assert report.impact.task_count == 5
        assert report.timeline.estimated_minutes > 0
        assert len(report.timeline.phases) == 5

    def test_simulate_warning_status(
        self,
        analyzer: GoalAnalyzer,
        pipeline: EngineeringIntelligencePipeline,
        simulator: PlanSimulator,
    ) -> None:
        goal = analyzer.analyze(PlanningGoal(goal_type=GoalType.REFACTOR, title="Rename X"))
        artifact = pipeline.analyze(goal)
        report = simulator.simulate(artifact)

        assert report.status == SimulationStatus.WARNING
        assert len(report.warnings) > 0
        assert "High risk" in report.warnings[0]

    def test_impact_analysis_rename(
        self,
        analyzer: GoalAnalyzer,
        pipeline: EngineeringIntelligencePipeline,
        simulator: PlanSimulator,
    ) -> None:
        goal = analyzer.analyze(PlanningGoal(goal_type=GoalType.REFACTOR, title="Rename X"))
        artifact = pipeline.analyze(goal)
        report = simulator.simulate(artifact)

        assert report.impact.affected_symbols == 5
        assert report.impact.affected_files == 2

    def test_checkpoint_analysis_validation(
        self,
        analyzer: GoalAnalyzer,
        pipeline: EngineeringIntelligencePipeline,
        simulator: PlanSimulator,
    ) -> None:
        goal = analyzer.analyze(PlanningGoal(goal_type=GoalType.FEATURE, title="Add Export"))
        artifact = pipeline.analyze(goal)
        report = simulator.simulate(artifact)

        # Should have a checkpoint after "Test"
        assert any("Test" in cp.name for cp in report.checkpoints)

    def test_checkpoint_analysis_dangerous_op(
        self,
        analyzer: GoalAnalyzer,
        pipeline: EngineeringIntelligencePipeline,
        simulator: PlanSimulator,
    ) -> None:
        goal = analyzer.analyze(PlanningGoal(goal_type=GoalType.MAINTENANCE, title="Delete X"))
        artifact = pipeline.analyze(goal)
        report = simulator.simulate(artifact)

        assert any("Pre-delete" in cp.name for cp in report.checkpoints)

    def test_summary_is_explainable(
        self,
        analyzer: GoalAnalyzer,
        pipeline: EngineeringIntelligencePipeline,
        simulator: PlanSimulator,
    ) -> None:
        goal = analyzer.analyze(PlanningGoal(goal_type=GoalType.FEATURE, title="Add Export"))
        artifact = pipeline.analyze(goal)
        report = simulator.simulate(artifact)

        assert "ready for execution" in report.summary
