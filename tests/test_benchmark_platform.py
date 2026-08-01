"""Comprehensive tests for the Benchmark Platform (EBS-0)."""

import pytest
from pathlib import Path
from typing import Any

from eag.benchmark import (
    Benchmark,
    BenchmarkCategory,
    BenchmarkDifficulty,
    BenchmarkError,
    BenchmarkEvaluator,
    BenchmarkExecutor,
    BenchmarkOutcome,
    BenchmarkRegistry,
    BenchmarkReport,
    BenchmarkResult,
    BenchmarkRun,
    BenchmarkRunner,
    BenchmarkScore,
    BenchmarkState,
    CapabilityProfile,
    DefaultEvaluator,
    DefaultReporter,
    EvaluationError,
    FixtureError,
    FixtureManager,
    RegistryError,
    RunnerError,
    ScoreLevel,
)


# --- Mock Executor ---

class MockExecutor:
    def __init__(self, success: bool = True, metadata: dict | None = None) -> None:
        self._success = success
        self._metadata = metadata or {}

    def execute(self, benchmark: Benchmark, workspace: Path) -> BenchmarkResult:
        return BenchmarkResult(
            run_id="mock_run",
            benchmark_id=benchmark.id,
            success=self._success,
            metadata=self._metadata
        )

class FailingExecutor:
    def execute(self, benchmark: Benchmark, workspace: Path) -> BenchmarkResult:
        raise RuntimeError("Execution failed")


@pytest.fixture
def registry() -> BenchmarkRegistry:
    reg = BenchmarkRegistry()
    reg.register(Benchmark(id="B001", name="Calculator"))
    reg.register(Benchmark(id="B002", name="Notes", category=BenchmarkCategory.FEATURE_ENGINEERING))
    return reg

@pytest.fixture
def runner() -> BenchmarkRunner:
    return BenchmarkRunner(executor=MockExecutor(success=True, metadata={"tests_pass": True, "readme_exists": True, "valid_structure": True}))

@pytest.fixture
def failing_runner() -> BenchmarkRunner:
    return BenchmarkRunner(executor=FailingExecutor())

def make_benchmark(bid: str = "B001") -> Benchmark:
    return Benchmark(id=bid, name=f"Benchmark {bid}")


# --- Model Tests (20) ---

class TestBenchmarkModels:
    def test_benchmark_immutable(self) -> None:
        b = make_benchmark()
        with pytest.raises(Exception):
            b.id = "new"  # type: ignore[misc]

    def test_benchmark_invalid_id(self) -> None:
        with pytest.raises(ValueError):
            Benchmark(id="", name="Test")

    def test_benchmark_invalid_name(self) -> None:
        with pytest.raises(ValueError):
            Benchmark(id="B001", name="")

    def test_benchmark_defaults(self) -> None:
        b = Benchmark(id="B001", name="Test")
        assert b.difficulty == BenchmarkDifficulty.EASY
        assert b.category == BenchmarkCategory.PROJECT_GENERATION

    def test_benchmark_run_immutable(self) -> None:
        r = BenchmarkRun(benchmark_id="B001")
        with pytest.raises(Exception):
            r.state = BenchmarkState.COMPLETED  # type: ignore[misc]

    def test_benchmark_result_immutable(self) -> None:
        r = BenchmarkResult(run_id="r1", benchmark_id="B001", success=True)
        with pytest.raises(Exception):
            r.success = False  # type: ignore[misc]

    def test_benchmark_score_immutable(self) -> None:
        s = BenchmarkScore(run_id="r1")
        with pytest.raises(Exception):
            s.overall = 100  # type: ignore[misc]

    def test_benchmark_score_validation(self) -> None:
        with pytest.raises(ValueError):
            BenchmarkScore(run_id="r1", overall=101)

    def test_benchmark_score_validation_negative(self) -> None:
        with pytest.raises(ValueError):
            BenchmarkScore(run_id="r1", overall=-1)

    def test_benchmark_report_immutable(self) -> None:
        r = BenchmarkReport(run_id="r1", benchmark_id="B001", outcome=BenchmarkOutcome.PASS, score=BenchmarkScore(run_id="r1"), duration_ms=100.0)
        with pytest.raises(Exception):
            r.outcome = BenchmarkOutcome.FAIL  # type: ignore[misc]

    def test_capability_profile_immutable(self) -> None:
        p = CapabilityProfile()
        with pytest.raises(Exception):
            p.profiles = {}  # type: ignore[misc]

    def test_benchmark_state_values(self) -> None:
        assert BenchmarkState.RUNNING == "running"
        assert BenchmarkState.COMPLETED == "completed"

    def test_benchmark_outcome_values(self) -> None:
        assert BenchmarkOutcome.PASS == "pass"
        assert BenchmarkOutcome.FAIL == "fail"

    def test_benchmark_difficulty_values(self) -> None:
        assert BenchmarkDifficulty.EASY == "easy"
        assert BenchmarkDifficulty.EXTREME == "extreme"

    def test_benchmark_category_values(self) -> None:
        assert BenchmarkCategory.DEBUGGING == "debugging"
        assert BenchmarkCategory.SELF_ENGINEERING == "self_engineering"

    def test_score_level_values(self) -> None:
        assert ScoreLevel.EXCELLENT == "excellent"
        assert ScoreLevel.FAILING == "failing"

    def test_benchmark_metadata(self) -> None:
        b = Benchmark(id="B001", name="Test", metadata={"key": "value"})
        assert b.metadata["key"] == "value"

    def test_benchmark_result_metadata(self) -> None:
        r = BenchmarkResult(run_id="r1", benchmark_id="B001", success=True, metadata={"key": "value"})
        assert r.metadata["key"] == "value"

    def test_benchmark_run_defaults(self) -> None:
        r = BenchmarkRun(benchmark_id="B001")
        assert r.state == BenchmarkState.CREATED
        assert r.workspace_path is None

    def test_benchmark_score_defaults(self) -> None:
        s = BenchmarkScore(run_id="r1")
        assert s.overall == 0
        assert s.level == ScoreLevel.FAILING

    def test_capability_profile_creation(self) -> None:
        p = CapabilityProfile(profiles={BenchmarkCategory.DEBUGGING: 85})
        assert p.profiles[BenchmarkCategory.DEBUGGING] == 85


# --- Registry Tests (15) ---

class TestBenchmarkRegistry:
    def test_register(self, registry: BenchmarkRegistry) -> None:
        assert len(registry.list()) == 2

    def test_duplicate_raises(self, registry: BenchmarkRegistry) -> None:
        with pytest.raises(RegistryError):
            registry.register(Benchmark(id="B001", name="Calc"))

    def test_find_success(self, registry: BenchmarkRegistry) -> None:
        b = registry.find("B001")
        assert b.name == "Calculator"

    def test_find_missing_raises(self, registry: BenchmarkRegistry) -> None:
        with pytest.raises(RegistryError):
            registry.find("missing")

    def test_list_sorted(self, registry: BenchmarkRegistry) -> None:
        b_ids = [b.id for b in registry.list()]
        assert b_ids == ["B001", "B002"]

    def test_list_by_category(self, registry: BenchmarkRegistry) -> None:
        b_list = registry.list_by_category("feature_engineering")
        assert len(b_list) == 1
        assert b_list[0].id == "B002"

    def test_list_empty(self) -> None:
        reg = BenchmarkRegistry()
        assert len(reg.list()) == 0

    def test_list_by_category_empty(self, registry: BenchmarkRegistry) -> None:
        assert len(registry.list_by_category("debugging")) == 0

    def test_register_multiple(self) -> None:
        reg = BenchmarkRegistry()
        reg.register(Benchmark(id="B1", name="B1"))
        reg.register(Benchmark(id="B2", name="B2"))
        assert len(reg.list()) == 2

    def test_list_returns_tuple(self, registry: BenchmarkRegistry) -> None:
        assert isinstance(registry.list(), tuple)

    def test_list_by_category_returns_tuple(self, registry: BenchmarkRegistry) -> None:
        assert isinstance(registry.list_by_category("project_generation"), tuple)

    def test_find_returns_benchmark(self, registry: BenchmarkRegistry) -> None:
        b = registry.find("B001")
        assert isinstance(b, Benchmark)

    def test_register_benchmark(self) -> None:
        reg = BenchmarkRegistry()
        b = Benchmark(id="B1", name="B1")
        reg.register(b)
        assert reg.find("B1") is b

    def test_list_by_category_string_match(self, registry: BenchmarkRegistry) -> None:
        b_list = registry.list_by_category("project_generation")
        assert len(b_list) == 1

    def test_list_by_category_enum_match(self, registry: BenchmarkRegistry) -> None:
        b_list = registry.list_by_category(BenchmarkCategory.PROJECT_GENERATION.value)
        assert len(b_list) == 1


# --- Evaluator & Reporter Tests (15) ---

class TestEvaluatorAndReporter:
    def test_evaluator_success(self) -> None:
        evaluator = DefaultEvaluator()
        result = BenchmarkResult(
            run_id="r1", benchmark_id="B001", success=True,
            metadata={"tests_pass": True, "readme_exists": True, "valid_structure": True}
        )
        score = evaluator.evaluate(result)
        assert score.overall == 100
        assert score.level == ScoreLevel.EXCELLENT

    def test_evaluator_failure(self) -> None:
        evaluator = DefaultEvaluator()
        result = BenchmarkResult(run_id="r1", benchmark_id="B001", success=False)
        score = evaluator.evaluate(result)
        assert score.overall == 0
        assert score.level == ScoreLevel.FAILING

    def test_evaluator_partial_metadata(self) -> None:
        evaluator = DefaultEvaluator()
        result = BenchmarkResult(
            run_id="r1", benchmark_id="B001", success=True,
            metadata={"tests_pass": True}
        )
        score = evaluator.evaluate(result)
        assert score.tests == 100
        assert score.documentation == 50
        assert score.overall == 83  # (100+50+50)//3

    def test_reporter_success(self) -> None:
        reporter = DefaultReporter()
        result = BenchmarkResult(run_id="r1", benchmark_id="B001", success=True, metadata={"tests_pass": True, "readme_exists": True, "valid_structure": True})
        score = BenchmarkScore(run_id="r1", overall=100, level=ScoreLevel.EXCELLENT)
        report = reporter.generate(result, score)
        assert report.outcome == BenchmarkOutcome.PASS
        assert "100/100" in report.summary

    def test_reporter_failure(self) -> None:
        reporter = DefaultReporter()
        result = BenchmarkResult(run_id="r1", benchmark_id="B001", success=False)
        score = BenchmarkScore(run_id="r1", overall=0, level=ScoreLevel.FAILING)
        report = reporter.generate(result, score)
        assert report.outcome == BenchmarkOutcome.FAIL

    def test_reporter_recommendations(self) -> None:
        reporter = DefaultReporter()
        result = BenchmarkResult(run_id="r1", benchmark_id="B001", success=True)
        score = BenchmarkScore(run_id="r1", overall=50, tests=50, documentation=50, level=ScoreLevel.FAIR)
        report = reporter.generate(result, score)
        assert len(report.recommendations) == 2

    def test_evaluator_score_bounds(self) -> None:
        evaluator = DefaultEvaluator()
        result = BenchmarkResult(run_id="r1", benchmark_id="B001", success=True)
        score = evaluator.evaluate(result)
        assert 0 <= score.overall <= 100

    def test_reporter_outcome_pass_threshold(self) -> None:
        reporter = DefaultReporter()
        result = BenchmarkResult(run_id="r1", benchmark_id="B001", success=True)
        score = BenchmarkScore(run_id="r1", overall=50, level=ScoreLevel.FAIR)
        report = reporter.generate(result, score)
        assert report.outcome == BenchmarkOutcome.PASS

    def test_reporter_outcome_fail_threshold(self) -> None:
        reporter = DefaultReporter()
        result = BenchmarkResult(run_id="r1", benchmark_id="B001", success=True)
        score = BenchmarkScore(run_id="r1", overall=49, level=ScoreLevel.POOR)
        report = reporter.generate(result, score)
        assert report.outcome == BenchmarkOutcome.FAIL

    def test_evalutor_level_good(self) -> None:
        evaluator = DefaultEvaluator()
        result = BenchmarkResult(run_id="r1", benchmark_id="B001", success=True, metadata={"tests_pass": True, "readme_exists": True, "valid_structure": False})
        score = evaluator.evaluate(result)
        assert score.overall == 83
        assert score.level == ScoreLevel.GOOD

    def test_evaluator_level_fair(self) -> None:
        evaluator = DefaultEvaluator()
        result = BenchmarkResult(run_id="r1", benchmark_id="B001", success=True, metadata={"tests_pass": True, "readme_exists": False, "valid_structure": False})
        score = evaluator.evaluate(result)
        assert score.overall == 66
        assert score.level == ScoreLevel.FAIR

    def test_evaluator_level_poor(self) -> None:
        evaluator = DefaultEvaluator()
        result = BenchmarkResult(run_id="r1", benchmark_id="B001", success=True, metadata={"tests_pass": False, "readme_exists": False, "valid_structure": False})
        score = evaluator.evaluate(result)
        assert score.overall == 50
        assert score.level == ScoreLevel.POOR

    def test_reporter_summary_contains_level(self) -> None:
        reporter = DefaultReporter()
        result = BenchmarkResult(run_id="r1", benchmark_id="B001", success=True)
        score = BenchmarkScore(run_id="r1", overall=100, level=ScoreLevel.EXCELLENT)
        report = reporter.generate(result, score)
        assert "excellent" in report.summary

    def test_reporter_recommendations_empty(self) -> None:
        reporter = DefaultReporter()
        result = BenchmarkResult(run_id="r1", benchmark_id="B001", success=True, metadata={"tests_pass": True, "readme_exists": True, "valid_structure": True})
        score = BenchmarkScore(run_id="r1", overall=100, tests=100, documentation=100, level=ScoreLevel.EXCELLENT)
        report = reporter.generate(result, score)
        assert len(report.recommendations) == 0

    def test_evaluator_protocol(self) -> None:
        assert isinstance(DefaultEvaluator(), BenchmarkEvaluator)


# --- Runner & Fixtures Tests (10) ---

class TestRunnerAndFixtures:
    def test_runner_success(self, runner: BenchmarkRunner) -> None:
        b = make_benchmark()
        run, report = runner.run(b)
        assert run.state == BenchmarkState.COMPLETED
        assert report.outcome == BenchmarkOutcome.PASS
        assert report.score.overall == 100

    def test_runner_failure(self, failing_runner: BenchmarkRunner) -> None:
        b = make_benchmark()
        run, report = failing_runner.run(b)
        assert run.state == BenchmarkState.FAILED
        assert report.outcome == BenchmarkOutcome.FAIL
        assert "Execution failed" in run.error

    def test_runner_cleans_up_workspace(self, runner: BenchmarkRunner) -> None:
        b = make_benchmark()
        run, report = runner.run(b)
        assert run.workspace_path is not None
        assert not run.workspace_path.exists()  # Should be cleaned up

    def test_fixture_manager_creates_temp_dir(self) -> None:
        fm = FixtureManager()
        b = make_benchmark()
        workspace = fm.prepare(b)
        assert workspace.exists()
        fm.cleanup(workspace)
        assert not workspace.exists()

    def test_fixture_manager_copies_fixture(self, tmp_path: Path) -> None:
        # Create a fake fixture
        fixture_dir = tmp_path / "fixture"
        fixture_dir.mkdir()
        (fixture_dir / "test.txt").write_text("test")
        
        fm = FixtureManager()
        b = Benchmark(id="B001", name="Test", fixture_path=fixture_dir)
        workspace = fm.prepare(b)
        
        assert (workspace / "test.txt").exists()
        fm.cleanup(workspace)

    def test_runner_returns_report(self, runner: BenchmarkRunner) -> None:
        b = make_benchmark()
        _, report = runner.run(b)
        assert isinstance(report, BenchmarkReport)

    def test_runner_returns_run(self, runner: BenchmarkRunner) -> None:
        b = make_benchmark()
        run, _ = runner.run(b)
        assert isinstance(run, BenchmarkRun)

    def test_runner_duration_positive(self, runner: BenchmarkRunner) -> None:
        b = make_benchmark()
        _, report = runner.run(b)
        assert report.duration_ms >= 0.0

    def test_runner_error_state(self, failing_runner: BenchmarkRunner) -> None:
        b = make_benchmark()
        run, _ = failing_runner.run(b)
        assert run.state == BenchmarkState.FAILED

    def test_runner_error_message(self, failing_runner: BenchmarkRunner) -> None:
        b = make_benchmark()
        run, _ = failing_runner.run(b)
        assert "Execution failed" in run.error