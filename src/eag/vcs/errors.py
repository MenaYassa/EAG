"""Repository domain errors for EAG."""


class RepositoryError(Exception):
    """Base error for all version control failures."""


class RepositoryValidationError(RepositoryError):
    """Raised when repository validation fails."""


class GitError(RepositoryError):
    """Raised when a Git command fails."""


class TransactionError(RepositoryError):
    """Raised when a transaction operation fails."""
