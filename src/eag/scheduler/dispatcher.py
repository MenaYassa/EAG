"""Dispatcher for EAG Scheduler."""

from eag.scheduler.models import WorkerAssignment
from eag.task_graph.models import TaskNode
from eag.workers.manager import WorkerManager


class Dispatcher:
    """Maps ready tasks to available workers via the WorkerManager."""

    def __init__(self, manager: WorkerManager) -> None:
        self._manager = manager

    def dispatch(self, task: TaskNode) -> WorkerAssignment | None:
        """Finds the best worker for a task and assigns it."""
        worker = self._manager.find_best_worker(task)
        if not worker:
            return None
            
        assigned = self._manager.assign(worker.profile.id, task.id)
        if not assigned:
            return None
            
        return WorkerAssignment(
            worker_id=worker.profile.id,
            task_id=task.id
        )

    def release(self, worker_id: str) -> None:
        """Releases a worker back to the pool."""
        self._manager.release(worker_id)