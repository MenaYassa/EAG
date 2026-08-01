"""Comprehensive tests for the Chief Runtime Platform (Sprint 7.4)."""

import pytest
from dataclasses import dataclass, field
from typing import Any
from pathlib import Path

from eag.chief.runtime import (
    ChiefRun,
    ChiefRuntime,
    Coordinator,
    DefaultValidator,
    Executor,
    Plan,
    PlanStep,
    Planner,
    RunContext,
    RunHistory,
    RunMetrics,
    RunOutcome,
    RunPhase,
    RunResult,
    RunState,
    RuntimeRegistry,
    StepResult,
    TaskScheduler,
    ValidationDecision,
    Validator,
    RunCheckpoint
)
from eag.chief.runtime.errors import ChiefRuntimeError, RunStateError, SchedulingError
from eag.chief.runtime.events import (
    ExecutionCompleted,
    ExecutionStarted,
    PlanningCompleted,
    PlanningStarted,
    RunFailed,
    RunFinished,
    ValidationCompleted,
    ValidationStarted,
)
from eag.events import EventBus


# --- Mock Components ---

# Update the MockPlanner class in tests/test_chief_runtime.py

class MockPlanner:
    def create_plan(self, context: RunContext) -> Plan:
        return Plan(steps=(
            PlanStep(step_id="step_1", name="Step 1", capability_id="analyze"),
            PlanStep(step_id="step_2", name="Step 2", capability_id="execute", dependencies=("step_1",)),
        ))


class MockExecutor:
    def __init__(self, fail_step: str | None = None) -> None:
        self._fail_step = fail_step
        self._call_count = 0

    def execute_step(self, step: PlanStep, run: ChiefRun) -> StepResult:
        self._call_count += 1
        if self._fail_step and step.name == self._fail_step:
            return StepResult(step_id=step.step_id, success=False, error="Mock failure")
        return StepResult(step_id=step.step_id, success=True, output=f"Result for {step.name}")


class AlwaysFailExecutor:
    def execute_step(self, step: PlanStep, run: ChiefRun) -> StepResult:
        return StepResult(step_id=step.step_id, success=False, error="Always fails")


@dataclass
class MockEventBus:
    published_events: list[Any] = field(default_factory=list)
    def publish(self, event: Any) -> None:
        self.published_events.append(event)


@pytest.fixture
def event_bus() -> MockEventBus:
    return MockEventBus()

@pytest.fixture
def registry() -> RuntimeRegistry:
    reg = RuntimeRegistry()
    reg.register_planner("default", MockPlanner())
    reg.register_executor("default", MockExecutor())
    reg.register_validator("default", DefaultValidator(max_retries=1))
    return reg

@pytest.fixture
def runtime(registry: RuntimeRegistry, event_bus: MockEventBus) -> ChiefRuntime:
    return ChiefRuntime(registry=registry, event_bus=event_bus)

@pytest.fixture
def context() -> RunContext:
    return RunContext(goal_text="Build a TODO app")


# --- Enum & State Tests (15) ---

class TestRunState:
    def test_initial_state(self) -> None:
        assert RunState.CREATED == "created"

    def test_terminal_states(self) -> None:
        assert RunState.COMPLETED.is_terminal is True
        assert RunState.FAILED.is_terminal is True
        assert RunState.CANCELLED.is_terminal is True
        assert RunState.EXECUTING.is_terminal is False

    def test_valid_transition(self) -> None:
        assert RunState.CREATED.can_transition_to(RunState.RECEIVED) is True
        assert RunState.RECEIVED.can_transition_to(RunState.ANALYZING) is True

    def test_invalid_transition(self) -> None:
        assert RunState.CREATED.can_transition_to(RunState.EXECUTING) is False
        assert RunState.COMPLETED.can_transition_to(RunState.EXECUTING) is False

    def test_transition_to_self(self) -> None:
        assert RunState.EXECUTING.can_transition_to(RunState.EXECUTING) is True

    def test_terminal_cannot_transition(self) -> None:
        assert RunState.COMPLETED.can_transition_to(RunState.CREATED) is False

    def test_rollback_transition(self) -> None:
        assert RunState.EXECUTING.can_transition_to(RunState.ROLLING_BACK) is True
        assert RunState.ROLLING_BACK.can_transition_to(RunState.FAILED) is True

    def test_pause_resume(self) -> None:
        assert RunState.EXECUTING.can_transition_to(RunState.PAUSED) is True
        assert RunState.PAUSED.can_transition_to(RunState.EXECUTING) is True

    def test_outcome_values(self) -> None:
        assert RunOutcome.SUCCESS == "success"
        assert RunOutcome.FAILURE == "failure"

    def test_phase_values(self) -> None:
        assert RunPhase.EXECUTION == "execution"
        assert RunPhase.PLANNING == "planning"

    def test_validation_decision_values(self) -> None:
        assert ValidationDecision.CONTINUE == "continue"
        assert ValidationDecision.RETRY == "retry"
        assert ValidationDecision.ABORT == "abort"

    def test_step_state_values(self) -> None:
        assert RunState.EXECUTING == "executing"

    def test_created_to_received(self) -> None:
        assert RunState.CREATED.can_transition_to(RunState.RECEIVED)

    def test_received_to_analyzing(self) -> None:
        assert RunState.RECEIVED.can_transition_to(RunState.ANALYZING)

    def test_ready_to_executing(self) -> None:
        assert RunState.READY.can_transition_to(RunState.EXECUTING)


# --- Model Tests (25) ---

class TestRuntimeModels:
    def test_run_context_creation(self) -> None:
        c = RunContext(goal_text="Test goal")
        assert c.goal_text == "Test goal"
        assert c.run_id is not None

    def test_run_context_empty_rejected(self) -> None:
        with pytest.raises(ValueError):
            RunContext(goal_text="")

    def test_run_context_immutable(self) -> None:
        c = RunContext(goal_text="Test")
        with pytest.raises(Exception):
            c.goal_text = "new"  # type: ignore[misc]

    def test_plan_step_creation(self) -> None:
        s = PlanStep(name="Step 1")
        assert s.name == "Step 1"
        assert s.state == "pending"

    def test_plan_step_empty_name_rejected(self) -> None:
        with pytest.raises(ValueError):
            PlanStep(name="")

    def test_plan_step_immutable(self) -> None:
        s = PlanStep(name="Test")
        with pytest.raises(Exception):
            s.name = "new"  # type: ignore[misc]

    def test_plan_creation(self) -> None:
        s = PlanStep(name="Step 1")
        p = Plan(steps=(s,))
        assert len(p.steps) == 1

    def test_plan_immutable(self) -> None:
        p = Plan()
        with pytest.raises(Exception):
            p.steps = ()  # type: ignore[misc]

    def test_step_result_creation(self) -> None:
        r = StepResult(step_id="s1", success=True)
        assert r.success is True

    def test_step_result_immutable(self) -> None:
        r = StepResult(step_id="s1", success=True)
        with pytest.raises(Exception):
            r.success = False  # type: ignore[misc]

    def test_run_result_creation(self) -> None:
        r = RunResult(run_id="r1", outcome=RunOutcome.SUCCESS)
        assert r.outcome == RunOutcome.SUCCESS

    def test_run_result_immutable(self) -> None:
        r = RunResult(run_id="r1", outcome=RunOutcome.SUCCESS)
        with pytest.raises(Exception):
            r.outcome = RunOutcome.FAILURE  # type: ignore[misc]

    def test_run_metrics_defaults(self) -> None:
        m = RunMetrics()
        assert m.planning_time_ms == 0.0
        assert m.steps_total == 0

    def test_run_metrics_immutable(self) -> None:
        m = RunMetrics()
        with pytest.raises(Exception):
            m.retries = 5  # type: ignore[misc]

    def test_chief_run_creation(self) -> None:
        ctx = RunContext(goal_text="Test")
        run = ChiefRun(context=ctx)
        assert run.state == RunState.CREATED
        assert run.run_id == ctx.run_id

    def test_chief_run_immutable(self) -> None:
        ctx = RunContext(goal_text="Test")
        run = ChiefRun(context=ctx)
        with pytest.raises(Exception):
            run.state = RunState.COMPLETED  # type: ignore[misc]

    def test_plan_step_dependencies(self) -> None:
        s = PlanStep(name="Step 2", dependencies=("s1",))
        assert "s1" in s.dependencies

    def test_plan_step_metadata(self) -> None:
        s = PlanStep(name="Step 1", metadata={"key": "value"})
        assert s.metadata["key"] == "value"

    def test_step_result_metadata(self) -> None:
        r = StepResult(step_id="s1", success=True, metadata={"key": "value"})
        assert r.metadata["key"] == "value"

    def test_run_context_metadata(self) -> None:
        c = RunContext(goal_text="Test", metadata={"key": "value"})
        assert c.metadata["key"] == "value"

    def test_run_result_summary(self) -> None:
        r = RunResult(run_id="r1", outcome=RunOutcome.SUCCESS, summary="Done")
        assert r.summary == "Done"

    def test_run_result_duration(self) -> None:
        r = RunResult(run_id="r1", outcome=RunOutcome.SUCCESS, duration_ms=100.0)
        assert r.duration_ms == 100.0

    def test_run_checkpoint_creation(self) -> None:
        cp = RunCheckpoint(step_id="s1")
        assert cp.step_id == "s1"

    def test_run_checkpoint_immutable(self) -> None:
        cp = RunCheckpoint(step_id="s1")
        with pytest.raises(Exception):
            cp.step_id = "s2"  # type: ignore[misc]

    def test_chief_run_plan_none_default(self) -> None:
        ctx = RunContext(goal_text="Test")
        run = ChiefRun(context=ctx)
        assert run.plan is None

    def test_chief_run_outcome_none_default(self) -> None:
        ctx = RunContext(goal_text="Test")
        run = ChiefRun(context=ctx)
        assert run.outcome is None


# --- Scheduler Tests (15) ---

class TestTaskScheduler:
    def test_schedule_returns_ready_steps(self) -> None:
        s1 = PlanStep(step_id="s1", name="Step 1")
        s2 = PlanStep(step_id="s2", name="Step 2", dependencies=("s1",))
        plan = Plan(steps=(s1, s2))
        scheduler = TaskScheduler()
        ready = scheduler.schedule(plan)
        assert len(ready) == 1
        assert ready[0].step_id == "s1"

    def test_schedule_respects_dependencies(self) -> None:
        s1 = PlanStep(step_id="s1", name="Step 1")
        s2 = PlanStep(step_id="s2", name="Step 2", dependencies=("s1",))
        plan = Plan(steps=(s1, s2))
        scheduler = TaskScheduler()
        ready = scheduler.schedule(plan, completed_steps={"s1"})
        assert len(ready) == 1
        assert ready[0].step_id == "s2"

    def test_get_next_step(self) -> None:
        s1 = PlanStep(step_id="s1", name="Step 1")
        plan = Plan(steps=(s1,))
        scheduler = TaskScheduler()
        step = scheduler.get_next_step(plan)
        assert step is not None
        assert step.step_id == "s1"

    def test_get_next_step_none_when_complete(self) -> None:
        s1 = PlanStep(step_id="s1", name="Step 1")
        plan = Plan(steps=(s1,))
        scheduler = TaskScheduler()
        step = scheduler.get_next_step(plan, completed_steps={"s1"})
        assert step is None

    def test_is_complete(self) -> None:
        s1 = PlanStep(step_id="s1", name="Step 1")
        plan = Plan(steps=(s1,))
        scheduler = TaskScheduler()
        assert scheduler.is_complete(plan, {"s1"}) is True

    def test_is_not_complete(self) -> None:
        s1 = PlanStep(step_id="s1", name="Step 1")
        plan = Plan(steps=(s1,))
        scheduler = TaskScheduler()
        assert scheduler.is_complete(plan, set()) is False

    def test_schedule_empty_plan(self) -> None:
        plan = Plan()
        scheduler = TaskScheduler()
        ready = scheduler.schedule(plan)
        assert len(ready) == 0

    def test_schedule_deadlock_raises(self) -> None:
        s1 = PlanStep(step_id="s1", name="Step 1", dependencies=("s2",))
        s2 = PlanStep(step_id="s2", name="Step 2", dependencies=("s1",))
        plan = Plan(steps=(s1, s2))
        scheduler = TaskScheduler()
        with pytest.raises(SchedulingError):
            scheduler.schedule(plan)

    def test_schedule_multiple_ready(self) -> None:
        s1 = PlanStep(step_id="s1", name="Step 1")
        s2 = PlanStep(step_id="s2", name="Step 2")
        plan = Plan(steps=(s1, s2))
        scheduler = TaskScheduler()
        ready = scheduler.schedule(plan)
        assert len(ready) == 2

    def test_schedule_skips_completed(self) -> None:
        s1 = PlanStep(step_id="s1", name="Step 1")
        s2 = PlanStep(step_id="s2", name="Step 2")
        plan = Plan(steps=(s1, s2))
        scheduler = TaskScheduler()
        ready = scheduler.schedule(plan, completed_steps={"s1"})
        assert len(ready) == 1
        assert ready[0].step_id == "s2"

    def test_schedule_skips_non_pending(self) -> None:
        s1 = PlanStep(step_id="s1", name="Step 1", state="success")
        s2 = PlanStep(step_id="s2", name="Step 2")
        plan = Plan(steps=(s1, s2))
        scheduler = TaskScheduler()
        ready = scheduler.schedule(plan)
        assert len(ready) == 1
        assert ready[0].step_id == "s2"

    def test_get_next_step_with_deps(self) -> None:
        s1 = PlanStep(step_id="s1", name="Step 1")
        s2 = PlanStep(step_id="s2", name="Step 2", dependencies=("s1",))
        plan = Plan(steps=(s1, s2))
        scheduler = TaskScheduler()
        assert scheduler.get_next_step(plan).step_id == "s1"
        assert scheduler.get_next_step(plan, {"s1"}).step_id == "s2"

    def test_is_complete_empty_plan(self) -> None:
        plan = Plan()
        scheduler = TaskScheduler()
        assert scheduler.is_complete(plan, set()) is True

    def test_schedule_returns_list(self) -> None:
        s1 = PlanStep(step_id="s1", name="Step 1")
        plan = Plan(steps=(s1,))
        scheduler = TaskScheduler()
        ready = scheduler.schedule(plan)
        assert isinstance(ready, list)

    def test_schedule_chain(self) -> None:
        s1 = PlanStep(step_id="s1", name="Step 1")
        s2 = PlanStep(step_id="s2", name="Step 2", dependencies=("s1",))
        s3 = PlanStep(step_id="s3", name="Step 3", dependencies=("s2",))
        plan = Plan(steps=(s1, s2, s3))
        scheduler = TaskScheduler()
        assert scheduler.get_next_step(plan).step_id == "s1"
        assert scheduler.get_next_step(plan, {"s1"}).step_id == "s2"
        assert scheduler.get_next_step(plan, {"s1", "s2"}).step_id == "s3"
        assert scheduler.get_next_step(plan, {"s1", "s2", "s3"}) is None


# --- Validator Tests (10) ---

class TestDefaultValidator:
    def test_continue_on_success(self) -> None:
        v = DefaultValidator()
        step = PlanStep(name="Step 1")
        result = StepResult(step_id=step.step_id, success=True)
        run = ChiefRun(context=RunContext(goal_text="test"))
        assert v.validate(step, result, run) == ValidationDecision.CONTINUE

    def test_retry_on_failure(self) -> None:
        v = DefaultValidator(max_retries=2)
        step = PlanStep(name="Step 1")
        result = StepResult(step_id=step.step_id, success=False)
        run = ChiefRun(context=RunContext(goal_text="test"))
        assert v.validate(step, result, run) == ValidationDecision.RETRY

    def test_abort_after_max_retries(self) -> None:
        v = DefaultValidator(max_retries=1)
        step = PlanStep(name="Step 1")
        result = StepResult(step_id=step.step_id, success=False)
        run = ChiefRun(context=RunContext(goal_text="test"))
        v.validate(step, result, run)  # First failure -> RETRY
        assert v.validate(step, result, run) == ValidationDecision.ABORT  # Second failure -> ABORT

    def test_retry_count_resets_on_success(self) -> None:
        v = DefaultValidator(max_retries=1)
        step = PlanStep(name="Step 1")
        fail_result = StepResult(step_id=step.step_id, success=False)
        success_result = StepResult(step_id=step.step_id, success=True)
        run = ChiefRun(context=RunContext(goal_text="test"))
        v.validate(step, fail_result, run)  # RETRY
        v.validate(step, success_result, run)  # CONTINUE, resets count
        assert v.validate(step, fail_result, run) == ValidationDecision.RETRY  # RETRY again

    def test_max_retries_zero(self) -> None:
        v = DefaultValidator(max_retries=0)
        step = PlanStep(name="Step 1")
        result = StepResult(step_id=step.step_id, success=False)
        run = ChiefRun(context=RunContext(goal_text="test"))
        assert v.validate(step, result, run) == ValidationDecision.ABORT


# --- Registry Tests (10) ---

class TestRuntimeRegistry:
    def test_register_planner(self) -> None:
        reg = RuntimeRegistry()
        reg.register_planner("default", MockPlanner())
        assert "default" in reg.list_planners()

    def test_register_executor(self) -> None:
        reg = RuntimeRegistry()
        reg.register_executor("default", MockExecutor())
        assert "default" in reg.list_executors()

    def test_register_validator(self) -> None:
        reg = RuntimeRegistry()
        reg.register_validator("default", DefaultValidator())
        assert "default" in reg.list_validators()

    def test_get_planner(self) -> None:
        reg = RuntimeRegistry()
        p = MockPlanner()
        reg.register_planner("default", p)
        assert reg.get_planner("default") is p

    def test_get_executor(self) -> None:
        reg = RuntimeRegistry()
        e = MockExecutor()
        reg.register_executor("default", e)
        assert reg.get_executor("default") is e

    def test_get_validator(self) -> None:
        reg = RuntimeRegistry()
        v = DefaultValidator()
        reg.register_validator("default", v)
        assert reg.get_validator("default") is v

    def test_get_missing_planner_raises(self) -> None:
        reg = RuntimeRegistry()
        with pytest.raises(ChiefRuntimeError):
            reg.get_planner("missing")

    def test_get_missing_executor_raises(self) -> None:
        reg = RuntimeRegistry()
        with pytest.raises(ChiefRuntimeError):
            reg.get_executor("missing")

    def test_list_planners_empty(self) -> None:
        reg = RuntimeRegistry()
        assert reg.list_planners() == ()

    def test_list_executors_empty(self) -> None:
        reg = RuntimeRegistry()
        assert reg.list_executors() == ()


# --- History Tests (10) ---

class TestRunHistory:
    def test_record_run(self) -> None:
        h = RunHistory()
        run = ChiefRun(context=RunContext(goal_text="test"))
        h.record(run)
        assert h.get_run(run.run_id) is run

    def test_record_result(self) -> None:
        h = RunHistory()
        result = RunResult(run_id="r1", outcome=RunOutcome.SUCCESS)
        h.record_result(result)
        assert h.get_result("r1") is result

    def test_get_missing_run(self) -> None:
        h = RunHistory()
        assert h.get_run("missing") is None

    def test_get_missing_result(self) -> None:
        h = RunHistory()
        assert h.get_result("missing") is None

    def test_list_runs(self) -> None:
        h = RunHistory()
        h.record(ChiefRun(context=RunContext(goal_text="t1")))
        h.record(ChiefRun(context=RunContext(goal_text="t2")))
        assert len(h.list_runs()) == 2

    def test_list_results(self) -> None:
        h = RunHistory()
        h.record_result(RunResult(run_id="r1", outcome=RunOutcome.SUCCESS))
        h.record_result(RunResult(run_id="r2", outcome=RunOutcome.FAILURE))
        assert len(h.list_results()) == 2

    def test_clear(self) -> None:
        h = RunHistory()
        h.record(ChiefRun(context=RunContext(goal_text="test")))
        h.clear()
        assert len(h.list_runs()) == 0

    def test_list_runs_returns_tuple(self) -> None:
        h = RunHistory()
        h.record(ChiefRun(context=RunContext(goal_text="test")))
        assert isinstance(h.list_runs(), tuple)

    def test_list_results_returns_tuple(self) -> None:
        h = RunHistory()
        h.record_result(RunResult(run_id="r1", outcome=RunOutcome.SUCCESS))
        assert isinstance(h.list_results(), tuple)

    def test_clear_results(self) -> None:
        h = RunHistory()
        h.record_result(RunResult(run_id="r1", outcome=RunOutcome.SUCCESS))
        h.clear()
        assert len(h.list_results()) == 0


# --- Coordinator & Runtime Integration Tests (20) ---

class TestCoordinatorAndRuntime:
    def test_runtime_execute_success(self, runtime: ChiefRuntime, context: RunContext) -> None:
        result = runtime.execute_goal(context)
        assert result.outcome == RunOutcome.SUCCESS, f"Run Failed! Result object: {result}"
        assert len(result.step_results) == 2
        assert all(r.success for r in result.step_results)

    def test_runtime_state_completed(self, runtime: ChiefRuntime, context: RunContext) -> None:
        runtime.execute_goal(context)
        assert runtime.state == RunState.COMPLETED

    def test_runtime_state_failed_on_error(self, registry: RuntimeRegistry, event_bus: MockEventBus, context: RunContext) -> None:
        registry.register_executor("default", AlwaysFailExecutor())
        registry.register_validator("default", DefaultValidator(max_retries=0))
        rt = ChiefRuntime(registry=registry, event_bus=event_bus)
        result = rt.execute_goal(context)
        assert result.outcome == RunOutcome.FAILURE
        assert rt.state == RunState.FAILED

    def test_events_published(self, runtime: ChiefRuntime, context: RunContext, event_bus: MockEventBus) -> None:
        runtime.execute_goal(context)
        event_types = [type(e) for e in event_bus.published_events]
        assert PlanningStarted in event_types
        assert PlanningCompleted in event_types
        assert ExecutionStarted in event_types
        assert ExecutionCompleted in event_types
        assert ValidationStarted in event_types
        assert ValidationCompleted in event_types
        assert RunFinished in event_types

    def test_planning_events_order(self, runtime: ChiefRuntime, context: RunContext, event_bus: MockEventBus) -> None:
        runtime.execute_goal(context)
        event_types = [type(e) for e in event_bus.published_events]
        planning_idx = event_types.index(PlanningStarted)
        planning_completed_idx = event_types.index(PlanningCompleted)
        assert planning_idx < planning_completed_idx

    def test_execution_events_order(self, runtime: ChiefRuntime, context: RunContext, event_bus: MockEventBus) -> None:
        runtime.execute_goal(context)
        event_types = [type(e) for e in event_bus.published_events]
        exec_idx = event_types.index(ExecutionStarted)
        exec_completed_idx = event_types.index(ExecutionCompleted)
        assert exec_idx < exec_completed_idx

    def test_run_result_has_plan(self, runtime: ChiefRuntime, context: RunContext) -> None:
        result = runtime.execute_goal(context)
        assert result.plan is not None
        assert len(result.plan.steps) == 2

    def test_run_result_duration_positive(self, runtime: ChiefRuntime, context: RunContext) -> None:
        result = runtime.execute_goal(context)
        assert result.duration_ms >= 0.0

    def test_run_result_summary(self, runtime: ChiefRuntime, context: RunContext) -> None:
        result = runtime.execute_goal(context)
        assert "Completed" in result.summary

    def test_coordinator_direct(self, event_bus: MockEventBus, context: RunContext) -> None:
        coord = Coordinator(
            planner=MockPlanner(),
            executor=MockExecutor(),
            validator=DefaultValidator(),
            event_bus=event_bus
        )
        result = coord.run(context)
        assert result.outcome == RunOutcome.SUCCESS

    def test_coordinator_failure(self, event_bus: MockEventBus, context: RunContext) -> None:
        coord = Coordinator(
            planner=MockPlanner(),
            executor=AlwaysFailExecutor(),
            validator=DefaultValidator(max_retries=0),
            event_bus=event_bus
        )
        result = coord.run(context)
        assert result.outcome == RunOutcome.FAILURE

    def test_runtime_missing_planner_raises(self, context: RunContext) -> None:
        rt = ChiefRuntime()
        with pytest.raises(ChiefRuntimeError):
            rt.execute_goal(context)

    def test_runtime_with_custom_executor(self, registry: RuntimeRegistry, event_bus: MockEventBus, context: RunContext) -> None:
        registry.register_executor("custom", MockExecutor())
        rt = ChiefRuntime(registry=registry, event_bus=event_bus)
        result = rt.execute_goal(context, executor_name="custom")
        assert result.outcome == RunOutcome.SUCCESS

    def test_runtime_retries(self, registry: RuntimeRegistry, event_bus: MockEventBus, context: RunContext) -> None:
        # Executor that fails first time, succeeds second time
        class FlakyExecutor:
            def __init__(self):
                self.calls = 0
            def execute_step(self, step: PlanStep, run: ChiefRun) -> StepResult:
                self.calls += 1
                if self.calls == 1:
                    return StepResult(step_id=step.step_id, success=False, error="Transient")
                return StepResult(step_id=step.step_id, success=True)
        
        registry.register_executor("flaky", FlakyExecutor())
        registry.register_validator("default", DefaultValidator(max_retries=2))
        rt = ChiefRuntime(registry=registry, event_bus=event_bus)
        result = rt.execute_goal(context, executor_name="flaky")
        assert result.outcome == RunOutcome.SUCCESS

    def test_runtime_abort_on_failure(self, registry: RuntimeRegistry, event_bus: MockEventBus, context: RunContext) -> None:
        registry.register_executor("default", AlwaysFailExecutor())
        registry.register_validator("default", DefaultValidator(max_retries=0))
        rt = ChiefRuntime(registry=registry, event_bus=event_bus)
        result = rt.execute_goal(context)
        assert result.outcome == RunOutcome.FAILURE
        # Only first step attempted, second step skipped
        assert len(result.step_results) == 1

    def test_run_failed_event_on_error(self, registry: RuntimeRegistry, event_bus: MockEventBus, context: RunContext) -> None:
        registry.register_executor("default", AlwaysFailExecutor())
        registry.register_validator("default", DefaultValidator(max_retries=0))
        rt = ChiefRuntime(registry=registry, event_bus=event_bus)
        rt.execute_goal(context)
        assert any(isinstance(e, RunFailed) for e in event_bus.published_events)

    def test_runtime_terminal_state_raises(self, registry: RuntimeRegistry, event_bus: MockEventBus, context: RunContext) -> None:
        rt = ChiefRuntime(registry=registry, event_bus=event_bus)
        rt._state = RunState.COMPLETED
        with pytest.raises(ChiefRuntimeError):
            rt.execute_goal(context)

    def test_validation_events_published(self, runtime: ChiefRuntime, context: RunContext, event_bus: MockEventBus) -> None:
        runtime.execute_goal(context)
        assert any(isinstance(e, ValidationStarted) for e in event_bus.published_events)
        assert any(isinstance(e, ValidationCompleted) for e in event_bus.published_events)

    def test_run_finished_event_on_success(self, runtime: ChiefRuntime, context: RunContext, event_bus: MockEventBus) -> None:
        runtime.execute_goal(context)
        assert any(isinstance(e, RunFinished) for e in event_bus.published_events)

    def test_step_results_contain_ids(self, runtime: ChiefRuntime, context: RunContext) -> None:
        result = runtime.execute_goal(context)
        assert all(r.step_id for r in result.step_results)

    def test_determinism(self, runtime: ChiefRuntime, context: RunContext) -> None:
        r1 = runtime.execute_goal(context)
        r2 = runtime.execute_goal(context)
        assert r1.outcome == r2.outcome
        assert len(r1.step_results) == len(r2.step_results)