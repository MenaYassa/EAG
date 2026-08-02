"""Worker domain errors for EAG."""


class WorkerError(Exception):
    """Base error for all worker failures."""


class WorkerNotFoundError(WorkerError):
    """Raised when a specific worker is not found."""


class WorkerBusyError(WorkerError):
    """Raised when a worker is too busy to accept a new task."""


class WorkerUnavailableError(WorkerError):
    """Raised when a worker is unavailable."""


class WorkerCapabilityError(WorkerError):
    """Raised when a worker lacks the required capability."""


class WorkerAssignmentError(WorkerError):
    """Raised when an assignment fails."""
