"""Execution domain errors for EAG."""


class ExecutionError(Exception):
    """Base error for all execution failures."""


class ProviderUnavailableError(ExecutionError):
    """Raised when a provider is unavailable."""


class ExecutionTimeoutError(ExecutionError):
    """Raised when an execution times out."""


class ExecutionCancelledError(ExecutionError):
    """Raised when an execution is cancelled."""


class ExecutionFailedError(ExecutionError):
    """Raised when an execution fails."""


class RetryExceededError(ExecutionError):
    """Raised when retry limits are exceeded."""


class ProviderNotFoundError(ExecutionError):
    """Raised when a specific provider is not found."""


class DiscoveryFailedError(ExecutionError):
    """Raised when model discovery fails."""


class PricingUnavailableError(ExecutionError):
    """Raised when pricing information is unavailable."""


class StreamingError(ExecutionError):
    """Raised when streaming fails."""


class FallbackFailedError(ExecutionError):
    """Raised when all fallback providers fail."""
