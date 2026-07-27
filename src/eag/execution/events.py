"""Execution lifecycle events."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from eag.events import Event
from eag.execution.models import (
    CommandRequest,
    CommandResult,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class CommandExecutionStarted(Event):
    """Published immediately before a command starts."""

    request: CommandRequest


@dataclass(frozen=True, slots=True, kw_only=True)
class CommandExecutionCompleted(Event):
    """Published after a command completes."""

    result: CommandResult


@dataclass(frozen=True, slots=True, kw_only=True)
class CommandExecutionTimedOut(Event):
    """Published when command execution exceeds its timeout."""

    result: CommandResult


@dataclass(frozen=True, slots=True, kw_only=True)
class CommandExecutionRejected(Event):
    """Published when an execution request is rejected."""

    request: CommandRequest
    error_type: str
    error_message: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionEvent:
    """Base class for execution events."""

    execution_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionStarted(ExecutionEvent):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionValidated(ExecutionEvent):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionApproved(ExecutionEvent):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionStepStarted(ExecutionEvent):
    step_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionStepCompleted(ExecutionEvent):
    step_id: str
    success: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class CheckpointCreated(ExecutionEvent):
    checkpoint_id: str
    name: str


@dataclass(frozen=True, slots=True, kw_only=True)
class RollbackStarted(ExecutionEvent):
    rollback_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class RollbackCompleted(ExecutionEvent):
    rollback_id: str
    success: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionCompleted(ExecutionEvent):
    success: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionFailed(ExecutionEvent):
    error: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionCancelled(ExecutionEvent):
    reason: str
