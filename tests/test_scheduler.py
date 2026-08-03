"""Comprehensive tests for the Parallel Scheduler Platform (Sprint 8.4)."""

import pytest
from dataclasses import dataclass, field
from typing import Any
from pathlib import Path

from eag.events import EventBus
from eag.scheduler import (
    Dispatcher,
    DispatcherError,
    ExecutionBatch,
    QueueError,
    ReadyQueue,
    SchedulerError,
    SchedulerMetrics,
    SchedulerRuntime,
    SchedulingDecision,
    SchedulingPolicy,
    WorkerAssignment,
)
from eag.task_graph import TaskEdge, TaskGraph, TaskNode
from eag.workers import (
    WorkerContext,
    WorkerHealthManager,
    WorkerManager,
    WorkerNotFoundError,
    WorkerProfile,
    WorkerRegistry,
    WorkerResult,
    WorkerRole,
    WorkerRuntime,
    WorkerState,
)
from eag.workers.enums import TaskPriority


# --- Mocks & Fixtures ---

class MockWorker:
    def __init__(self, profile: WorkerProfile, fail: bool = False, delay: float = 0.0) -> None:
        self._profile = profile
        self._fail = fail
        self._delay = delay

    @property
    def profile(self) -> WorkerProfile:
        return self._profile

    def supports(self, task: TaskNode) -> bool:
        if not task.required_capability:
            return True
        return task.required_capability in self._profile.capabilities

    def estimate(self, task: TaskNode) -> float:
        return 1.0

    def execute(self, task: TaskNode, context: WorkerContext) -> WorkerResult:
        import time
        if self._delay > 0:
            time.sleep(self._delay)
        if self._fail:
            raise RuntimeError("Mock execution failed")
        return WorkerResult(
            worker_id=self._profile.id,
            task_id=task.id,
            success=True,
            summary=f"Task {task.id} completed"
        )

@dataclass
class MockEventBus:
    published_events: list[Any] = field(default_factory=list)
    def publish(self, event: Any) -> None:
        self.published_events.append(event)

@pytest.fixture
def event_bus() -> MockEventBus:
    return MockEventBus()

@pytest.fixture
def health_manager() -> WorkerHealthManager:
    return WorkerHealthManager()

@pytest.fixture
def registry() -> WorkerRegistry:
    reg = WorkerRegistry()
    reg.register(MockWorker(WorkerProfile(id="w1", name="Alice", capabilities=("python",), preferred_capabilities=("python",))))
    reg.register(MockWorker(WorkerProfile(id="w2", name="Bob", capabilities=("react",))))
    reg.register(MockWorker(WorkerProfile(id="w3", name="Charlie", capabilities=("python", "pytest"))))
    return reg

@pytest.fixture
def manager(registry: WorkerRegistry, health_manager: WorkerHealthManager) -> WorkerManager:
    return WorkerManager(registry=registry, health_manager=health_manager)

@pytest.fixture
def worker_runtime(event_bus: MockEventBus, health_manager: WorkerHealthManager, manager: WorkerManager) -> WorkerRuntime:
    return WorkerRuntime(event_bus=event_bus, health_manager=health_manager, manager=manager)

@pytest.fixture
def scheduler_runtime(event_bus: MockEventBus, manager: WorkerManager, worker_runtime: WorkerRuntime) -> SchedulerRuntime:
    return SchedulerRuntime(event_bus=event_bus, manager=manager, worker_runtime=worker_runtime)

@pytest.fixture
def context() -> WorkerContext:
    return WorkerContext(run_id="r1", goal="Test", workspace=Path("/tmp"))

def make_node(node_id: str = "n1", cap: str = "python", priority: TaskPriority = TaskPriority.NORMAL) -> TaskNode:
    return TaskNode(id=node_id, title=f"Task {node_id}", required_capability=cap, priority=priority)

def make_edge(source: str, target: str) -> TaskEdge:
    return TaskEdge(source=source, target=target)


# --- Model Tests ---

class TestSchedulerModels:
    def test_execution_batch_immutable(self) -> None:
        b = ExecutionBatch()
        with pytest.raises(Exception):
            b.parallelism = 5  # type: ignore[misc]

    def test_execution_batch_defaults(self) -> None:
        b = ExecutionBatch()
        assert b.assignments == ()
        assert b.parallelism == 0

    def test_execution_batch_parallelism(self) -> None:
        a1 = WorkerAssignment(worker_id="w1", task_id="t1")
        b = ExecutionBatch(assignments=(a1,))
        assert b.parallelism == 1

    def test_execution_batch_metadata(self) -> None:
        b = ExecutionBatch(metadata={"k": "v"})
        assert b.metadata["k"] == "v"

    def test_execution_batch_invalid_metadata(self) -> None:
        with pytest.raises(TypeError):
            ExecutionBatch(metadata="bad")  # type: ignore[arg-type]

    def test_scheduling_decision_immutable(self) -> None:
        d = SchedulingDecision()
        with pytest.raises(Exception):
            d.policy = SchedulingPolicy.ROUND_ROBIN  # type: ignore[misc]

    def test_scheduling_decision_defaults(self) -> None:
        d = SchedulingDecision()
        assert d.policy == SchedulingPolicy.BEST_CAPABILITY
        assert d.ready_tasks == ()

    def test_scheduling_decision_metadata(self) -> None:
        d = SchedulingDecision(metadata={"k": "v"})
        assert d.metadata["k"] == "v"

    def test_worker_assignment_immutable(self) -> None:
        a = WorkerAssignment(worker_id="w1", task_id="t1")
        with pytest.raises(Exception):
            a.worker_id = "w2"  # type: ignore[misc]

    def test_worker_assignment_defaults(self) -> None:
        a = WorkerAssignment(worker_id="w1", task_id="t1")
        assert a.reason == ""
        assert not a.metadata

    def test_scheduler_metrics_immutable(self) -> None:
        m = SchedulerMetrics()
        with pytest.raises(Exception):
            m.total_cycles = 5  # type: ignore[misc]

    def test_scheduler_metrics_defaults(self) -> None:
        m = SchedulerMetrics()
        assert m.total_cycles == 0
        assert m.max_parallelism == 0

    def test_policy_values(self) -> None:
        assert SchedulingPolicy.BEST_CAPABILITY == "best_capability"
        assert SchedulingPolicy.ROUND_ROBIN == "round_robin"

    def test_execution_batch_hashable(self) -> None:
        b = ExecutionBatch()
        assert hash(b) is not None

    def test_scheduling_decision_hashable(self) -> None:
        d = SchedulingDecision()
        assert hash(d) is not None

    def test_worker_assignment_hashable(self) -> None:
        a = WorkerAssignment(worker_id="w1", task_id="t1")
        assert hash(a) is not None

    def test_execution_batch_invalid_assignments(self) -> None:
        with pytest.raises(TypeError):
            ExecutionBatch(assignments=[])  # type: ignore[arg-type]

    def test_execution_batch_id_generated(self) -> None:
        b1 = ExecutionBatch()
        b2 = ExecutionBatch()
        assert b1.id != b2.id

    def test_scheduling_decision_id_generated(self) -> None:
        d1 = SchedulingDecision()
        d2 = SchedulingDecision()
        assert d1.id != d2.id

    def test_worker_assignment_id_generated(self) -> None:
        a1 = WorkerAssignment(worker_id="w1", task_id="t1")
        a2 = WorkerAssignment(worker_id="w1", task_id="t1")
        assert a1.assignment_id != a2.assignment_id

    def test_execution_batch_equality(self) -> None:
        b1 = ExecutionBatch(id="b1")
        b2 = ExecutionBatch(id="b1")
        assert b1 == b2

    def test_scheduling_decision_equality(self) -> None:
        d1 = SchedulingDecision(id="d1")
        d2 = SchedulingDecision(id="d1")
        assert d1 == d2

    def test_worker_assignment_equality(self) -> None:
        a1 = WorkerAssignment(assignment_id="a1", worker_id="w1", task_id="t1")
        a2 = WorkerAssignment(assignment_id="a1", worker_id="w1", task_id="t1")
        assert a1 == a2

    def test_error_hierarchy(self) -> None:
        assert issubclass(DispatcherError, SchedulerError)
        assert issubclass(QueueError, SchedulerError)

    def test_scheduler_error_raises(self) -> None:
        with pytest.raises(SchedulerError):
            raise SchedulerError("Failed")

    def test_queue_error_raises(self) -> None:
        with pytest.raises(QueueError):
            raise QueueError("Failed")


# --- Ready Queue Tests ---

class TestReadyQueue:
    def test_empty_queue(self) -> None:
        q = ReadyQueue()
        assert q.empty() is True
        assert q.size() == 0

    def test_push_single_task(self) -> None:
        q = ReadyQueue()
        q.push(make_node("t1"))
        assert q.size() == 1
        assert q.empty() is False

    def test_pop_single_task(self) -> None:
        q = ReadyQueue()
        t1 = make_node("t1")
        q.push(t1)
        popped = q.pop()
        assert popped == t1
        assert q.empty() is True

    def test_peek_does_not_remove(self) -> None:
        q = ReadyQueue()
        t1 = make_node("t1")
        q.push(t1)
        peeked = q.peek()
        assert peeked == t1
        assert q.size() == 1

    def test_pop_empty_raises(self) -> None:
        q = ReadyQueue()
        with pytest.raises(QueueError):
            q.pop()

    def test_peek_empty_raises(self) -> None:
        q = ReadyQueue()
        with pytest.raises(QueueError):
            q.peek()

    def test_priority_ordering(self) -> None:
        q = ReadyQueue()
        q.push(make_node("t1", priority=TaskPriority.LOW))
        q.push(make_node("t2", priority=TaskPriority.HIGH))
        q.push(make_node("t3", priority=TaskPriority.CRITICAL))
        
        assert q.pop().id == "t3"
        assert q.pop().id == "t2"
        assert q.pop().id == "t1"

    def test_deterministic_ordering_same_priority(self) -> None:
        q = ReadyQueue()
        q.push(make_node("t3"))
        q.push(make_node("t1"))
        q.push(make_node("t2"))
        
        assert q.pop().id == "t1"
        assert q.pop().id == "t2"
        assert q.pop().id == "t3"

    def test_duplicate_rejection(self) -> None:
        q = ReadyQueue()
        q.push(make_node("t1"))
        with pytest.raises(QueueError):
            q.push(make_node("t1"))

    def test_remove_existing(self) -> None:
        q = ReadyQueue()
        q.push(make_node("t1"))
        assert q.remove("t1") is True
        assert q.empty() is True

    def test_remove_missing(self) -> None:
        q = ReadyQueue()
        assert q.remove("missing") is False

    def test_contains_existing(self) -> None:
        q = ReadyQueue()
        q.push(make_node("t1"))
        assert q.contains("t1") is True

    def test_contains_missing(self) -> None:
        q = ReadyQueue()
        assert q.contains("missing") is False

    def test_clear(self) -> None:
        q = ReadyQueue()
        q.push(make_node("t1"))
        q.push(make_node("t2"))
        q.clear()
        assert q.empty() is True

    def test_mixed_priority_and_id(self) -> None:
        q = ReadyQueue()
        q.push(make_node("t1", priority=TaskPriority.HIGH))
        q.push(make_node("t2", priority=TaskPriority.HIGH))
        q.push(make_node("t3", priority=TaskPriority.LOW))
        
        assert q.pop().id == "t1"
        assert q.pop().id == "t2"
        assert q.pop().id == "t3"

    def test_peek_after_pop(self) -> None:
        q = ReadyQueue()
        q.push(make_node("t1"))
        q.push(make_node("t2"))
        q.pop()
        assert q.peek().id == "t2"

    def test_remove_middle(self) -> None:
        q = ReadyQueue()
        q.push(make_node("t1"))
        q.push(make_node("t2"))
        q.push(make_node("t3"))
        q.remove("t2")
        assert q.size() == 2
        assert not q.contains("t2")

    def test_pop_all(self) -> None:
        q = ReadyQueue()
        q.push(make_node("t1"))
        q.push(make_node("t2"))
        q.pop()
        q.pop()
        with pytest.raises(QueueError):
            q.pop()

    def test_size_after_operations(self) -> None:
        q = ReadyQueue()
        q.push(make_node("t1"))
        q.push(make_node("t2"))
        assert q.size() == 2
        q.pop()
        assert q.size() == 1
        q.clear()
        assert q.size() == 0

    def test_empty_returns_bool(self) -> None:
        q = ReadyQueue()
        assert isinstance(q.empty(), bool)

    def test_size_returns_int(self) -> None:
        q = ReadyQueue()
        assert isinstance(q.size(), int)

    def test_contains_returns_bool(self) -> None:
        q = ReadyQueue()
        assert isinstance(q.contains("t1"), bool)

    def test_remove_returns_bool(self) -> None:
        q = ReadyQueue()
        assert isinstance(q.remove("t1"), bool)

    def test_push_multiple_mixed(self) -> None:
        q = ReadyQueue()
        q.push(make_node("t1", priority=TaskPriority.HIGH))
        q.push(make_node("t2", priority=TaskPriority.LOW))
        q.push(make_node("t3", priority=TaskPriority.NORMAL))
        q.push(make_node("t4", priority=TaskPriority.CRITICAL))
        
        assert q.pop().id == "t4"
        assert q.pop().id == "t1"
        assert q.pop().id == "t3"
        assert q.pop().id == "t2"

    def test_push_same_id_different_priority(self) -> None:
        q = ReadyQueue()
        q.push(make_node("t1", priority=TaskPriority.HIGH))
        with pytest.raises(QueueError):
            q.push(make_node("t1", priority=TaskPriority.LOW))

    def test_priority_order_complex(self) -> None:
        q = ReadyQueue()
        q.push(make_node("n1", priority=TaskPriority.NORMAL))
        q.push(make_node("c1", priority=TaskPriority.CRITICAL))
        q.push(make_node("l1", priority=TaskPriority.LOW))
        q.push(make_node("h1", priority=TaskPriority.HIGH))
        q.push(make_node("c2", priority=TaskPriority.CRITICAL))
        
        assert q.pop().id == "c1"
        assert q.pop().id == "c2"
        assert q.pop().id == "h1"
        assert q.pop().id == "n1"
        assert q.pop().id == "l1"

    def test_peek_stays_same(self) -> None:
        q = ReadyQueue()
        q.push(make_node("t1"))
        q.push(make_node("t2"))
        assert q.peek().id == "t1"
        assert q.peek().id == "t1"

    def test_remove_clears_contains(self) -> None:
        q = ReadyQueue()
        q.push(make_node("t1"))
        q.remove("t1")
        assert q.contains("t1") is False

    def test_push_does_not_mutate_input(self) -> None:
        q = ReadyQueue()
        t1 = make_node("t1")
        q.push(t1)
        assert q.peek() == t1

    def test_queue_isolation(self) -> None:
        q1 = ReadyQueue()
        q2 = ReadyQueue()
        q1.push(make_node("t1"))
        assert q2.empty() is True

    def test_clear_already_empty(self) -> None:
        q = ReadyQueue()
        q.clear()
        assert q.empty() is True

    def test_remove_from_empty(self) -> None:
        q = ReadyQueue()
        assert q.remove("t1") is False

    def test_pop_preserves_priority(self) -> None:
        q = ReadyQueue()
        q.push(make_node("t1", priority=TaskPriority.LOW))
        q.push(make_node("t2", priority=TaskPriority.HIGH))
        popped = q.pop()
        assert popped.priority == TaskPriority.HIGH

    def test_large_queue(self) -> None:
        q = ReadyQueue()
        for i in range(100):
            q.push(make_node(f"t{i}"))
        assert q.size() == 100
        for i in range(100):
            q.pop()
        assert q.empty() is True

    def test_large_queue_priority(self) -> None:
        q = ReadyQueue()
        for i in range(50):
            q.push(make_node(f"t{i}", priority=TaskPriority.LOW))
        for i in range(50):
            q.push(make_node(f"t{i+50}", priority=TaskPriority.HIGH))
            
        for i in range(50):
            assert q.pop().priority == TaskPriority.HIGH


# --- Dispatcher Tests ---

class TestDispatcher:
    def test_dispatch_success(self, manager: WorkerManager) -> None:
        d = Dispatcher(manager)
        task = make_node("t1", cap="python")
        assignment = d.dispatch(task)
        assert assignment is not None
        assert assignment.task_id == "t1"
        assert assignment.worker_id == "w1"

    def test_dispatch_no_worker_available(self, manager: WorkerManager) -> None:
        d = Dispatcher(manager)
        task = make_node("t1", cap="rust")
        assignment = d.dispatch(task)
        assert assignment is None

    def test_dispatch_assigns_worker(self, manager: WorkerManager) -> None:
        d = Dispatcher(manager)
        task = make_node("t1", cap="python")
        d.dispatch(task)
        assert manager.get_state("w1") == WorkerState.ASSIGNED

    def test_dispatch_busy_worker_skipped(self, manager: WorkerManager) -> None:
        d = Dispatcher(manager)
        task1 = make_node("t1", cap="python")
        task2 = make_node("t2", cap="python")
        
        d.dispatch(task1)
        assignment2 = d.dispatch(task2)
        assert assignment2 is not None
        assert assignment2.worker_id == "w3"

    def test_dispatch_all_busy(self, manager: WorkerManager) -> None:
        d = Dispatcher(manager)
        manager.assign("w1", "t0")
        manager.assign("w3", "t0")
        
        task = make_node("t1", cap="python")
        assignment = d.dispatch(task)
        assert assignment is None

    def test_release(self, manager: WorkerManager) -> None:
        d = Dispatcher(manager)
        d.dispatch(make_node("t1", cap="python"))
        d.release("w1")
        assert manager.get_state("w1") == WorkerState.IDLE

    def test_best_worker_selected(self, manager: WorkerManager) -> None:
        d = Dispatcher(manager)
        task = make_node("t1", cap="python")
        assignment = d.dispatch(task)
        assert assignment.worker_id == "w1"

    def test_unhealthy_worker_skipped(self, registry: WorkerRegistry, health_manager: WorkerHealthManager) -> None:
        health_manager.record_failure("w1")
        health_manager.record_failure("w1")
        health_manager.record_failure("w1")
        mgr = WorkerManager(registry=registry, health_manager=health_manager)
        d = Dispatcher(mgr)
        
        task = make_node("t1", cap="python")
        assignment = d.dispatch(task)
        assert assignment.worker_id == "w3"

    def test_assignment_has_correct_ids(self, manager: WorkerManager) -> None:
        d = Dispatcher(manager)
        task = make_node("t1", cap="python")
        assignment = d.dispatch(task)
        assert assignment.worker_id == "w1"
        assert assignment.task_id == "t1"

    def test_release_missing_worker(self, manager: WorkerManager) -> None:
        d = Dispatcher(manager)
        with pytest.raises(WorkerNotFoundError):
            d.release("missing")

    def test_dispatch_assigns_first_available(self, manager: WorkerManager) -> None:
        manager.assign("w1", "t0")
        d = Dispatcher(manager)
        task = make_node("t1", cap="python")
        assignment = d.dispatch(task)
        assert assignment.worker_id == "w3"

    def test_dispatch_multiple_different_capabilities(self, manager: WorkerManager) -> None:
        d = Dispatcher(manager)
        task_py = make_node("t1", cap="python")
        task_react = make_node("t2", cap="react")
        
        assign_py = d.dispatch(task_py)
        assign_react = d.dispatch(task_react)
        
        assert assign_py.worker_id == "w1"
        assert assign_react.worker_id == "w2"

    def test_dispatch_no_cap_required(self, manager: WorkerManager) -> None:
        d = Dispatcher(manager)
        task = make_node("t1", cap="")
        assignment = d.dispatch(task)
        assert assignment is not None
        assert assignment.worker_id == "w1"


# --- Scheduler Runtime Tests ---

class TestSchedulerRuntime:
    def test_execute_empty_graph(self, scheduler_runtime: SchedulerRuntime, context: WorkerContext) -> None:
        graph = TaskGraph()
        completed, failed = scheduler_runtime.execute_graph(graph, context)
        assert len(completed) == 0
        assert len(failed) == 0

    def test_execute_single_node(self, scheduler_runtime: SchedulerRuntime, context: WorkerContext) -> None:
        n1 = make_node("n1")
        graph = TaskGraph(nodes=(n1,))
        
        completed, failed = scheduler_runtime.execute_graph(graph, context)
        
        assert len(completed) == 1
        assert "n1" in completed
        assert len(failed) == 0

    def test_execute_linear_graph(self, scheduler_runtime: SchedulerRuntime, context: WorkerContext) -> None:
        n1, n2, n3 = make_node("n1"), make_node("n2"), make_node("n3")
        graph = TaskGraph(nodes=(n1, n2, n3), edges=(make_edge("n1", "n2"), make_edge("n2", "n3")))
        
        completed, failed = scheduler_runtime.execute_graph(graph, context)
        
        assert len(completed) == 3
        assert len(failed) == 0

    def test_execute_diamond_graph(self, scheduler_runtime: SchedulerRuntime, context: WorkerContext) -> None:
        n1, n2, n3, n4 = (make_node(f"n{i}") for i in range(1, 5))
        edges = (make_edge("n1", "n2"), make_edge("n1", "n3"), make_edge("n2", "n4"), make_edge("n3", "n4"))
        graph = TaskGraph(nodes=(n1, n2, n3, n4), edges=edges)
        
        completed, failed = scheduler_runtime.execute_graph(graph, context)
        
        assert len(completed) == 4
        assert len(failed) == 0

    def test_execute_multiple_roots(self, scheduler_runtime: SchedulerRuntime, context: WorkerContext) -> None:
        n1, n2, n3 = make_node("n1"), make_node("n2"), make_node("n3")
        graph = TaskGraph(nodes=(n1, n2, n3))
        
        completed, failed = scheduler_runtime.execute_graph(graph, context)
        
        assert len(completed) == 3
        assert len(failed) == 0

    def test_execute_with_failure(self, registry: WorkerRegistry, event_bus: MockEventBus, context: WorkerContext) -> None:
        # Give the failing worker an exclusive capability so no other worker steals the task
        registry.register(MockWorker(WorkerProfile(id="w_fail", name="Fail", capabilities=("broken",)), fail=True))
        hm = WorkerHealthManager()
        mgr = WorkerManager(registry=registry, health_manager=hm)
        wrt = WorkerRuntime(event_bus=event_bus, health_manager=hm, manager=mgr)
        rt = SchedulerRuntime(event_bus=event_bus, manager=mgr, worker_runtime=wrt)
        
        # Require the exclusive capability so the dispatcher must pick the failing worker
        n1 = make_node("n1", cap="broken")
        n2 = make_node("n2", cap="broken")
        graph = TaskGraph(nodes=(n1, n2), edges=(make_edge("n1", "n2"),))
        
        completed, failed = rt.execute_graph(graph, context)
        
        assert len(failed) > 0
        assert "n1" in failed or "n2" in failed


    def test_metrics_completed_tasks(self, scheduler_runtime: SchedulerRuntime, context: WorkerContext) -> None:
        n1, n2 = make_node("n1"), make_node("n2")
        graph = TaskGraph(nodes=(n1, n2))
        
        scheduler_runtime.execute_graph(graph, context)
        
        metrics = scheduler_runtime._metrics
        assert metrics.tasks_completed == 2

    def test_metrics_batches_executed(self, scheduler_runtime: SchedulerRuntime, context: WorkerContext) -> None:
        n1, n2 = make_node("n1"), make_node("n2")
        graph = TaskGraph(nodes=(n1, n2))
        
        scheduler_runtime.execute_graph(graph, context)
        
        metrics = scheduler_runtime._metrics
        assert metrics.batches_executed == 1

    def test_metrics_max_parallelism(self, scheduler_runtime: SchedulerRuntime, context: WorkerContext) -> None:
        n1, n2, n3 = make_node("n1"), make_node("n2"), make_node("n3")
        graph = TaskGraph(nodes=(n1, n2, n3))
        
        scheduler_runtime.execute_graph(graph, context)
        
        metrics = scheduler_runtime._metrics
        assert metrics.max_parallelism == 2

    def test_deterministic_scheduling(self, scheduler_runtime: SchedulerRuntime, context: WorkerContext) -> None:
        n1, n2, n3 = make_node("n1"), make_node("n2"), make_node("n3")
        graph = TaskGraph(nodes=(n1, n2, n3))
        
        completed1, _ = scheduler_runtime.execute_graph(graph, context)
        scheduler_runtime2 = SchedulerRuntime(
            event_bus=MockEventBus(),
            manager=scheduler_runtime._manager,
            worker_runtime=scheduler_runtime._worker_runtime
        )
        completed2, _ = scheduler_runtime2.execute_graph(graph, context)
        
        assert completed1 == completed2

    def test_dependency_unlock(self, scheduler_runtime: SchedulerRuntime, context: WorkerContext) -> None:
        n1, n2 = make_node("n1"), make_node("n2")
        graph = TaskGraph(nodes=(n1, n2), edges=(make_edge("n1", "n2"),))
        
        completed, _ = scheduler_runtime.execute_graph(graph, context)
        
        assert "n1" in completed
        assert "n2" in completed

    def test_priority_scheduling(self, scheduler_runtime: SchedulerRuntime, context: WorkerContext) -> None:
        n1 = make_node("n1", priority=TaskPriority.LOW)
        n2 = make_node("n2", priority=TaskPriority.HIGH)
        graph = TaskGraph(nodes=(n1, n2))
        
        completed, _ = scheduler_runtime.execute_graph(graph, context)
        
        assert len(completed) == 2

    def test_worker_release_after_execution(self, scheduler_runtime: SchedulerRuntime, context: WorkerContext) -> None:
        n1 = make_node("n1")
        graph = TaskGraph(nodes=(n1,))
        
        scheduler_runtime.execute_graph(graph, context)
        
        assert scheduler_runtime._manager.get_state("w1") == WorkerState.IDLE

    def test_events_published(self, scheduler_runtime: SchedulerRuntime, event_bus: MockEventBus, context: WorkerContext) -> None:
        n1 = make_node("n1")
        graph = TaskGraph(nodes=(n1,))
        
        scheduler_runtime.execute_graph(graph, context)
        
        assert len(event_bus.published_events) > 0

    def test_graph_not_mutated(self, scheduler_runtime: SchedulerRuntime, context: WorkerContext) -> None:
        n1, n2 = make_node("n1"), make_node("n2")
        graph = TaskGraph(nodes=(n1, n2), edges=(make_edge("n1", "n2"),))
        
        original_nodes = graph.nodes
        original_edges = graph.edges
        
        scheduler_runtime.execute_graph(graph, context)
        
        assert graph.nodes == original_nodes
        assert graph.edges == original_edges

    def test_execution_with_multiple_worker_types(self, scheduler_runtime: SchedulerRuntime, context: WorkerContext) -> None:
        n1 = make_node("n1", cap="python")
        n2 = make_node("n2", cap="react")
        n3 = make_node("n3", cap="pytest")
        graph = TaskGraph(nodes=(n1, n2, n3))
        
        completed, _ = scheduler_runtime.execute_graph(graph, context)
        
        assert len(completed) == 3

    def test_parallel_batch_execution(self, scheduler_runtime: SchedulerRuntime, context: WorkerContext) -> None:
        n1 = make_node("n1", cap="python")
        n2 = make_node("n2", cap="react")
        graph = TaskGraph(nodes=(n1, n2))
        
        completed, _ = scheduler_runtime.execute_graph(graph, context)
        
        assert len(completed) == 2
        metrics = scheduler_runtime._metrics
        assert metrics.batches_executed == 1
        assert metrics.max_parallelism == 2

    def test_deadlock_detection_empty_queue(self, scheduler_runtime: SchedulerRuntime, context: WorkerContext) -> None:
        n1 = make_node("n1", cap="rust")
        graph = TaskGraph(nodes=(n1,))
        
        completed, failed = scheduler_runtime.execute_graph(graph, context)
        
        assert len(completed) == 0
        assert len(failed) == 0

    def test_metrics_average_batch_size(self, scheduler_runtime: SchedulerRuntime, context: WorkerContext) -> None:
        n1, n2, n3 = make_node("n1"), make_node("n2"), make_node("n3")
        graph = TaskGraph(nodes=(n1, n2, n3))
        
        scheduler_runtime.execute_graph(graph, context)
        
        metrics = scheduler_runtime._metrics
        assert metrics.average_batch_size == 1.5
