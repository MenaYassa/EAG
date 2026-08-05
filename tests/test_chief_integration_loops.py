"""Integration tests for Chief Runtime loops (Sprints 8, 9.1, 9.2)."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from eag.execution_graph import ExecutionGraph, ExecutionNode, ParallelExecutionRuntime
from eag.memory import InMemoryStorage, MemoryRuntime
from eag.reflection import DefaultReflectionEngine, ReflectionRuntime
from eag.reflection.models import ReflectionContext
from eag.workers import (
    WorkerContext,
    WorkerHealthManager,
    WorkerManager,
    WorkerProfile,
    WorkerRegistry,
    WorkerResult,
    WorkerRuntime,
    WorkerTask,
)

# --- Mocks ---


class MockWorker:
    def __init__(self, profile: WorkerProfile) -> None:
        self._profile = profile

    @property
    def profile(self) -> WorkerProfile:
        return self._profile

    def supports(self, task: WorkerTask) -> bool:
        return True

    def estimate(self, task: WorkerTask) -> float:
        return 1.0

    def execute(self, task: WorkerTask, context: WorkerContext) -> WorkerResult:
        return WorkerResult(
            worker_id=self.profile.id, task_id=task.id, success=True, summary="Done"
        )


@dataclass
class MockRunResult:
    run_id: str = "r1"
    outcome: str = "success"
    summary: str = "Build a FastAPI project"


@dataclass
class MockEventBus:
    published_events: list[Any] = field(default_factory=list)

    def publish(self, event: Any) -> None:
        self.published_events.append(event)


@pytest.fixture
def event_bus() -> MockEventBus:
    return MockEventBus()


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    return tmp_path


class TestChiefIntegrationLoops:
    """Verifies that the Chief orchestrates Workers, Reflection, and Memory."""

    def test_chief_delegates_to_workers(self, event_bus: MockEventBus, workspace: Path):
        """Sprint 8 Integration: Chief -> Scheduler -> Worker Runtime."""
        # 1. Setup Workers
        w_registry = WorkerRegistry()
        w_registry.register(
            MockWorker(WorkerProfile(id="w1", name="Alice", capabilities=("python",)))
        )
        w_manager = WorkerManager(registry=w_registry, health_manager=WorkerHealthManager())
        w_runtime = WorkerRuntime(
            event_bus=event_bus, health_manager=WorkerHealthManager(), manager=w_manager
        )

        # 2. Setup Execution Graph & Parallel Runtime
        graph = ExecutionGraph(nodes=(ExecutionNode(id="n1", task_id="t1", title="Build"),))
        p_runtime = ParallelExecutionRuntime(
            event_bus=event_bus, manager=w_manager, worker_runtime=w_runtime
        )

        # 3. Setup Chief to use Parallel Runtime instead of Capability Runtime
        # (Simulated by having the coordinator pass work to p_runtime)
        context = WorkerContext(run_id="r1", goal="Test", workspace=workspace)
        completed, failed = p_runtime.execute(graph, context)

        assert len(completed) == 1
        assert len(failed) == 0
        assert w_manager.get_state("w1") == "idle"  # Worker released

    def test_chief_triggers_reflection(self, event_bus: MockEventBus, workspace: Path):
        """Sprint 9.1 Integration: Chief -> Reflection Runtime."""
        # 1. Setup Reflection
        ref_engine = DefaultReflectionEngine()
        ref_runtime = ReflectionRuntime(engine=ref_engine, event_bus=event_bus)

        # 2. Simulate end of Chief Run
        run_result = MockRunResult(run_id="r1", outcome="success", summary="FastAPI")
        ref_ctx = ReflectionContext(run_id="r1", run_result=run_result)

        # 3. Trigger Reflection
        report = ref_runtime.reflect(ref_ctx)

        assert report is not None
        assert report.run_id == "r1"
        assert any("Successful" in f.title for f in report.findings)
        assert any(
            isinstance(e, type(event_bus.published_events[0])) for e in event_bus.published_events
        )

    def test_chief_stores_memory(self, event_bus: MockEventBus, workspace: Path):
        """Sprint 9.2 Integration: Reflection -> Memory Runtime."""
        # 1. Setup Memory
        mem_storage = InMemoryStorage()
        mem_runtime = MemoryRuntime(storage=mem_storage, event_bus=event_bus)

        # 2. Setup Reflection
        ref_engine = DefaultReflectionEngine()
        ref_runtime = ReflectionRuntime(engine=ref_engine, event_bus=event_bus)
        run_result = MockRunResult(run_id="r1", outcome="success", summary="FastAPI")
        ref_ctx = ReflectionContext(run_id="r1", run_result=run_result)
        report = ref_runtime.reflect(ref_ctx)

        # 3. Store in Memory
        entry = mem_runtime.store_reflection(ref_ctx, report)

        assert mem_runtime.statistics().total_runs == 1
        assert mem_runtime.retrieve(entry.id).run_id == "r1"

        # 4. Retrieve Experience
        exp = mem_runtime.get_relevant_experience("FastAPI")
        assert exp is not None
        assert exp.project_type == "fastapi"
