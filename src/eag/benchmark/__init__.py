"""Benchmark Platform for EAG."""

from eag.benchmark.enums import (
    BenchmarkCategory,
    BenchmarkDifficulty,
    BenchmarkOutcome,
    BenchmarkState,
    ScoreLevel,
)
from eag.benchmark.errors import (
    BenchmarkError,
    EvaluationError,
    FixtureError,
    RegistryError,
    RunnerError,
)
from eag.benchmark.evaluator import DefaultEvaluator
from eag.benchmark.fixtures import FixtureManager
from eag.benchmark.models import (
    Benchmark,
    BenchmarkEvaluator,
    BenchmarkExecutor,
    BenchmarkReport,
    BenchmarkResult,
    BenchmarkRun,
    BenchmarkScore,
    BenchmarkReporter,
    CapabilityProfile,
)
from eag.benchmark.registry import BenchmarkRegistry
from eag.benchmark.reporter import DefaultReporter
from eag.benchmark.runner import BenchmarkRunner

__all__ = [
    # Enums
    "BenchmarkCategory",
    "BenchmarkDifficulty",
    "BenchmarkOutcome",
    "BenchmarkState",
    "ScoreLevel",
    # Errors
    "BenchmarkError",
    "EvaluationError",
    "FixtureError",
    "RegistryError",
    "RunnerError",
    # Models
    "Benchmark",
    "BenchmarkEvaluator",
    "BenchmarkExecutor",
    "BenchmarkReport",
    "BenchmarkResult",
    "BenchmarkRun",
    "BenchmarkScore",
    "BenchmarkReporter",
    "CapabilityProfile",
    # Components
    "BenchmarkRegistry",
    "BenchmarkRunner",
    "DefaultEvaluator",
    "DefaultReporter",
    "FixtureManager",
]