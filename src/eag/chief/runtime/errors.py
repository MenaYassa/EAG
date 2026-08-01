"""Chief Runtime errors for EAG."""


class ChiefRuntimeError(Exception):
    """Base error for all Chief Runtime failures."""


class PlanningError(ChiefRuntimeError):
    """Raised when planning fails."""


class SchedulingError(ChiefRuntimeError):
    """Raised when scheduling fails."""


class ValidationError(ChiefRuntimeError):
    """Raised when validation fails."""


class CoordinationError(ChiefRuntimeError):
    """Raised when coordination fails."""


class RunStateError(ChiefRuntimeError):
    """Raised when an invalid state transition is attempted."""


class ExecutionGraphError(ChiefRuntimeError):
    """Raised when the execution graph is invalid."""