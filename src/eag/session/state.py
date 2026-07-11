"""Execution Session states."""

from enum import StrEnum


class SessionState(StrEnum):
    """States for an ExecutionSession."""

    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
