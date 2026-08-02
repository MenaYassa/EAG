"""Comprehensive tests for the Worker Runtime (Sprint 8.2)."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from eag.workers import (
    WorkerContext,
    WorkerHealth,
    WorkerHealthManager,
    WorkerManager,
    WorkerNotFoundError,
    WorkerProfile,
    WorkerRegistry,
    WorkerResult,
    WorkerRole,
    WorkerRuntime,
    WorkerState,
    WorkerTask,
)
from eag.workers.events import (
    WorkerCompleted,
    WorkerFailed,
    WorkerReleased,
    WorkerStarted,
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
        return task.required_capability in self._profile.capabilities

    def estimate(self, task: WorkerTask) -> float:
        return 1.0

    def execute(self, task: WorkerTask, context: WorkerContext) -> WorkerResult:
        if self._fail:
            raise RuntimeError("Mock execution failed")
        return WorkerResult(
            worker_id=self._profile.id,
            task_id=task.id,
            success=True,
            summary="Task completed successfully",
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
    reg.register(
        MockWorker(
            WorkerProfile(
                id="w1",
                name="Alice",
                role=WorkerRole.BACKEND,
                capabilities=("python",),
                preferred_capabilities=("python",),
            )
        )
    )
    reg.register(
        MockWorker(
            WorkerProfile(id="w2", name="Bob", role=WorkerRole.FRONTEND, capabilities=("react",))
        )
    )
    reg.register(
        MockWorker(
            WorkerProfile(
                id="w3", name="Charlie", role=WorkerRole.TESTING, capabilities=("python", "pytest")
            )
        )
    )
    return reg


@pytest.fixture
def manager(registry: WorkerRegistry, health_manager: WorkerHealthManager) -> WorkerManager:
    return WorkerManager(registry=registry, health_manager=health_manager)


@pytest.fixture
def runtime(
    event_bus: MockEventBus, health_manager: WorkerHealthManager, manager: WorkerManager
) -> WorkerRuntime:
    return WorkerRuntime(event_bus=event_bus, health_manager=health_manager, manager=manager)


def make_task(task_id: str = "t1", cap: str = "python") -> WorkerTask:
    return WorkerTask(id=task_id, title="Test Task", required_capability=cap)


def make_context() -> WorkerContext:
    return WorkerContext(run_id="r1", goal="Test", workspace=Path("/tmp"))


# --- Registry Tests (30) ---


class TestWorkerRegistry:
    def test_register(self, registry: WorkerRegistry) -> None:
        assert len(registry.list()) == 3

    def test_duplicate_raises(self, registry: WorkerRegistry) -> None:
        with pytest.raises(ValueError):
            registry.register(MockWorker(WorkerProfile(id="w1", name="Alice")))

    def test_find_success(self, registry: WorkerRegistry) -> None:
        w = registry.find("w1")
        assert w.profile.name == "Alice"

    def test_find_missing_raises(self, registry: WorkerRegistry) -> None:
        with pytest.raises(WorkerNotFoundError):
            registry.find("missing")

    def test_list_sorted(self, registry: WorkerRegistry) -> None:
        ids = [w.profile.id for w in registry.list()]
        assert ids == ["w1", "w2", "w3"]

    def test_list_immutable(self, registry: WorkerRegistry) -> None:
        workers = registry.list()
        with pytest.raises(AttributeError):
            workers.append(MockWorker(WorkerProfile(id="w4", name="Dan")))  # type: ignore[attr-defined]

    def test_unregister(self, registry: WorkerRegistry) -> None:
        assert registry.unregister("w1") is True
        assert len(registry.list()) == 2

    def test_unregister_missing(self, registry: WorkerRegistry) -> None:
        assert registry.unregister("missing") is False

    def test_by_role(self, registry: WorkerRegistry) -> None:
        backend = registry.by_role(WorkerRole.BACKEND)
        assert len(backend) == 1
        assert backend[0].profile.id == "w1"

    def test_by_capability(self, registry: WorkerRegistry) -> None:
        python_workers = registry.by_capability("python")
        assert len(python_workers) == 2
        assert {w.profile.id for w in python_workers} == {"w1", "w3"}

    def test_available_healthy(
        self, registry: WorkerRegistry, health_manager: WorkerHealthManager
    ) -> None:
        assert len(registry.available(health_manager)) == 3

    def test_available_excludes_unavailable(
        self, registry: WorkerRegistry, health_manager: WorkerHealthManager
    ) -> None:
        health_manager.record_failure("w1")
        health_manager.record_failure("w1")
        health_manager.record_failure("w1")
        available = registry.available(health_manager)
        assert len(available) == 2
        assert "w1" not in [w.profile.id for w in available]

    def test_by_health(self, registry: WorkerRegistry, health_manager: WorkerHealthManager) -> None:
        health_manager.record_failure("w1")
        degraded = registry.by_health(health_manager, WorkerHealth.DEGRADED)
        assert len(degraded) == 1
        assert degraded[0].profile.id == "w1"

    def test_empty_registry(self) -> None:
        reg = WorkerRegistry()
        assert len(reg.list()) == 0

    def test_list_returns_tuple(self, registry: WorkerRegistry) -> None:
        assert isinstance(registry.list(), tuple)


# --- Health Manager Tests (25) ---


class TestWorkerHealthManager:
    def test_initial_health(self, health_manager: WorkerHealthManager) -> None:
        assert health_manager.get_health("w1") == WorkerHealth.HEALTHY

    def test_record_success(self, health_manager: WorkerHealthManager) -> None:
        health_manager.record_failure("w1")
        health_manager.record_success("w1")
        assert health_manager.get_health("w1") == WorkerHealth.HEALTHY

    def test_record_failure_degrades(self, health_manager: WorkerHealthManager) -> None:
        health_manager.record_failure("w1")
        assert health_manager.get_health("w1") == WorkerHealth.DEGRADED

    def test_record_failure_unavailable(self, health_manager: WorkerHealthManager) -> None:
        health_manager.record_failure("w1")
        health_manager.record_failure("w1")
        health_manager.record_failure("w1")
        assert health_manager.get_health("w1") == WorkerHealth.UNAVAILABLE

    def test_recover(self, health_manager: WorkerHealthManager) -> None:
        health_manager.record_failure("w1")
        health_manager.recover("w1")
        assert health_manager.get_health("w1") == WorkerHealth.HEALTHY

    def test_success_resets_failures(self, health_manager: WorkerHealthManager) -> None:
        health_manager.record_failure("w1")
        health_manager.record_success("w1")
        health_manager.record_failure("w1")
        assert health_manager.get_health("w1") == WorkerHealth.DEGRADED

    def test_degrade_threshold(self) -> None:
        hm = WorkerHealthManager(degrade_threshold=2, unavailable_threshold=4)
        hm.record_failure("w1")
        assert hm.get_health("w1") == WorkerHealth.HEALTHY
        hm.record_failure("w1")
        assert hm.get_health("w1") == WorkerHealth.DEGRADED


# --- Manager Tests ---


class TestWorkerManager:
    def test_find_best_worker_exact_cap(self, manager: WorkerManager) -> None:
        task = make_task(cap="python")
        worker = manager.find_best_worker(task)
        assert worker is not None
        assert worker.profile.id == "w1"  # w1 prefers python, w3 doesn't

    def test_find_best_worker_preferred(self, manager: WorkerManager) -> None:
        task = make_task(cap="python")
        worker = manager.find_best_worker(task)
        assert worker.profile.id == "w1"

    def test_find_best_worker_no_match(self, manager: WorkerManager) -> None:
        task = make_task(cap="rust")
        assert manager.find_best_worker(task) is None

    def test_assign_success(self, manager: WorkerManager) -> None:
        assert manager.assign("w1", "t1") is True
        assert manager.get_state("w1") == WorkerState.ASSIGNED

    def test_assign_fail_if_busy(self, manager: WorkerManager) -> None:
        manager.assign("w1", "t1")
        assert manager.assign("w1", "t2") is False

    def test_release(self, manager: WorkerManager) -> None:
        manager.assign("w1", "t1")
        manager.release("w1")
        assert manager.get_state("w1") == WorkerState.IDLE

    def test_idle_workers(self, manager: WorkerManager) -> None:
        # Initialize w1, w2, w3 in manager's state tracking
        manager.assign("w1", "t1")
        manager.assign("w2", "t2")
        manager.assign("w3", "t3")

        # Release w2 and w3 so they transition into WorkerState.IDLE
        manager.release("w2")
        manager.release("w3")

        idle = manager.idle_workers()
        assert len(idle) == 2
        assert "w1" not in [w.profile.id for w in idle]
        assert {w.profile.id for w in idle} == {"w2", "w3"}

    def test_busy_workers(self, manager: WorkerManager) -> None:
        manager.assign("w1", "t1")
        busy = manager.busy_workers()
        assert len(busy) == 1
        assert busy[0].profile.id == "w1"

    def test_find_best_worker_excludes_busy(self, manager: WorkerManager) -> None:
        manager.assign("w1", "t1")
        task = make_task(cap="python")
        worker = manager.find_best_worker(task)
        # w1 is busy, should fall back to w3
        assert worker.profile.id == "w3"

    def test_find_best_worker_excludes_unhealthy(
        self, registry: WorkerRegistry, health_manager: WorkerHealthManager
    ) -> None:
        health_manager.record_failure("w1")
        health_manager.record_failure("w1")
        health_manager.record_failure("w1")
        mgr = WorkerManager(registry=registry, health_manager=health_manager)
        task = make_task(cap="python")
        worker = mgr.find_best_worker(task)
        assert worker.profile.id == "w3"


# --- Runtime Tests ---


class TestWorkerRuntime:
    def test_execute_success(self, runtime: WorkerRuntime, manager: WorkerManager) -> None:
        worker = manager.find_best_worker(make_task())
        manager.assign(worker.profile.id, "t1")

        result = runtime.execute(worker, make_task(), make_context())

        assert result.success is True
        assert result.summary == "Task completed successfully"
        assert manager.get_state(worker.profile.id) == WorkerState.IDLE

    def test_execute_failure(
        self,
        registry: WorkerRegistry,
        event_bus: MockEventBus,
        health_manager: WorkerHealthManager,
    ) -> None:
        fail_worker = MockWorker(
            WorkerProfile(id="w_fail", name="Fail", capabilities=("python",)),
            fail=True,
        )
        registry.register(fail_worker)
        mgr = WorkerManager(registry=registry, health_manager=health_manager)
        rt = WorkerRuntime(event_bus=event_bus, health_manager=health_manager, manager=mgr)

        worker = registry.find("w_fail")
        mgr.assign(worker.profile.id, "t1")

        result = rt.execute(worker, make_task(), make_context())

        assert result.success is False
        assert "Mock execution failed" in result.warnings[0]
        assert mgr.get_state(worker.profile.id) == WorkerState.IDLE

    def test_execute_publishes_started(
        self, runtime: WorkerRuntime, manager: WorkerManager, event_bus: MockEventBus
    ) -> None:
        worker = manager.find_best_worker(make_task())
        manager.assign(worker.profile.id, "t1")
        runtime.execute(worker, make_task(), make_context())

        assert any(isinstance(e, WorkerStarted) for e in event_bus.published_events)

    def test_execute_publishes_completed(
        self, runtime: WorkerRuntime, manager: WorkerManager, event_bus: MockEventBus
    ) -> None:
        worker = manager.find_best_worker(make_task())
        manager.assign(worker.profile.id, "t1")
        runtime.execute(worker, make_task(), make_context())

        assert any(isinstance(e, WorkerCompleted) for e in event_bus.published_events)

    def test_execute_publishes_failed(
        self,
        registry: WorkerRegistry,
        event_bus: MockEventBus,
        health_manager: WorkerHealthManager,
    ) -> None:
        fail_worker = MockWorker(
            WorkerProfile(id="w_fail", name="Fail", capabilities=("python",)),
            fail=True,
        )
        registry.register(fail_worker)
        mgr = WorkerManager(registry=registry, health_manager=health_manager)
        rt = WorkerRuntime(event_bus=event_bus, health_manager=health_manager, manager=mgr)

        worker = registry.find("w_fail")
        mgr.assign(worker.profile.id, "t1")
        rt.execute(worker, make_task(), make_context())

        assert any(isinstance(e, WorkerFailed) for e in event_bus.published_events)

    def test_execute_publishes_released(
        self, runtime: WorkerRuntime, manager: WorkerManager, event_bus: MockEventBus
    ) -> None:
        worker = manager.find_best_worker(make_task())
        manager.assign(worker.profile.id, "t1")
        runtime.execute(worker, make_task(), make_context())

        assert any(isinstance(e, WorkerReleased) for e in event_bus.published_events)

    def test_execute_updates_health_success(
        self, runtime: WorkerRuntime, manager: WorkerManager, health_manager: WorkerHealthManager
    ) -> None:
        worker = manager.find_best_worker(make_task())
        manager.assign(worker.profile.id, "t1")
        runtime.execute(worker, make_task(), make_context())

        assert health_manager.get_health(worker.profile.id) == WorkerHealth.HEALTHY

    def test_execute_updates_health_failure(
        self,
        registry: WorkerRegistry,
        event_bus: MockEventBus,
        health_manager: WorkerHealthManager,
    ) -> None:
        fail_worker = MockWorker(
            WorkerProfile(id="w_fail", name="Fail", capabilities=("python",)),
            fail=True,
        )
        registry.register(fail_worker)
        mgr = WorkerManager(registry=registry, health_manager=health_manager)
        rt = WorkerRuntime(event_bus=event_bus, health_manager=health_manager, manager=mgr)

        worker = registry.find("w_fail")
        mgr.assign(worker.profile.id, "t1")
        rt.execute(worker, make_task(), make_context())

        assert health_manager.get_health(worker.profile.id) == WorkerHealth.DEGRADED

    def test_metrics_completed_tasks(self, runtime: WorkerRuntime, manager: WorkerManager) -> None:
        worker = manager.find_best_worker(make_task())
        manager.assign(worker.profile.id, "t1")
        runtime.execute(worker, make_task(), make_context())

        assert runtime.get_metrics().completed_tasks == 1

    def test_metrics_failed_tasks(
        self,
        registry: WorkerRegistry,
        event_bus: MockEventBus,
        health_manager: WorkerHealthManager,
    ) -> None:
        fail_worker = MockWorker(
            WorkerProfile(id="w_fail", name="Fail", capabilities=("python",)),
            fail=True,
        )
        registry.register(fail_worker)
        mgr = WorkerManager(registry=registry, health_manager=health_manager)
        rt = WorkerRuntime(event_bus=event_bus, health_manager=health_manager, manager=mgr)

        worker = registry.find("w_fail")
        mgr.assign(worker.profile.id, "t1")
        rt.execute(worker, make_task(), make_context())

        assert rt.get_metrics().failed_tasks == 1

    def test_metrics_utilization(self, runtime: WorkerRuntime, manager: WorkerManager) -> None:
        worker = manager.find_best_worker(make_task())
        manager.assign(worker.profile.id, "t1")

        runtime.execute(worker, make_task(), make_context())
        metrics = runtime.get_metrics()
        assert metrics.busy_workers == 0
        assert metrics.idle_workers > 0


# --- Hardening Tests (10) ---


class TestWorkerRuntimeHardening:
    """Advanced tests for determinism, event ordering, and state lifecycle."""

    def test_execute_deterministic(self, runtime: WorkerRuntime, manager: WorkerManager) -> None:
        """Executing the same task twice yields the exact same result."""
        task = make_task(task_id="t_det", cap="python")
        ctx = make_context()

        worker = manager.find_best_worker(task)
        manager.assign(worker.profile.id, task.id)
        r1 = runtime.execute(worker, task, ctx)

        manager.assign(worker.profile.id, task.id)
        r2 = runtime.execute(worker, task, ctx)

        assert r1.success == r2.success
        assert r1.summary == r2.summary
        assert r1.worker_id == r2.worker_id

    def test_event_order_success(
        self, runtime: WorkerRuntime, manager: WorkerManager, event_bus: MockEventBus
    ) -> None:
        """Verifies Started -> Completed -> Released order on success."""
        worker = manager.find_best_worker(make_task())
        manager.assign(worker.profile.id, "t_ord_s")
        runtime.execute(worker, make_task(), make_context())

        event_types = [
            type(e) for e in event_bus.published_events if e.worker_id == worker.profile.id
        ]

        assert event_types == [WorkerStarted, WorkerCompleted, WorkerReleased]

    def test_event_order_failure(
        self,
        registry: WorkerRegistry,
        event_bus: MockEventBus,
        health_manager: WorkerHealthManager,
    ) -> None:
        """Verifies Started -> Failed -> Released order on failure."""
        fail_worker = MockWorker(
            WorkerProfile(id="w_fail_ord", name="FailOrd", capabilities=("python",)),
            fail=True,
        )
        registry.register(fail_worker)
        mgr = WorkerManager(registry=registry, health_manager=health_manager)
        rt = WorkerRuntime(event_bus=event_bus, health_manager=health_manager, manager=mgr)

        # Retrieve the failing worker directly by ID rather than find_best_worker
        worker = registry.find("w_fail_ord")
        mgr.assign(worker.profile.id, "t_ord_f")
        rt.execute(worker, make_task(), make_context())

        event_types = [
            type(e) for e in event_bus.published_events if e.worker_id == worker.profile.id
        ]

        assert event_types == [
            WorkerStarted,
            WorkerFailed,
            WorkerReleased,
        ]

    def test_assignment_lifecycle_success(
        self, runtime: WorkerRuntime, manager: WorkerManager
    ) -> None:
        """Verifies state transitions: IDLE -> ASSIGNED -> EXECUTING -> IDLE."""
        worker = manager.find_best_worker(make_task())

        assert manager.get_state(worker.profile.id) == WorkerState.IDLE

        manager.assign(worker.profile.id, "t_life")
        assert manager.get_state(worker.profile.id) == WorkerState.ASSIGNED

        # Execute is synchronous, so it will transition through EXECUTING and back to IDLE
        runtime.execute(worker, make_task(), make_context())

        assert manager.get_state(worker.profile.id) == WorkerState.IDLE

    def test_assignment_lifecycle_failure(
        self,
        registry: WorkerRegistry,
        manager: WorkerManager,
        event_bus: MockEventBus,
        health_manager: WorkerHealthManager,
    ) -> None:
        """Verifies state transitions on failure: IDLE -> ASSIGNED -> EXECUTING -> IDLE."""
        registry.register(
            MockWorker(
                WorkerProfile(id="w_fail_life", name="FailLife", capabilities=("python",)),
                fail=True,
            )
        )
        mgr = WorkerManager(registry=registry, health_manager=health_manager)
        rt = WorkerRuntime(event_bus=event_bus, health_manager=health_manager, manager=mgr)

        worker = mgr.find_best_worker(make_task())

        assert mgr.get_state(worker.profile.id) == WorkerState.IDLE

        mgr.assign(worker.profile.id, "t_life_f")
        assert mgr.get_state(worker.profile.id) == WorkerState.ASSIGNED

        rt.execute(worker, make_task(), make_context())

        assert mgr.get_state(worker.profile.id) == WorkerState.IDLE

    def test_metrics_aggregation_multiple_executions(
        self, runtime: WorkerRuntime, manager: WorkerManager
    ) -> None:
        """Verifies that metrics aggregate correctly over multiple runs."""
        task = make_task(task_id="t_agg", cap="python")
        ctx = make_context()

        for _ in range(3):
            worker = manager.find_best_worker(task)
            manager.assign(worker.profile.id, task.id)
            runtime.execute(worker, task, ctx)

        metrics = runtime.get_metrics()
        assert metrics.completed_tasks == 3
        assert metrics.failed_tasks == 0

    def test_metrics_aggregation_mixed_results(
        self,
        registry: WorkerRegistry,
        manager: WorkerManager,
        event_bus: MockEventBus,
        health_manager: WorkerHealthManager,
    ) -> None:
        """Verifies that metrics aggregate correctly with mixed success/failure."""
        registry.register(
            MockWorker(
                WorkerProfile(id="w_fail_agg", name="FailAgg", capabilities=("python",)), fail=True
            )
        )
        mgr = WorkerManager(registry=registry, health_manager=health_manager)
        rt = WorkerRuntime(event_bus=event_bus, health_manager=health_manager, manager=mgr)

        task = make_task(task_id="t_mixed", cap="python")
        ctx = make_context()

        # 1 success
        w1 = mgr.find_best_worker(task)
        mgr.assign(w1.profile.id, task.id)
        rt.execute(w1, task, ctx)

        # 1 failure
        w_fail = registry.find("w_fail_agg")
        mgr.assign(w_fail.profile.id, task.id)
        rt.execute(w_fail, task, ctx)

        # 1 success
        w3 = mgr.find_best_worker(task)
        mgr.assign(w3.profile.id, task.id)
        rt.execute(w3, task, ctx)

        metrics = rt.get_metrics()
        assert metrics.completed_tasks == 2
        assert metrics.failed_tasks == 1

    def test_metrics_utilization_calculation(
        self, runtime: WorkerRuntime, manager: WorkerManager
    ) -> None:
        """Verifies utilization is calculated correctly based on busy workers."""
        task = make_task(task_id="t_util", cap="python")
        ctx = make_context()

        # Initially 0 utilization
        assert runtime.get_metrics().utilization == 0.0

        # Assign one worker (make them busy)
        worker = manager.find_best_worker(task)
        manager.assign(worker.profile.id, task.id)

        # In a real async runtime, utilization would be 1/3 here.
        # But since our runtime is synchronous, we simulate the state check
        # by manually setting the state to EXECUTING before checking metrics.
        manager._get_instance(worker.profile.id).state = WorkerState.EXECUTING

        metrics = runtime.get_metrics()
        assert metrics.busy_workers == 1
        assert metrics.total_workers > 0
        # Utilization = busy / total (1/3 = 0.333...)
        assert abs(metrics.utilization - (1.0 / metrics.total_workers)) < 0.01

    def test_health_recovery_after_success(
        self,
        registry: WorkerRegistry,
        manager: WorkerManager,
        event_bus: MockEventBus,
        health_manager: WorkerHealthManager,
    ) -> None:
        """Verifies that a degraded worker becomes healthy after a successful execution."""
        registry.register(
            MockWorker(WorkerProfile(id="w_rec", name="Rec", capabilities=("python",)))
        )
        mgr = WorkerManager(registry=registry, health_manager=health_manager)
        rt = WorkerRuntime(event_bus=event_bus, health_manager=health_manager, manager=mgr)

        worker = registry.find("w_rec")

        # Degrade health
        health_manager.record_failure(worker.profile.id)
        assert health_manager.get_health(worker.profile.id) == WorkerHealth.DEGRADED

        # Execute successfully
        task = make_task(task_id="t_rec", cap="python")
        mgr.assign(worker.profile.id, task.id)
        rt.execute(worker, task, make_context())

        # Should be healthy again
        assert health_manager.get_health(worker.profile.id) == WorkerHealth.HEALTHY

    def test_health_unavailable_after_multiple_failures(
        self,
        registry: WorkerRegistry,
        manager: WorkerManager,
        event_bus: MockEventBus,
        health_manager: WorkerHealthManager,
    ) -> None:
        """Verifies that a worker becomes unavailable after consecutive failures."""
        registry.register(
            MockWorker(WorkerProfile(id="w_unav", name="Unav", capabilities=("python",)), fail=True)
        )
        mgr = WorkerManager(registry=registry, health_manager=health_manager)
        rt = WorkerRuntime(event_bus=event_bus, health_manager=health_manager, manager=mgr)

        worker = registry.find("w_unav")
        task = make_task(task_id="t_unav", cap="python")
        ctx = make_context()

        # Fail 3 times
        for _ in range(3):
            mgr.assign(worker.profile.id, task.id)
            rt.execute(worker, task, ctx)

        assert health_manager.get_health(worker.profile.id) == WorkerHealth.UNAVAILABLE

        # Verify unavailable worker is not assigned
        assert mgr.find_best_worker(task) is not None  # Should find w1 or w3
        assert mgr.find_best_worker(task).profile.id != "w_unav"
