"""Hardening tests for the plan simulation engine."""

import pytest

from eag.planner.enums import GoalType, RiskLevel
from eag.planner.intelligence.goal_analyzer import GoalAnalyzer
from eag.planner.intelligence.models import (
    EngineeringComplexity,
    EngineeringExecutionProfile,
    EngineeringGoal,
    EngineeringOperation,
    EngineeringPlanningArtifact,
    EngineeringRiskAssessment,
    EngineeringScope,
    TaskDependencyGraph,
    TaskDependencyNode,
    TaskDependencyStatistics,
)
from eag.planner.intelligence.pipeline import EngineeringIntelligencePipeline
from eag.planner.models import EngineeringTask, PlanningGoal
from eag.planner.simulation.models import (
    EngineeringSimulationReport,
    SimulationImpact,
    SimulationStatus,
    SimulationTimeline,
)
from eag.planner.simulation.simulator import PlanSimulator
from eag.planner.validation.validator import PlanValidator


@pytest.fixture
def analyzer() -> GoalAnalyzer:
    return GoalAnalyzer()


@pytest.fixture
def pipeline() -> EngineeringIntelligencePipeline:
    return EngineeringIntelligencePipeline()


@pytest.fixture
def validator() -> PlanValidator:
    return PlanValidator()


@pytest.fixture
def simulator() -> PlanSimulator:
    return PlanSimulator()


class TestSimulationModelsImmutability:
    def test_report_is_immutable(self) -> None:
        impact = SimulationImpact(
            task_count=1,
            operation_count=1,
            affected_files=1,
            affected_symbols=1,
            affected_modules=1,
        )
        timeline = SimulationTimeline(
            estimated_minutes=10, critical_path_minutes=5, parallel_savings_minutes=5
        )
        report = EngineeringSimulationReport(
            status=SimulationStatus.READY, impact=impact, timeline=timeline, summary="Test"
        )
        with pytest.raises(Exception, match="."):
            report.status = SimulationStatus.BLOCKED  # type: ignore[misc]

    def test_impact_is_immutable(self) -> None:
        impact = SimulationImpact(
            task_count=1,
            operation_count=1,
            affected_files=1,
            affected_symbols=1,
            affected_modules=1,
        )
        with pytest.raises(Exception, match="."):
            impact.task_count = 5  # type: ignore[misc]

    def test_timeline_is_immutable(self) -> None:
        timeline = SimulationTimeline(
            estimated_minutes=10, critical_path_minutes=5, parallel_savings_minutes=5
        )
        with pytest.raises(Exception, match="."):
            timeline.estimated_minutes = 20  # type: ignore[misc]


class TestTimelineCalculations:
    def test_critical_path_preserved(
        self,
        analyzer: GoalAnalyzer,
        pipeline: EngineeringIntelligencePipeline,
        simulator: PlanSimulator,
    ) -> None:
        goal = analyzer.analyze(PlanningGoal(goal_type=GoalType.FEATURE, title="Add Export"))
        artifact = pipeline.analyze(goal)
        report = simulator.simulate(artifact)

        assert (
            report.timeline.critical_path_minutes
            == artifact.execution_profile.critical_path_duration
        )

    def test_parallel_savings_calculated(
        self,
        analyzer: GoalAnalyzer,
        pipeline: EngineeringIntelligencePipeline,
        simulator: PlanSimulator,
    ) -> None:
        goal = analyzer.analyze(PlanningGoal(goal_type=GoalType.FEATURE, title="Add Export"))
        artifact = pipeline.analyze(goal)
        report = simulator.simulate(artifact)

        assert (
            report.timeline.parallel_savings_minutes == artifact.execution_profile.parallel_savings
        )

    def test_zero_duration_plan(self, simulator: PlanSimulator) -> None:
        # Manually construct an artifact with zero duration
        planning_goal = PlanningGoal(goal_type=GoalType.ANALYSIS, title="Analyze X")
        eng_goal = EngineeringGoal(
            planning_goal=planning_goal,
            operation=EngineeringOperation.ANALYZE,
            target="X",
            complexity=EngineeringComplexity.TRIVIAL,
            scope=EngineeringScope.SYMBOL,
        )
        task = EngineeringTask(id="T1", title="Analyze")
        node = TaskDependencyNode(task=task, incoming=(), outgoing=())
        graph = TaskDependencyGraph(
            nodes={"T1": node},
            statistics=TaskDependencyStatistics(
                task_count=1,
                edge_count=0,
                root_count=1,
                leaf_count=1,
                maximum_depth=0,
                independent_tasks=1,
            ),
        )
        risk = EngineeringRiskAssessment(overall_risk=RiskLevel.NONE)

        profile = EngineeringExecutionProfile(
            total_engineering_time=0.0,
            critical_path_duration=0.0,
            parallel_savings=0.0,
            estimated_active_work=0.0,
            estimated_validation=0.0,
            estimated_review=0.0,
            confidence=1.0,
            summary="Zero",
        )

        artifact = EngineeringPlanningArtifact(
            goal=planning_goal,
            engineering_goal=eng_goal,
            tasks=(task,),
            graph=graph,
            risk=risk,
            execution_profile=profile,
        )

        report = simulator.simulate(artifact)
        assert report.timeline.estimated_minutes == 0.0
        assert report.status == SimulationStatus.READY


class TestIntegrationPipeline:
    def test_validation_to_simulation_pipeline(
        self,
        analyzer: GoalAnalyzer,
        pipeline: EngineeringIntelligencePipeline,
        validator: PlanValidator,
        simulator: PlanSimulator,
    ) -> None:
        """Test the complete chain: Goal -> Planner -> Validation -> Simulation -> Report"""
        goal = analyzer.analyze(PlanningGoal(goal_type=GoalType.REFACTOR, title="Rename EventBus"))
        artifact = pipeline.analyze(goal)

        # Validate
        validation_result = validator.validate(artifact)
        assert validation_result.valid is True

        # Simulate (only if valid)
        if validation_result.valid:
            sim_report = simulator.simulate(artifact)
            assert sim_report.status in [SimulationStatus.READY, SimulationStatus.WARNING]
            assert "Rename EventBus" in artifact.goal.title
            assert sim_report.impact.task_count > 0
        else:
            pytest.fail("Validation failed, cannot simulate.")
