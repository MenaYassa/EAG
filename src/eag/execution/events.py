"""Execution lifecycle events."""

from dataclasses import dataclass

from eag.execution.models import CommandRequest, CommandResult


@dataclass(frozen=True, slots=True, kw_only=True)
class CommandExecutionStarted:
    """Published immediately before a command starts."""

    request: CommandRequest


@dataclass(frozen=True, slots=True, kw_only=True)
class CommandExecutionCompleted:
    """Published after a command completes."""

    result: CommandResult


@dataclass(frozen=True, slots=True, kw_only=True)
class CommandExecutionTimedOut:
    """Published when command execution exceeds its timeout."""

    result: CommandResult


@dataclass(frozen=True, slots=True, kw_only=True)
class CommandExecutionRejected:
    """Published when an execution request is rejected."""

    request: CommandRequest
    error_type: str
    error_message: str
