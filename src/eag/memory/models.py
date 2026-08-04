"""Engineering Memory domain models for EAG."""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any

from eag.memory.enums import KnowledgeLevel, MemoryCategory


def _validate_mapping(value: Mapping[str, Any], field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a Mapping")
    return MappingProxyType(dict(value))


def _validate_non_empty_str(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} cannot be empty or whitespace")
    return value.strip()


def _validate_confidence(value: float) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TypeError("confidence must be a float")
    if not (0.0 <= value <= 1.0):
        raise ValueError("confidence must be between 0.0 and 1.0")
    return float(value)


@dataclass(frozen=True, slots=True, kw_only=True)
class LessonLearned:
    """An immutable lesson extracted from an engineering run."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    category: MemoryCategory
    description: str
    evidence: str = ""
    confidence: float = 1.0
    recommendation: str = ""
    level: KnowledgeLevel = KnowledgeLevel.LESSON

    def __post_init__(self) -> None:
        if not isinstance(self.category, MemoryCategory):
            raise TypeError("category must be a MemoryCategory")
        object.__setattr__(self, "description", _validate_non_empty_str(self.description, "description"))
        object.__setattr__(self, "confidence", _validate_confidence(self.confidence))
        if not isinstance(self.level, KnowledgeLevel):
            raise TypeError("level must be a KnowledgeLevel")


@dataclass(frozen=True, slots=True, kw_only=True)
class MemoryEntry:
    """The atomic record of an engineering run stored in memory."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()), compare=False)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC), compare=False)
    run_id: str
    goal: str
    reflection_id: str
    summary: str = ""
    tags: tuple[str, ...] = ()
    lessons: tuple[LessonLearned, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _validate_non_empty_str(self.run_id, "run_id"))
        object.__setattr__(self, "goal", _validate_non_empty_str(self.goal, "goal"))
        object.__setattr__(self, "reflection_id", _validate_non_empty_str(self.reflection_id, "reflection_id"))
        if not isinstance(self.tags, tuple):
            raise TypeError("tags must be a tuple")
        if not isinstance(self.lessons, tuple):
            raise TypeError("lessons must be a tuple")
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class EngineeringExperience:
    """A normalized experience derived from one or more memory entries."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    project_type: str
    goal_type: str = ""
    complexity: str = "medium"
    benchmark_score: float = 0.0
    outcome: str = "unknown"
    confidence: float = 1.0
    lessons: tuple[LessonLearned, ...] = ()
    source_entries: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_type", _validate_non_empty_str(self.project_type, "project_type"))
        object.__setattr__(self, "confidence", _validate_confidence(self.confidence))
        if not isinstance(self.lessons, tuple):
            raise TypeError("lessons must be a tuple")
        if not isinstance(self.source_entries, tuple):
            raise TypeError("source_entries must be a tuple")


@dataclass(frozen=True, slots=True, kw_only=True)
class MemoryStatistics:
    """Aggregate statistics over the memory base."""
    total_runs: int = 0
    success_rate: float = 0.0
    average_score: float = 0.0
    average_duration_ms: float = 0.0
    most_common_findings: tuple[str, ...] = ()
    most_common_recommendations: tuple[str, ...] = ()
    worker_success_rates: Mapping[str, float] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "worker_success_rates", _validate_mapping(self.worker_success_rates, "worker_success_rates"))


@dataclass(frozen=True, slots=True, kw_only=True)
class MemorySnapshot:
    """An immutable snapshot of the memory base at a point in time."""
    version: str = "1.0.0"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    entries: tuple[MemoryEntry, ...] = ()
    statistics: MemoryStatistics = field(default_factory=MemoryStatistics)


@dataclass(frozen=True, slots=True, kw_only=True)
class MemoryQuery:
    """A structured query against the memory base."""
    goal_contains: str = ""
    tags: tuple[str, ...] = ()
    categories: tuple[MemoryCategory, ...] = ()
    min_score: float = 0.0
    limit: int = 100

    def __post_init__(self) -> None:
        if not isinstance(self.tags, tuple):
            raise TypeError("tags must be a tuple")
        if not isinstance(self.categories, tuple):
            raise TypeError("categories must be a tuple")


@dataclass(frozen=True, slots=True, kw_only=True)
class MemorySearchResult:
    """The result of a memory query."""
    records: tuple[MemoryEntry, ...]
    statistics: MemoryStatistics
    count: int