"""Worker runtime for EAG."""

from eag.events import EventBus
from eag.workers.enums import WorkerState
from eag.workers.events import (
    WorkerCompleted,
    WorkerFailed,
    WorkerReleased,
    WorkerStarted,
)
from eag.workers.health import WorkerHealthManager
from eag.workers.manager import WorkerManager
from eag.workers.metrics import WorkerRuntimeMetrics
from eag.workers.models import WorkerContext, WorkerResult, WorkerTask
from eag.workers.protocol import Worker


class WorkerRuntime:
    """Orchestrates the execution of tasks by workers."""

    def __init__(
        self, event_bus: EventBus, health_manager: WorkerHealthManager, manager: WorkerManager
    ) -> None:
        self._event_bus = event_bus
        self._health = health_manager
        self._manager = manager
        self._completed_tasks = 0
        self._failed_tasks = 0

    def execute(self, worker: Worker, task: WorkerTask, context: WorkerContext) -> WorkerResult:
        """Executes a task using the assigned worker."""
        worker_id = worker.profile.id
        task_id = task.id

        # Update state to EXECUTING
        inst = self._manager._get_instance(worker_id)
        inst.state = WorkerState.EXECUTING

        self._event_bus.publish(WorkerStarted(worker_id=worker_id, task_id=task_id))

        try:
            result = worker.execute(task, context)

            if result.success:
                self._health.record_success(worker_id)
                self._event_bus.publish(
                    WorkerCompleted(worker_id=worker_id, task_id=task_id, success=True)
                )
                self._completed_tasks += 1
            else:
                self._health.record_failure(worker_id)
                self._event_bus.publish(
                    WorkerCompleted(worker_id=worker_id, task_id=task_id, success=False)
                )
                self._failed_tasks += 1

            return result

        except Exception as e:
            self._health.record_failure(worker_id)
            self._event_bus.publish(
                WorkerFailed(worker_id=worker_id, task_id=task_id, error=str(e))
            )
            self._failed_tasks += 1

            return WorkerResult(
                worker_id=worker_id,
                task_id=task_id,
                success=False,
                summary="Execution failed with exception",
                warnings=(str(e),),
            )
        finally:
            self._manager.release(worker_id)
            self._event_bus.publish(WorkerReleased(worker_id=worker_id))

    def get_metrics(self) -> WorkerRuntimeMetrics:
        # Calculate total across the entire registry, not just cached instances
        total = len(self._manager._registry.list())
        idle = len(self._manager.idle_workers())
        busy = len(self._manager.busy_workers())
        
        utilization = (busy / total) if total > 0 else 0.0

        return WorkerRuntimeMetrics(
            total_workers=total,
            idle_workers=idle,
            busy_workers=busy,
            completed_tasks=self._completed_tasks,
            failed_tasks=self._failed_tasks,
            utilization=utilization,
        )
