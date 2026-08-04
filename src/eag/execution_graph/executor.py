"""Parallel Batch Executor for EAG."""

from dataclasses import dataclass, field
from eag.execution_graph.enums import FailurePolicy
from eag.execution_graph.models import ExecutionNode
from eag.events import EventBus
from eag.workers.manager import WorkerManager
from eag.workers.models import WorkerContext, WorkerResult, WorkerTask
from eag.workers.runtime import WorkerRuntime


@dataclass
class BatchResult:
    """The result of executing a batch of nodes."""
    completed: set[str] = field(default_factory=set)
    failed: set[str] = field(default_factory=set)
    results: dict[str, WorkerResult] = field(default_factory=dict)


class BatchExecutor:
    """Executes batches of nodes in parallel (currently sequential internally)."""

    def __init__(
        self,
        event_bus: EventBus,
        manager: WorkerManager,
        worker_runtime: WorkerRuntime,
        failure_policy: FailurePolicy = FailurePolicy.CONTINUE
    ) -> None:
        self._event_bus = event_bus
        self._manager = manager
        self._worker_runtime = worker_runtime
        self._failure_policy = failure_policy

    def execute_batch(
        self, 
        batch: tuple[ExecutionNode, ...], 
        context: WorkerContext
    ) -> BatchResult:
        """Executes a batch of nodes concurrently (sequentially under the hood)."""
        result = BatchResult()
        
        for node in batch:
            # Find a worker for this node's task
            worker = self._manager.find_best_worker_for_task(node.task_id)
            if not worker:
                result.failed.add(node.id)
                continue
                
            self._manager.assign(worker.profile.id, node.id)
            
            # Create a task object for the worker runtime
            task = WorkerTask(id=node.task_id, title=node.title)
            
            worker_result = self._worker_runtime.execute(worker, task, context)
            result.results[node.id] = worker_result
            
            if worker_result.success:
                result.completed.add(node.id)
            else:
                result.failed.add(node.id)
                if self._failure_policy == FailurePolicy.FAIL_FAST:
                    break
                    
        return result