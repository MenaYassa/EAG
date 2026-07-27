"""ChangeSet subsystem errors."""


class ChangeSetError(Exception):
    """Base exception for ChangeSet subsystem."""


class ChangeSetFinalizedError(ChangeSetError):
    """Raised when modifying a finalized ChangeSetBuilder."""


class RecorderNotAttachedError(ChangeSetError):
    """Raised when a recorder operation is attempted before attaching."""


__all__ = [
    "ChangeSetError",
    "ChangeSetFinalizedError",
    "RecorderNotAttachedError",
]
