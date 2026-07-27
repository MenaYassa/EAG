"""Engineering Execution Platform for EAG."""

from eag.execution.enums import (
    CheckpointType,
    ExecutionMode,
    ExecutionState,
    RollbackStrategy,
    StepState,
)
from eag.execution.errors import (
    CommandStartError,
    ExecutableNotFoundError,
    ExecutionError,
    ExecutionPolicyError,
    ExecutionTimeout,
    FileModificationError,
    GitExecutionError,
    InvalidExecutionError,
    InvalidExecutionTransition,
    InvalidOutputLimitError,
    InvalidTimeoutError,
    RollbackError,
    UnsafeExecutionError,
    WorkingDirectoryOutsideWorkspaceError,
    WorkspaceError,
)
from eag.execution.errors import (
    ExecutionCancelled as ExecutionCancelledError,
)
from eag.execution.events import (
    CheckpointCreated,
    CommandExecutionCompleted,
    CommandExecutionRejected,
    CommandExecutionStarted,
    CommandExecutionTimedOut,
    ExecutionApproved,
    ExecutionCancelled,
    ExecutionCompleted,
    ExecutionEvent,
    ExecutionFailed,
    ExecutionStarted,
    ExecutionStepCompleted,
    ExecutionStepStarted,
    ExecutionValidated,
    RollbackCompleted,
    RollbackStarted,
)
from eag.execution.executor import CommandExecutor
from eag.execution.models import (
    CommandRequest,
    CommandResult,
    ExecutionCheckpoint,
    ExecutionContext,
    ExecutionMetrics,
    ExecutionReport,
    ExecutionResult,
    ExecutionRuntimeHealth,
    ExecutionStep,
    RollbackPoint,
)
from eag.execution.policy import ExecutionPolicy
from eag.execution.protocol import ExecutionRuntime as ExecutionRuntimeProtocol
from eag.execution.runtime import (
    Dispatcher,
    DummyExecutor,
    ExecutionRuntime,
    Executor,
    ExecutorRegistry,
    LifecycleManager,
    MetricsRuntime,
    Scheduler,
)

__all__ = [
    # Enums
    "CheckpointType",
    "ExecutionMode",
    "ExecutionState",
    "RollbackStrategy",
    "StepState",
    # Errors
    "CommandStartError",
    "ExecutableNotFoundError",
    "ExecutionCancelledError",
    "ExecutionError",
    "ExecutionPolicyError",
    "ExecutionTimeout",
    "FileModificationError",
    "GitExecutionError",
    "InvalidExecutionError",
    "InvalidExecutionTransition",
    "InvalidOutputLimitError",
    "InvalidTimeoutError",
    "RollbackError",
    "UnsafeExecutionError",
    "WorkingDirectoryOutsideWorkspaceError",
    "WorkspaceError",
    # Events
    "CheckpointCreated",
    "CommandExecutionCompleted",
    "CommandExecutionRejected",
    "CommandExecutionStarted",
    "CommandExecutionTimedOut",
    "ExecutionApproved",
    "ExecutionCancelled",
    "ExecutionCompleted",
    "ExecutionEvent",
    "ExecutionFailed",
    "ExecutionStarted",
    "ExecutionStepCompleted",
    "ExecutionStepStarted",
    "ExecutionValidated",
    "RollbackCompleted",
    "RollbackStarted",
    # Executor
    "CommandExecutor",
    # Models
    "CommandRequest",
    "CommandResult",
    "ExecutionCheckpoint",
    "ExecutionContext",
    "ExecutionMetrics",
    "ExecutionReport",
    "ExecutionResult",
    "ExecutionRuntimeHealth",
    "ExecutionStep",
    "RollbackPoint",
    # Policy
    "ExecutionPolicy",
    # Protocol
    "ExecutionRuntimeProtocol",
    # Runtime Platform
    "Dispatcher",
    "DummyExecutor",
    "ExecutionRuntime",
    "Executor",
    "ExecutorRegistry",
    "LifecycleManager",
    "MetricsRuntime",
    "Scheduler",
]
