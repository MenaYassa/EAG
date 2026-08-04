"""Parallel Execution Runtime for EAG."""

from eag.events import EventBus
from eag.execution_graph.enums import FailurePolicy
from eag.execution_graph.executor import BatchExecutor
from eag.execution_graph.graph import ExecutionGraph
from eag.workers.manager import WorkerManager
from eag.workers.models import WorkerContext
from eag.workers.runtime import WorkerRuntime


class ParallelExecutionRuntime:
    """Orchestrates the execution of an ExecutionGraph in parallel batches."""

    def __init__(
        self,
        event_bus: EventBus,
        manager: WorkerManager,
        worker_runtime: WorkerRuntime,
        failure_policy: FailurePolicy = FailurePolicy.CONTINUE
    ) -> None:
        self._event_bus = event_bus
        self._manager = manager
        self._executor = BatchExecutor(
            event_bus=event_bus,
            manager=manager,
            worker_runtime=worker_runtime,
            failure_policy=failure_policy
        )

    def execute(self, graph: ExecutionGraph, context: WorkerContext) -> tuple[set[str], set[str]]:
        """Executes the entire graph in parallel batches."""
        completed: set[str] = set()
        failed: set[str] = set()
        
        while not graph.is_complete(completed.union(failed)):
            ready_nodes = graph.ready(completed.union(failed))
            if not ready_nodes:
                break  # Deadlock or done
                
            # Form a batch
            batch = ready_nodes
            
            # Execute batch
            batch_result = self._executor.execute_batch(batch, context)
            
            completed.update(batch_result.completed)
            failed.update(batch_result.failed)
            
            # If fail_fast and we have failures, stop the whole graph
            if self._executor._failure_policy == FailurePolicy.FAIL_FAST and batch_result.failed:
                break
                
        return completed, failed