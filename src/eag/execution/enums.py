"""Execution domain vocabulary for EAG."""

from enum import StrEnum


class ExecutionState(StrEnum):
    """Lifecycle state of an execution."""

    CREATED = "created"
    READY = "ready"
    VALIDATING = "validating"
    WAITING_APPROVAL = "waiting_approval"
    RUNNING = "running"
    PAUSED = "paused"
    CHECKPOINTING = "checkpointing"
    ROLLING_BACK = "rolling_back"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in {
            ExecutionState.COMPLETED,
            ExecutionState.ROLLED_BACK,
            ExecutionState.CANCELLED,
        }

    def can_transition_to(self, target: "ExecutionState") -> bool:
        if self.is_terminal:
            return False
        if self is target:
            return True

        allowed = {
            ExecutionState.CREATED: {ExecutionState.READY, ExecutionState.CANCELLED},
            ExecutionState.READY: {
                ExecutionState.VALIDATING,
                ExecutionState.RUNNING,
                ExecutionState.CANCELLED,
            },
            ExecutionState.VALIDATING: {
                ExecutionState.WAITING_APPROVAL,
                ExecutionState.FAILED,
                ExecutionState.CANCELLED,
            },
            ExecutionState.WAITING_APPROVAL: {ExecutionState.RUNNING, ExecutionState.CANCELLED},
            ExecutionState.RUNNING: {
                ExecutionState.CHECKPOINTING,
                ExecutionState.PAUSED,
                ExecutionState.FAILED,
                ExecutionState.COMPLETED,
                ExecutionState.CANCELLED,
            },
            ExecutionState.PAUSED: {ExecutionState.RUNNING, ExecutionState.CANCELLED},
            ExecutionState.CHECKPOINTING: {ExecutionState.RUNNING, ExecutionState.FAILED},
            ExecutionState.FAILED: {ExecutionState.ROLLING_BACK},
            ExecutionState.ROLLING_BACK: {ExecutionState.ROLLED_BACK, ExecutionState.FAILED},
        }
        return target in allowed.get(self, set())


class ExecutionMode(StrEnum):
    """How the execution should be carried out."""

    DRY_RUN = "dry_run"
    SAFE = "safe"
    LIVE = "live"
    RECOVERY = "recovery"


class StepState(StrEnum):
    """Lifecycle state of an individual execution step."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"


class CheckpointType(StrEnum):
    """The nature of an execution checkpoint."""

    AUTOMATIC = "automatic"
    MANUAL = "manual"
    ROLLBACK = "rollback"
    SAFETY = "safety"


class RollbackStrategy(StrEnum):
    """The mechanism used to rollback an execution."""

    NONE = "none"
    FILESYSTEM = "filesystem"
    GIT = "git"
    HYBRID = "hybrid"
