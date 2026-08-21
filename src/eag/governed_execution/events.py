"""State-controller events for the deterministic G2.4.1 execution ledger."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from eag.events import Event
from eag.governed_execution.enums import (
    GovernedExecutionState,
    GovernedExecutionStopReason,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class GovernedExecutionEvent(Event):
    """Base redacted event emitted by the G2.4.1 transition controller."""

    execution_id: str
    run_id: str
    iteration: int
    sequence: int
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True, kw_only=True)
class GovernedExecutionStarted(GovernedExecutionEvent):
    """Marks the transition from ``CREATED`` into governed execution."""

    state: GovernedExecutionState


@dataclass(frozen=True, slots=True, kw_only=True)
class GovernedExecutionTransitioned(GovernedExecutionEvent):
    """Marks one accepted legal transition and its redacted evidence count."""

    from_state: GovernedExecutionState
    to_state: GovernedExecutionState
    evidence_count: int


@dataclass(frozen=True, slots=True, kw_only=True)
class GovernedExecutionStopped(GovernedExecutionEvent):
    """Marks a deterministic terminal state with its typed reason."""

    state: GovernedExecutionState
    reason: GovernedExecutionStopReason


__all__ = [
    "GovernedExecutionEvent",
    "GovernedExecutionStarted",
    "GovernedExecutionStopped",
    "GovernedExecutionTransitioned",
]
