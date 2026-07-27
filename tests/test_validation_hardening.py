"""Hardening tests for the plan validation engine."""

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
from eag.planner.validation.models import (
    EngineeringPlanValidationResult,
    ValidationCategory,
    ValidationIssue,
    ValidationSeverity,
)
from eag.planner.validation.validator import PlanValidator


@pytest.fixture
def validator() -> PlanValidator:
    return PlanValidator()


def build_broken_artifact(
    tasks: tuple[EngineeringTask, ...],
    cyclic: bool = False,
    goal_type: GoalType = GoalType.REFACTOR,
    operation: EngineeringOperation = EngineeringOperation.REFACTOR,
    risk_level: RiskLevel = RiskLevel.NONE,
    rollback: EngineeringComplexity = EngineeringComplexity.LOW,
) -> EngineeringPlanningArtifact:
    """Helper to manually construct an artifact with specific flaws, bypassing the pipeline."""
    nodes = {}
    incoming_map = {t.id: [] for t in tasks}
    for t in tasks:
        for dep in t.dependencies:
            if dep in incoming_map:
                incoming_map[dep].append(t.id)

    for t in tasks:
        nodes[t.id] = TaskDependencyNode(
            task=t, incoming=tuple(incoming_map.get(t.id, [])), outgoing=t.dependencies
        )

    stats = TaskDependencyStatistics(
        task_count=len(tasks),
        edge_count=sum(len(t.dependencies) for t in tasks),
        root_count=sum(1 for t in tasks if not t.dependencies),
        leaf_count=sum(1 for n in nodes.values() if not n.incoming),
        maximum_depth=1,
        independent_tasks=sum(1 for n in nodes.values() if not n.incoming and not n.outgoing),
        cyclic=cyclic,
    )
    graph = TaskDependencyGraph(nodes=nodes, statistics=stats)

    planning_goal = PlanningGoal(goal_type=goal_type, title="Test Goal")
    eng_goal = EngineeringGoal(
        planning_goal=planning_goal,
        operation=operation,
        target="Test",
        complexity=EngineeringComplexity.LOW,
        scope=EngineeringScope.FILE,
        confidence=1.0,
    )

    risk = EngineeringRiskAssessment(
        overall_risk=risk_level, confidence=1.0, rollback_complexity=rollback
    )

    profile = EngineeringExecutionProfile(
        total_engineering_time=1.0,
        critical_path_duration=1.0,
        parallel_savings=0.0,
        estimated_active_work=1.0,
        estimated_validation=0.0,
        estimated_review=0.0,
        confidence=1.0,
        summary="Test",
    )

    return EngineeringPlanningArtifact(
        goal=planning_goal,
        engineering_goal=eng_goal,
        tasks=tasks,
        graph=graph,
        risk=risk,
        execution_profile=profile,
    )


class TestValidationModels:
    def test_validation_issue_is_immutable(self) -> None:
        issue = ValidationIssue(
            category=ValidationCategory.STRUCTURE, severity=ValidationSeverity.ERROR, message="Test"
        )
        with pytest.raises(Exception, match="."):
            issue.message = "New"  # type: ignore[misc]

    def test_validation_result_is_immutable(self) -> None:
        result = EngineeringPlanValidationResult(valid=True)
        with pytest.raises(Exception, match="."):
            result.valid = False  # type: ignore[misc]

    def test_empty_message_rejected(self) -> None:
        with pytest.raises(ValueError, match="message cannot be empty"):
            ValidationIssue(
                category=ValidationCategory.STRUCTURE, severity=ValidationSeverity.ERROR, message=""
            )

    def test_invalid_severity_rejected(self) -> None:
        with pytest.raises(TypeError, match="severity must be a ValidationSeverity"):
            ValidationIssue(
                category=ValidationCategory.STRUCTURE,
                severity="bad",  # type: ignore[arg-type]
                message="Test",
            )

    def test_invalid_category_rejected(self) -> None:
        with pytest.raises(TypeError, match="category must be a ValidationCategory"):
            ValidationIssue(
                category="bad",  # type: ignore[arg-type]
                severity=ValidationSeverity.ERROR,
                message="Test",
            )


class TestDependencyValidation:
    def test_missing_dependency_detected(self, validator: PlanValidator) -> None:
        tasks = (
            EngineeringTask(id="A", title="Task A"),
            EngineeringTask(id="B", title="Task B", dependencies=("X",)),
        )
        artifact = build_broken_artifact(tasks)
        result = validator.validate(artifact)

        assert not result.valid
        assert any("missing task X" in i.message for i in result.issues)

    def test_cycle_detected(self, validator: PlanValidator) -> None:
        tasks = (
            EngineeringTask(id="A", title="Task A", dependencies=("B",)),
            EngineeringTask(id="B", title="Task B", dependencies=("A",)),
        )
        artifact = build_broken_artifact(tasks, cyclic=True)
        result = validator.validate(artifact)

        assert not result.valid
        assert any("Circular dependency" in i.message for i in result.issues)

    def test_orphan_task_detected(self, validator: PlanValidator) -> None:
        tasks = (
            EngineeringTask(id="A", title="Task A"),
            EngineeringTask(id="B", title="Task B"),
        )
        artifact = build_broken_artifact(tasks)
        result = validator.validate(artifact)

        assert any("disconnected" in i.message for i in result.issues)


class TestMultipleIssues:
    def test_multiple_validation_issues_collected(self, validator: PlanValidator) -> None:
        tasks = (
            EngineeringTask(id="A", title="Task A"),
            EngineeringTask(id="B", title="Task B", dependencies=("X",)),
        )
        artifact = build_broken_artifact(
            tasks,
            goal_type=GoalType.MAINTENANCE,
            operation=EngineeringOperation.DELETE,
            risk_level=RiskLevel.HIGH,
            rollback=EngineeringComplexity.EXTREME,
        )

        result = validator.validate(artifact)

        assert not result.valid
        assert result.errors > 0
        assert result.critical > 0
        assert result.warnings > 0

        assert any(
            i.category == ValidationCategory.DEPENDENCY and i.severity == ValidationSeverity.ERROR
            for i in result.issues
        )
        assert any(
            i.category == ValidationCategory.SAFETY and i.severity == ValidationSeverity.CRITICAL
            for i in result.issues
        )
        assert any(
            i.category == ValidationCategory.RISK and i.severity == ValidationSeverity.WARNING
            for i in result.issues
        )


class TestValidationSummary:
    def test_summary_is_explainable(self, validator: PlanValidator) -> None:
        tasks = (
            EngineeringTask(id="A", title="Task A"),
            EngineeringTask(id="B", title="Task B", dependencies=("X",)),
        )
        artifact = build_broken_artifact(tasks)
        result = validator.validate(artifact)

        assert "failed" in result.summary
        assert "1 errors" in result.summary


class TestIntegrationCheck:
    def test_pipeline_still_produces_valid_artifact(self, validator: PlanValidator) -> None:
        analyzer = GoalAnalyzer()
        pipeline = EngineeringIntelligencePipeline()
        goal = analyzer.analyze(PlanningGoal(goal_type=GoalType.FEATURE, title="Add new feature"))
        artifact = pipeline.analyze(goal)
        result = validator.validate(artifact)
        assert result.valid
