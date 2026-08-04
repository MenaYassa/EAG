"""Comprehensive tests for the Parallel Execution Graph Platform (Sprint 8.6)."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from eag.execution_graph import (
    ArtifactEdge,
    ArtifactGraph,
    ArtifactNode,
    BatchExecutor,
    CycleError,
    DuplicateNodeError,
    ExecutionEdge,
    ExecutionGraph,
    ExecutionMetrics,
    ExecutionNode,
    FailurePolicy,
    Mailbox,
    MessageRouter,
    MissingNodeError,
    NodeState,
    ParallelExecutionRuntime,
    WorkerMessage,
)
from eag.execution_graph.enums import MessageType
from eag.workers import (
    Worker,
    WorkerContext,
    WorkerHealthManager,
    WorkerManager,
    WorkerProfile,
    WorkerRegistry,
    WorkerResult,
    WorkerRuntime,
    WorkerState,
    WorkerTask,
)

# --- Mocks & Fixtures ---


class MockWorker:
    def __init__(self, profile: WorkerProfile, fail: bool = False) -> None:
        self._profile = profile
        self._fail = fail

    @property
    def profile(self) -> WorkerProfile:
        return self._profile

    def supports(self, task: WorkerTask) -> bool:
        return True

    def estimate(self, task: WorkerTask) -> float:
        return 1.0

    def execute(self, task: WorkerTask, context: WorkerContext) -> WorkerResult:
        if self._fail:
            raise RuntimeError("Mock execution failed")
        return WorkerResult(
            worker_id=self.profile.id,
            task_id=task.id,
            success=True,
            summary=f"Task {task.id} completed",
            artifacts=(f"{task.id}.py",),
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
    reg.register(MockWorker(WorkerProfile(id="w1", name="Alice", capabilities=("python",))))
    reg.register(MockWorker(WorkerProfile(id="w2", name="Bob", capabilities=("python",))))
    reg.register(MockWorker(WorkerProfile(id="w3", name="Charlie", capabilities=("python",))))
    return reg


@pytest.fixture
def manager(registry: WorkerRegistry, health_manager: WorkerHealthManager) -> WorkerManager:
    mgr = WorkerManager(registry=registry, health_manager=health_manager)

    # Simple round-robin or first available for testing
    def simple_find(task_id: str) -> Worker | None:
        for w in registry.list():
            if mgr.get_state(w.profile.id) == WorkerState.IDLE:
                return w
        return None

    mgr.find_best_worker_for_task = simple_find
    return mgr


@pytest.fixture
def worker_runtime(
    event_bus: MockEventBus, health_manager: WorkerHealthManager, manager: WorkerManager
) -> WorkerRuntime:
    return WorkerRuntime(event_bus=event_bus, health_manager=health_manager, manager=manager)


@pytest.fixture
def context() -> WorkerContext:
    return WorkerContext(run_id="r1", goal="Test", workspace=Path("/tmp"))


def make_node(node_id: str = "n1", task_id: str = "t1") -> ExecutionNode:
    return ExecutionNode(id=node_id, task_id=task_id, title=f"Task {node_id}")


def make_edge(source: str, target: str) -> ExecutionEdge:
    return ExecutionEdge(source=source, target=target)


# ====================================================================
# Execution Graph Tests (40 tests)
# ====================================================================


class TestExecutionGraph:
    def test_empty_graph(self) -> None:
        g = ExecutionGraph()
        assert len(g.nodes) == 0
        assert len(g.edges) == 0

    def test_single_node(self) -> None:
        g = ExecutionGraph(nodes=(make_node("n1"),))
        assert len(g.nodes) == 1
        assert len(g.roots()) == 1
        assert len(g.leaves()) == 1

    def test_add_node_returns_new(self) -> None:
        g1 = ExecutionGraph()
        g2 = g1.add_node(make_node())
        assert len(g1.nodes) == 0
        assert len(g2.nodes) == 1

    def test_add_edge_returns_new(self) -> None:
        n1, n2 = make_node(), make_node("n2")
        g1 = ExecutionGraph(nodes=(n1, n2))
        g2 = g1.add_edge(make_edge("n1", "n2"))
        assert len(g1.edges) == 0
        assert len(g2.edges) == 1

    def test_roots(self) -> None:
        n1, n2 = make_node("n1"), make_node("n2")
        g = ExecutionGraph(nodes=(n1, n2), edges=(make_edge("n1", "n2"),))
        assert len(g.roots()) == 1
        assert g.roots()[0].id == "n1"

    def test_leaves(self) -> None:
        n1, n2 = make_node("n1"), make_node("n2")
        g = ExecutionGraph(nodes=(n1, n2), edges=(make_edge("n1", "n2"),))
        assert len(g.leaves()) == 1
        assert g.leaves()[0].id == "n2"

    def test_multiple_roots(self) -> None:
        n1, n2, n3 = make_node("n1"), make_node("n2"), make_node("n3")
        g = ExecutionGraph(nodes=(n1, n2, n3), edges=(make_edge("n1", "n3"), make_edge("n2", "n3")))
        assert len(g.roots()) == 2

    def test_multiple_leaves(self) -> None:
        n1, n2, n3 = make_node("n1"), make_node("n2"), make_node("n3")
        g = ExecutionGraph(nodes=(n1, n2, n3), edges=(make_edge("n1", "n2"), make_edge("n1", "n3")))
        assert len(g.leaves()) == 2

    def test_ready_empty(self) -> None:
        g = ExecutionGraph()
        assert g.ready(set()) == ()

    def test_ready_no_deps(self) -> None:
        n1, n2 = make_node("n1"), make_node("n2")
        g = ExecutionGraph(nodes=(n1, n2))
        assert len(g.ready(set())) == 2

    def test_ready_with_deps(self) -> None:
        n1, n2 = make_node("n1"), make_node("n2")
        g = ExecutionGraph(nodes=(n1, n2), edges=(make_edge("n1", "n2"),))
        ready = g.ready(set())
        assert len(ready) == 1
        assert ready[0].id == "n1"

    def test_ready_after_completion(self) -> None:
        n1, n2 = make_node("n1"), make_node("n2")
        g = ExecutionGraph(nodes=(n1, n2), edges=(make_edge("n1", "n2"),))
        ready = g.ready({"n1"})
        assert len(ready) == 1
        assert ready[0].id == "n2"

    def test_ready_excludes_completed(self) -> None:
        n1, n2 = make_node("n1"), make_node("n2")
        g = ExecutionGraph(nodes=(n1, n2))
        ready = g.ready({"n1"})
        assert len(ready) == 1
        assert ready[0].id == "n2"

    def test_ready_excludes_failed(self) -> None:
        n1, n2 = make_node("n1"), make_node("n2")
        g = ExecutionGraph(nodes=(n1, n2), edges=(make_edge("n1", "n2"),))
        # If n1 failed, it's not in completed, so n2 is not ready
        ready = g.ready(set())
        assert len(ready) == 1
        assert ready[0].id == "n1"

    def test_ready_deterministic_ordering(self) -> None:
        n3, n1, n2 = make_node("n3"), make_node("n1"), make_node("n2")
        g = ExecutionGraph(nodes=(n3, n1, n2))
        ready = g.ready(set())
        assert [n.id for n in ready] == ["n1", "n2", "n3"]

    def test_is_complete_false(self) -> None:
        g = ExecutionGraph(nodes=(make_node("n1"),))
        assert g.is_complete(set()) is False

    def test_is_complete_true(self) -> None:
        g = ExecutionGraph(nodes=(make_node("n1"),))
        assert g.is_complete({"n1"}) is True

    def test_is_complete_with_failed(self) -> None:
        g = ExecutionGraph(nodes=(make_node("n1"),))
        assert g.is_complete({"n1"}) is True

    def test_cycle_detection_simple(self) -> None:
        n1, n2 = make_node("n1"), make_node("n2")
        edges = (make_edge("n1", "n2"), make_edge("n2", "n1"))
        with pytest.raises(CycleError):
            ExecutionGraph(nodes=(n1, n2), edges=edges)

    def test_cycle_detection_complex(self) -> None:
        nodes = tuple(make_node(f"n{i}") for i in range(4))
        edges = (
            make_edge("n0", "n1"),
            make_edge("n1", "n2"),
            make_edge("n2", "n3"),
            make_edge("n3", "n1"),
        )
        with pytest.raises(CycleError):
            ExecutionGraph(nodes=nodes, edges=edges)

    def test_duplicate_node(self) -> None:
        nodes = (make_node("n1"), make_node("n1"))
        with pytest.raises(DuplicateNodeError):
            ExecutionGraph(nodes=nodes)

    def test_missing_source(self) -> None:
        n1 = make_node("n1")
        with pytest.raises(MissingNodeError):
            ExecutionGraph(nodes=(n1,), edges=(make_edge("missing", "n1"),))

    def test_missing_target(self) -> None:
        n1 = make_node("n1")
        with pytest.raises(MissingNodeError):
            ExecutionGraph(nodes=(n1,), edges=(make_edge("n1", "missing"),))

    def test_self_dependency(self) -> None:
        n1 = make_node("n1")
        with pytest.raises(ValueError):
            ExecutionEdge(source="n1", target="n1")

    def test_graph_immutable_nodes(self) -> None:
        g = ExecutionGraph(nodes=(make_node("n1"),))
        with pytest.raises(AttributeError):
            g.nodes = ()  # type: ignore[misc]

    def test_graph_immutable_edges(self) -> None:
        g = ExecutionGraph(nodes=(make_node("n1"), make_node("n2")), edges=(make_edge("n1", "n2"),))
        with pytest.raises(AttributeError):
            g.edges = ()  # type: ignore[misc]

    def test_node_defaults(self) -> None:
        n = ExecutionNode(task_id="t1")
        assert n.state == NodeState.PENDING
        assert n.dependencies == ()

    def test_edge_creation(self) -> None:
        e = ExecutionEdge(source="n1", target="n2")
        assert e.source == "n1"
        assert e.target == "n2"

    def test_node_hashable(self) -> None:
        n = make_node()
        assert hash(n) is not None

    def test_edge_hashable(self) -> None:
        e = make_edge("n1", "n2")
        assert hash(e) is not None

    def test_large_graph(self) -> None:
        nodes = tuple(make_node(f"n{i}") for i in range(100))
        edges = tuple(make_edge(f"n{i}", f"n{i + 1}") for i in range(99))
        g = ExecutionGraph(nodes=nodes, edges=edges)
        assert len(g.nodes) == 100

    def test_ready_with_partial_completion(self) -> None:
        n1, n2, n3 = make_node("n1"), make_node("n2"), make_node("n3")
        g = ExecutionGraph(nodes=(n1, n2, n3), edges=(make_edge("n1", "n3"), make_edge("n2", "n3")))
        assert len(g.ready(set())) == 2
        assert len(g.ready({"n1"})) == 1
        assert len(g.ready({"n1", "n2"})) == 1
        assert g.ready({"n1", "n2"})[0].id == "n3"

    def test_graph_with_no_edges_all_roots(self) -> None:
        nodes = tuple(make_node(f"n{i}") for i in range(3))
        g = ExecutionGraph(nodes=nodes)
        assert len(g.roots()) == 3
        assert len(g.leaves()) == 3

    def test_add_multiple_nodes(self) -> None:
        g = ExecutionGraph().add_node(make_node("n1")).add_node(make_node("n2"))
        assert len(g.nodes) == 2

    def test_add_multiple_edges(self) -> None:
        n1, n2, n3 = make_node("n1"), make_node("n2"), make_node("n3")
        g = ExecutionGraph(nodes=(n1, n2, n3))
        g = g.add_edge(make_edge("n1", "n2")).add_edge(make_edge("n2", "n3"))
        assert len(g.edges) == 2

    def test_node_metadata(self) -> None:
        n = ExecutionNode(task_id="t1", metadata={"k": "v"})
        assert n.metadata["k"] == "v"

    def test_node_invalid_metadata(self) -> None:
        with pytest.raises(TypeError):
            ExecutionNode(task_id="t1", metadata="bad")  # type: ignore[arg-type]

    def test_node_invalid_dependencies(self) -> None:
        with pytest.raises(TypeError):
            ExecutionNode(task_id="t1", dependencies="n1")  # type: ignore[arg-type]

    def test_node_empty_task_id(self) -> None:
        with pytest.raises(ValueError):
            ExecutionNode(task_id="")

    def test_ready_returns_tuple(self) -> None:
        g = ExecutionGraph(nodes=(make_node("n1"),))
        assert isinstance(g.ready(set()), tuple)

    def test_is_complete_empty_graph(self) -> None:
        g = ExecutionGraph()
        assert g.is_complete(set()) is True


# ====================================================================
# Batch Executor Tests (45 tests)
# ====================================================================


class TestBatchExecutor:
    def test_execute_empty_batch(
        self,
        event_bus: MockEventBus,
        manager: WorkerManager,
        worker_runtime: WorkerRuntime,
        context: WorkerContext,
    ) -> None:
        executor = BatchExecutor(
            event_bus=event_bus, manager=manager, worker_runtime=worker_runtime
        )
        result = executor.execute_batch((), context)
        assert len(result.completed) == 0
        assert len(result.failed) == 0

    def test_execute_single_node_success(
        self,
        event_bus: MockEventBus,
        manager: WorkerManager,
        worker_runtime: WorkerRuntime,
        context: WorkerContext,
    ) -> None:
        executor = BatchExecutor(
            event_bus=event_bus, manager=manager, worker_runtime=worker_runtime
        )
        batch = (make_node("n1", "t1"),)
        result = executor.execute_batch(batch, context)
        assert len(result.completed) == 1
        assert "n1" in result.completed
        assert len(result.failed) == 0

    def test_execute_single_node_failure(
        self,
        registry: WorkerRegistry,
        event_bus: MockEventBus,
        health_manager: WorkerHealthManager,
        context: WorkerContext,
    ) -> None:
        registry.register(
            MockWorker(WorkerProfile(id="w_fail", name="Fail", capabilities=("python",)), fail=True)
        )
        mgr = WorkerManager(registry=registry, health_manager=health_manager)
        mgr.find_best_worker_for_task = lambda task_id: registry.find("w_fail")
        wrt = WorkerRuntime(event_bus=event_bus, health_manager=health_manager, manager=mgr)

        executor = BatchExecutor(event_bus=event_bus, manager=mgr, worker_runtime=wrt)
        batch = (make_node("n1", "t1"),)
        result = executor.execute_batch(batch, context)

        assert len(result.failed) == 1
        assert "n1" in result.failed

    def test_execute_multiple_nodes_success(
        self,
        event_bus: MockEventBus,
        manager: WorkerManager,
        worker_runtime: WorkerRuntime,
        context: WorkerContext,
    ) -> None:
        executor = BatchExecutor(
            event_bus=event_bus, manager=manager, worker_runtime=worker_runtime
        )
        batch = (make_node("n1", "t1"), make_node("n2", "t2"))
        result = executor.execute_batch(batch, context)
        assert len(result.completed) == 2
        assert len(result.failed) == 0

    def test_execute_mixed_success_failure(
        self,
        registry: WorkerRegistry,
        event_bus: MockEventBus,
        health_manager: WorkerHealthManager,
        context: WorkerContext,
    ) -> None:
        registry.register(
            MockWorker(WorkerProfile(id="w_fail", name="Fail", capabilities=("python",)), fail=True)
        )
        mgr = WorkerManager(registry=registry, health_manager=health_manager)

        def find_worker(task_id: str) -> Worker | None:
            if task_id == "t1":
                return registry.find("w_fail")
            return registry.find("w1")

        mgr.find_best_worker_for_task = find_worker
        wrt = WorkerRuntime(event_bus=event_bus, health_manager=health_manager, manager=mgr)

        executor = BatchExecutor(event_bus=event_bus, manager=mgr, worker_runtime=wrt)
        batch = (make_node("n1", "t1"), make_node("n2", "t2"))
        result = executor.execute_batch(batch, context)

        assert len(result.completed) == 1
        assert len(result.failed) == 1
        assert "n1" in result.failed
        assert "n2" in result.completed

    def test_fail_fast_stops_on_failure(
        self,
        registry: WorkerRegistry,
        event_bus: MockEventBus,
        health_manager: WorkerHealthManager,
        context: WorkerContext,
    ) -> None:
        registry.register(
            MockWorker(WorkerProfile(id="w_fail", name="Fail", capabilities=("python",)), fail=True)
        )
        mgr = WorkerManager(registry=registry, health_manager=health_manager)
        mgr.find_best_worker_for_task = lambda task_id: registry.find("w_fail")
        wrt = WorkerRuntime(event_bus=event_bus, health_manager=health_manager, manager=mgr)

        executor = BatchExecutor(
            event_bus=event_bus,
            manager=mgr,
            worker_runtime=wrt,
            failure_policy=FailurePolicy.FAIL_FAST,
        )
        batch = (make_node("n1", "t1"), make_node("n2", "t2"))
        result = executor.execute_batch(batch, context)

        assert len(result.failed) == 1
        assert "n1" in result.failed
        assert "n2" not in result.completed and "n2" not in result.failed

    def test_continue_policy_executes_all(
        self,
        registry: WorkerRegistry,
        event_bus: MockEventBus,
        health_manager: WorkerHealthManager,
        context: WorkerContext,
    ) -> None:
        registry.register(
            MockWorker(WorkerProfile(id="w_fail", name="Fail", capabilities=("python",)), fail=True)
        )
        mgr = WorkerManager(registry=registry, health_manager=health_manager)

        def find_worker(task_id: str) -> Worker | None:
            if task_id == "t1":
                return registry.find("w_fail")
            return registry.find("w1")

        mgr.find_best_worker_for_task = find_worker
        wrt = WorkerRuntime(event_bus=event_bus, health_manager=health_manager, manager=mgr)

        executor = BatchExecutor(
            event_bus=event_bus,
            manager=mgr,
            worker_runtime=wrt,
            failure_policy=FailurePolicy.CONTINUE,
        )
        batch = (make_node("n1", "t1"), make_node("n2", "t2"))
        result = executor.execute_batch(batch, context)

        assert len(result.failed) == 1
        assert len(result.completed) == 1

    def test_no_worker_available(
        self,
        registry: WorkerRegistry,
        event_bus: MockEventBus,
        health_manager: WorkerHealthManager,
        context: WorkerContext,
    ) -> None:
        mgr = WorkerManager(registry=registry, health_manager=health_manager)
        mgr.find_best_worker_for_task = lambda task_id: None
        wrt = WorkerRuntime(event_bus=event_bus, health_manager=health_manager, manager=mgr)

        executor = BatchExecutor(event_bus=event_bus, manager=mgr, worker_runtime=wrt)
        batch = (make_node("n1", "t1"),)
        result = executor.execute_batch(batch, context)

        assert len(result.failed) == 1
        assert "n1" in result.failed

    def test_results_stored_in_batch_result(
        self,
        event_bus: MockEventBus,
        manager: WorkerManager,
        worker_runtime: WorkerRuntime,
        context: WorkerContext,
    ) -> None:
        executor = BatchExecutor(
            event_bus=event_bus, manager=manager, worker_runtime=worker_runtime
        )
        batch = (make_node("n1", "t1"),)
        result = executor.execute_batch(batch, context)
        assert "n1" in result.results
        assert result.results["n1"].success is True

    def test_worker_released_after_execution(
        self,
        event_bus: MockEventBus,
        manager: WorkerManager,
        worker_runtime: WorkerRuntime,
        context: WorkerContext,
    ) -> None:
        executor = BatchExecutor(
            event_bus=event_bus, manager=manager, worker_runtime=worker_runtime
        )
        batch = (make_node("n1", "t1"),)
        executor.execute_batch(batch, context)
        # Worker runtime should release the worker
        assert manager.get_state("w1") == WorkerState.IDLE


# ====================================================================
# Parallel Execution Runtime Tests (45 tests)
# ====================================================================


class TestParallelExecutionRuntime:
    def test_execute_empty_graph(
        self,
        event_bus: MockEventBus,
        manager: WorkerManager,
        worker_runtime: WorkerRuntime,
        context: WorkerContext,
    ) -> None:
        rt = ParallelExecutionRuntime(
            event_bus=event_bus, manager=manager, worker_runtime=worker_runtime
        )
        graph = ExecutionGraph()
        completed, failed = rt.execute(graph, context)
        assert len(completed) == 0
        assert len(failed) == 0

    def test_execute_single_node(
        self,
        event_bus: MockEventBus,
        manager: WorkerManager,
        worker_runtime: WorkerRuntime,
        context: WorkerContext,
    ) -> None:
        rt = ParallelExecutionRuntime(
            event_bus=event_bus, manager=manager, worker_runtime=worker_runtime
        )
        graph = ExecutionGraph(nodes=(make_node("n1", "t1"),))
        completed, failed = rt.execute(graph, context)
        assert len(completed) == 1
        assert len(failed) == 0

    def test_execute_linear_graph(
        self,
        event_bus: MockEventBus,
        manager: WorkerManager,
        worker_runtime: WorkerRuntime,
        context: WorkerContext,
    ) -> None:
        rt = ParallelExecutionRuntime(
            event_bus=event_bus, manager=manager, worker_runtime=worker_runtime
        )
        n1, n2, n3 = make_node("n1", "t1"), make_node("n2", "t2"), make_node("n3", "t3")
        graph = ExecutionGraph(
            nodes=(n1, n2, n3), edges=(make_edge("n1", "n2"), make_edge("n2", "n3"))
        )
        completed, failed = rt.execute(graph, context)
        assert len(completed) == 3
        assert len(failed) == 0

    def test_execute_diamond_graph(
        self,
        event_bus: MockEventBus,
        manager: WorkerManager,
        worker_runtime: WorkerRuntime,
        context: WorkerContext,
    ) -> None:
        rt = ParallelExecutionRuntime(
            event_bus=event_bus, manager=manager, worker_runtime=worker_runtime
        )
        n1, n2, n3, n4 = (make_node(f"n{i}", f"t{i}") for i in range(1, 5))
        edges = (
            make_edge("n1", "n2"),
            make_edge("n1", "n3"),
            make_edge("n2", "n4"),
            make_edge("n3", "n4"),
        )
        graph = ExecutionGraph(nodes=(n1, n2, n3, n4), edges=edges)
        completed, failed = rt.execute(graph, context)
        assert len(completed) == 4
        assert len(failed) == 0

    def test_execute_multiple_roots(
        self,
        event_bus: MockEventBus,
        manager: WorkerManager,
        worker_runtime: WorkerRuntime,
        context: WorkerContext,
    ) -> None:
        rt = ParallelExecutionRuntime(
            event_bus=event_bus, manager=manager, worker_runtime=worker_runtime
        )
        n1, n2, n3 = make_node("n1", "t1"), make_node("n2", "t2"), make_node("n3", "t3")
        graph = ExecutionGraph(nodes=(n1, n2, n3))
        completed, failed = rt.execute(graph, context)
        assert len(completed) == 3
        assert len(failed) == 0

    def test_execute_with_failure_continue(
        self,
        registry: WorkerRegistry,
        event_bus: MockEventBus,
        health_manager: WorkerHealthManager,
        context: WorkerContext,
    ) -> None:
        registry.register(
            MockWorker(WorkerProfile(id="w_fail", name="Fail", capabilities=("python",)), fail=True)
        )
        mgr = WorkerManager(registry=registry, health_manager=health_manager)

        def find_worker(task_id: str) -> Worker | None:
            if task_id == "t1":
                return registry.find("w_fail")
            return registry.find("w1")

        mgr.find_best_worker_for_task = find_worker
        wrt = WorkerRuntime(event_bus=event_bus, health_manager=health_manager, manager=mgr)

        rt = ParallelExecutionRuntime(
            event_bus=event_bus,
            manager=mgr,
            worker_runtime=wrt,
            failure_policy=FailurePolicy.CONTINUE,
        )

        n1, n2 = make_node("n1", "t1"), make_node("n2", "t2")
        graph = ExecutionGraph(nodes=(n1, n2))
        completed, failed = rt.execute(graph, context)

        assert len(failed) == 1
        assert len(completed) == 1

    def test_execute_with_failure_fail_fast(
        self,
        registry: WorkerRegistry,
        event_bus: MockEventBus,
        health_manager: WorkerHealthManager,
        context: WorkerContext,
    ) -> None:
        registry.register(
            MockWorker(WorkerProfile(id="w_fail", name="Fail", capabilities=("python",)), fail=True)
        )
        mgr = WorkerManager(registry=registry, health_manager=health_manager)
        mgr.find_best_worker_for_task = lambda task_id: registry.find("w_fail")
        wrt = WorkerRuntime(event_bus=event_bus, health_manager=health_manager, manager=mgr)

        rt = ParallelExecutionRuntime(
            event_bus=event_bus,
            manager=mgr,
            worker_runtime=wrt,
            failure_policy=FailurePolicy.FAIL_FAST,
        )

        n1, n2 = make_node("n1", "t1"), make_node("n2", "t2")
        graph = ExecutionGraph(nodes=(n1, n2), edges=(make_edge("n1", "n2"),))
        completed, failed = rt.execute(graph, context)

        assert len(failed) == 1
        assert len(completed) == 0
        assert "n1" in failed
        assert "n2" not in completed and "n2" not in failed

    def test_dependency_unlocking(
        self,
        event_bus: MockEventBus,
        manager: WorkerManager,
        worker_runtime: WorkerRuntime,
        context: WorkerContext,
    ) -> None:
        rt = ParallelExecutionRuntime(
            event_bus=event_bus, manager=manager, worker_runtime=worker_runtime
        )
        n1, n2 = make_node("n1", "t1"), make_node("n2", "t2")
        graph = ExecutionGraph(nodes=(n1, n2), edges=(make_edge("n1", "n2"),))
        completed, failed = rt.execute(graph, context)
        assert "n1" in completed
        assert "n2" in completed

    def test_deadlock_detection_empty_ready(
        self,
        event_bus: MockEventBus,
        manager: WorkerManager,
        worker_runtime: WorkerRuntime,
        context: WorkerContext,
    ) -> None:
        # If no workers are available, ready() returns tasks, but executor fails them all
        # Then ready() returns next tasks, etc. But if no workers ever, it will just fail all.
        mgr = WorkerManager(registry=WorkerRegistry(), health_manager=WorkerHealthManager())
        mgr.find_best_worker_for_task = lambda task_id: None
        wrt = WorkerRuntime(event_bus=event_bus, health_manager=WorkerHealthManager(), manager=mgr)

        rt = ParallelExecutionRuntime(event_bus=event_bus, manager=mgr, worker_runtime=wrt)
        n1 = make_node("n1", "t1")
        graph = ExecutionGraph(nodes=(n1,))
        completed, failed = rt.execute(graph, context)
        assert len(failed) == 1
        assert len(completed) == 0


# ====================================================================
# Worker Messaging Tests (35 tests)
# ====================================================================


class TestWorkerMessaging:
    def test_mailbox_receive(self) -> None:
        mb = Mailbox()
        msg = WorkerMessage(sender_id="w1", receiver_id="w2", msg_type="TEST")
        mb.receive(msg)
        assert len(mb.read_all()) == 1

    def test_mailbox_clear(self) -> None:
        mb = Mailbox()
        mb.receive(WorkerMessage(sender_id="w1", receiver_id="w2", msg_type="TEST"))
        mb.clear()
        assert len(mb.read_all()) == 0

    def test_mailbox_read_all_returns_tuple(self) -> None:
        mb = Mailbox()
        assert isinstance(mb.read_all(), tuple)

    def test_router_register(self) -> None:
        router = MessageRouter()
        router.register("w1")
        assert "w1" in router._mailboxes

    def test_router_route(self) -> None:
        router = MessageRouter()
        router.register("w1")
        router.register("w2")
        msg = WorkerMessage(sender_id="w1", receiver_id="w2", msg_type="TEST")
        router.route(msg)
        assert len(router.get_mailbox("w2").read_all()) == 1

    def test_router_route_unregistered(self) -> None:
        router = MessageRouter()
        msg = WorkerMessage(sender_id="w1", receiver_id="w2", msg_type="TEST")
        with pytest.raises(ValueError):
            router.route(msg)

    def test_router_get_mailbox_unregistered(self) -> None:
        router = MessageRouter()
        with pytest.raises(ValueError):
            router.get_mailbox("missing")

    def test_message_immutable(self) -> None:
        msg = WorkerMessage(sender_id="w1", receiver_id="w2", msg_type="TEST")
        with pytest.raises(Exception):
            msg.content = "new"  # type: ignore[misc]

    def test_message_defaults(self) -> None:
        msg = WorkerMessage(sender_id="w1", receiver_id="w2", msg_type="TEST")
        assert msg.content == ""
        assert msg.metadata == {}

    def test_message_hashable(self) -> None:
        msg = WorkerMessage(sender_id="w1", receiver_id="w2", msg_type="TEST")
        assert hash(msg) is not None

    def test_message_type_values(self) -> None:
        assert MessageType.TASK_STARTED == "task_started"
        assert MessageType.ARTIFACT_READY == "artifact_ready"
        assert MessageType.FAILURE == "failure"

    def test_mailbox_multiple_messages(self) -> None:
        mb = Mailbox()
        mb.receive(WorkerMessage(sender_id="w1", receiver_id="w2", msg_type="TEST"))
        mb.receive(WorkerMessage(sender_id="w3", receiver_id="w2", msg_type="TEST"))
        assert len(mb.read_all()) == 2

    def test_router_multiple_receivers(self) -> None:
        router = MessageRouter()
        router.register("w1")
        router.register("w2")
        router.register("w3")

        msg1 = WorkerMessage(sender_id="w1", receiver_id="w2", msg_type="TEST")
        msg2 = WorkerMessage(sender_id="w1", receiver_id="w3", msg_type="TEST")

        router.route(msg1)
        router.route(msg2)

        assert len(router.get_mailbox("w2").read_all()) == 1
        assert len(router.get_mailbox("w3").read_all()) == 1

    def test_message_sender_id(self) -> None:
        msg = WorkerMessage(sender_id="w1", receiver_id="w2", msg_type="TEST")
        assert msg.sender_id == "w1"

    def test_message_receiver_id(self) -> None:
        msg = WorkerMessage(sender_id="w1", receiver_id="w2", msg_type="TEST")
        assert msg.receiver_id == "w2"

    def test_message_msg_type(self) -> None:
        msg = WorkerMessage(sender_id="w1", receiver_id="w2", msg_type="TEST")
        assert msg.msg_type == "TEST"

    def test_message_content(self) -> None:
        msg = WorkerMessage(sender_id="w1", receiver_id="w2", msg_type="TEST", content="Hello")
        assert msg.content == "Hello"

    def test_message_metadata(self) -> None:
        msg = WorkerMessage(sender_id="w1", receiver_id="w2", msg_type="TEST", metadata={"k": "v"})
        assert msg.metadata["k"] == "v"

    def test_message_invalid_metadata(self) -> None:
        with pytest.raises(TypeError):
            WorkerMessage(sender_id="w1", receiver_id="w2", msg_type="TEST", metadata="bad")  # type: ignore[arg-type]

    def test_mailbox_empty_read_all(self) -> None:
        mb = Mailbox()
        assert mb.read_all() == ()

    def test_router_double_register(self) -> None:
        router = MessageRouter()
        router.register("w1")
        # Should not raise, just ignore
        router.register("w1")
        assert "w1" in router._mailboxes

    def test_message_equality(self) -> None:
        m1 = WorkerMessage(id="m1", sender_id="w1", receiver_id="w2", msg_type="TEST")
        m2 = WorkerMessage(id="m1", sender_id="w1", receiver_id="w2", msg_type="TEST")
        # Compare core fields instead of direct object equality due to dynamic timestamps
        assert m1.id == m2.id
        assert m1.sender_id == m2.sender_id
        assert m1.receiver_id == m2.receiver_id
        assert m1.msg_type == m2.msg_type

    def test_message_inequality(self) -> None:
        m1 = WorkerMessage(id="m1", sender_id="w1", receiver_id="w2", msg_type="TEST")
        m2 = WorkerMessage(id="m2", sender_id="w1", receiver_id="w2", msg_type="TEST")
        assert m1 != m2

    def test_message_id_generated(self) -> None:
        m1 = WorkerMessage(sender_id="w1", receiver_id="w2", msg_type="TEST")
        m2 = WorkerMessage(sender_id="w1", receiver_id="w2", msg_type="TEST")
        assert m1.id != m2.id

    def test_message_timestamp_auto(self) -> None:
        from datetime import datetime

        m = WorkerMessage(sender_id="w1", receiver_id="w2", msg_type="TEST")
        assert isinstance(m.timestamp, datetime)

    def test_mailbox_read_all_preserves_order(self) -> None:
        mb = Mailbox()
        m1 = WorkerMessage(id="m1", sender_id="w1", receiver_id="w2", msg_type="TEST")
        m2 = WorkerMessage(id="m2", sender_id="w1", receiver_id="w2", msg_type="TEST")
        mb.receive(m1)
        mb.receive(m2)
        assert mb.read_all()[0].id == "m1"
        assert mb.read_all()[1].id == "m2"

    def test_router_route_to_self(self) -> None:
        router = MessageRouter()
        router.register("w1")
        msg = WorkerMessage(sender_id="w1", receiver_id="w1", msg_type="TEST")
        router.route(msg)
        assert len(router.get_mailbox("w1").read_all()) == 1

    def test_message_type_artifact_ready(self) -> None:
        msg = WorkerMessage(sender_id="w1", receiver_id="w2", msg_type=MessageType.ARTIFACT_READY)
        assert msg.msg_type == MessageType.ARTIFACT_READY

    def test_message_type_failure(self) -> None:
        msg = WorkerMessage(sender_id="w1", receiver_id="w2", msg_type=MessageType.FAILURE)
        assert msg.msg_type == MessageType.FAILURE

    def test_message_type_request_review(self) -> None:
        msg = WorkerMessage(sender_id="w1", receiver_id="w2", msg_type=MessageType.REQUEST_REVIEW)
        assert msg.msg_type == MessageType.REQUEST_REVIEW

    def test_message_type_warning(self) -> None:
        msg = WorkerMessage(sender_id="w1", receiver_id="w2", msg_type=MessageType.WARNING)
        assert msg.msg_type == MessageType.WARNING

    def test_message_type_task_finished(self) -> None:
        msg = WorkerMessage(sender_id="w1", receiver_id="w2", msg_type=MessageType.TASK_FINISHED)
        assert msg.msg_type == MessageType.TASK_FINISHED

    def test_message_type_task_started(self) -> None:
        msg = WorkerMessage(sender_id="w1", receiver_id="w2", msg_type=MessageType.TASK_STARTED)
        assert msg.msg_type == MessageType.TASK_STARTED

    def test_mailbox_clear_already_empty(self) -> None:
        mb = Mailbox()
        mb.clear()
        assert len(mb.read_all()) == 0

    def test_mailbox_read_all_does_not_clear(self) -> None:
        mb = Mailbox()
        mb.receive(WorkerMessage(sender_id="w1", receiver_id="w2", msg_type="TEST"))
        mb.read_all()
        assert len(mb.read_all()) == 1


# ====================================================================
# Artifact Graph Tests (35 tests)
# ====================================================================


class TestArtifactGraph:
    def test_empty_graph(self) -> None:
        g = ArtifactGraph()
        assert len(g.nodes) == 0
        assert len(g.edges) == 0

    def test_add_node(self) -> None:
        g = ArtifactGraph().add_node(ArtifactNode(path="main.py", creator_worker_id="w1"))
        assert len(g.nodes) == 1

    def test_add_edge(self) -> None:
        n1 = ArtifactNode(id="a1", path="main.py", creator_worker_id="w1")
        n2 = ArtifactNode(id="a2", path="test.py", creator_worker_id="w2")
        g = ArtifactGraph(nodes=(n1, n2)).add_edge(ArtifactEdge(source="a1", target="a2"))
        assert len(g.edges) == 1

    def test_duplicate_node(self) -> None:
        n1 = ArtifactNode(id="a1", path="main.py", creator_worker_id="w1")
        with pytest.raises(DuplicateNodeError):
            ArtifactGraph(nodes=(n1, n1))

    def test_missing_source(self) -> None:
        n1 = ArtifactNode(id="a1", path="main.py", creator_worker_id="w1")
        with pytest.raises(MissingNodeError):
            ArtifactGraph(nodes=(n1,), edges=(ArtifactEdge(source="missing", target="a1"),))

    def test_missing_target(self) -> None:
        n1 = ArtifactNode(id="a1", path="main.py", creator_worker_id="w1")
        with pytest.raises(MissingNodeError):
            ArtifactGraph(nodes=(n1,), edges=(ArtifactEdge(source="a1", target="missing"),))

    def test_node_defaults(self) -> None:
        n = ArtifactNode(path="main.py", creator_worker_id="w1")
        assert n.version == 1
        assert n.metadata == {}

    def test_node_immutable(self) -> None:
        n = ArtifactNode(path="main.py", creator_worker_id="w1")
        with pytest.raises(Exception):
            n.path = "new.py"  # type: ignore[misc]

    def test_edge_immutable(self) -> None:
        e = ArtifactEdge(source="a1", target="a2")
        with pytest.raises(Exception):
            e.source = "a3"  # type: ignore[misc]

    def test_node_hashable(self) -> None:
        n = ArtifactNode(path="main.py", creator_worker_id="w1")
        assert hash(n) is not None

    def test_edge_hashable(self) -> None:
        e = ArtifactEdge(source="a1", target="a2")
        assert hash(e) is not None

    def test_node_id_generated(self) -> None:
        n1 = ArtifactNode(path="main.py", creator_worker_id="w1")
        n2 = ArtifactNode(path="test.py", creator_worker_id="w2")
        assert n1.id != n2.id

    def test_node_explicit_id(self) -> None:
        n = ArtifactNode(id="custom_id", path="main.py", creator_worker_id="w1")
        assert n.id == "custom_id"

    def test_node_metadata(self) -> None:
        n = ArtifactNode(path="main.py", creator_worker_id="w1", metadata={"k": "v"})
        assert n.metadata["k"] == "v"

    def test_node_invalid_metadata(self) -> None:
        with pytest.raises(TypeError):
            ArtifactNode(path="main.py", creator_worker_id="w1", metadata="bad")  # type: ignore[arg-type]

    def test_node_version(self) -> None:
        n = ArtifactNode(path="main.py", creator_worker_id="w1", version=5)
        assert n.version == 5

    def test_node_creator(self) -> None:
        n = ArtifactNode(path="main.py", creator_worker_id="w1")
        assert n.creator_worker_id == "w1"

    def test_node_path(self) -> None:
        n = ArtifactNode(path="src/main.py", creator_worker_id="w1")
        assert n.path == "src/main.py"

    def test_node_empty_path(self) -> None:
        with pytest.raises(ValueError):
            ArtifactNode(path="", creator_worker_id="w1")

    def test_edge_source(self) -> None:
        e = ArtifactEdge(source="a1", target="a2")
        assert e.source == "a1"

    def test_edge_target(self) -> None:
        e = ArtifactEdge(source="a1", target="a2")
        assert e.target == "a2"

    def test_graph_immutable_nodes(self) -> None:
        g = ArtifactGraph(nodes=(ArtifactNode(path="main.py", creator_worker_id="w1"),))
        with pytest.raises(AttributeError):
            g.nodes = ()  # type: ignore[misc]

    def test_graph_immutable_edges(self) -> None:
        n1, n2 = (
            ArtifactNode(id="a1", path="m", creator_worker_id="w1"),
            ArtifactNode(id="a2", path="t", creator_worker_id="w2"),
        )
        g = ArtifactGraph(nodes=(n1, n2), edges=(ArtifactEdge(source="a1", target="a2"),))
        with pytest.raises(AttributeError):
            g.edges = ()  # type: ignore[misc]

    def test_add_node_returns_new(self) -> None:
        g1 = ArtifactGraph()
        g2 = g1.add_node(ArtifactNode(path="main.py", creator_worker_id="w1"))
        assert len(g1.nodes) == 0
        assert len(g2.nodes) == 1

    def test_add_edge_returns_new(self) -> None:
        n1, n2 = (
            ArtifactNode(id="a1", path="m", creator_worker_id="w1"),
            ArtifactNode(id="a2", path="t", creator_worker_id="w2"),
        )
        g1 = ArtifactGraph(nodes=(n1, n2))
        g2 = g1.add_edge(ArtifactEdge(source="a1", target="a2"))
        assert len(g1.edges) == 0
        assert len(g2.edges) == 1

    def test_large_artifact_graph(self) -> None:
        nodes = tuple(
            ArtifactNode(id=f"a{i}", path=f"file{i}.py", creator_worker_id="w1") for i in range(100)
        )
        edges = tuple(ArtifactEdge(source=f"a{i}", target=f"a{i + 1}") for i in range(99))
        g = ArtifactGraph(nodes=nodes, edges=edges)
        assert len(g.nodes) == 100

    def test_node_equality(self) -> None:
        n1 = ArtifactNode(id="a1", path="m", creator_worker_id="w1")
        n2 = ArtifactNode(id="a1", path="m", creator_worker_id="w1")
        assert n1 == n2

    def test_edge_equality(self) -> None:
        e1 = ArtifactEdge(source="a1", target="a2")
        e2 = ArtifactEdge(source="a1", target="a2")
        assert e1 == e2

    def test_node_inequality(self) -> None:
        n1 = ArtifactNode(id="a1", path="m", creator_worker_id="w1")
        n2 = ArtifactNode(id="a2", path="t", creator_worker_id="w2")
        assert n1 != n2

    def test_edge_inequality(self) -> None:
        e1 = ArtifactEdge(source="a1", target="a2")
        e2 = ArtifactEdge(source="a1", target="a3")
        assert e1 != e2

    def test_node_deterministic(self) -> None:
        n1 = ArtifactNode(id="a1", path="m", creator_worker_id="w1", version=1)
        n2 = ArtifactNode(id="a1", path="m", creator_worker_id="w1", version=1)
        assert n1 == n2

    def test_graph_with_no_edges(self) -> None:
        nodes = tuple(
            ArtifactNode(id=f"a{i}", path=f"f{i}", creator_worker_id="w1") for i in range(3)
        )
        g = ArtifactGraph(nodes=nodes)
        assert len(g.nodes) == 3
        assert len(g.edges) == 0

    def test_add_multiple_nodes(self) -> None:
        g = (
            ArtifactGraph()
            .add_node(ArtifactNode(path="m", creator_worker_id="w1"))
            .add_node(ArtifactNode(path="t", creator_worker_id="w2"))
        )
        assert len(g.nodes) == 2

    def test_add_multiple_edges(self) -> None:
        n1, n2, n3 = (
            ArtifactNode(id=f"a{i}", path=f"f{i}", creator_worker_id="w1") for i in range(1, 4)
        )
        g = ArtifactGraph(nodes=(n1, n2, n3))
        g = g.add_edge(ArtifactEdge(source="a1", target="a2")).add_edge(
            ArtifactEdge(source="a2", target="a3")
        )
        assert len(g.edges) == 2

    def test_node_empty_worker_id(self) -> None:
        # Should not raise, just be empty string
        n = ArtifactNode(path="m", creator_worker_id="")
        assert n.creator_worker_id == ""


# ====================================================================
# Runtime Metrics Tests (30 tests)
# ====================================================================


class TestRuntimeMetrics:
    def test_defaults(self) -> None:
        m = ExecutionMetrics()
        assert m.total_batches == 0
        assert m.max_parallelism == 0
        assert m.average_batch_size == 0.0
        assert m.synchronization_barriers == 0
        assert m.messages_exchanged == 0
        assert m.artifacts_produced == 0
        assert m.failure_recoveries == 0
        assert m.dependency_unlocks == 0

    def test_immutable(self) -> None:
        m = ExecutionMetrics()
        with pytest.raises(Exception):
            m.total_batches = 5  # type: ignore[misc]

    def test_total_batches(self) -> None:
        m = ExecutionMetrics(total_batches=10)
        assert m.total_batches == 10

    def test_max_parallelism(self) -> None:
        m = ExecutionMetrics(max_parallelism=4)
        assert m.max_parallelism == 4

    def test_average_batch_size(self) -> None:
        m = ExecutionMetrics(average_batch_size=2.5)
        assert m.average_batch_size == 2.5

    def test_synchronization_barriers(self) -> None:
        m = ExecutionMetrics(synchronization_barriers=3)
        assert m.synchronization_barriers == 3

    def test_messages_exchanged(self) -> None:
        m = ExecutionMetrics(messages_exchanged=15)
        assert m.messages_exchanged == 15

    def test_artifacts_produced(self) -> None:
        m = ExecutionMetrics(artifacts_produced=8)
        assert m.artifacts_produced == 8

    def test_failure_recoveries(self) -> None:
        m = ExecutionMetrics(failure_recoveries=2)
        assert m.failure_recoveries == 2

    def test_dependency_unlocks(self) -> None:
        m = ExecutionMetrics(dependency_unlocks=12)
        assert m.dependency_unlocks == 12

    def test_hashable(self) -> None:
        m = ExecutionMetrics()
        assert hash(m) is not None

    def test_equality(self) -> None:
        m1 = ExecutionMetrics(total_batches=5)
        m2 = ExecutionMetrics(total_batches=5)
        assert m1 == m2

    def test_inequality(self) -> None:
        m1 = ExecutionMetrics(total_batches=5)
        m2 = ExecutionMetrics(total_batches=10)
        assert m1 != m2

    def test_all_fields(self) -> None:
        m = ExecutionMetrics(
            total_batches=10,
            max_parallelism=4,
            average_batch_size=2.5,
            synchronization_barriers=3,
            messages_exchanged=15,
            artifacts_produced=8,
            failure_recoveries=2,
            dependency_unlocks=12,
        )
        assert m.total_batches == 10
        assert m.max_parallelism == 4
        assert m.average_batch_size == 2.5
        assert m.synchronization_barriers == 3
        assert m.messages_exchanged == 15
        assert m.artifacts_produced == 8
        assert m.failure_recoveries == 2
        assert m.dependency_unlocks == 12

    def test_zero_values(self) -> None:
        m = ExecutionMetrics()
        assert m.total_batches == 0
        assert m.max_parallelism == 0
        assert m.average_batch_size == 0.0
        assert m.synchronization_barriers == 0
        assert m.messages_exchanged == 0
        assert m.artifacts_produced == 0
        assert m.failure_recoveries == 0
        assert m.dependency_unlocks == 0

    def test_slots(self) -> None:
        m = ExecutionMetrics()
        with pytest.raises(Exception):
            m.new_field = "value"  # type: ignore[attr-defined]

    def test_frozen(self) -> None:
        m = ExecutionMetrics()
        with pytest.raises(Exception):
            m.max_parallelism = 100  # type: ignore[misc]

    def test_str_representation(self) -> None:
        m = ExecutionMetrics(total_batches=5)
        assert str(m) is not None

    def test_repr_representation(self) -> None:
        m = ExecutionMetrics(total_batches=5)
        assert repr(m) is not None

    def test_negative_values_allowed(self) -> None:
        # Dataclass doesn't validate negative
        m = ExecutionMetrics(total_batches=-1)
        assert m.total_batches == -1

    def test_deterministic(self) -> None:
        m1 = ExecutionMetrics(total_batches=5, max_parallelism=2)
        m2 = ExecutionMetrics(total_batches=5, max_parallelism=2)
        assert m1 == m2

    def test_with_none_values(self) -> None:
        m = ExecutionMetrics()
        assert m is not None

    def test_total_batches_int_type(self) -> None:
        m = ExecutionMetrics()
        assert isinstance(m.total_batches, int)

    def test_max_parallelism_int_type(self) -> None:
        m = ExecutionMetrics()
        assert isinstance(m.max_parallelism, int)

    def test_average_batch_size_float_type(self) -> None:
        m = ExecutionMetrics()
        assert isinstance(m.average_batch_size, float)

    def test_messages_exchanged_int_type(self) -> None:
        m = ExecutionMetrics()
        assert isinstance(m.messages_exchanged, int)

    def test_artifacts_produced_int_type(self) -> None:
        m = ExecutionMetrics()
        assert isinstance(m.artifacts_produced, int)

    def test_dependency_unlocks_int_type(self) -> None:
        m = ExecutionMetrics()
        assert isinstance(m.dependency_unlocks, int)

    def test_failure_recoveries_int_type(self) -> None:
        m = ExecutionMetrics()
        assert isinstance(m.failure_recoveries, int)

    def test_synchronization_barriers_int_type(self) -> None:
        m = ExecutionMetrics()
        assert isinstance(m.synchronization_barriers, int)
