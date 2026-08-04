"""Parallel Scheduler Runtime for EAG."""

from eag.events import EventBus
from eag.scheduler.dispatcher import Dispatcher
from eag.scheduler.models import (
    ExecutionBatch,
    SchedulerMetrics,
)
from eag.scheduler.queue import ReadyQueue
from eag.task_graph.graph import TaskGraph
from eag.workers.manager import WorkerManager
from eag.workers.models import WorkerContext
from eag.workers.runtime import WorkerRuntime


class SchedulerRuntime:
    """Orchestrates parallel execution of a TaskGraph."""

    def __init__(
        self, event_bus: EventBus, manager: WorkerManager, worker_runtime: WorkerRuntime
    ) -> None:
        self._event_bus = event_bus
        self._manager = manager
        self._worker_runtime = worker_runtime
        self._dispatcher = Dispatcher(manager)
        self._queue = ReadyQueue()
        self._completed: set[str] = set()
        self._failed: set[str] = set()

        self._metrics = SchedulerMetrics()
        self._total_batch_size = 0
        self._max_parallelism = 0

    def execute_graph(self, graph: TaskGraph, context: WorkerContext) -> tuple[set[str], set[str]]:
        """Executes the entire graph in parallel batches."""

        while True:
            # 1. Find newly ready tasks and push to queue
            ready_tasks = graph.ready(self._completed)
            for task in ready_tasks:
                if not self._queue.contains(task.id):
                    self._queue.push(task)

            # 2. If queue is empty, we are done (or deadlocked)
            if self._queue.empty():
                break

            # 3. Form a batch
            batch_assignments = []
            while not self._queue.empty():
                task = self._queue.pop()
                assignment = self._dispatcher.dispatch(task)
                if assignment:
                    batch_assignments.append(assignment)
                else:
                    # No worker available, put back in queue and wait for next cycle
                    self._queue.push(task)
                    break

            if not batch_assignments:
                # No workers available for any ready task
                break

            # 4. Execute batch (synchronous internally, but logically parallel)
            batch = ExecutionBatch(assignments=tuple(batch_assignments))
            self._execute_batch(batch, graph, context)

            # Pre-calculate to avoid ZeroDivisionError
            new_batches = self._metrics.batches_executed + 1
            new_total = self._total_batch_size + batch.parallelism
            self._max_parallelism = max(self._max_parallelism, batch.parallelism)

            self._metrics = SchedulerMetrics(
                total_cycles=self._metrics.total_cycles + 1,
                batches_executed=new_batches,
                tasks_completed=len(self._completed),
                tasks_failed=len(self._failed),
                average_batch_size=new_total / new_batches,
                max_parallelism=self._max_parallelism,
            )
            self._total_batch_size = new_total

        return self._completed, self._failed

    def _execute_batch(
        self, batch: ExecutionBatch, graph: TaskGraph, context: WorkerContext
    ) -> None:
        """Executes a batch of assignments concurrently (currently sequential)."""
        for assignment in batch.assignments:
            worker = self._manager._registry.find(assignment.worker_id)
            task = next(n for n in graph.nodes if n.id == assignment.task_id)

            result = self._worker_runtime.execute(worker, task, context)

            if result.success:
                self._completed.add(task.id)
            else:
                self._failed.add(task.id)
                # In a real scheduler, we might retry or escalate
