"""Chief Runtime events for EAG."""

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class RuntimeEvent:
    run_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True, kw_only=True)
class RunCreated(RuntimeEvent):
    goal_text: str


@dataclass(frozen=True, slots=True, kw_only=True)
class GoalReceived(RuntimeEvent):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class PlanningStarted(RuntimeEvent):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class PlanningCompleted(RuntimeEvent):
    plan_id: str
    step_count: int


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionStarted(RuntimeEvent):
    step_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionCompleted(RuntimeEvent):
    step_id: str
    success: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class ValidationStarted(RuntimeEvent):
    step_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ValidationCompleted(RuntimeEvent):
    step_id: str
    decision: str


@dataclass(frozen=True, slots=True, kw_only=True)
class RunFinished(RuntimeEvent):
    outcome: str


@dataclass(frozen=True, slots=True, kw_only=True)
class RunFailed(RuntimeEvent):
    error: str
