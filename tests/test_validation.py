"""Tests for the plan validation engine."""

import pytest

from eag.planner.enums import GoalType
from eag.planner.intelligence.goal_analyzer import GoalAnalyzer
from eag.planner.intelligence.pipeline import EngineeringIntelligencePipeline
from eag.planner.models import PlanningGoal
from eag.planner.validation.models import ValidationCategory, ValidationSeverity
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


class TestPlanValidator:
    def test_valid_plan_passes(
        self, analyzer: GoalAnalyzer, pipeline: EngineeringIntelligencePipeline, validator: PlanValidator
    ) -> None:
        goal = analyzer.analyze(PlanningGoal(goal_type=GoalType.REFACTOR, title="Rename X"))
        artifact = pipeline.analyze(goal)
        result = validator.validate(artifact)
        
        assert result.valid is True
        assert result.errors == 0
        assert result.critical == 0
        assert "passed" in result.summary

    def test_high_risk_requires_approval(
        self, analyzer: GoalAnalyzer, pipeline: EngineeringIntelligencePipeline, validator: PlanValidator
    ) -> None:
        goal = analyzer.analyze(PlanningGoal(goal_type=GoalType.REFACTOR, title="Rename X"))
        artifact = pipeline.analyze(goal)
        result = validator.validate(artifact)
        
        assert result.requires_approval is True
        assert any(i.category == ValidationCategory.RISK and i.severity == ValidationSeverity.WARNING for i in result.issues)

    def test_dangerous_operation_safety_warning(
        self, analyzer: GoalAnalyzer, pipeline: EngineeringIntelligencePipeline, validator: PlanValidator
    ) -> None:
        goal = analyzer.analyze(PlanningGoal(goal_type=GoalType.MAINTENANCE, title="Delete X"))
        artifact = pipeline.analyze(goal)
        result = validator.validate(artifact)
        
        assert any(i.category == ValidationCategory.SAFETY for i in result.issues)