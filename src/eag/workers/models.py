"""Worker domain models for EAG."""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any

from eag.workers.enums import (
    ExperienceLevel,
    TaskPriority,
    WorkerHealth,
    WorkerRole,
)


def _validate_mapping(value: Mapping[str, Any], field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a Mapping")
    return MappingProxyType(dict(value))


def _validate_non_empty_str(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} cannot be empty or whitespace")
    return value.strip()


def _validate_non_negative_int(value: int, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return value


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkerMetrics:
    """Metrics tracking the performance of a worker."""

    tasks_completed: int = 0
    tasks_failed: int = 0
    average_duration_ms: float = 0.0
    average_review_score: float = 0.0
    retry_count: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "tasks_completed",
            _validate_non_negative_int(self.tasks_completed, "tasks_completed"),
        )
        object.__setattr__(
            self, "tasks_failed", _validate_non_negative_int(self.tasks_failed, "tasks_failed")
        )
        object.__setattr__(
            self, "retry_count", _validate_non_negative_int(self.retry_count, "retry_count")
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkerProfile:
    """Represents an engineer."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    role: WorkerRole = WorkerRole.GENERAL
    experience: ExperienceLevel = ExperienceLevel.MID
    capabilities: tuple[str, ...] = ()
    preferred_capabilities: tuple[str, ...] = ()
    supported_languages: tuple[str, ...] = ()
    max_parallel_tasks: int = 1
    health: WorkerHealth = WorkerHealth.HEALTHY
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _validate_non_empty_str(self.name, "name"))
        if not isinstance(self.role, WorkerRole):
            raise TypeError("role must be a WorkerRole")
        if not isinstance(self.experience, ExperienceLevel):
            raise TypeError("experience must be an ExperienceLevel")
        if not isinstance(self.health, WorkerHealth):
            raise TypeError("health must be a WorkerHealth")
        if not isinstance(self.capabilities, tuple):
            raise TypeError("capabilities must be a tuple")
        if not isinstance(self.preferred_capabilities, tuple):
            raise TypeError("preferred_capabilities must be a tuple")
        if not isinstance(self.supported_languages, tuple):
            raise TypeError("supported_languages must be a tuple")
        if (
            not isinstance(self.max_parallel_tasks, int)
            or isinstance(self.max_parallel_tasks, bool)
            or self.max_parallel_tasks < 1
        ):
            raise ValueError("max_parallel_tasks must be an integer >= 1")
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkerTask:
    """Represents one engineering task."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str = ""
    required_capability: str = ""
    estimated_complexity: float = 1.0
    priority: TaskPriority = TaskPriority.NORMAL
    dependencies: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "title", _validate_non_empty_str(self.title, "title"))
        if not isinstance(self.priority, TaskPriority):
            raise TypeError("priority must be a TaskPriority")
        if not isinstance(self.dependencies, tuple):
            raise TypeError("dependencies must be a tuple")
        if (
            not isinstance(self.estimated_complexity, (int, float))
            or isinstance(self.estimated_complexity, bool)
            or self.estimated_complexity < 0
        ):
            raise ValueError("estimated_complexity must be a non-negative number")
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkerAssignment:
    """Represents the assignment of a task to a worker."""

    assignment_id: str = field(
        default_factory=lambda: str(uuid.uuid4()),
        compare=False,  # Excluded from equality checks if auto-generated
    )
    worker_id: str
    task_id: str
    assigned_at: datetime = field(
        default_factory=lambda: datetime.now(UTC),
        compare=False,  # Prevents sub-millisecond timestamp mismatch during equality checks
    )
    reason: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "worker_id", _validate_non_empty_str(self.worker_id, "worker_id"))
        object.__setattr__(self, "task_id", _validate_non_empty_str(self.task_id, "task_id"))

        # Ensure metadata is validated and stored as an immutable MappingProxyType for frozen dataclass compatibility
        validated_meta = _validate_mapping(self.metadata, "metadata")
        if not isinstance(validated_meta, MappingProxyType):
            validated_meta = MappingProxyType(dict(validated_meta))
        object.__setattr__(self, "metadata", validated_meta)


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkerContext:
    """Execution context provided to a worker."""

    run_id: str
    goal: str
    workspace: Path
    repository: Path | None = None
    trace_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _validate_non_empty_str(self.run_id, "run_id"))
        object.__setattr__(self, "goal", _validate_non_empty_str(self.goal, "goal"))
        if not isinstance(self.workspace, Path):
            raise TypeError("workspace must be a Path")
        if self.repository is not None and not isinstance(self.repository, Path):
            raise TypeError("repository must be a Path or None")
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkerResult:
    """The result of a worker executing a task."""

    worker_id: str
    task_id: str
    success: bool
    summary: str = ""
    artifacts: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metrics: WorkerMetrics = field(default_factory=WorkerMetrics)
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "worker_id", _validate_non_empty_str(self.worker_id, "worker_id"))
        object.__setattr__(self, "task_id", _validate_non_empty_str(self.task_id, "task_id"))
        if not isinstance(self.success, bool):
            raise TypeError("success must be a bool")
        if not isinstance(self.artifacts, tuple):
            raise TypeError("artifacts must be a tuple")
        if not isinstance(self.warnings, tuple):
            raise TypeError("warnings must be a tuple")
        if not isinstance(self.metrics, WorkerMetrics):
            raise TypeError("metrics must be a WorkerMetrics")
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))

    @property
    def is_success(self) -> bool:
        return self.success

    @property
    def is_failure(self) -> bool:
        return not self.success
