"""Worker health manager for EAG."""

from eag.workers.enums import WorkerHealth


class WorkerHealthManager:
    """Tracks and manages worker health metrics."""

    def __init__(self, degrade_threshold: int = 1, unavailable_threshold: int = 3) -> None:
        self._health: dict[str, WorkerHealth] = {}
        self._failure_counts: dict[str, int] = {}
        self._degrade_threshold = degrade_threshold
        self._unavailable_threshold = unavailable_threshold

    def record_success(self, worker_id: str) -> None:
        self._failure_counts[worker_id] = 0
        self._health[worker_id] = WorkerHealth.HEALTHY

    def record_failure(self, worker_id: str) -> None:
        count = self._failure_counts.get(worker_id, 0) + 1
        self._failure_counts[worker_id] = count

        if count >= self._unavailable_threshold:
            self._health[worker_id] = WorkerHealth.UNAVAILABLE
        elif count >= self._degrade_threshold:
            self._health[worker_id] = WorkerHealth.DEGRADED

    def get_health(self, worker_id: str) -> WorkerHealth:
        return self._health.get(worker_id, WorkerHealth.HEALTHY)

    def recover(self, worker_id: str) -> None:
        self._health[worker_id] = WorkerHealth.HEALTHY
        self._failure_counts[worker_id] = 0
