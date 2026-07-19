"""Tests for the planner approval and governance engine (Sprint 5.7)."""

import pytest

from eag.planner.approval.engine import ApprovalEngine
from eag.planner.approval.enums import ApprovalLevel, ApprovalReason, ApprovalState
from eag.planner.approval.models import ApprovalDecision, ApprovalRequest
from eag.planner.approval.policies import (
    AutomaticApprovalPolicy,
    DangerousOperationPolicy,
    OwnershipPolicy,
    RiskApprovalPolicy,
)
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
from eag.planner.validation.models import (
    EngineeringPlanValidationResult,
)
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
def engine() -> ApprovalEngine:
    return ApprovalEngine()


def build_artifact(
    goal_type: GoalType = GoalType.FEATURE,
    operation: EngineeringOperation = EngineeringOperation.CREATE,
    risk_level: RiskLevel = RiskLevel.NONE,
    scope: EngineeringScope = EngineeringScope.MODULE,
) -> EngineeringPlanningArtifact:
    planning_goal = PlanningGoal(goal_type=goal_type, title="Test Goal")
    eng_goal = EngineeringGoal(
        planning_goal=planning_goal,
        operation=operation,
        target="Test",
        complexity=EngineeringComplexity.LOW,
        scope=scope,
    )
    task = EngineeringTask(id="T1", title="Test Task")
    node = TaskDependencyNode(task=task)
    graph = TaskDependencyGraph(
        nodes={"T1": node},
        statistics=TaskDependencyStatistics(task_count=1, root_count=1, leaf_count=1),
    )
    risk = EngineeringRiskAssessment(overall_risk=risk_level)
    profile = EngineeringExecutionProfile(
        total_engineering_time=1.0,
        critical_path_duration=1.0,
        parallel_savings=0.0,
        estimated_active_work=1.0,
        estimated_validation=0.0,
        estimated_review=0.0,
        confidence=1.0,
        summary="Test execution profile summary",
    )
    return EngineeringPlanningArtifact(
        goal=planning_goal,
        engineering_goal=eng_goal,
        tasks=(task,),
        graph=graph,
        risk=risk,
        execution_profile=profile,
    )


def build_validation(valid: bool = True) -> EngineeringPlanValidationResult:
    return EngineeringPlanValidationResult(valid=valid)


def build_simulation(
    status: SimulationStatus = SimulationStatus.READY,
) -> EngineeringSimulationReport:
    impact = SimulationImpact(
        task_count=1, operation_count=1, affected_files=1, affected_symbols=1, affected_modules=1
    )
    timeline = SimulationTimeline(
        estimated_minutes=1.0, critical_path_minutes=1.0, parallel_savings_minutes=0.0
    )
    return EngineeringSimulationReport(status=status, impact=impact, timeline=timeline)


class TestPlannerApprovalModels:
    def test_request_is_immutable(self) -> None:
        req = ApprovalRequest(id="req-1", plan_id="plan-1")
        with pytest.raises(Exception, match="."):
            req.id = "new"  # type: ignore[misc]

    def test_decision_is_immutable(self) -> None:
        dec = ApprovalDecision(state=ApprovalState.APPROVED)
        with pytest.raises(Exception, match="."):
            dec.state = ApprovalState.REJECTED  # type: ignore[misc]

    def test_invalid_state_rejected(self) -> None:
        with pytest.raises(TypeError):
            ApprovalDecision(state="bad")  # type: ignore[arg-type]


class TestPlannerApprovalPolicies:
    def test_auto_approval(self) -> None:
        artifact = build_artifact(risk_level=RiskLevel.LOW)
        policy = AutomaticApprovalPolicy()
        finding = policy.evaluate(artifact, build_validation(), build_simulation())
        assert finding.approved is True
        assert finding.requires_manual is False

    def test_high_risk_requires_manual(self) -> None:
        artifact = build_artifact(risk_level=RiskLevel.HIGH)
        policy = RiskApprovalPolicy()
        finding = policy.evaluate(artifact, build_validation(), build_simulation())
        assert finding.requires_manual is True
        assert finding.required_level == ApprovalLevel.HIGH

    def test_dangerous_operation_requires_critical(self) -> None:
        artifact = build_artifact(operation=EngineeringOperation.DELETE)
        policy = DangerousOperationPolicy()
        finding = policy.evaluate(artifact, build_validation(), build_simulation())
        assert finding.requires_manual is True
        assert finding.required_level == ApprovalLevel.CRITICAL

    def test_ownership_policy_repository_scope(self) -> None:
        artifact = build_artifact(scope=EngineeringScope.REPOSITORY)
        policy = OwnershipPolicy()
        finding = policy.evaluate(artifact, build_validation(), build_simulation())
        assert finding.requires_manual is True
        assert finding.required_level == ApprovalLevel.HIGH


class TestPlannerApprovalEngine:
    def test_auto_approves_safe_plan(self, engine: ApprovalEngine) -> None:
        artifact = build_artifact(risk_level=RiskLevel.LOW, scope=EngineeringScope.FILE)
        result = engine.evaluate(artifact, build_validation(), build_simulation())
        assert result.approved is True
        assert result.decision.state == ApprovalState.AUTO_APPROVED

    def test_requires_manual_for_high_risk(self, engine: ApprovalEngine) -> None:
        artifact = build_artifact(risk_level=RiskLevel.HIGH, scope=EngineeringScope.FILE)
        result = engine.evaluate(artifact, build_validation(), build_simulation())
        assert result.approved is False
        assert result.decision.state == ApprovalState.PENDING
        assert result.required_level == ApprovalLevel.HIGH

    def test_rejects_invalid_plan(self, engine: ApprovalEngine) -> None:
        artifact = build_artifact(risk_level=RiskLevel.LOW)
        result = engine.evaluate(artifact, build_validation(valid=False), build_simulation())
        assert result.approved is False
        assert result.decision.state == ApprovalState.REJECTED
        assert result.decision.reason == ApprovalReason.VALIDATION_FAILURE

    def test_integration_pipeline(
        self,
        analyzer: GoalAnalyzer,
        pipeline: EngineeringIntelligencePipeline,
        validator: PlanValidator,
        engine: ApprovalEngine,
    ) -> None:
        # Full pipeline: Goal -> Plan -> Validate -> Simulate -> Approve
        goal = analyzer.analyze(PlanningGoal(goal_type=GoalType.ANALYSIS, title="Analyze Export"))
        artifact = pipeline.analyze(goal)

        validation = validator.validate(artifact)
        assert validation.valid is True

        # Use a mock simulation report for the test
        simulation = build_simulation(status=SimulationStatus.READY)

        approval = engine.evaluate(artifact, validation, simulation)
        assert approval.approved is True
