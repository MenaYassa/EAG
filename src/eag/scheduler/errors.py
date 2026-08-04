"""Scheduler domain errors for EAG."""


class SchedulerError(Exception):
    """Base error for all scheduler failures."""


class DispatcherError(SchedulerError):
    """Raised when dispatching fails."""


class QueueError(SchedulerError):
    """Raised when queue operations fail."""
