"""Worker registry for EAG."""

from eag.workers.enums import WorkerHealth, WorkerRole
from eag.workers.errors import WorkerNotFoundError
from eag.workers.health import WorkerHealthManager
from eag.workers.protocol import Worker


class WorkerRegistry:
    """Discovers and manages available engineering workers."""

    def __init__(self) -> None:
        self._workers: dict[str, Worker] = {}

    def register(self, worker: Worker) -> None:
        wid = worker.profile.id
        if wid in self._workers:
            raise ValueError(f"Worker '{wid}' is already registered.")
        self._workers[wid] = worker

    def unregister(self, worker_id: str) -> bool:
        return self._workers.pop(worker_id, None) is not None

    def find(self, worker_id: str) -> Worker:
        if worker_id not in self._workers:
            raise WorkerNotFoundError(f"Worker '{worker_id}' not found.")
        return self._workers[worker_id]

    def list(self) -> tuple[Worker, ...]:
        """Returns all workers, sorted by ID for determinism."""
        return tuple(sorted(self._workers.values(), key=lambda w: w.profile.id))

    def available(self, health_manager: WorkerHealthManager) -> tuple[Worker, ...]:
        """Returns healthy or degraded workers."""
        return tuple(
            w
            for w in self.list()
            if health_manager.get_health(w.profile.id)
            in [WorkerHealth.HEALTHY, WorkerHealth.DEGRADED]
        )

    def by_role(self, role: WorkerRole) -> tuple[Worker, ...]:
        return tuple(w for w in self.list() if w.profile.role == role)

    def by_capability(self, capability: str) -> tuple[Worker, ...]:
        return tuple(w for w in self.list() if capability in w.profile.capabilities)

    def by_health(
        self, health_manager: WorkerHealthManager, health: WorkerHealth
    ) -> tuple[Worker, ...]:
        return tuple(w for w in self.list() if health_manager.get_health(w.profile.id) == health)
