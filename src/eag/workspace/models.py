"""Workspace domain models for EAG."""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType

from eag.workspace.enums import (
    DiffType,
    WorkspaceMode,
    WorkspaceState,
)


def _validate_non_empty_str(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} cannot be empty or whitespace")
    return value.strip()


def _validate_mapping(value: Mapping[str, str], field_name: str) -> Mapping[str, str]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a Mapping")
    return MappingProxyType(dict(value))


@dataclass(frozen=True, slots=True, kw_only=True)
class Workspace:
    """Immutable workspace descriptor."""

    workspace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    root: Path
    repository: str = ""
    mode: WorkspaceMode = WorkspaceMode.LIVE
    state: WorkspaceState = WorkspaceState.CREATING
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: Mapping[str, str] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        if not isinstance(self.root, Path):
            raise TypeError("root must be a Path")
        if not isinstance(self.mode, WorkspaceMode):
            raise TypeError("mode must be a WorkspaceMode")
        if not isinstance(self.state, WorkspaceState):
            raise TypeError("state must be a WorkspaceState")
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class FileEntry:
    """Represents a file in the workspace manifest."""

    path: str
    size: int
    hash: str
    modified_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class Manifest:
    """A catalog of workspace contents."""

    root: Path
    files: tuple[FileEntry, ...] = ()
    directories: tuple[str, ...] = ()
    ignored: tuple[str, ...] = ()
    generated: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class Snapshot:
    """An immutable snapshot of the workspace state."""

    snapshot_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    manifest: Manifest
    metadata: Mapping[str, str] = field(default_factory=dict, hash=False)


@dataclass(frozen=True, slots=True, kw_only=True)
class DiffEntry:
    """A single file change between two manifests."""

    path: str
    type: DiffType
    old_path: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkspaceMetrics:
    """Metrics collected during workspace operations."""

    files_read: int = 0
    files_written: int = 0
    directories_created: int = 0
    bytes_read: int = 0
    bytes_written: int = 0
    snapshots_created: int = 0


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkspaceHealth:
    """Health status of the workspace runtime."""

    state: WorkspaceState
    filesystem_status: str = "OK"
    validator_status: str = "OK"
    snapshot_status: str = "OK"
    locker_status: str = "OK"
    resolver_status: str = "OK"
    summary: str = "Workspace is healthy."
