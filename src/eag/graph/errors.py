class GraphError(Exception):
    """Base error for engineering graph operations."""


class GraphValidationError(GraphError):
    """Raised when graph validation fails."""


class GraphBuildError(GraphError):
    """Raised when graph building fails."""


class GraphQueryError(GraphError):
    """Raised when a graph query fails."""


class GraphNotLoadedError(GraphError):
    """Raised when an operation requires a loaded graph but none exists."""
