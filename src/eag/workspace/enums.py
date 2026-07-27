"""Workspace domain vocabulary for EAG."""

from enum import StrEnum


class WorkspaceMode(StrEnum):
    READ_ONLY = "read_only"
    DRY_RUN = "dry_run"
    LIVE = "live"


class WorkspaceState(StrEnum):
    CREATING = "creating"
    READY = "ready"
    LOCKED = "locked"
    MODIFIED = "modified"
    DIRTY = "dirty"
    FAILED = "failed"
    CLOSED = "closed"


class WorkspaceOperation(StrEnum):
    READ = "read"
    WRITE = "write"
    MOVE = "move"
    COPY = "copy"
    DELETE = "delete"
    CREATE_DIRECTORY = "create_directory"
    LIST = "list"
    SNAPSHOT = "snapshot"


class LockState(StrEnum):
    UNLOCKED = "unlocked"
    LOCKED = "locked"
    RELEASED = "released"
    EXPIRED = "expired"


class DiffType(StrEnum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    MOVED = "moved"
    UNCHANGED = "unchanged"
