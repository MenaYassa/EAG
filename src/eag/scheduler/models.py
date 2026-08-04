"""Scheduler domain models for EAG."""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any

from eag.scheduler.enums import SchedulingPolicy
from eag.task_graph.models import TaskNode
from eag.workers.models import WorkerAssignment


def _validate_mapping(value: Mapping[str, Any], field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a Mapping")
    return MappingProxyType(dict(value))


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionBatch:
    """One scheduling iteration containing parallel assignments."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()), compare=False)
    assignments: tuple[WorkerAssignment, ...] = ()
    parallelism: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        if not isinstance(self.assignments, tuple):
            raise TypeError("assignments must be a tuple")
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))
        object.__setattr__(self, "parallelism", len(self.assignments))


@dataclass(frozen=True, slots=True, kw_only=True)
class SchedulingDecision:
    """Represents one scheduling cycle output."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()), compare=False)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC), compare=False)
    ready_tasks: tuple[TaskNode, ...] = ()
    assigned_workers: tuple[WorkerAssignment, ...] = ()
    policy: SchedulingPolicy = SchedulingPolicy.BEST_CAPABILITY
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class SchedulerMetrics:
    """Metrics tracking the overall scheduler activity."""

    total_cycles: int = 0
    batches_executed: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    average_batch_size: float = 0.0
    max_parallelism: int = 0
