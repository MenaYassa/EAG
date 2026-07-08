"""Filesystem plugin errors."""


class FilesystemError(Exception):
    """Base exception for filesystem capability failures."""


class WorkspaceBoundaryError(FilesystemError):
    """Raised when a path escapes the configured workspace."""


class UnsupportedFilesystemCapabilityError(FilesystemError):
    """Raised when the tool receives an unsupported capability."""
