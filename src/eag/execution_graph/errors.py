"""Execution Graph errors for EAG."""


class ExecutionGraphError(Exception):
    """Base error for execution graph failures."""


class CycleError(ExecutionGraphError):
    """Raised when a cycle is detected."""


class DuplicateNodeError(ExecutionGraphError):
    """Raised when a duplicate node is added."""


class MissingNodeError(ExecutionGraphError):
    """Raised when a dependency is missing."""