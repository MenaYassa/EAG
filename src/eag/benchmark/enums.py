"""Benchmark domain vocabulary for EAG."""

from enum import StrEnum


class BenchmarkState(StrEnum):
    """Lifecycle state of a benchmark run."""
    CREATED = "created"
    READY = "ready"
    RUNNING = "running"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BenchmarkOutcome(StrEnum):
    """The final outcome of a benchmark."""
    PASS = "pass"
    FAIL = "fail"
    PARTIAL = "partial"
    ERROR = "error"


class BenchmarkDifficulty(StrEnum):
    """Difficulty tiers for benchmarks."""
    TRIVIAL = "trivial"
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXTREME = "extreme"


class BenchmarkCategory(StrEnum):
    """Engineering categories assessed by benchmarks."""
    PROJECT_GENERATION = "project_generation"
    FEATURE_ENGINEERING = "feature_engineering"
    REFACTORING = "refactoring"
    DEBUGGING = "debugging"
    FULL_APPLICATION = "full_application"
    SELF_ENGINEERING = "self_engineering"


class ScoreLevel(StrEnum):
    """Qualitative levels for benchmark scores."""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    FAILING = "failing"