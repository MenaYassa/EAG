"""Safety state definitions."""

from enum import StrEnum


class SafetyState(StrEnum):
    """States for the safety runtime."""

    UNKNOWN = "unknown"
    READY = "ready"
    CHECKPOINT_CREATED = "checkpoint_created"
    EXECUTING = "executing"
    ROLLBACK_AVAILABLE = "rollback_available"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"
    COMPLETED = "completed"


__all__ = [
    "SafetyState",
]
