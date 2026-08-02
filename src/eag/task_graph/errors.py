"""Task Graph domain errors for EAG."""


class TaskGraphError(Exception):
    """Base error for all task graph failures."""


class CycleError(TaskGraphError):
    """Raised when a cycle is detected in the graph."""


class DuplicateNodeError(TaskGraphError):
    """Raised when a node with the same ID is added twice."""


class DuplicateEdgeError(TaskGraphError):
    """Raised when a duplicate edge is added."""


class MissingNodeError(TaskGraphError):
    """Raised when an edge references a missing node."""


class SelfDependencyError(TaskGraphError):
    """Raised when a node depends on itself."""