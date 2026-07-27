"""Workspace domain errors for EAG."""


class WorkspaceError(Exception):
    """Base error for all workspace failures."""


class PathTraversalError(WorkspaceError):
    """Raised when a path attempts to escape the workspace root."""


class WorkspaceLockedError(WorkspaceError):
    """Raised when an operation is attempted on a locked workspace."""


class WorkspaceValidationError(WorkspaceError):
    """Raised when workspace validation fails."""


class FilesystemError(WorkspaceError):
    """Raised when a raw filesystem operation fails."""
