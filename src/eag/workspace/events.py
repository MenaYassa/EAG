"""Workspace domain events for EAG."""

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkspaceEvent:
    workspace_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkspaceOpened(WorkspaceEvent):
    root: str


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkspaceValidated(WorkspaceEvent):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class FileRead(WorkspaceEvent):
    path: str


@dataclass(frozen=True, slots=True, kw_only=True)
class FileWritten(WorkspaceEvent):
    path: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotCreated(WorkspaceEvent):
    snapshot_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkspaceLocked(WorkspaceEvent):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkspaceUnlocked(WorkspaceEvent):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkspaceClosed(WorkspaceEvent):
    pass
