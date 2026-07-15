"""Planning domain events for EAG.

Defines the complete lifecycle events emitted by the Planner Runtime.
Every event includes identifiers, strategy, and a timestamp, making
them extremely useful for logging, metrics, UI, and the Chief AI.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from eag.events import Event
from eag.planner.enums import ExecutionMode, GoalType, RiskLevel


@dataclass(frozen=True, slots=True, kw_only=True)
class PlanningStarted(Event):
    goal_id: str
    goal_type: GoalType
    execution_mode: ExecutionMode = ExecutionMode.DRY_RUN
    plan_id: str | None = None
    strategy: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True, kw_only=True)
class GoalValidated(Event):
    goal_id: str
    plan_id: str | None = None
    strategy: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True, kw_only=True)
class StrategySelected(Event):
    goal_id: str
    plan_id: str | None = None
    strategy: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True, kw_only=True)
class PlanGenerated(Event):
    goal_id: str
    plan_id: str
    strategy: str | None = None
    task_count: int
    step_count: int
    risk: RiskLevel
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True, kw_only=True)
class PlanValidated(Event):
    goal_id: str
    plan_id: str
    strategy: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True, kw_only=True)
class PlanningCompleted(Event):
    goal_id: str
    plan_id: str
    strategy: str | None = None
    task_count: int
    step_count: int
    risk: RiskLevel
    duration: float
    execution_mode: ExecutionMode = ExecutionMode.DRY_RUN
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True, kw_only=True)
class PlanningFailed(Event):
    goal_id: str | None
    goal_type: GoalType | None = None  # Made optional in case parsing fails early
    plan_id: str | None = None
    strategy: str | None = None
    error: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
