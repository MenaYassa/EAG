"""Worker domain events for EAG."""

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkerEvent:
    worker_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkerRegistered(WorkerEvent):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkerAssigned(WorkerEvent):
    task_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkerStarted(WorkerEvent):
    task_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkerCompleted(WorkerEvent):
    task_id: str
    success: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkerFailed(WorkerEvent):
    task_id: str
    error: str


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkerRecovered(WorkerEvent):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkerReleased(WorkerEvent):
    pass
