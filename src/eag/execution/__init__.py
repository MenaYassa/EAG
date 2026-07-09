"""Execution engine for EAG."""

from eag.execution.errors import (
    CommandStartError,
    ExecutableNotFoundError,
    ExecutionPolicyError,
    InvalidOutputLimitError,
    InvalidTimeoutError,
    WorkingDirectoryOutsideWorkspaceError,
)
from eag.execution.events import (
    CommandExecutionCompleted,
    CommandExecutionRejected,
    CommandExecutionStarted,
    CommandExecutionTimedOut,
)
from eag.execution.executor import CommandExecutor
from eag.execution.models import CommandRequest, CommandResult
from eag.execution.policy import ExecutionPolicy

__all__ = [
    "CommandExecutor",
    "CommandRequest",
    "CommandResult",
    "ExecutionPolicy",
    "CommandStartError",
    "ExecutableNotFoundError",
    "ExecutionPolicyError",
    "InvalidOutputLimitError",
    "InvalidTimeoutError",
    "WorkingDirectoryOutsideWorkspaceError",
    "CommandExecutionCompleted",
    "CommandExecutionRejected",
    "CommandExecutionStarted",
    "CommandExecutionTimedOut",
]
