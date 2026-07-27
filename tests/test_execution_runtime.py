"""Tests for the execution runtime platform."""

from pathlib import Path

import pytest

from eag.events import EventBus
from eag.execution.enums import ExecutionMode, ExecutionState, StepState
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


@pytest.fixture
def dummy_plan():
    """A mock EngineeringPlanningArtifact."""

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


@pytest.fixture
def runtime(registry):
    event_bus = EventBus()
    dispatcher = Dispatcher(registry)
    return ExecutionRuntime(
        event_bus=event_bus,
        dispatcher=dispatcher,
        scheduler=Scheduler(),
        metrics=MetricsRuntime(),
        lifecycle=LifecycleManager(),
    )


class TestExecutionRuntime:
    def test_execute_success(self, runtime: ExecutionRuntime, context: ExecutionContext) -> None:
        report = runtime.execute(context)

        assert report.state == ExecutionState.COMPLETED
        assert report.result.success is True
        assert len(report.steps) == 2
        assert report.steps[0].state == StepState.SUCCESS
        assert report.metrics.steps_completed == 2

    def test_execute_failure(self, registry: ExecutorRegistry, context: ExecutionContext) -> None:
        # Setup a failing executor
        class FailingExecutor:
            @property
            def name(self) -> str:
                return "FailingExecutor"

            def supports(self, op) -> bool:
                return True

            def execute(self, op, task, ctx) -> ExecutionResult:
                return ExecutionResult(success=False, summary="Intentional failure")

        registry._executors.clear()
        registry.register(FailingExecutor())

        event_bus = EventBus()
        dispatcher = Dispatcher(registry)
        runtime = ExecutionRuntime(event_bus, dispatcher)

        report = runtime.execute(context)

        assert report.state == ExecutionState.FAILED
        assert report.result.success is False
        assert len(report.steps) == 1
        assert report.steps[0].state == StepState.FAILED

    def test_scheduler_preserves_order(self) -> None:
        scheduler = Scheduler()
        tasks = (1, 2, 3)
        assert scheduler.schedule(tasks) == tasks

    def test_registry_finds_executor(self, registry: ExecutorRegistry) -> None:
        executor = registry.find("RENAME")
        assert isinstance(executor, DummyExecutor)

    def test_lifecycle_transitions(self) -> None:
        lifecycle = LifecycleManager()
        assert lifecycle.state == ExecutionState.CREATED
        lifecycle.transition_to(ExecutionState.READY)
        assert lifecycle.state == ExecutionState.READY
