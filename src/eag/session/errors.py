"""Execution Session subsystem errors."""


class SessionError(Exception):
    """Base exception for Execution Session subsystem."""


class SessionStateError(SessionError):
    """Raised when an invalid state transition is attempted."""


class SessionFinalizedError(SessionError):
    """Raised when modifying a finalized ExecutionSessionRuntime."""
