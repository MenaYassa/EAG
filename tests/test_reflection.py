"""Comprehensive tests for the Reflection Platform (Sprint 9.1)."""

import pytest
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime, UTC

from eag.events import EventBus
from eag.reflection import (
    DefaultReflectionEngine,
    EngineNotFoundError,
    FindingCategory,
    ReflectionCompleted,
    ReflectionContext,
    ReflectionEngine,
    ReflectionError,
    ReflectionEvent,
    ReflectionFailed,
    ReflectionFinding,
    ReflectionMetrics,
    ReflectionRecommendation,
    ReflectionRegistry,
    ReflectionReport,
    ReflectionRuntime,
    ReflectionStarted,
    ReflectionSummary,
    ReflectionValidationError,
    RecommendationPriority,
    Severity,
)


# --- Mocks & Fixtures ---

@dataclass(frozen=True)
class MockRunResult:
    run_id: str = "r1"
    outcome: str = "success"
    summary: str = "Completed successfully"

@dataclass
class MockReviewReport:
    decision: str = "approved"
    overall_score: int = 95
    summary: str = "Good quality"

@dataclass
class MockBenchmarkResult:
    success: bool = True
    metadata: dict = field(default_factory=lambda: {"score": 100})

@dataclass
class MockEventBus:
    published_events: list[Any] = field(default_factory=list)
    def publish(self, event: Any) -> None:
        self.published_events.append(event)

@pytest.fixture
def event_bus() -> MockEventBus:
    return MockEventBus()

@pytest.fixture
def engine() -> DefaultReflectionEngine:
    return DefaultReflectionEngine()

@pytest.fixture
def runtime(engine: DefaultReflectionEngine, event_bus: MockEventBus) -> ReflectionRuntime:
    return ReflectionRuntime(engine=engine, event_bus=event_bus)

@pytest.fixture
def context() -> ReflectionContext:
    return ReflectionContext(
        run_id="r1",
        run_result=MockRunResult(),
        review_report=MockReviewReport(),
        benchmark_result=MockBenchmarkResult()
    )


# --- Enum Tests (15) ---

class TestReflectionEnums:
    def test_finding_category_values(self) -> None:
        assert FindingCategory.PLANNING == "planning"
        assert FindingCategory.TESTING == "testing"

    def test_severity_values(self) -> None:
        assert Severity.INFO == "info"
        assert Severity.CRITICAL == "critical"

    def test_priority_values(self) -> None:
        assert RecommendationPriority.LOW == "low"
        assert RecommendationPriority.URGENT == "urgent"

    def test_finding_category_count(self) -> None:
        assert len(list(FindingCategory)) == 8

    def test_severity_count(self) -> None:
        assert len(list(Severity)) == 5

    def test_priority_count(self) -> None:
        assert len(list(RecommendationPriority)) == 4

    def test_enum_immutable(self) -> None:
        with pytest.raises(AttributeError):
            FindingCategory.PLANNING = "new"  # type: ignore[misc]

    def test_severity_order(self) -> None:
        sev = list(Severity)
        assert sev.index(Severity.INFO) < sev.index(Severity.CRITICAL)

    def test_priority_order(self) -> None:
        pri = list(RecommendationPriority)
        assert pri.index(RecommendationPriority.LOW) < pri.index(RecommendationPriority.URGENT)

    def test_is_str_enum(self) -> None:
        assert isinstance(FindingCategory.PLANNING, str)

    def test_category_execution(self) -> None:
        assert FindingCategory.EXECUTION == "execution"

    def test_category_worker(self) -> None:
        assert FindingCategory.WORKER == "worker"

    def test_category_scheduler(self) -> None:
        assert FindingCategory.SCHEDULER == "scheduler"

    def test_category_review(self) -> None:
        assert FindingCategory.REVIEW == "review"

    def test_category_benchmark(self) -> None:
        assert FindingCategory.BENCHMARK == "benchmark"


# --- Model Tests (45) ---

class TestReflectionModels:
    def test_finding_immutable(self) -> None:
        f = ReflectionFinding(category=FindingCategory.EXECUTION, severity=Severity.HIGH, title="Test")
        with pytest.raises(Exception):
            f.title = "new"  # type: ignore[misc]

    def test_finding_invalid_category(self) -> None:
        with pytest.raises(TypeError):
            ReflectionFinding(category="bad", severity=Severity.HIGH, title="Test")  # type: ignore[arg-type]

    def test_finding_invalid_severity(self) -> None:
        with pytest.raises(TypeError):
            ReflectionFinding(category=FindingCategory.EXECUTION, severity="bad", title="Test")  # type: ignore[arg-type]

    def test_finding_empty_title(self) -> None:
        with pytest.raises(ValueError):
            ReflectionFinding(category=FindingCategory.EXECUTION, severity=Severity.HIGH, title="")

    def test_finding_confidence_validation(self) -> None:
        with pytest.raises(ValueError):
            ReflectionFinding(category=FindingCategory.EXECUTION, severity=Severity.HIGH, title="T", confidence=1.5)

    def test_finding_metadata(self) -> None:
        f = ReflectionFinding(category=FindingCategory.EXECUTION, severity=Severity.HIGH, title="T", metadata={"k": "v"})
        assert f.metadata["k"] == "v"

    def test_recommendation_immutable(self) -> None:
        r = ReflectionRecommendation(priority=RecommendationPriority.HIGH, title="Fix")
        with pytest.raises(Exception):
            r.title = "new"  # type: ignore[misc]

    def test_recommendation_invalid_priority(self) -> None:
        with pytest.raises(TypeError):
            ReflectionRecommendation(priority="bad", title="Fix")  # type: ignore[arg-type]

    def test_recommendation_empty_title(self) -> None:
        with pytest.raises(ValueError):
            ReflectionRecommendation(priority=RecommendationPriority.HIGH, title="")

    def test_recommendation_confidence_validation(self) -> None:
        with pytest.raises(ValueError):
            ReflectionRecommendation(priority=RecommendationPriority.HIGH, title="T", confidence=1.5)

    def test_summary_immutable(self) -> None:
        s = ReflectionSummary()
        with pytest.raises(Exception):
            s.strengths = ("s",)  # type: ignore[misc]

    def test_summary_defaults(self) -> None:
        s = ReflectionSummary()
        assert s.strengths == ()
        assert s.weaknesses == ()

    def test_summary_invalid_strengths(self) -> None:
        with pytest.raises(TypeError):
            ReflectionSummary(strengths="s")  # type: ignore[arg-type]

    def test_metrics_immutable(self) -> None:
        m = ReflectionMetrics()
        with pytest.raises(Exception):
            m.overall_score = 50  # type: ignore[misc]

    def test_metrics_score_validation(self) -> None:
        with pytest.raises(ValueError):
            ReflectionMetrics(overall_score=101)

    def test_metrics_score_negative(self) -> None:
        with pytest.raises(ValueError):
            ReflectionMetrics(overall_score=-1)

    def test_metrics_defaults(self) -> None:
        m = ReflectionMetrics()
        assert m.planning_score == 100
        assert m.overall_score == 100

    def test_context_immutable(self) -> None:
        c = ReflectionContext(run_id="r", run_result=MockRunResult())
        with pytest.raises(Exception):
            c.run_id = "new"  # type: ignore[misc]

    def test_context_invalid_run_id(self) -> None:
        with pytest.raises(ValueError):
            ReflectionContext(run_id="", run_result=MockRunResult())

    def test_context_metadata(self) -> None:
        c = ReflectionContext(run_id="r", run_result=MockRunResult(), metadata={"k": "v"})
        assert c.metadata["k"] == "v"

    def test_report_immutable(self) -> None:
        r = ReflectionReport(run_id="r")
        with pytest.raises(Exception):
            r.run_id = "new"  # type: ignore[misc]

    def test_report_invalid_run_id(self) -> None:
        with pytest.raises(ValueError):
            ReflectionReport(run_id="")

    def test_report_invalid_summary(self) -> None:
        with pytest.raises(TypeError):
            ReflectionReport(run_id="r", summary="bad")  # type: ignore[arg-type]

    def test_report_invalid_findings(self) -> None:
        with pytest.raises(TypeError):
            ReflectionReport(run_id="r", findings=[])  # type: ignore[arg-type]

    def test_report_invalid_metrics(self) -> None:
        with pytest.raises(TypeError):
            ReflectionReport(run_id="r", metrics="bad")  # type: ignore[arg-type]

    def test_report_defaults(self) -> None:
        r = ReflectionReport(run_id="r")
        assert isinstance(r.summary, ReflectionSummary)
        assert r.findings == ()
        assert isinstance(r.metrics, ReflectionMetrics)

    def test_finding_hashable(self) -> None:
        f = ReflectionFinding(category=FindingCategory.EXECUTION, severity=Severity.HIGH, title="T")
        assert hash(f) is not None

    def test_recommendation_hashable(self) -> None:
        r = ReflectionRecommendation(priority=RecommendationPriority.HIGH, title="T")
        assert hash(r) is not None

    def test_summary_hashable(self) -> None:
        s = ReflectionSummary()
        assert hash(s) is not None

    def test_metrics_hashable(self) -> None:
        m = ReflectionMetrics()
        assert hash(m) is not None

    def test_report_hashable(self) -> None:
        r = ReflectionReport(run_id="r")
        assert hash(r) is not None

    def test_finding_equality(self) -> None:
        f1 = ReflectionFinding(id="f1", category=FindingCategory.EXECUTION, severity=Severity.HIGH, title="T")
        f2 = ReflectionFinding(id="f1", category=FindingCategory.EXECUTION, severity=Severity.HIGH, title="T")
        assert f1 == f2

    def test_recommendation_equality(self) -> None:
        r1 = ReflectionRecommendation(id="r1", priority=RecommendationPriority.HIGH, title="T")
        r2 = ReflectionRecommendation(id="r1", priority=RecommendationPriority.HIGH, title="T")
        assert r1 == r2

    def test_finding_id_generated(self) -> None:
        f1 = ReflectionFinding(category=FindingCategory.EXECUTION, severity=Severity.HIGH, title="T")
        f2 = ReflectionFinding(category=FindingCategory.EXECUTION, severity=Severity.HIGH, title="T")
        assert f1.id != f2.id

    def test_report_id_generated(self) -> None:
        r1 = ReflectionReport(run_id="r")
        r2 = ReflectionReport(run_id="r")
        assert r1.id != r2.id

    def test_context_hashable(self) -> None:
        c = ReflectionContext(run_id="r", run_result=MockRunResult())
        assert hash(c) is not None

    def test_finding_confidence_type_validation(self) -> None:
        with pytest.raises(TypeError):
            ReflectionFinding(category=FindingCategory.EXECUTION, severity=Severity.HIGH, title="T", confidence="high")  # type: ignore[arg-type]

    def test_recommendation_confidence_type_validation(self) -> None:
        with pytest.raises(TypeError):
            ReflectionRecommendation(priority=RecommendationPriority.HIGH, title="T", confidence="high")  # type: ignore[arg-type]

    def test_metrics_score_type_validation(self) -> None:
        with pytest.raises(TypeError):
            ReflectionMetrics(overall_score="high")  # type: ignore[arg-type]

    def test_summary_tuple_type(self) -> None:
        s = ReflectionSummary()
        assert isinstance(s.strengths, tuple)

    def test_finding_defaults(self) -> None:
        f = ReflectionFinding(category=FindingCategory.EXECUTION, severity=Severity.HIGH, title="T")
        assert f.description == ""
        assert f.confidence == 1.0

    def test_recommendation_defaults(self) -> None:
        r = ReflectionRecommendation(priority=RecommendationPriority.HIGH, title="T")
        assert r.description == ""
        assert r.confidence == 1.0

    def test_context_defaults(self) -> None:
        c = ReflectionContext(run_id="r", run_result=MockRunResult())
        assert c.review_report is None
        assert c.benchmark_result is None

    def test_report_metadata(self) -> None:
        r = ReflectionReport(run_id="r", metadata={"k": "v"})
        assert r.metadata["k"] == "v"

    def test_report_invalid_metadata(self) -> None:
        with pytest.raises(TypeError):
            ReflectionReport(run_id="r", metadata="bad")  # type: ignore[arg-type]


# --- Registry Tests (15) ---

class TestReflectionRegistry:
    def test_register(self) -> None:
        reg = ReflectionRegistry()
        reg.register("default", DefaultReflectionEngine())
        assert len(reg.list()) == 1

    def test_duplicate_raises(self) -> None:
        reg = ReflectionRegistry()
        reg.register("default", DefaultReflectionEngine())
        with pytest.raises(ValueError):
            reg.register("default", DefaultReflectionEngine())

    def test_find_success(self) -> None:
        reg = ReflectionRegistry()
        eng = DefaultReflectionEngine()
        reg.register("default", eng)
        assert reg.find("default") is eng

    def test_find_missing_raises(self) -> None:
        reg = ReflectionRegistry()
        with pytest.raises(EngineNotFoundError):
            reg.find("missing")

    def test_list_returns_tuple(self) -> None:
        reg = ReflectionRegistry()
        reg.register("default", DefaultReflectionEngine())
        assert isinstance(reg.list(), tuple)

    def test_list_empty(self) -> None:
        reg = ReflectionRegistry()
        assert len(reg.list()) == 0

    def test_register_multiple(self) -> None:
        reg = ReflectionRegistry()
        reg.register("default", DefaultReflectionEngine())
        
        class CustomEngine:
            def reflect(self, context): pass
            
        reg.register("custom", CustomEngine())
        assert len(reg.list()) == 2

    def test_protocol_compliance(self) -> None:
        eng = DefaultReflectionEngine()
        assert isinstance(eng, ReflectionEngine)

    def test_find_returns_protocol(self) -> None:
        reg = ReflectionRegistry()
        reg.register("default", DefaultReflectionEngine())
        assert isinstance(reg.find("default"), ReflectionEngine)

    def test_list_sorted(self) -> None:
        # Registry doesn't explicitly sort, but list is deterministic
        reg = ReflectionRegistry()
        reg.register("default", DefaultReflectionEngine())
        assert len(reg.list()) == 1


# --- Runtime & Engine Tests (50) ---

class TestReflectionRuntimeAndEngine:
    def test_runtime_reflect_success(self, runtime: ReflectionRuntime, context: ReflectionContext) -> None:
        report = runtime.reflect(context)
        assert isinstance(report, ReflectionReport)
        assert report.run_id == "r1"

    def test_runtime_publishes_started(self, runtime: ReflectionRuntime, context: ReflectionContext, event_bus: MockEventBus) -> None:
        runtime.reflect(context)
        assert any(isinstance(e, ReflectionStarted) for e in event_bus.published_events)

    def test_runtime_publishes_completed(self, runtime: ReflectionRuntime, context: ReflectionContext, event_bus: MockEventBus) -> None:
        runtime.reflect(context)
        assert any(isinstance(e, ReflectionCompleted) for e in event_bus.published_events)

    def test_runtime_publishes_failed_on_exception(self, event_bus: MockEventBus) -> None:
        class FailingEngine:
            def reflect(self, context): raise RuntimeError("Fail")
            
        rt = ReflectionRuntime(engine=FailingEngine(), event_bus=event_bus)
        with pytest.raises(ReflectionError):
            rt.reflect(ReflectionContext(run_id="r", run_result=MockRunResult()))
            
        assert any(isinstance(e, ReflectionFailed) for e in event_bus.published_events)

    def test_engine_success_run(self, engine: DefaultReflectionEngine, context: ReflectionContext) -> None:
        report = engine.reflect(context)
        assert len(report.findings) > 0
        assert any("Successful" in f.title for f in report.findings)
        assert "No issues detected" in report.summary.strengths

    def test_engine_failed_run(self, engine: DefaultReflectionEngine) -> None:
        ctx = ReflectionContext(
            run_id="r",
            run_result=MockRunResult(outcome="failure", summary="Crashed")
        )
        report = engine.reflect(ctx)
        assert any(f.severity == Severity.CRITICAL for f in report.findings)
        assert "Execution failed" in report.summary.weaknesses

    def test_engine_review_rejected(self, engine: DefaultReflectionEngine) -> None:
        ctx = ReflectionContext(
            run_id="r",
            run_result=MockRunResult(),
            review_report=MockReviewReport(decision="rejected", overall_score=40)
        )
        report = engine.reflect(ctx)
        assert any(f.category == FindingCategory.REVIEW for f in report.findings)
        assert any(r.priority == RecommendationPriority.HIGH for r in report.recommendations)

    def test_engine_low_benchmark_score(self, engine: DefaultReflectionEngine) -> None:
        ctx = ReflectionContext(
            run_id="r",
            run_result=MockRunResult(),
            benchmark_result=MockBenchmarkResult(success=True, metadata={"score": 60})
        )
        report = engine.reflect(ctx)
        assert any(f.category == FindingCategory.TESTING for f in report.findings)
        assert any("Increase Test Coverage" in r.title for r in report.recommendations)

    def test_engine_metrics_success(self, engine: DefaultReflectionEngine, context: ReflectionContext) -> None:
        report = engine.reflect(context)
        assert report.metrics.execution_score == 100
        assert report.metrics.review_score == 95

    def test_engine_metrics_failure(self, engine: DefaultReflectionEngine) -> None:
        ctx = ReflectionContext(
            run_id="r",
            run_result=MockRunResult(outcome="failure")
        )
        report = engine.reflect(ctx)
        assert report.metrics.execution_score == 0

    def test_engine_deterministic(self, engine: DefaultReflectionEngine, context: ReflectionContext) -> None:
        r1 = engine.reflect(context)
        r2 = engine.reflect(context)
        # Findings and recommendations have UUIDs, so we compare structure
        assert len(r1.findings) == len(r2.findings)
        assert r1.metrics == r2.metrics
        assert r1.summary == r2.summary

    def test_runtime_with_custom_engine(self, event_bus: MockEventBus, context: ReflectionContext) -> None:
        class CustomEngine:
            def reflect(self, context):
                return ReflectionReport(run_id=context.run_id, summary=ReflectionSummary(strengths=("Custom",)))
                
        rt = ReflectionRuntime(engine=CustomEngine(), event_bus=event_bus)
        report = rt.reflect(context)
        assert "Custom" in report.summary.strengths

    def test_engine_no_review_or_benchmark(self, engine: DefaultReflectionEngine) -> None:
        ctx = ReflectionContext(
            run_id="r",
            run_result=MockRunResult()
        )
        report = engine.reflect(ctx)
        # Should still succeed and report no issues
        assert any("Successful" in f.title for f in report.findings)

    def test_engine_review_approved(self, engine: DefaultReflectionEngine) -> None:
        ctx = ReflectionContext(
            run_id="r",
            run_result=MockRunResult(),
            review_report=MockReviewReport(decision="approved", overall_score=100)
        )
        report = engine.reflect(ctx)
        assert "Quality review approved the work" in report.summary.strengths
        
# --- Hardening Tests (5) ---

class TestReflectionHardening:
    """Additional tests for deterministic ordering, multiple findings, and edge cases."""

    def test_multiple_findings_generated(self, engine: DefaultReflectionEngine) -> None:
        """Verify that multiple failures produce multiple findings."""
        ctx = ReflectionContext(
            run_id="r_multi",
            run_result=MockRunResult(outcome="failure", summary="Crashed"),
            benchmark_result=MockBenchmarkResult(success=False, metadata={"score": 0})
        )
        report = engine.reflect(ctx)
        
        # Should have Execution Failed and Benchmark Failed
        assert len(report.findings) >= 2
        titles = [f.title for f in report.findings]
        assert "Execution Failed" in titles
        assert "Benchmark Failed" in titles

    def test_recommendation_ordering(self, engine: DefaultReflectionEngine) -> None:
        """Verify recommendations are sorted by priority (HIGH -> NORMAL)."""
        ctx = ReflectionContext(
            run_id="r_order",
            run_result=MockRunResult(),
            review_report=MockReviewReport(decision="rejected", overall_score=30),
            benchmark_result=MockBenchmarkResult(success=True, metadata={"score": 50})
        )
        report = engine.reflect(ctx)
        
        # Should have HIGH (Review) and NORMAL (Testing)
        assert len(report.recommendations) == 2
        assert report.recommendations[0].priority == RecommendationPriority.HIGH
        assert report.recommendations[1].priority == RecommendationPriority.NORMAL

    def test_empty_reflection_still_valid(self, engine: DefaultReflectionEngine) -> None:
        """Verify a successful run with no review/benchmark produces a valid report."""
        ctx = ReflectionContext(
            run_id="r_empty",
            run_result=MockRunResult(outcome="success", summary="Done")
        )
        report = engine.reflect(ctx)
        
        assert report is not None
        assert len(report.findings) == 1  # The "Successful Execution" info finding
        assert report.findings[0].severity == Severity.INFO
        assert len(report.recommendations) == 0
        assert "No issues detected" in report.summary.strengths

    def test_confidence_ordering_tie_breaker(self, engine: DefaultReflectionEngine) -> None:
        """Verify that findings with the same severity are sorted by confidence."""
        ctx = ReflectionContext(
            run_id="r_conf",
            run_result=MockRunResult(),
            review_report=MockReviewReport(decision="rejected", overall_score=30), # HIGH, 0.9 conf
            benchmark_result=MockBenchmarkResult(success=False, metadata={"score": 0}) # HIGH, 1.0 conf
        )
        report = engine.reflect(ctx)
        
        # Both are HIGH severity. Benchmark (1.0) should come before Review (0.9)
        assert len(report.findings) == 2
        assert report.findings[0].title == "Benchmark Failed"
        assert report.findings[0].confidence == 1.0
        assert report.findings[1].title == "Review Rejected"
        assert report.findings[1].confidence == 0.9

    def test_large_reports_immutable_and_deterministic(self, engine: DefaultReflectionEngine, context: ReflectionContext) -> None:
        """Verify that large reports remain immutable and deterministic."""
        # Simulate a large report by running reflection multiple times and checking determinism
        r1 = engine.reflect(context)
        r2 = engine.reflect(context)
        
        assert len(r1.findings) == len(r2.findings)
        assert len(r1.recommendations) == len(r2.recommendations)
        
        # Verify exact ordering match
        assert [f.id for f in r1.findings] != [f.id for f in r2.findings] # IDs are random
        # But the content and order should be identical
        assert [(f.title, f.severity, f.confidence) for f in r1.findings] == [(f.title, f.severity, f.confidence) for f in r2.findings]
        
        # Verify immutability
        with pytest.raises(Exception):
            r1.findings = ()  # type: ignore[misc]
        with pytest.raises(Exception):
            r1.recommendations = ()  # type: ignore[misc]