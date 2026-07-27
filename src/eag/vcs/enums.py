"""Repository domain vocabulary for EAG."""

from enum import StrEnum


class RepositoryProviderType(StrEnum):
    """Supported version control providers."""

    GIT = "git"
    UNKNOWN = "unknown"


class RepositoryState(StrEnum):
    """Lifecycle state of a repository."""

    UNINITIALIZED = "uninitialized"
    READY = "ready"
    DIRTY = "dirty"
    CLEAN = "clean"
    DETACHED = "detached"
    FAILED = "failed"


class FileStatus(StrEnum):
    """Status of a file in version control."""

    MODIFIED = "modified"
    ADDED = "added"
    DELETED = "deleted"
    RENAMED = "renamed"
    UNTRACKED = "untracked"
    IGNORED = "ignored"
    UNCHANGED = "unchanged"


class TransactionState(StrEnum):
    """State of a repository transaction."""

    READY = "ready"
    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"
