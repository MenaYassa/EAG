"""Autonomous Loop domain models for EAG."""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any

from eag.autonomous.enums import (
    ApprovalState,
    CompletionAction,
    LoopOutcome,
    LoopState,
    RecoveryActionType,
    RecoveryPolicy,
)


def _validate_mapping(value: Mapping[str, Any], field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a Mapping")
    return MappingProxyType(dict(value))


def _validate_confidence(value: float) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TypeError("confidence must be a float")
    if not (0.0 <= value <= 1.0):
        raise ValueError("confidence must be between 0.0 and 1.0")
    return float(value)


# ... [Keep existing _validate functions and LoopIteration, LoopDecision, LoopMetrics, LoopContext, LoopResult] ...


@dataclass(frozen=True, slots=True, kw_only=True)
class RecoveryAction:
    """A concrete recovery action to be applied to the next iteration."""

    action_type: RecoveryActionType
    target_worker_id: str | None = None
    new_capability: str | None = None
    new_strategy: str | None = None
    reason: str = ""


@dataclass(frozen=True, slots=True, kw_only=True)
class ApprovalRequest:
    """A request for human approval during the autonomous loop."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    loop_id: str
    iteration: int
    reason: str
    state: ApprovalState = ApprovalState.PENDING
    reviewed_by: str | None = None
    comments: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    resolved_at: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.state, ApprovalState):
            raise TypeError("state must be an ApprovalState")


@dataclass(frozen=True, slots=True, kw_only=True)
class LoopIteration:
    """Represents a single pass of the autonomous engineering loop."""

    iteration_number: int
    run_id: str
    plan_id: str
    reflection_id: str
    memory_id: str
    planning_decision_id: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    duration_ms: float = 0.0
    success: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        if not isinstance(self.iteration_number, int) or self.iteration_number < 1:
            raise ValueError("iteration_number must be a positive integer")
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class LoopDecision:
    """The decision made by the completion engine between iterations."""

    continue_loop: bool
    reason: str
    confidence: float = 1.0
    action: CompletionAction = CompletionAction.CONTINUE
    next_strategy: str | None = None
    requires_human: bool = False
    expected_improvement: float = 0.0
    recovery_policy: RecoveryPolicy = RecoveryPolicy.RETRY
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "confidence", _validate_confidence(self.confidence))
        object.__setattr__(
            self, "expected_improvement", _validate_confidence(self.expected_improvement)
        )
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class LoopMetrics:
    """Metrics for the entire autonomous loop."""

    total_iterations: int = 0
    successful_iterations: int = 0
    failed_iterations: int = 0
    total_duration_ms: float = 0.0
    replans_triggered: int = 0
    recoveries_triggered: int = 0


@dataclass(frozen=True, slots=True, kw_only=True)
class LoopContext:
    """Context for the autonomous loop."""

    loop_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal: str
    max_iterations: int = 5
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        if not isinstance(self.goal, str) or not self.goal.strip():
            raise ValueError("goal cannot be empty")
        if not isinstance(self.max_iterations, int) or self.max_iterations < 1:
            raise ValueError("max_iterations must be a positive integer")
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class LoopResult:
    """The final result of an autonomous loop."""

    loop_id: str
    state: LoopState
    outcome: LoopOutcome
    iterations: tuple[LoopIteration, ...] = ()
    final_decision: LoopDecision | None = None
    metrics: LoopMetrics = field(default_factory=LoopMetrics)
    summary: str = ""
    duration_ms: float = 0.0
    pending_approval_id: str | None = None
