"""Benchmark domain models for EAG."""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any, Protocol, runtime_checkable

from eag.benchmark.enums import (
    BenchmarkCategory,
    BenchmarkDifficulty,
    BenchmarkOutcome,
    BenchmarkState,
    ScoreLevel,
)


def _validate_mapping(value: Mapping[str, Any], field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a Mapping")
    return MappingProxyType(dict(value))


@dataclass(frozen=True, slots=True, kw_only=True)
class Benchmark:
    """Immutable specification of a benchmark."""

    id: str
    name: str
    description: str = ""
    difficulty: BenchmarkDifficulty = BenchmarkDifficulty.EASY
    category: BenchmarkCategory = BenchmarkCategory.PROJECT_GENERATION
    goal: str = ""
    success_criteria: tuple[str, ...] = ()
    fixture_path: Path | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("id cannot be empty")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name cannot be empty")
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class BenchmarkRun:
    """Tracks the execution state of a benchmark."""

    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    benchmark_id: str
    state: BenchmarkState = BenchmarkState.CREATED
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    workspace_path: Path | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class BenchmarkResult:
    """The raw outcome of running a benchmark."""

    run_id: str
    benchmark_id: str
    success: bool
    duration_ms: float = 0.0
    artifacts: tuple[Path, ...] = ()
    logs: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class BenchmarkScore:
    """Individual scores for a benchmark run."""

    run_id: str
    planning: int = 0
    execution: int = 0
    architecture: int = 0
    tests: int = 0
    documentation: int = 0
    recovery: int = 0
    overall: int = 0
    level: ScoreLevel = ScoreLevel.FAILING

    def __post_init__(self) -> None:
        for field_name in [
            "planning",
            "execution",
            "architecture",
            "tests",
            "documentation",
            "recovery",
            "overall",
        ]:
            val = getattr(self, field_name)
            if not isinstance(val, int) or not (0 <= val <= 100):
                raise ValueError(f"{field_name} must be an integer between 0 and 100")


@dataclass(frozen=True, slots=True, kw_only=True)
class BenchmarkReport:
    """The final generated report."""

    run_id: str
    benchmark_id: str
    outcome: BenchmarkOutcome
    score: BenchmarkScore
    duration_ms: float
    summary: str = ""
    recommendations: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityProfile:
    """Aggregation of scores across categories."""

    profiles: Mapping[BenchmarkCategory, int] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "profiles", _validate_mapping(self.profiles, "profiles"))


@runtime_checkable
class BenchmarkExecutor(Protocol):
    """Protocol for executing a benchmark task."""

    def execute(self, benchmark: Benchmark, workspace: Path) -> BenchmarkResult: ...


@runtime_checkable
class BenchmarkEvaluator(Protocol):
    """Protocol for evaluating benchmark results."""

    def evaluate(self, result: BenchmarkResult) -> BenchmarkScore: ...


@runtime_checkable
class BenchmarkReporter(Protocol):
    """Protocol for generating reports."""

    def generate(self, result: BenchmarkResult, score: BenchmarkScore) -> BenchmarkReport: ...
