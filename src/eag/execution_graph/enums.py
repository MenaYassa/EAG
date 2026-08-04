"""Execution Graph domain vocabulary for EAG."""

from enum import StrEnum


class NodeState(StrEnum):
    """Lifecycle state of an execution node."""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class FailurePolicy(StrEnum):
    """Policies for handling failures during parallel execution."""
    FAIL_FAST = "fail_fast"
    CONTINUE = "continue"
    RETRY = "retry"
    FALLBACK = "fallback"


class MessageType(StrEnum):
    """Types of messages exchanged between workers."""
    TASK_STARTED = "task_started"
    TASK_FINISHED = "task_finished"
    ARTIFACT_READY = "artifact_ready"
    WARNING = "warning"
    FAILURE = "failure"
    REQUEST_REVIEW = "request_review"