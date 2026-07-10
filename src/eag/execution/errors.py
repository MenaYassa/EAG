"""Execution subsystem errors."""

from eag.execution.classification import (
    PolicyDecision,
)


class ExecutionError(Exception):
    """Base exception for execution subsystem failures."""


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
