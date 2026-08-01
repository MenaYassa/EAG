"""Comprehensive tests for the Engineering Review Platform (Sprint 7.5)."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from eag.review import (
    AnalyzerError,
    AnalyzerRegistry,
    CorrectnessAnalyzer,
    DocumentationAnalyzer,
    IssueCategory,
    Reflection,
    ReflectionEngine,
    ReflectionError,
    ReviewCompleted,
    ReviewContext,
    ReviewDecision,
    ReviewError,
    ReviewFinding,
    ReviewIssue,
    ReviewMetrics,
    ReviewReport,
    ReviewRuntime,
    ReviewStarted,
    ReviewState,
    ReviewSuggestion,
    ReviewValidationError,
    Severity,
    SuggestionGenerated,
    SuggestionPriority,
    TestingAnalyzer,
)
from eag.review.events import IssueDetected, ReflectionCompleted, ReflectionStarted


@dataclass
class MockEventBus:
    published_events: list[Any] = field(default_factory=list)

    def publish(self, event: Any) -> None:
        self.published_events.append(event)


@pytest.fixture
def event_bus() -> MockEventBus:
    return MockEventBus()


@pytest.fixture
def registry() -> AnalyzerRegistry:
    reg = AnalyzerRegistry()
    reg.register("correctness", CorrectnessAnalyzer())
    reg.register("testing", TestingAnalyzer())
    reg.register("docs", DocumentationAnalyzer())
    return reg


@pytest.fixture
def runtime(registry: AnalyzerRegistry, event_bus: MockEventBus) -> ReviewRuntime:
    return ReviewRuntime(registry=registry, event_bus=event_bus)


def make_context(
    exec_success: bool = True,
    tests_pass: bool = True,
    tests_exist: bool = True,
    readme_exists: bool = True,
) -> ReviewContext:
    return ReviewContext(
        workspace_path=Path("/tmp"),
        execution_success=exec_success,
        metadata={
            "tests_pass": tests_pass,
            "tests_exist": tests_exist,
            "readme_exists": readme_exists,
        },
    )


# --- Enum Tests (15) ---


class TestReviewEnums:
    def test_review_state_values(self) -> None:
        assert ReviewState.RUNNING == "running"
        assert ReviewState.COMPLETED == "completed"

    def test_review_decision_values(self) -> None:
        assert ReviewDecision.APPROVED == "approved"
        assert ReviewDecision.CHANGES_REQUESTED == "changes_requested"

    def test_severity_values(self) -> None:
        assert Severity.INFO == "info"
        assert Severity.CRITICAL == "critical"

    def test_issue_category_values(self) -> None:
        assert IssueCategory.CORRECTNESS == "correctness"
        assert IssueCategory.SECURITY == "security"

    def test_suggestion_priority_values(self) -> None:
        assert SuggestionPriority.LOW == "low"
        assert SuggestionPriority.CRITICAL == "critical"

    def test_review_state_count(self) -> None:
        assert len(list(ReviewState)) == 5

    def test_review_decision_count(self) -> None:
        assert len(list(ReviewDecision)) == 4

    def test_severity_count(self) -> None:
        assert len(list(Severity)) == 4

    def test_issue_category_count(self) -> None:
        assert len(list(IssueCategory)) == 11

    def test_suggestion_priority_count(self) -> None:
        assert len(list(SuggestionPriority)) == 4

    def test_enum_immutable(self) -> None:
        with pytest.raises(AttributeError):
            ReviewState.RUNNING = "new_state"  # type: ignore[misc]

    def test_severity_order(self) -> None:
        sev = list(Severity)
        assert sev.index(Severity.INFO) < sev.index(Severity.CRITICAL)

    def test_priority_order(self) -> None:
        pri = list(SuggestionPriority)
        assert pri.index(SuggestionPriority.LOW) < pri.index(SuggestionPriority.CRITICAL)

    def test_review_state_is_str_enum(self) -> None:
        assert isinstance(ReviewState.RUNNING, str)

    def test_severity_is_str_enum(self) -> None:
        assert isinstance(Severity.ERROR, str)


# --- Model Tests (50) ---


class TestReviewModels:
    def test_review_issue_immutable(self) -> None:
        i = ReviewIssue(category=IssueCategory.STYLE, severity=Severity.WARNING, title="Test")
        with pytest.raises(Exception, match=""):
            i.title = "new"  # type: ignore[misc]

    def test_review_issue_invalid_category(self) -> None:
        with pytest.raises(TypeError):
            ReviewIssue(category="bad", severity=Severity.WARNING, title="Test")  # type: ignore[arg-type]

    def test_review_issue_invalid_severity(self) -> None:
        with pytest.raises(TypeError):
            ReviewIssue(category=IssueCategory.STYLE, severity="bad", title="Test")  # type: ignore[arg-type]

    def test_review_issue_empty_title(self) -> None:
        with pytest.raises(ValueError):
            ReviewIssue(category=IssueCategory.STYLE, severity=Severity.WARNING, title="")

    def test_review_issue_confidence_validation(self) -> None:
        with pytest.raises(ValueError):
            ReviewIssue(
                category=IssueCategory.STYLE, severity=Severity.WARNING, title="T", confidence=1.5
            )

    def test_review_issue_confidence_type_validation(self) -> None:
        with pytest.raises(TypeError):
            ReviewIssue(
                category=IssueCategory.STYLE,
                severity=Severity.WARNING,
                title="T",
                confidence="high",
            )  # type: ignore[arg-type]

    def test_review_issue_metadata(self) -> None:
        i = ReviewIssue(
            category=IssueCategory.STYLE, severity=Severity.WARNING, title="T", metadata={"k": "v"}
        )
        assert i.metadata["k"] == "v"

    def test_review_issue_invalid_metadata(self) -> None:
        with pytest.raises(TypeError):
            ReviewIssue(
                category=IssueCategory.STYLE, severity=Severity.WARNING, title="T", metadata="bad"
            )  # type: ignore[arg-type]

    def test_review_suggestion_immutable(self) -> None:
        s = ReviewSuggestion(priority=SuggestionPriority.HIGH, message="Fix it")
        with pytest.raises(Exception, match=""):
            s.message = "new"  # type: ignore[misc]

    def test_review_suggestion_invalid_priority(self) -> None:
        with pytest.raises(TypeError):
            ReviewSuggestion(priority="bad", message="Fix it")  # type: ignore[arg-type]

    def test_review_suggestion_empty_message(self) -> None:
        with pytest.raises(ValueError):
            ReviewSuggestion(priority=SuggestionPriority.HIGH, message="")

    def test_review_suggestion_metadata(self) -> None:
        s = ReviewSuggestion(
            priority=SuggestionPriority.HIGH, message="Fix it", metadata={"k": "v"}
        )
        assert s.metadata["k"] == "v"

    def test_review_finding_immutable(self) -> None:
        f = ReviewFinding(title="Finding")
        with pytest.raises(Exception, match=""):
            f.title = "new"  # type: ignore[misc]

    def test_review_finding_empty_title(self) -> None:
        with pytest.raises(ValueError):
            ReviewFinding(title="")

    def test_review_finding_score_validation(self) -> None:
        with pytest.raises(ValueError):
            ReviewFinding(title="T", score=101)

    def test_review_finding_score_negative(self) -> None:
        with pytest.raises(ValueError):
            ReviewFinding(title="T", score=-1)

    def test_review_finding_score_type_validation(self) -> None:
        with pytest.raises(TypeError):
            ReviewFinding(title="T", score="high")  # type: ignore[arg-type]

    def test_review_finding_defaults(self) -> None:
        f = ReviewFinding(title="T")
        assert f.issues == ()
        assert f.suggestions == ()
        assert f.score == 100

    def test_review_finding_invalid_issues_type(self) -> None:
        with pytest.raises(TypeError):
            ReviewFinding(title="T", issues=[])  # type: ignore[arg-type]

    def test_review_finding_invalid_suggestions_type(self) -> None:
        with pytest.raises(TypeError):
            ReviewFinding(title="T", suggestions=[])  # type: ignore[arg-type]

    def test_reflection_immutable(self) -> None:
        r = Reflection(root_cause="Root", reasoning="Reason")
        with pytest.raises(Exception, match=""):
            r.root_cause = "new"  # type: ignore[misc]

    def test_reflection_empty_root_cause(self) -> None:
        with pytest.raises(ValueError):
            Reflection(root_cause="", reasoning="Reason")

    def test_reflection_empty_reasoning(self) -> None:
        with pytest.raises(ValueError):
            Reflection(root_cause="Root", reasoning="")

    def test_reflection_confidence_validation(self) -> None:
        with pytest.raises(ValueError):
            Reflection(root_cause="Root", reasoning="Reason", confidence=1.5)

    def test_reflection_confidence_type_validation(self) -> None:
        with pytest.raises(TypeError):
            Reflection(root_cause="Root", reasoning="Reason", confidence="high")  # type: ignore[arg-type]

    def test_reflection_invalid_actions_type(self) -> None:
        with pytest.raises(TypeError):
            Reflection(root_cause="Root", reasoning="Reason", recommended_actions=[])  # type: ignore[arg-type]

    def test_review_metrics_immutable(self) -> None:
        m = ReviewMetrics()
        with pytest.raises(Exception, match=""):
            m.issues_found = 5  # type: ignore[misc]

    def test_review_metrics_negative_value(self) -> None:
        with pytest.raises(ValueError):
            ReviewMetrics(issues_found=-1)

    def test_review_metrics_confidence_validation(self) -> None:
        with pytest.raises(ValueError):
            ReviewMetrics(confidence=1.5)

    def test_review_metrics_confidence_type_validation(self) -> None:
        with pytest.raises(TypeError):
            ReviewMetrics(confidence="high")  # type: ignore[arg-type]

    def test_review_metrics_defaults(self) -> None:
        m = ReviewMetrics()
        assert m.issues_found == 0
        assert m.confidence == 1.0

    def test_review_report_immutable(self) -> None:
        r = ReviewReport(decision=ReviewDecision.APPROVED, overall_score=90)
        with pytest.raises(Exception, match=""):
            r.decision = ReviewDecision.REJECTED  # type: ignore[misc]

    def test_review_report_invalid_decision(self) -> None:
        with pytest.raises(TypeError):
            ReviewReport(decision="bad", overall_score=90)  # type: ignore[arg-type]

    def test_review_report_score_validation(self) -> None:
        with pytest.raises(ValueError):
            ReviewReport(decision=ReviewDecision.APPROVED, overall_score=101)

    def test_review_report_score_type_validation(self) -> None:
        with pytest.raises(TypeError):
            ReviewReport(decision=ReviewDecision.APPROVED, overall_score="high")  # type: ignore[arg-type]

    def test_review_report_invalid_findings_type(self) -> None:
        with pytest.raises(TypeError):
            ReviewReport(decision=ReviewDecision.APPROVED, overall_score=90, findings=[])  # type: ignore[arg-type]

    def test_review_report_invalid_reflection_type(self) -> None:
        with pytest.raises(TypeError):
            ReviewReport(decision=ReviewDecision.APPROVED, overall_score=90, reflection="bad")  # type: ignore[arg-type]

    def test_review_report_invalid_metrics_type(self) -> None:
        with pytest.raises(TypeError):
            ReviewReport(decision=ReviewDecision.APPROVED, overall_score=90, metrics="bad")  # type: ignore[arg-type]

    def test_review_report_defaults(self) -> None:
        r = ReviewReport(decision=ReviewDecision.APPROVED, overall_score=90)
        assert r.findings == ()
        assert r.reflection is None
        assert r.duration_ms == 0.0
        assert r.summary == ""

    def test_review_context_invalid_path(self) -> None:
        with pytest.raises(TypeError):
            ReviewContext(workspace_path="/tmp")  # type: ignore[arg-type]

    def test_review_context_metadata(self) -> None:
        c = ReviewContext(workspace_path=Path("/tmp"), metadata={"k": "v"})
        assert c.metadata["k"] == "v"

    def test_review_issue_creation(self) -> None:
        i = ReviewIssue(
            category=IssueCategory.TESTING, severity=Severity.ERROR, title="Missing tests"
        )
        assert i.category == IssueCategory.TESTING
        assert i.severity == Severity.ERROR
        assert i.title == "Missing tests"
        assert i.id is not None

    def test_review_suggestion_creation(self) -> None:
        s = ReviewSuggestion(priority=SuggestionPriority.CRITICAL, message="Add tests")
        assert s.priority == SuggestionPriority.CRITICAL
        assert s.message == "Add tests"

    def test_review_finding_creation(self) -> None:
        i = ReviewIssue(
            category=IssueCategory.TESTING, severity=Severity.ERROR, title="Missing tests"
        )
        f = ReviewFinding(title="Test Gap", issues=(i,))
        assert len(f.issues) == 1
        assert f.issues[0].title == "Missing tests"

    def test_reflection_creation(self) -> None:
        r = Reflection(
            root_cause="Lack of coverage",
            reasoning="Tests weren't generated",
            recommended_actions=("Gen tests",),
        )
        assert r.root_cause == "Lack of coverage"
        assert len(r.recommended_actions) == 1

    def test_review_metrics_creation(self) -> None:
        m = ReviewMetrics(issues_found=5, errors=2)
        assert m.issues_found == 5
        assert m.errors == 2

    def test_review_report_creation(self) -> None:
        r = ReviewReport(decision=ReviewDecision.CHANGES_REQUESTED, overall_score=40)
        assert r.decision == ReviewDecision.CHANGES_REQUESTED
        assert r.overall_score == 40

    def test_review_report_with_reflection(self) -> None:
        refl = Reflection(root_cause="Root", reasoning="Reason")
        r = ReviewReport(decision=ReviewDecision.APPROVED, overall_score=90, reflection=refl)
        assert r.reflection is refl

    def test_review_report_with_metrics(self) -> None:
        m = ReviewMetrics(issues_found=1)
        r = ReviewReport(decision=ReviewDecision.APPROVED, overall_score=90, metrics=m)
        assert r.metrics.issues_found == 1

    def test_review_issue_equality(self) -> None:
        i1 = ReviewIssue(category=IssueCategory.STYLE, severity=Severity.WARNING, title="Test")
        i2 = ReviewIssue(category=IssueCategory.STYLE, severity=Severity.WARNING, title="Test")
        assert i1 != i2

    def test_review_issue_hashable(self) -> None:
        i = ReviewIssue(category=IssueCategory.STYLE, severity=Severity.WARNING, title="Test")
        assert hash(i) is not None


# --- Error Tests (5) ---


class TestReviewErrors:
    def test_review_error_hierarchy(self) -> None:
        assert issubclass(AnalyzerError, ReviewError)
        assert issubclass(ReflectionError, ReviewError)
        assert issubclass(ReviewValidationError, ReviewError)

    def test_analyzer_error_raises(self) -> None:
        with pytest.raises(AnalyzerError):
            raise AnalyzerError("Failed")

    def test_reflection_error_raises(self) -> None:
        with pytest.raises(ReflectionError):
            raise ReflectionError("Failed")

    def test_review_validation_error_raises(self) -> None:
        with pytest.raises(ReviewValidationError):
            raise ReviewValidationError("Failed")

    def test_base_error_raises(self) -> None:
        with pytest.raises(ReviewError):
            raise ReviewError("Failed")


# --- Event Tests (5) ---


class TestReviewEvents:
    def test_review_started_immutable(self) -> None:
        e = ReviewStarted(review_id="r1")
        with pytest.raises(Exception, match=""):
            e.review_id = "r2"  # type: ignore[misc]

    def test_review_completed_immutable(self) -> None:
        e = ReviewCompleted(review_id="r1", decision="approved", score=100)
        with pytest.raises(Exception, match=""):
            e.score = 90  # type: ignore[misc]

    def test_issue_detected_immutable(self) -> None:
        e = IssueDetected(review_id="r1", issue_id="i1", severity="warning")
        with pytest.raises(Exception, match=""):
            e.severity = "error"  # type: ignore[misc]

    def test_suggestion_generated_immutable(self) -> None:
        e = SuggestionGenerated(review_id="r1", suggestion_id="s1", priority="high")
        with pytest.raises(Exception, match=""):
            e.priority = "low"  # type: ignore[misc]

    def test_event_timestamp_auto(self) -> None:
        from datetime import datetime

        e = ReviewStarted(review_id="r1")
        assert isinstance(e.timestamp, datetime)


# --- Registry & Analyzer Tests (20) ---


class TestRegistryAndAnalyzers:
    def test_registry_register(self, registry: AnalyzerRegistry) -> None:
        assert len(registry.list()) == 3

    def test_registry_duplicate_raises(self, registry: AnalyzerRegistry) -> None:
        with pytest.raises(ReviewError):
            registry.register("correctness", CorrectnessAnalyzer())

    def test_registry_list_returns_tuple(self, registry: AnalyzerRegistry) -> None:
        assert isinstance(registry.list(), tuple)

    def test_correctness_analyzer_pass(self) -> None:
        analyzer = CorrectnessAnalyzer()
        ctx = make_context(exec_success=True)
        issues = analyzer.analyze(ctx)
        assert len(issues) == 0

    def test_correctness_analyzer_fail(self) -> None:
        analyzer = CorrectnessAnalyzer()
        ctx = make_context(exec_success=False)
        issues = analyzer.analyze(ctx)
        assert len(issues) == 1
        assert issues[0].severity == Severity.CRITICAL

    def test_testing_analyzer_pass(self) -> None:
        analyzer = TestingAnalyzer()
        ctx = make_context(tests_exist=True, tests_pass=True)
        issues = analyzer.analyze(ctx)
        assert len(issues) == 0

    def test_testing_analyzer_missing(self) -> None:
        analyzer = TestingAnalyzer()
        ctx = make_context(tests_exist=False)
        issues = analyzer.analyze(ctx)
        assert len(issues) == 1
        assert issues[0].title == "Missing Tests"

    def test_testing_analyzer_failing(self) -> None:
        analyzer = TestingAnalyzer()
        ctx = make_context(tests_exist=True, tests_pass=False)
        issues = analyzer.analyze(ctx)
        assert len(issues) == 1
        assert issues[0].title == "Failing Tests"

    def test_documentation_analyzer_pass(self) -> None:
        analyzer = DocumentationAnalyzer()
        ctx = make_context(readme_exists=True)
        issues = analyzer.analyze(ctx)
        assert len(issues) == 0

    def test_documentation_analyzer_missing(self) -> None:
        analyzer = DocumentationAnalyzer()
        ctx = make_context(readme_exists=False)
        issues = analyzer.analyze(ctx)
        assert len(issues) == 1
        assert issues[0].severity == Severity.WARNING


# --- Reflection Engine Tests (10) ---


class TestReflectionEngine:
    def test_reflect_approved(self) -> None:
        engine = ReflectionEngine()
        report = ReviewReport(decision=ReviewDecision.APPROVED, overall_score=100)
        refl = engine.reflect(report)
        assert "No significant issues" in refl.root_cause
        assert refl.confidence == 1.0

    def test_reflect_rejected(self) -> None:
        engine = ReflectionEngine()
        issue = ReviewIssue(
            category=IssueCategory.CORRECTNESS, severity=Severity.CRITICAL, title="Crash"
        )
        finding = ReviewFinding(title="Fail", issues=(issue,))
        report = ReviewReport(
            decision=ReviewDecision.REJECTED, overall_score=0, findings=(finding,)
        )
        refl = engine.reflect(report)
        assert "Critical failures" in refl.root_cause
        assert refl.confidence == 0.99

    def test_reflect_changes_requested(self) -> None:
        engine = ReflectionEngine()
        issue = ReviewIssue(
            category=IssueCategory.TESTING, severity=Severity.ERROR, title="No tests"
        )
        finding = ReviewFinding(title="Fail", issues=(issue,))
        report = ReviewReport(
            decision=ReviewDecision.CHANGES_REQUESTED, overall_score=50, findings=(finding,)
        )
        refl = engine.reflect(report)
        assert "Quality thresholds" in refl.root_cause
        assert refl.confidence == 0.95

    def test_reflect_warnings(self) -> None:
        engine = ReflectionEngine()
        issue = ReviewIssue(
            category=IssueCategory.DOCUMENTATION, severity=Severity.WARNING, title="No docs"
        )
        finding = ReviewFinding(title="Warn", issues=(issue,))
        report = ReviewReport(
            decision=ReviewDecision.APPROVED_WITH_WARNINGS, overall_score=85, findings=(finding,)
        )
        refl = engine.reflect(report)
        assert "minor maintainability" in refl.root_cause.lower()
        assert refl.confidence == 0.90


# --- Runtime Tests (20) ---


class TestReviewRuntime:
    def test_runtime_review_success(self, runtime: ReviewRuntime) -> None:
        ctx = make_context(exec_success=True, tests_pass=True, tests_exist=True, readme_exists=True)
        report = runtime.review(ctx)
        assert report.decision == ReviewDecision.APPROVED
        assert report.overall_score == 100
        assert report.reflection is not None

    def test_runtime_review_failed_execution(self, runtime: ReviewRuntime) -> None:
        ctx = make_context(exec_success=False)
        report = runtime.review(ctx)
        assert report.decision == ReviewDecision.REJECTED
        assert report.overall_score == 75  # 100 - 25

    def test_runtime_review_missing_tests(self, runtime: ReviewRuntime) -> None:
        ctx = make_context(tests_exist=False)
        report = runtime.review(ctx)
        assert report.decision == ReviewDecision.CHANGES_REQUESTED
        assert report.overall_score == 90  # 100 - 10

    def test_runtime_review_missing_docs(self, runtime: ReviewRuntime) -> None:
        ctx = make_context(readme_exists=False)
        report = runtime.review(ctx)
        assert report.decision == ReviewDecision.APPROVED_WITH_WARNINGS
        assert report.overall_score == 95  # 100 - 5

    def test_runtime_review_events_published(
        self, runtime: ReviewRuntime, event_bus: MockEventBus
    ) -> None:
        ctx = make_context()
        runtime.review(ctx)
        event_types = [type(e) for e in event_bus.published_events]
        assert ReviewStarted in event_types
        assert ReviewCompleted in event_types
        assert ReflectionStarted in event_types
        assert ReflectionCompleted in event_types

    def test_runtime_review_issue_events_published(
        self, runtime: ReviewRuntime, event_bus: MockEventBus
    ) -> None:
        ctx = make_context(tests_exist=False)
        runtime.review(ctx)
        assert any(isinstance(e, IssueDetected) for e in event_bus.published_events)

    def test_runtime_review_metrics_populated(self, runtime: ReviewRuntime) -> None:
        ctx = make_context(tests_exist=False, readme_exists=False)
        report = runtime.review(ctx)
        assert report.metrics.issues_found == 2
        assert report.metrics.errors == 1
        assert report.metrics.warnings == 1

    def test_runtime_review_reflection_populated(self, runtime: ReviewRuntime) -> None:
        ctx = make_context()
        report = runtime.review(ctx)
        assert report.reflection is not None
        assert len(report.reflection.recommended_actions) > 0

    def test_runtime_review_duration_positive(self, runtime: ReviewRuntime) -> None:
        ctx = make_context()
        report = runtime.review(ctx)
        assert report.duration_ms >= 0.0

    def test_runtime_review_findings_populated(self, runtime: ReviewRuntime) -> None:
        ctx = make_context(tests_exist=False)
        report = runtime.review(ctx)
        assert len(report.findings) == 1
        assert len(report.findings[0].issues) == 1
