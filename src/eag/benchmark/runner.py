"""Benchmark runner for EAG."""

import time
from pathlib import Path

from eag.benchmark.errors import RunnerError
from eag.benchmark.evaluator import DefaultEvaluator
from eag.benchmark.fixtures import FixtureManager
from eag.benchmark.models import (
    Benchmark,
    BenchmarkExecutor,
    BenchmarkReport,
    BenchmarkResult,
    BenchmarkRun,
    BenchmarkScore,
)
from eag.benchmark.reporter import DefaultReporter
from eag.benchmark.enums import BenchmarkState


class BenchmarkRunner:
    """Orchestrates benchmark execution, evaluation, and reporting."""

    def __init__(
        self,
        executor: BenchmarkExecutor,
        fixture_manager: FixtureManager | None = None,
        evaluator: DefaultEvaluator | None = None,
        reporter: DefaultReporter | None = None
    ) -> None:
        self._executor = executor
        self._fixtures = fixture_manager or FixtureManager()
        self._evaluator = evaluator or DefaultEvaluator()
        self._reporter = reporter or DefaultReporter()

    def run(self, benchmark: Benchmark) -> tuple[BenchmarkRun, BenchmarkReport]:
        """Executes a single benchmark and returns the run history and report."""
        workspace = self._fixtures.prepare(benchmark)
        run = BenchmarkRun(
            benchmark_id=benchmark.id,
            state=BenchmarkState.RUNNING,
            workspace_path=workspace
        )
        
        start_time = time.monotonic()
        
        try:
            result = self._executor.execute(benchmark, workspace)
            duration = (time.monotonic() - start_time) * 1000
            
            # Enrich result with duration
            result = BenchmarkResult(
                run_id=run.run_id,
                benchmark_id=benchmark.id,
                success=result.success,
                duration_ms=duration,
                artifacts=result.artifacts,
                logs=result.logs,
                metadata=result.metadata
            )
            
            score = self._evaluator.evaluate(result)
            report = self._reporter.generate(result, score)
            
            completed_run = BenchmarkRun(
                run_id=run.run_id,
                benchmark_id=benchmark.id,
                state=BenchmarkState.COMPLETED,
                started_at=run.started_at,
                workspace_path=workspace
            )
            
            return completed_run, report
            
        except Exception as e:
            duration = (time.monotonic() - start_time) * 1000
            failed_run = BenchmarkRun(
                run_id=run.run_id,
                benchmark_id=benchmark.id,
                state=BenchmarkState.FAILED,
                started_at=run.started_at,
                workspace_path=workspace,
                error=str(e)
            )
            # Create a failed report
            failed_result = BenchmarkResult(
                run_id=run.run_id,
                benchmark_id=benchmark.id,
                success=False,
                duration_ms=duration,
                logs=(str(e),)
            )
            failed_score = self._evaluator.evaluate(failed_result)
            failed_report = self._reporter.generate(failed_result, failed_score)
            return failed_run, failed_report
            
        finally:
            self._fixtures.cleanup(workspace)