"""Worker manager for EAG."""

from dataclasses import dataclass

from eag.workers.enums import WorkerHealth, WorkerState
from eag.workers.health import WorkerHealthManager
from eag.workers.models import WorkerTask
from eag.workers.protocol import Worker
from eag.workers.registry import WorkerRegistry


@dataclass
class WorkerInstance:
    """Internal state tracking for a worker."""

    worker: Worker
    state: WorkerState = WorkerState.IDLE
    current_task_id: str | None = None


class WorkerManager:
    """Manages worker lifecycle and assignments (HR)."""

    def __init__(self, registry: WorkerRegistry, health_manager: WorkerHealthManager) -> None:
        self._registry = registry
        self._health = health_manager
        self._instances: dict[str, WorkerInstance] = {}

    def _get_instance(self, worker_id: str) -> WorkerInstance:
        if worker_id not in self._instances:
            self._instances[worker_id] = WorkerInstance(worker=self._registry.find(worker_id))
        return self._instances[worker_id]

    def find_best_worker(self, task: WorkerTask) -> Worker | None:
        """Finds the best available worker for a given task."""
        # If no capability is required, any worker is a candidate
        if not task.required_capability:
            candidates = self._registry.list()
        else:
            candidates = self._registry.by_capability(task.required_capability)

        available = []

        for w in candidates:
            inst = self._get_instance(w.profile.id)
            health = self._health.get_health(w.profile.id)
            if inst.state == WorkerState.IDLE and health in [
                WorkerHealth.HEALTHY,
                WorkerHealth.DEGRADED,
            ]:
                available.append(w)

        if not available:
            return None

        # Prefer workers who have this capability as a preference
        if task.required_capability:
            preferred = [
                w for w in available if task.required_capability in w.profile.preferred_capabilities
            ]
            if preferred:
                return preferred[0]  # Already sorted by ID from registry

        return available[0]

    # Alias for backward compatibility with Chief integration loops
    def find_best_worker_for_task(self, task) -> "Worker | None":
        from eag.workers.models import WorkerTask

        # If the legacy executor passes a raw string ID, wrap it in a dummy task
        if isinstance(task, str):
            task = WorkerTask(
                id=task,
                title="Legacy Execution",
                required_capability="python",
                description="Legacy execution",
            )

        return self.find_best_worker(task)

    def assign(self, worker_id: str, task_id: str) -> bool:
        """Assigns a task to a worker."""
        inst = self._get_instance(worker_id)
        if inst.state != WorkerState.IDLE:
            return False

        inst.state = WorkerState.ASSIGNED
        inst.current_task_id = task_id
        return True

    def release(self, worker_id: str) -> None:
        """Releases a worker back to the pool."""
        inst = self._get_instance(worker_id)
        inst.state = WorkerState.IDLE
        inst.current_task_id = None

    def get_state(self, worker_id: str) -> WorkerState:
        return self._get_instance(worker_id).state

    def idle_workers(self) -> tuple[Worker, ...]:
        """Returns all unassigned workers by checking the registry, not just cached instances."""
        idle = []
        for w in self._registry.list():
            inst = self._instances.get(w.profile.id)
            if not inst or inst.state == WorkerState.IDLE:
                idle.append(w)
        return tuple(idle)

    def busy_workers(self) -> tuple[Worker, ...]:
        """Returns all currently busy workers."""
        busy = []
        for w in self._registry.list():
            inst = self._instances.get(w.profile.id)
            if inst and inst.state in [WorkerState.EXECUTING, WorkerState.ASSIGNED]:
                busy.append(w)
        return tuple(busy)
