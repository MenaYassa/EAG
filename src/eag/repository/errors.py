class RepositoryError(Exception):
    """Base error for repository operations."""


class RepositoryNotFoundError(RepositoryError):
    """Raised when the repository directory does not exist or is inaccessible."""


class UnsupportedRepositoryError(RepositoryError):
    """Raised when the repository type is not supported."""


class ScanFailedError(RepositoryError):
    """Raised when a repository scan fails."""
