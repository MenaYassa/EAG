"""Execution subsystem errors."""


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
