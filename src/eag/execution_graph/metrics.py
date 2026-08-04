"""Execution Graph runtime metrics for EAG."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionMetrics:
    """Metrics tracking the parallel execution activity."""

    total_batches: int = 0
    max_parallelism: int = 0
    average_batch_size: float = 0.0
    synchronization_barriers: int = 0
    messages_exchanged: int = 0
    artifacts_produced: int = 0
    failure_recoveries: int = 0
    dependency_unlocks: int = 0
