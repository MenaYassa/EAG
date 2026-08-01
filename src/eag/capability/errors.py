"""Error definitions for the capability module."""


class CapabilityError(Exception):
    """Base exception for all capability-related errors."""

    pass


class CapabilityExecutionError(CapabilityError):
    """Raised when a capability fails to execute."""

    pass


class CapabilityNotFoundError(CapabilityError):
    """Raised when a requested capability is not registered."""

    pass
