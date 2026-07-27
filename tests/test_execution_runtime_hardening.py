"""Hardening tests for the execution runtime platform."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from eag.execution.enums import ExecutionMode, ExecutionState
from eag.execution.events import (
    ExecutionCompleted,
    ExecutionFailed,
    ExecutionStarted,
    ExecutionStepCompleted,
    ExecutionStepStarted,
)
from eag.execution.models import ExecutionContext, ExecutionResult
from eag.execution.runtime import (
    Dispatcher,
    DummyExecutor,
    ExecutionRuntime,
    ExecutorRegistry,
    LifecycleManager,
    MetricsRuntime,
    Scheduler,
)


class MockTask:
    def __init__(self, tid, title):
        self.id = tid
        self.title = title


class MockGoal:
    def __init__(self, op):
        self.operation = op


class MockPlan:
    def __init__(self, tasks):
        self.tasks = tasks
        self.engineering_goal = MockGoal("RENAME")


@pytest.fixture
def dummy_plan():
    return MockPlan(
        [
            MockTask("T1", "Task 1"),
            MockTask("T2", "Task 2"),
        ]
    )


@pytest.fixture
def context(dummy_plan):
    return ExecutionContext(approved_plan=dummy_plan, workspace=Path("."), mode=ExecutionMode.LIVE)


@pytest.fixture
def registry():
    reg = ExecutorRegistry()
    reg.register(DummyExecutor())
    return reg


@dataclass
class MockEventBus:
    published_events: list[Any] = field(default_factory=list)

    def publish(self, event: Any) -> None:
        self.published_events.append(event)


@pytest.fixture
def event_bus():
    return MockEventBus()


@pytest.fixture
def runtime(registry, event_bus):
    dispatcher = Dispatcher(registry)
    return ExecutionRuntime(
        event_bus=event_bus,
        dispatcher=dispatcher,
        scheduler=Scheduler(),
        metrics=MetricsRuntime(),
        lifecycle=LifecycleManager(),
    )


class TestRuntimeMetrics:
    def test_metrics_progress(self, runtime: ExecutionRuntime, context: ExecutionContext) -> None:
        report = runtime.execute(context)
        metrics = runtime.metrics()
        assert metrics.steps_total == 2
        assert metrics.steps_completed == 2
        assert report.metrics.steps_completed == 2

    def test_metrics_failure(
        self, registry: ExecutorRegistry, context: ExecutionContext, event_bus: MockEventBus
    ) -> None:
        class FailingExecutor:
            @property
            def name(self) -> str:
                return "FailingExecutor"

            def supports(self, op) -> bool:
                return True

            def execute(self, op, task, ctx) -> ExecutionResult:
                return ExecutionResult(success=False, summary="Fail")

        registry._executors.clear()
        registry.register(FailingExecutor())
        runtime = ExecutionRuntime(event_bus, Dispatcher(registry))

        runtime.execute(context)
        metrics = runtime.metrics()
        assert metrics.steps_failed == 1
        assert metrics.steps_completed == 0


class TestRuntimeHealth:
    def test_health_ready(self, runtime: ExecutionRuntime) -> None:
        health = runtime.health()
        assert health.state == ExecutionState.CREATED
        assert "healthy" in health.summary

    def test_health_completed(self, runtime: ExecutionRuntime, context: ExecutionContext) -> None:
        runtime.execute(context)
        health = runtime.health()
        assert health.state == ExecutionState.COMPLETED

    def test_health_failed(
        self, registry: ExecutorRegistry, context: ExecutionContext, event_bus: MockEventBus
    ) -> None:
        class FailingExecutor:
            @property
            def name(self) -> str:
                return "FailingExecutor"

            def supports(self, op) -> bool:
                return True

            def execute(self, op, task, ctx) -> ExecutionResult:
                return ExecutionResult(success=False, summary="Fail")

        registry._executors.clear()
        registry.register(FailingExecutor())
        runtime = ExecutionRuntime(event_bus, Dispatcher(registry))

        runtime.execute(context)
        health = runtime.health()
        assert health.state == ExecutionState.FAILED


class TestRuntimeExplainability:
    def test_explain_contains_state(
        self, runtime: ExecutionRuntime, context: ExecutionContext
    ) -> None:
        report = runtime.execute(context)
        explanation = runtime.explain(report)
        assert "State: COMPLETED" in explanation

    def test_explain_contains_progress(
        self, runtime: ExecutionRuntime, context: ExecutionContext
    ) -> None:
        report = runtime.execute(context)
        explanation = runtime.explain(report)
        assert "Steps Completed: 2 / 2" in explanation

    def test_explain_live_status(self, runtime: ExecutionRuntime) -> None:
        explanation = runtime.explain()
        assert "Execution Runtime Status" in explanation
        assert "State: CREATED" in explanation


class TestRuntimeEvents:
    def test_started_event(
        self, runtime: ExecutionRuntime, context: ExecutionContext, event_bus: MockEventBus
    ) -> None:
        runtime.execute(context)
        assert any(isinstance(e, ExecutionStarted) for e in event_bus.published_events)

    def test_completed_event(
        self, runtime: ExecutionRuntime, context: ExecutionContext, event_bus: MockEventBus
    ) -> None:
        runtime.execute(context)
        assert any(isinstance(e, ExecutionCompleted) for e in event_bus.published_events)

    def test_failed_event(
        self, registry: ExecutorRegistry, context: ExecutionContext, event_bus: MockEventBus
    ) -> None:
        class FailingExecutor:
            @property
            def name(self) -> str:
                return "FailingExecutor"

            def supports(self, op) -> bool:
                return True

            def execute(self, op, task, ctx) -> ExecutionResult:
                return ExecutionResult(success=False, summary="Fail")

        registry._executors.clear()
        registry.register(FailingExecutor())
        runtime = ExecutionRuntime(event_bus, Dispatcher(registry))

        runtime.execute(context)
        assert any(isinstance(e, ExecutionFailed) for e in event_bus.published_events)

    def test_event_order(
        self, runtime: ExecutionRuntime, context: ExecutionContext, event_bus: MockEventBus
    ) -> None:
        runtime.execute(context)

        event_types = [type(e) for e in event_bus.published_events]
        # Expected: Started, StepStarted, StepCompleted, StepStarted, StepCompleted, Completed
        assert event_types == [
            ExecutionStarted,
            ExecutionStepStarted,
            ExecutionStepCompleted,
            ExecutionStepStarted,
            ExecutionStepCompleted,
            ExecutionCompleted,
        ]


class TestRuntimeLifecycleControls:
    def test_pause_and_resume(self, runtime: ExecutionRuntime) -> None:
        # Manually transition to RUNNING to test pause/resume outside execute loop
        runtime._lifecycle.transition_to(ExecutionState.READY)
        runtime._lifecycle.transition_to(ExecutionState.RUNNING)

        runtime.pause()
        assert runtime.health().state == ExecutionState.PAUSED

        runtime.resume()
        assert runtime.health().state == ExecutionState.RUNNING

    def test_cancel(self, runtime: ExecutionRuntime) -> None:
        runtime._lifecycle.transition_to(ExecutionState.READY)
        runtime._lifecycle.transition_to(ExecutionState.RUNNING)

        runtime.cancel()
        assert runtime.health().state == ExecutionState.CANCELLED
