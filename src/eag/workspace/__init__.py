"""Workspace Platform for EAG."""

from eag.workspace.enums import (
    DiffType,
    LockState,
    WorkspaceMode,
    WorkspaceOperation,
    WorkspaceState,
)
from eag.workspace.errors import (
    FilesystemError,
    PathTraversalError,
    WorkspaceError,
    WorkspaceLockedError,
    WorkspaceValidationError,
)
from eag.workspace.events import (
    FileRead,
    FileWritten,
    SnapshotCreated,
    WorkspaceClosed,
    WorkspaceEvent,
    WorkspaceLocked,
    WorkspaceOpened,
    WorkspaceUnlocked,
    WorkspaceValidated,
)
from eag.workspace.models import (
    DiffEntry,
    FileEntry,
    Manifest,
    Snapshot,
    Workspace,
    WorkspaceHealth,
    WorkspaceMetrics,
)
from eag.workspace.resolver import PathResolver
from eag.workspace.runtime import WorkspaceRuntime

__all__ = [
    # Enums
    "DiffType",
    "LockState",
    "WorkspaceMode",
    "WorkspaceOperation",
    "WorkspaceState",
    # Errors
    "FilesystemError",
    "PathTraversalError",
    "WorkspaceError",
    "WorkspaceLockedError",
    "WorkspaceValidationError",
    # Events
    "FileRead",
    "FileWritten",
    "SnapshotCreated",
    "WorkspaceClosed",
    "WorkspaceEvent",
    "WorkspaceLocked",
    "WorkspaceOpened",
    "WorkspaceUnlocked",
    "WorkspaceValidated",
    # Models
    "DiffEntry",
    "FileEntry",
    "Manifest",
    "Snapshot",
    "Workspace",
    "WorkspaceHealth",
    "WorkspaceMetrics",
    # Runtime
    "PathResolver",
    "WorkspaceRuntime",
]
