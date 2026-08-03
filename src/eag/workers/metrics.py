"""Worker runtime metrics for EAG."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkerRuntimeMetrics:
    """Metrics tracking the overall state of the worker pool."""

    total_workers: int = 0
    idle_workers: int = 0
    busy_workers: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    queue_size: int = 0
    utilization: float = 0.0
