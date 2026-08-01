"""Benchmark evaluator for EAG."""

from eag.benchmark.enums import ScoreLevel
from eag.benchmark.models import BenchmarkResult, BenchmarkScore


class DefaultEvaluator:
    """Evaluates benchmark results and produces a score."""

    def evaluate(self, result: BenchmarkResult) -> BenchmarkScore:
        if not result.success:
            return BenchmarkScore(
                run_id=result.run_id,
                planning=0,
                execution=0,
                architecture=0,
                tests=0,
                documentation=0,
                recovery=0,
                overall=0,
                level=ScoreLevel.FAILING,
            )

        planning = 100
        execution = 100
        recovery = 100

        # Helper to parse True=100, False=0, Missing=50
        def parse_score(key: str) -> int:
            if key not in result.metadata:
                return 50
            return 100 if result.metadata[key] else 0

        tests_score = parse_score("tests_pass")
        docs_score = parse_score("readme_exists")
        arch_score = parse_score("valid_structure")

        overall = (planning + execution + recovery + tests_score + docs_score + arch_score) // 6

        level = (
            ScoreLevel.EXCELLENT
            if overall >= 90
            else ScoreLevel.GOOD
            if overall >= 75
            else ScoreLevel.FAIR
            if overall > 50
            else ScoreLevel.POOR
        )

        return BenchmarkScore(
            run_id=result.run_id,
            planning=planning,
            execution=execution,
            architecture=arch_score,
            tests=tests_score,
            documentation=docs_score,
            recovery=recovery,
            overall=overall,
            level=level,
        )
