"""Tests for the engineering effort estimator."""

import pytest

from eag.planner.enums import GoalType
from eag.planner.intelligence.dependency_resolver import TaskDependencyResolver
from eag.planner.intelligence.effort_estimator import EffortEstimator
from eag.planner.intelligence.goal_analyzer import GoalAnalyzer
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


@pytest.fixture
def estimator() -> EffortEstimator:
    return EffortEstimator()


class TestEffortEstimatorBasics:
    def test_estimate_returns_profile_and_tasks(
        self, analyzer, decomposer, resolver, risk_analyzer, estimator
    ) -> None:
        goal = analyzer.analyze(PlanningGoal(goal_type=GoalType.REFACTOR, title="Rename X"))
        graph = resolver.build(decomposer.decompose(goal))
        risk = risk_analyzer.analyze(goal, graph)

        tasks, profile = estimator.estimate(goal, graph, risk)

        assert len(tasks) == 5
        assert profile.total_engineering_time > 0
        assert profile.critical_path_duration > 0
        assert profile.confidence == 0.95  # Repository scope

    def test_tasks_are_enriched_with_durations(
        self, analyzer, decomposer, resolver, risk_analyzer, estimator
    ) -> None:
        goal = analyzer.analyze(PlanningGoal(goal_type=GoalType.REFACTOR, title="Rename X"))
        graph = resolver.build(decomposer.decompose(goal))
        risk = risk_analyzer.analyze(goal, graph)

        tasks, _ = estimator.estimate(goal, graph, risk)

        assert all(t.estimated_duration > 0 for t in tasks)
        # Change "Validate" to "Validation" to match the actual task title
        assert any(t.estimated_validation > 0 for t in tasks if "Validation" in t.title)


class TestEffortEstimatorMathematics:
    def test_critical_path_calculation(
        self, analyzer, decomposer, resolver, risk_analyzer, estimator
    ) -> None:
        goal = analyzer.analyze(PlanningGoal(goal_type=GoalType.REFACTOR, title="Rename X"))
        graph = resolver.build(decomposer.decompose(goal))
        risk = risk_analyzer.analyze(goal, graph)

        tasks, profile = estimator.estimate(goal, graph, risk)

        # For a simple chain A->B->C->D->E, critical path == total time
        assert profile.critical_path_duration == pytest.approx(profile.total_engineering_time)
        assert profile.parallel_savings == 0.0

    def test_parallel_savings_calculation(
        self, analyzer, decomposer, resolver, risk_analyzer, estimator
    ) -> None:
        from eag.planner.models import EngineeringTask

        # Custom graph with parallel branches
        tasks = (
            EngineeringTask(id="A", title="Analyze"),
            EngineeringTask(id="B", title="Implement", dependencies=("A",)),
            EngineeringTask(id="C", title="Document", dependencies=("A",)),  # Parallel to B
            EngineeringTask(id="D", title="Validate", dependencies=("B", "C")),
        )
        goal = analyzer.analyze(PlanningGoal(goal_type=GoalType.FEATURE, title="Add X"))
        graph = resolver.build(tasks)
        risk = risk_analyzer.analyze(goal, graph)

        _, profile = estimator.estimate(goal, graph, risk)

        # Total = A + B + C + D
        # Critical = A + max(B, C) + D
        # Savings = min(B, C)
        assert profile.parallel_savings > 0
        assert profile.critical_path_duration < profile.total_engineering_time


class TestEffortEstimatorDeterminism:
    def test_repeated_estimates_are_identical(
        self, analyzer, decomposer, resolver, risk_analyzer, estimator
    ) -> None:
        goal = analyzer.analyze(PlanningGoal(goal_type=GoalType.REFACTOR, title="Rename X"))
        graph = resolver.build(decomposer.decompose(goal))
        risk = risk_analyzer.analyze(goal, graph)

        tasks1, profile1 = estimator.estimate(goal, graph, risk)
        tasks2, profile2 = estimator.estimate(goal, graph, risk)

        assert tasks1 == tasks2
        assert profile1 == profile2
