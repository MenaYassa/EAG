"""Tests for the execution domain models and lifecycle."""

from datetime import datetime
from pathlib import Path

import pytest

from eag.execution.enums import (
    ExecutionMode,
    ExecutionState,
    StepState,
)
from eag.execution.errors import (
    ExecutionError,
    InvalidExecutionTransition,
)
from eag.execution.events import (
    ExecutionCompleted,
    ExecutionStarted,
)
from eag.execution.models import (
    ExecutionCheckpoint,
    ExecutionContext,
    ExecutionMetrics,
    ExecutionReport,
    ExecutionStep,
)
from eag.execution.protocol import ExecutionRuntime


@pytest.fixture
def dummy_plan() -> dict:
    return {"id": "plan-123"}


@pytest.fixture
def context(dummy_plan) -> ExecutionContext:
    return ExecutionContext(
        approved_plan=dummy_plan,
        workspace=Path("."),
        mode=ExecutionMode.LIVE,
    )


class TestExecutionEnums:
    def test_state_is_terminal(self) -> None:
        assert ExecutionState.COMPLETED.is_terminal
        assert not ExecutionState.RUNNING.is_terminal

    def test_valid_transition(self) -> None:
        assert ExecutionState.CREATED.can_transition_to(ExecutionState.READY)
        assert ExecutionState.RUNNING.can_transition_to(ExecutionState.PAUSED)

    def test_invalid_transition(self) -> None:
        assert not ExecutionState.CREATED.can_transition_to(ExecutionState.RUNNING)
        assert not ExecutionState.COMPLETED.can_transition_to(ExecutionState.RUNNING)

    def test_rollback_transition(self) -> None:
        assert ExecutionState.FAILED.can_transition_to(ExecutionState.ROLLING_BACK)
        assert ExecutionState.ROLLING_BACK.can_transition_to(ExecutionState.ROLLED_BACK)


class TestExecutionModels:
    def test_context_is_immutable(self, context: ExecutionContext) -> None:
        with pytest.raises(Exception, match="."):
            context.mode = ExecutionMode.DRY_RUN  # type: ignore[misc]

    def test_context_requires_path(self, dummy_plan: dict) -> None:
        with pytest.raises(TypeError):
            ExecutionContext(approved_plan=dummy_plan, workspace=".")  # type: ignore[arg-type]

    def test_step_defaults(self) -> None:
        step = ExecutionStep(task={}, operation={})
        assert step.state == StepState.PENDING
        assert step.duration == 0.0
        assert step.rollback_point is None

    def test_metrics_validation(self) -> None:
        with pytest.raises(ValueError):
            ExecutionMetrics(steps_total=-1)

    def test_checkpoint_requires_name(self) -> None:
        with pytest.raises(ValueError):
            ExecutionCheckpoint(name="")

    def test_report_immutable(self) -> None:
        report = ExecutionReport(state=ExecutionState.CREATED)
        with pytest.raises(Exception, match="."):
            report.state = ExecutionState.COMPLETED  # type: ignore[misc]


class TestExecutionErrors:
    def test_hierarchy(self) -> None:
        assert issubclass(InvalidExecutionTransition, ExecutionError)

    def test_context_preserved(self) -> None:
        err = InvalidExecutionTransition("Bad transition", context={"from": "A", "to": "B"})
        assert err.context["from"] == "A"


class TestExecutionEvents:
    def test_events_are_immutable(self) -> None:
        event = ExecutionStarted(execution_id="exec-1")
        with pytest.raises(Exception, match="."):
            event.execution_id = "exec-2"  # type: ignore[misc]

    def test_event_timestamp_auto(self) -> None:
        event = ExecutionCompleted(execution_id="exec-1", success=True)
        assert isinstance(event.timestamp, datetime)


class TestExecutionProtocol:
    def test_dummy_runtime_isinstance(self) -> None:
        class DummyRuntime:
            def execute(self, context):
                return None

            def validate(self, context):
                return True

            def checkpoint(self, context, name):
                return None

            def rollback(self, context, rollback_point):
                return None

            def dry_run(self, context):
                return None

            def explain(self, report):
                return "..."

        assert isinstance(DummyRuntime(), ExecutionRuntime)
