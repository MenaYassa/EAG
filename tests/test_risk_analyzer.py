"""Tests for the engineering risk analyzer."""

import pytest

from eag.planner.enums import GoalType, RiskLevel
from eag.planner.intelligence.dependency_resolver import TaskDependencyResolver
from eag.planner.intelligence.goal_analyzer import GoalAnalyzer
from eag.planner.intelligence.models import (
    EngineeringRiskFactor,
)
from eag.planner.intelligence.risk_analyzer import RiskAnalyzer
from eag.planner.intelligence.task_decomposer import TaskDecomposer
from eag.planner.models import PlanningGoal


@pytest.fixture
def analyzer() -> GoalAnalyzer:
    return GoalAnalyzer()


@pytest.fixture
def decomposer() -> TaskDecomposer:
    return TaskDecomposer()


@pytest.fixture
def resolver() -> TaskDependencyResolver:
    return TaskDependencyResolver()


@pytest.fixture
def risk_analyzer() -> RiskAnalyzer:
    return RiskAnalyzer()


class TestRiskAnalyzerDimensions:
    def test_repository_refactor_is_high_risk(
        self, analyzer, decomposer, resolver, risk_analyzer
    ) -> None:
        goal = analyzer.analyze(PlanningGoal(goal_type=GoalType.REFACTOR, title="Rename X"))
        graph = resolver.build(decomposer.decompose(goal))
        assessment = risk_analyzer.analyze(goal, graph)

        assert assessment.scope_risk == RiskLevel.HIGH
        assert assessment.change_risk == RiskLevel.MEDIUM
        assert assessment.overall_risk == RiskLevel.HIGH

    def test_file_analysis_is_none_risk(
        self, analyzer, decomposer, resolver, risk_analyzer
    ) -> None:
        goal = analyzer.analyze(PlanningGoal(goal_type=GoalType.ANALYSIS, title="Analyze X"))
        graph = resolver.build(decomposer.decompose(goal))
        assessment = risk_analyzer.analyze(goal, graph)

        assert assessment.scope_risk == RiskLevel.LOW
        assert assessment.change_risk == RiskLevel.NONE
        assert assessment.overall_risk == RiskLevel.LOW


class TestRiskAnalyzerApproval:
    def test_high_risk_requires_approval(
        self, analyzer, decomposer, resolver, risk_analyzer
    ) -> None:
        goal = analyzer.analyze(PlanningGoal(goal_type=GoalType.REFACTOR, title="Rename X"))
        graph = resolver.build(decomposer.decompose(goal))
        assessment = risk_analyzer.analyze(goal, graph)

        assert assessment.requires_approval is True

    def test_low_risk_no_approval(self, analyzer, decomposer, resolver, risk_analyzer) -> None:
        goal = analyzer.analyze(PlanningGoal(goal_type=GoalType.ANALYSIS, title="Analyze X"))
        graph = resolver.build(decomposer.decompose(goal))
        assessment = risk_analyzer.analyze(goal, graph)

        assert assessment.requires_approval is False


class TestRiskAnalyzerExplainability:
    def test_summary_contains_task_count(
        self, analyzer, decomposer, resolver, risk_analyzer
    ) -> None:
        goal = analyzer.analyze(PlanningGoal(goal_type=GoalType.REFACTOR, title="Rename X"))
        graph = resolver.build(decomposer.decompose(goal))
        assessment = risk_analyzer.analyze(goal, graph)

        assert "5 engineering tasks" in assessment.summary

    def test_summary_contains_approval_warning(
        self, analyzer, decomposer, resolver, risk_analyzer
    ) -> None:
        goal = analyzer.analyze(PlanningGoal(goal_type=GoalType.REFACTOR, title="Rename X"))
        graph = resolver.build(decomposer.decompose(goal))
        assessment = risk_analyzer.analyze(goal, graph)

        assert "Manual approval required" in assessment.summary

    def test_factors_are_populated(self, analyzer, decomposer, resolver, risk_analyzer) -> None:
        goal = analyzer.analyze(PlanningGoal(goal_type=GoalType.REFACTOR, title="Rename X"))
        graph = resolver.build(decomposer.decompose(goal))
        assessment = risk_analyzer.analyze(goal, graph)

        assert EngineeringRiskFactor.LARGE_SCOPE in assessment.factors
        assert EngineeringRiskFactor.REFACTOR in assessment.factors

    def test_determinism(self, analyzer, decomposer, resolver, risk_analyzer) -> None:
        goal = analyzer.analyze(PlanningGoal(goal_type=GoalType.REFACTOR, title="Rename X"))
        graph = resolver.build(decomposer.decompose(goal))
        assessment1 = risk_analyzer.analyze(goal, graph)
        assessment2 = risk_analyzer.analyze(goal, graph)

        assert assessment1 == assessment2
