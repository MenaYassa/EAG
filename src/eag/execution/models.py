"""Data models for command execution."""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any

from eag.execution.enums import (
    CheckpointType,
    ExecutionMode,
    ExecutionState,
    RollbackStrategy,
    StepState,
)


def _validate_non_empty_str(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} cannot be empty or whitespace")
    return value.strip()


def _validate_non_negative_int(value: int, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return value


def _validate_non_negative_float(value: float, field_name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative number")
    return float(value)


def _validate_mapping(value: Mapping[str, Any], field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a Mapping")
    return MappingProxyType(dict(value))


def _validate_str_tuple(value: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise TypeError(f"{field_name} must be a tuple")
    for item in value:
        if not isinstance(item, str):
            raise TypeError(f"{field_name} must contain only strings")
    return value


@dataclass(frozen=True, slots=True, kw_only=True)
class CommandRequest:
    """Request to execute a command."""

    executable: str
    arguments: tuple[str, ...] = ()
    working_directory: Path | None = None
    timeout_seconds: float = 60.0
    environment: dict[str, str] = field(default_factory=dict)
    max_output_bytes: int = 1_000_000

    def __post_init__(self) -> None:
        """Validate request parameters."""
        if not self.executable:
            raise ValueError("Executable cannot be empty")
        # Timeout and output limit validation is delegated to policy

    @property
    def argv(self) -> tuple[str, ...]:
        """Return full argument vector."""
        return (self.executable,) + self.arguments


@dataclass(frozen=True, slots=True, kw_only=True)
class CommandResult:
    """Result of a command execution."""

    request: CommandRequest
    exit_code: int | None
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool
    stdout_truncated: bool
    stderr_truncated: bool

    @property
    def succeeded(self) -> bool:
        """Return True if the command succeeded (exit code 0 and not timed out)."""
        return self.exit_code == 0 and not self.timed_out

    @property
    def failed(self) -> bool:
        """Return True if the command failed (non-zero exit code or timed out)."""
        return not self.succeeded


@dataclass(frozen=True, slots=True, kw_only=True)
class PolicyDecision:
    """Result of evaluating a command request against policy."""

    classification: str
    outcome: str
    rule: str
    reason: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionContext:
    """Context required to execute an approved plan."""

    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    approved_plan: Any
    workspace: Path
    repository: Any = None
    mode: ExecutionMode = ExecutionMode.SAFE
    initiator: str = "system"
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "execution_id", _validate_non_empty_str(self.execution_id, "execution_id")
        )
        if not isinstance(self.workspace, Path):
            raise TypeError("workspace must be a Path")
        if not isinstance(self.mode, ExecutionMode):
            raise TypeError("mode must be an ExecutionMode")
        if not isinstance(self.initiator, str):
            raise TypeError("initiator must be a str")
        if not isinstance(self.started_at, datetime):
            raise TypeError("started_at must be a datetime")
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class RollbackPoint:
    """A point in execution that can be rolled back to."""

    rollback_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    strategy: RollbackStrategy = RollbackStrategy.NONE
    checkpoint: Any = None
    can_resume: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        if not isinstance(self.strategy, RollbackStrategy):
            raise TypeError("strategy must be a RollbackStrategy")
        if not isinstance(self.can_resume, bool):
            raise TypeError("can_resume must be a bool")
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionStep:
    """A single step in the execution pipeline."""

    step_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task: Any
    operation: Any
    state: StepState = StepState.PENDING
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration: float = 0.0
    files_modified: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    rollback_point: RollbackPoint | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.state, StepState):
            raise TypeError("state must be a StepState")
        if self.started_at is not None and not isinstance(self.started_at, datetime):
            raise TypeError("started_at must be a datetime or None")
        if self.finished_at is not None and not isinstance(self.finished_at, datetime):
            raise TypeError("finished_at must be a datetime or None")
        object.__setattr__(
            self, "duration", _validate_non_negative_float(self.duration, "duration")
        )
        object.__setattr__(
            self, "files_modified", _validate_str_tuple(self.files_modified, "files_modified")
        )
        object.__setattr__(self, "warnings", _validate_str_tuple(self.warnings, "warnings"))
        if self.rollback_point is not None and not isinstance(self.rollback_point, RollbackPoint):
            raise TypeError("rollback_point must be a RollbackPoint or None")


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionCheckpoint:
    """A snapshot of state during execution."""

    checkpoint_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    type: CheckpointType = CheckpointType.AUTOMATIC
    completed_steps: tuple[str, ...] = ()
    git_reference: str | None = None
    filesystem_snapshot: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _validate_non_empty_str(self.name, "name"))
        if not isinstance(self.type, CheckpointType):
            raise TypeError("type must be a CheckpointType")
        object.__setattr__(
            self, "completed_steps", _validate_str_tuple(self.completed_steps, "completed_steps")
        )
        if self.git_reference is not None and not isinstance(self.git_reference, str):
            raise TypeError("git_reference must be a str or None")
        if self.filesystem_snapshot is not None and not isinstance(self.filesystem_snapshot, str):
            raise TypeError("filesystem_snapshot must be a str or None")


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionMetrics:
    """Metrics collected during execution."""

    steps_total: int = 0
    steps_completed: int = 0
    steps_failed: int = 0
    files_changed: int = 0
    lines_added: int = 0
    lines_removed: int = 0
    execution_time: float = 0.0

    def __post_init__(self) -> None:
        for field_name in [
            "steps_total",
            "steps_completed",
            "steps_failed",
            "files_changed",
            "lines_added",
            "lines_removed",
        ]:
            object.__setattr__(
                self, field_name, _validate_non_negative_int(getattr(self, field_name), field_name)
            )
        object.__setattr__(
            self,
            "execution_time",
            _validate_non_negative_float(self.execution_time, "execution_time"),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionResult:
    """The outcome of an execution."""

    success: bool
    metrics: ExecutionMetrics = field(default_factory=ExecutionMetrics)
    rollback: RollbackPoint | None = None
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    summary: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.success, bool):
            raise TypeError("success must be a bool")
        if not isinstance(self.metrics, ExecutionMetrics):
            raise TypeError("metrics must be ExecutionMetrics")
        if self.rollback is not None and not isinstance(self.rollback, RollbackPoint):
            raise TypeError("rollback must be a RollbackPoint or None")
        object.__setattr__(self, "warnings", _validate_str_tuple(self.warnings, "warnings"))
        object.__setattr__(self, "errors", _validate_str_tuple(self.errors, "errors"))


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionReport:
    """The final artifact produced by the ExecutionRuntime."""

    state: ExecutionState
    steps: tuple[ExecutionStep, ...] = ()
    metrics: ExecutionMetrics = field(default_factory=ExecutionMetrics)
    result: ExecutionResult | None = None
    timeline: Mapping[str, Any] = field(default_factory=dict, hash=False)
    summary: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.state, ExecutionState):
            raise TypeError("state must be an ExecutionState")
        if not isinstance(self.steps, tuple):
            raise TypeError("steps must be a tuple")
        for step in self.steps:
            if not isinstance(step, ExecutionStep):
                raise TypeError("steps must contain ExecutionStep instances")
        if self.result is not None and not isinstance(self.result, ExecutionResult):
            raise TypeError("result must be an ExecutionResult or None")
        object.__setattr__(self, "timeline", _validate_mapping(self.timeline, "timeline"))


# Append to src/eag/execution/models.py


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionRuntimeHealth:
    """Snapshot of the ExecutionRuntime's current state and subsystem health."""

    state: ExecutionState
    scheduler_status: str = "OK"
    dispatcher_status: str = "OK"
    registry_status: str = "OK"
    metrics_status: str = "OK"
    event_bus_status: str = "OK"
    summary: str = "Runtime is healthy."

    def __post_init__(self) -> None:
        if not isinstance(self.state, ExecutionState):
            raise TypeError("state must be an ExecutionState")
        for field_name in [
            "scheduler_status",
            "dispatcher_status",
            "registry_status",
            "metrics_status",
            "event_bus_status",
            "summary",
        ]:
            if not isinstance(getattr(self, field_name), str):
                raise TypeError(f"{field_name} must be a str")
