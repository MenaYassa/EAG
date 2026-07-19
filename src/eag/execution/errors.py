"""Execution subsystem errors."""

from typing import Any

from eag.execution.classification import (
    PolicyDecision,
)


class ExecutionError(Exception):
    """Base error for all execution failures."""

    def __init__(self, message: str, *, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.context = context or {}


class ExecutionPolicyError(ExecutionError):
    """Raised when a command request violates execution policy."""


class WorkingDirectoryOutsideWorkspaceError(ExecutionPolicyError):
    """Raised when a working directory escapes the workspace."""


class InvalidTimeoutError(ExecutionPolicyError):
    """Raised when a timeout violates execution policy."""


class InvalidOutputLimitError(ExecutionPolicyError):
    """Raised when an output limit violates execution policy."""


class ExecutableNotFoundError(ExecutionError):
    """Raised when a requested executable cannot be found."""


class CommandStartError(ExecutionError):
    """Raised when a command process cannot be started."""


class CommandPolicyDecisionError(ExecutionPolicyError):
    """Base error for rejected policy decisions."""

    def __init__(
        self,
        decision: PolicyDecision,
    ) -> None:
        self.decision = decision
        super().__init__(decision.reason)


class CommandApprovalRequiredError(CommandPolicyDecisionError):
    """Raised when a command requires explicit approval."""


class CommandDeniedError(CommandPolicyDecisionError):
    """Raised when command policy denies execution."""


class InvalidExecutionError(ExecutionError):
    """Raised when an execution request is invalid."""


class InvalidExecutionTransition(ExecutionError):
    """Raised when an invalid state transition is attempted."""


class WorkspaceError(ExecutionError):
    """Raised when a workspace operation fails."""


class GitExecutionError(ExecutionError):
    """Raised when a Git operation fails during execution."""


class FileModificationError(ExecutionError):
    """Raised when a file modification fails."""


class UnsafeExecutionError(ExecutionError):
    """Raised when an execution is halted by safety rules."""


class RollbackError(ExecutionError):
    """Raised when a rollback operation fails."""


class ExecutionTimeout(ExecutionError):
    """Raised when an execution exceeds its time limit."""


class ExecutionCancelled(ExecutionError):
    """Raised when an execution is cancelled by the user or system."""
