"""Autonomous Loop domain vocabulary for EAG."""

from enum import StrEnum


class LoopState(StrEnum):
    """Lifecycle state of an autonomous loop."""

    CREATED = "created"
    RUNNING = "running"
    REFLECTING = "reflecting"
    REPLANNING = "replanning"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


class LoopOutcome(StrEnum):
    """The final outcome of an autonomous loop."""

    CONTINUE = "continue"
    FINISHED = "finished"
    FAILED = "failed"
    PAUSED = "paused"
    WAITING_APPROVAL = "waiting_approval"


class CompletionAction(StrEnum):
    """Actions the completion engine can recommend."""

    CONTINUE = "continue"
    STOP = "stop"
    REPLAN = "replan"
    ESCALATE = "escalate"


class RecoveryPolicy(StrEnum):
    """Policies for recovering from failures during the loop."""

    RETRY = "retry"
    DIFFERENT_WORKER = "different_worker"
    DIFFERENT_CAPABILITY = "different_capability"
    DIFFERENT_STRATEGY = "different_strategy"
    ABORT = "abort"


class RecoveryActionType(StrEnum):
    """The concrete action to take for recovery."""

    RETRY = "retry"
    EXCLUDE_WORKER = "exclude_worker"
    CHANGE_CAPABILITY = "change_capability"
    CHANGE_STRATEGY = "change_strategy"
    ABORT = "abort"


class ApprovalState(StrEnum):
    """State of an approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"
