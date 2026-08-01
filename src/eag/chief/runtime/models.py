"""Chief Runtime domain models for EAG."""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any, Protocol, runtime_checkable

from eag.chief.runtime.enums import (
    RunOutcome,
    RunPhase,
    RunState,
    StepState,
    ValidationDecision,
)


def _validate_mapping(value: Mapping[str, Any], field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a Mapping")
    return MappingProxyType(dict(value))


@dataclass(frozen=True, slots=True, kw_only=True)
class RunContext:
    """Context for a Chief run."""

    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal_text: str
    priority: str = "NORMAL"
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        if not isinstance(self.goal_text, str) or not self.goal_text.strip():
            raise ValueError("goal_text cannot be empty")
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class PlanStep:
    """A single step in an execution plan."""

    step_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    capability_id: str = ""
    dependencies: tuple[str, ...] = ()
    state: StepState = StepState.PENDING
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name cannot be empty")
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class Plan:
    """An execution plan produced by the planner."""

    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    steps: tuple[PlanStep, ...] = ()
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not isinstance(self.steps, tuple):
            raise TypeError("steps must be a tuple")


@dataclass(frozen=True, slots=True, kw_only=True)
class StepResult:
    """The result of executing a single plan step."""

    step_id: str
    success: bool
    output: str = ""
    error: str | None = None
    duration_ms: float = 0.0
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        if not isinstance(self.success, bool):
            raise TypeError("success must be a bool")
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class RunResult:
    """The final result of a Chief run."""

    run_id: str
    outcome: RunOutcome
    plan: Plan | None = None
    step_results: tuple[StepResult, ...] = ()
    summary: str = ""
    duration_ms: float = 0.0


@dataclass(frozen=True, slots=True, kw_only=True)
class RunMetrics:
    """Metrics collected during a run."""

    planning_time_ms: float = 0.0
    execution_time_ms: float = 0.0
    validation_time_ms: float = 0.0
    total_duration_ms: float = 0.0
    retries: int = 0
    failures: int = 0
    steps_total: int = 0
    steps_completed: int = 0


@dataclass(frozen=True, slots=True, kw_only=True)
class RunCheckpoint:
    """A checkpoint for rollback."""

    checkpoint_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    step_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class ChiefRun:
    """The complete history of a Chief run."""

    context: RunContext
    state: RunState = RunState.CREATED
    phase: RunPhase = RunPhase.INITIALIZATION
    plan: Plan | None = None
    step_results: tuple[StepResult, ...] = ()
    checkpoints: tuple[RunCheckpoint, ...] = ()
    metrics: RunMetrics = field(default_factory=RunMetrics)
    outcome: RunOutcome | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def run_id(self) -> str:
        return self.context.run_id


@runtime_checkable
class Executor(Protocol):
    """Protocol for executing a plan step."""

    def execute_step(self, step: PlanStep, run: ChiefRun) -> StepResult: ...


@runtime_checkable
class Validator(Protocol):
    """Protocol for validating step results."""

    def validate(self, step: PlanStep, result: StepResult, run: ChiefRun) -> ValidationDecision: ...


@runtime_checkable
class Planner(Protocol):
    """Protocol for creating execution plans."""

    def create_plan(self, context: RunContext) -> Plan: ...
