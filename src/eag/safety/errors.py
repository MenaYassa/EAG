"""Engineering safety subsystem errors."""


class SafetyError(Exception):
    """Base exception for safety subsystem."""


class WorkspaceUnsafeError(SafetyError):
    """Raised when the workspace is not safe for execution."""


class CheckpointError(SafetyError):
    """Raised when a checkpoint operation fails."""


class RollbackError(SafetyError):
    """Raised when a rollback operation fails."""


class UnsupportedBackendError(SafetyError):
    """Raised when an unsupported backend is requested."""


__all__ = [
    "CheckpointError",
    "RollbackError",
    "SafetyError",
    "UnsupportedBackendError",
    "WorkspaceUnsafeError",
]
