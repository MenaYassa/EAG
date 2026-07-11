"""Engineering safety domain models."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import PurePosixPath
from types import MappingProxyType

from eag.safety.state import SafetyState


class SafetyBackend(StrEnum):
    """Supported backends for safety operations."""

    GIT = "git"
    FILESYSTEM = "filesystem"
    DOCKER = "docker"
    UNKNOWN = "unknown"


class WorkspaceHealth(StrEnum):
    """Health status of the workspace."""

    HEALTHY = "healthy"
    WARNING = "warning"
    UNSAFE = "unsafe"


@dataclass(frozen=True, slots=True, kw_only=True)
class Checkpoint:
    """Represents a restore point created by a safety backend."""

    id: str
    created_at: datetime
    description: str
    backend: SafetyBackend
    backend_reference: str

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Checkpoint ID cannot be empty.")
        if not self.description:
            raise ValueError("Checkpoint description cannot be empty.")
        if not self.backend_reference:
            raise ValueError("Checkpoint backend reference cannot be empty.")


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkspaceStatus:
    """Immutable snapshot of the workspace state."""

    workspace: PurePosixPath
    backend: SafetyBackend
    branch: str | None
    head: str | None
    dirty: bool
    has_untracked: bool
    has_conflicts: bool
    detached_head: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class SafetyWarning:
    """A non-blocking warning identified during workspace inspection."""

    message: str
    code: str
    details: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.message:
            raise ValueError("Warning message cannot be empty.")
        if not self.code:
            raise ValueError("Warning code cannot be empty.")
        if not isinstance(self.details, MappingProxyType):
            object.__setattr__(self, "details", MappingProxyType(dict(self.details)))

    def __hash__(self) -> int:
        return hash((self.message, self.code, tuple(self.details.items())))


@dataclass(frozen=True, slots=True, kw_only=True)
class SafetyErrorRecord:
    """A blocking error identified during workspace inspection."""

    message: str
    code: str
    details: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.message:
            raise ValueError("Error message cannot be empty.")
        if not self.code:
            raise ValueError("Error code cannot be empty.")
        if not isinstance(self.details, MappingProxyType):
            object.__setattr__(self, "details", MappingProxyType(dict(self.details)))

    def __hash__(self) -> int:
        return hash((self.message, self.code, tuple(self.details.items())))


@dataclass(frozen=True, slots=True, kw_only=True)
class RollbackResult:
    """Result of a rollback operation."""

    success: bool
    checkpoint_id: str
    duration: timedelta
    warnings: tuple[SafetyWarning, ...] = ()
    errors: tuple[SafetyErrorRecord, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class SafetyReport:
    """The immutable result of a safety inspection or operation."""

    workspace: PurePosixPath
    backend: SafetyBackend
    health: WorkspaceHealth
    status: WorkspaceStatus
    state: SafetyState
    warnings: tuple[SafetyWarning, ...] = ()
    errors: tuple[SafetyErrorRecord, ...] = ()
    checkpoint: Checkpoint | None = None


__all__ = [
    "Checkpoint",
    "RollbackResult",
    "SafetyBackend",
    "SafetyErrorRecord",
    "SafetyReport",
    "SafetyWarning",
    "WorkspaceHealth",
    "WorkspaceStatus",
]
