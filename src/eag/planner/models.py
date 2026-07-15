"""Planning domain models for EAG.

This module defines the immutable data structures that form the
Engineering Planning Platform. All models are frozen dataclasses
with slots, ensuring strict immutability and memory efficiency.
"""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any

from eag.planner.enums import (
    ExecutionMode,
    GoalType,
    PlannerRuntimeState,
    PlanningStrategy,
    PlanState,
    RiskLevel,
    TaskPriority,
)


def _validate_non_empty_str(value: str, field_name: str) -> str:
    """Validates that a value is a non-empty, non-whitespace string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} cannot be empty or whitespace")
    return value.strip()


def _validate_non_negative_int(value: int, field_name: str) -> int:
    """Validates that a value is a non-negative integer (excluding booleans)."""
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return value


def _validate_non_negative_float(value: float, field_name: str) -> float:
    """Validates that a value is a non-negative float or integer."""
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative number")
    return float(value)


def _validate_str_tuple(value: tuple[Any, ...], field_name: str) -> tuple[str, ...]:
    """Validates that a value is a tuple containing only non-empty strings."""
    if not isinstance(value, tuple):
        raise TypeError(f"{field_name} must be a tuple")
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{field_name} contains empty or non-string items")
    return value


def _validate_type_tuple(
    value: tuple[Any, ...], expected_type: type, field_name: str
) -> tuple[Any, ...]:
    """Validates that a tuple contains only elements of a specific expected type."""
    if not isinstance(value, tuple):
        raise TypeError(f"{field_name} must be a tuple")
    for item in value:
        if not isinstance(item, expected_type):
            raise TypeError(f"{field_name} items must be of type {expected_type.__name__}")
    return value


def _validate_mapping(value: Mapping[str, str], field_name: str) -> Mapping[str, str]:
    """Validates that a value is a Mapping and returns an immutable view."""
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a Mapping")
    return MappingProxyType(dict(value))


@dataclass(frozen=True, slots=True, kw_only=True)
class PlanningGoal:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal_type: GoalType
    title: str
    description: str = ""
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: Mapping[str, str] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _validate_non_empty_str(self.id, "id"))
        if not isinstance(self.goal_type, GoalType):
            raise TypeError("goal_type must be a GoalType")
        object.__setattr__(self, "title", _validate_non_empty_str(self.title, "title"))
        if not isinstance(self.description, str):
            raise TypeError("description must be a str")
        if not isinstance(self.priority, TaskPriority):
            raise TypeError("priority must be a TaskPriority")
        if not isinstance(self.created_at, datetime):
            raise TypeError("created_at must be a datetime")
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class EngineeringTask:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str = ""
    priority: TaskPriority = TaskPriority.NORMAL
    estimated_duration: float = 0.0
    dependencies: tuple[str, ...] = ()
    metadata: Mapping[str, str] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _validate_non_empty_str(self.id, "id"))
        object.__setattr__(self, "title", _validate_non_empty_str(self.title, "title"))
        if not isinstance(self.description, str):
            raise TypeError("description must be a str")
        if not isinstance(self.priority, TaskPriority):
            raise TypeError("priority must be a TaskPriority")
        object.__setattr__(
            self,
            "estimated_duration",
            _validate_non_negative_float(self.estimated_duration, "estimated_duration"),
        )
        object.__setattr__(
            self, "dependencies", _validate_str_tuple(self.dependencies, "dependencies")
        )
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionAction:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    kind: str
    target: str
    parameters: Mapping[str, str] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _validate_non_empty_str(self.id, "id"))
        object.__setattr__(self, "kind", _validate_non_empty_str(self.kind, "kind"))
        object.__setattr__(self, "target", _validate_non_empty_str(self.target, "target"))
        object.__setattr__(self, "parameters", _validate_mapping(self.parameters, "parameters"))


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionStep:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    action: ExecutionAction
    description: str = ""
    expected_result: str = ""
    rollback: str = ""
    metadata: Mapping[str, str] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _validate_non_empty_str(self.id, "id"))
        object.__setattr__(self, "task_id", _validate_non_empty_str(self.task_id, "task_id"))
        if not isinstance(self.action, ExecutionAction):
            raise TypeError("action must be an ExecutionAction")
        if not isinstance(self.description, str):
            raise TypeError("description must be a str")
        if not isinstance(self.expected_result, str):
            raise TypeError("expected_result must be a str")
        if not isinstance(self.rollback, str):
            raise TypeError("rollback must be a str")
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class PlanningStatistics:
    task_count: int = 0
    step_count: int = 0
    estimated_minutes: float = 0.0
    risk_score: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "task_count", _validate_non_negative_int(self.task_count, "task_count")
        )
        object.__setattr__(
            self, "step_count", _validate_non_negative_int(self.step_count, "step_count")
        )
        object.__setattr__(
            self,
            "estimated_minutes",
            _validate_non_negative_float(self.estimated_minutes, "estimated_minutes"),
        )
        object.__setattr__(
            self, "risk_score", _validate_non_negative_float(self.risk_score, "risk_score")
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionPlan:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal: PlanningGoal
    tasks: tuple[EngineeringTask, ...] = ()
    steps: tuple[ExecutionStep, ...] = ()
    risk: RiskLevel = RiskLevel.NONE
    state: PlanState = PlanState.CREATED
    statistics: PlanningStatistics = field(default_factory=PlanningStatistics)
    strategy: str = "Unknown"
    metadata: Mapping[str, str] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _validate_non_empty_str(self.id, "id"))
        if not isinstance(self.goal, PlanningGoal):
            raise TypeError("goal must be a PlanningGoal")
        object.__setattr__(
            self, "tasks", _validate_type_tuple(self.tasks, EngineeringTask, "tasks")
        )
        object.__setattr__(self, "steps", _validate_type_tuple(self.steps, ExecutionStep, "steps"))
        if not isinstance(self.risk, RiskLevel):
            raise TypeError("risk must be a RiskLevel")
        if not isinstance(self.state, PlanState):
            raise TypeError("state must be a PlanState")
        if not isinstance(self.statistics, PlanningStatistics):
            raise TypeError("statistics must be a PlanningStatistics")
        if not isinstance(self.strategy, str):
            raise TypeError("strategy must be a str")
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))

    @property
    def is_executable(self) -> bool:
        """Return True if the plan is in a state ready for execution."""
        return self.state in {PlanState.APPROVED, PlanState.VALIDATED}


@dataclass(frozen=True, slots=True, kw_only=True)
class PlanningResult:
    plan: ExecutionPlan
    warnings: tuple[str, ...] = ()
    risk: RiskLevel = RiskLevel.NONE
    statistics: PlanningStatistics = field(default_factory=PlanningStatistics)

    def __post_init__(self) -> None:
        if not isinstance(self.plan, ExecutionPlan):
            raise TypeError("plan must be an ExecutionPlan")
        if not isinstance(self.warnings, tuple):
            raise TypeError("warnings must be a tuple")
        if not isinstance(self.risk, RiskLevel):
            raise TypeError("risk must be a RiskLevel")
        if not isinstance(self.statistics, PlanningStatistics):
            raise TypeError("statistics must be a PlanningStatistics")


@dataclass(frozen=True, slots=True, kw_only=True)
class PlanningContext:
    """Context provided to planning strategies.

    Encapsulates all external state required to make planning decisions,
    keeping the strategy API clean and testable.
    """

    repository: Any = None
    engineering_graph: Any = None
    repository_index: Any = None
    session: Any = None
    safety_state: Any = None
    execution_mode: ExecutionMode = ExecutionMode.DRY_RUN
    strategy: PlanningStrategy = PlanningStrategy.SAFE
    metadata: Mapping[str, str] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        if not isinstance(self.execution_mode, ExecutionMode):
            raise TypeError("execution_mode must be an ExecutionMode")
        if not isinstance(self.strategy, PlanningStrategy):
            raise TypeError("strategy must be a PlanningStrategy")
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class PlanningStrategyInfo:
    """Metadata describing a planning strategy.

    This allows the registry, CLI, and future Chief AI to inspect
    capabilities without instantiating or executing the strategy.
    """

    name: str
    description: str = ""
    priority: int = 100
    supported_goal_types: tuple[GoalType, ...] = ()
    supports_parallelism: bool = False
    experimental: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _validate_non_empty_str(self.name, "name"))
        if not isinstance(self.description, str):
            raise TypeError("description must be a str")
        if not isinstance(self.priority, int) or isinstance(self.priority, bool):
            raise TypeError("priority must be an int")
        object.__setattr__(
            self,
            "supported_goal_types",
            _validate_type_tuple(self.supported_goal_types, GoalType, "supported_goal_types"),
        )
        if not isinstance(self.supports_parallelism, bool):
            raise TypeError("supports_parallelism must be a bool")
        if not isinstance(self.experimental, bool):
            raise TypeError("experimental must be a bool")


@dataclass(frozen=True, slots=True, kw_only=True)
class PlanningRuntimeMetrics:
    """Metrics tracking the performance of the PlannerRuntime."""

    plans_generated: int = 0
    successful_plans: int = 0
    failed_plans: int = 0
    average_duration: float = 0.0
    last_strategy: str | None = None
    last_goal_type: GoalType | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "plans_generated",
            _validate_non_negative_int(self.plans_generated, "plans_generated"),
        )
        object.__setattr__(
            self,
            "successful_plans",
            _validate_non_negative_int(self.successful_plans, "successful_plans"),
        )
        object.__setattr__(
            self, "failed_plans", _validate_non_negative_int(self.failed_plans, "failed_plans")
        )
        object.__setattr__(
            self,
            "average_duration",
            _validate_non_negative_float(self.average_duration, "average_duration"),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class PlanningRuntimeHealth:
    """Snapshot of the PlannerRuntime's current state."""

    state: "PlannerRuntimeState"
    strategies_registered: int
    default_strategy: str | None
    last_planning_time: float | None
    metrics: PlanningRuntimeMetrics
