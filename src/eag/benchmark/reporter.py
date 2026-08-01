"""Benchmark reporter for EAG."""

from eag.benchmark.enums import BenchmarkOutcome
from eag.benchmark.models import BenchmarkReport, BenchmarkResult, BenchmarkScore


class DefaultReporter:
    """Generates human-readable and machine-readable reports."""

    def generate(self, result: BenchmarkResult, score: BenchmarkScore) -> BenchmarkReport:
        outcome = (
            BenchmarkOutcome.PASS
            if result.success and score.overall >= 50
            else BenchmarkOutcome.FAIL
        )

        summary = f"Completed with overall score {score.overall}/100 ({score.level.value})."
        recommendations = []

        if score.tests < 100:
            recommendations.append("Improve test coverage.")
        if score.documentation < 100:
            recommendations.append("Add missing documentation.")

        return BenchmarkReport(
            run_id=result.run_id,
            benchmark_id=result.benchmark_id,
            outcome=outcome,
            score=score,
            duration_ms=result.duration_ms,
            summary=summary,
            recommendations=tuple(recommendations),
        )
