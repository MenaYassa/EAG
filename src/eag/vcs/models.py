"""Repository domain models for EAG."""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from types import MappingProxyType

from eag.vcs.enums import FileStatus, RepositoryProviderType, RepositoryState


def _validate_mapping(value: Mapping[str, str], field_name: str) -> Mapping[str, str]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a Mapping")
    return MappingProxyType(dict(value))


@dataclass(frozen=True, slots=True, kw_only=True)
class RepositoryDescriptor:
    """Immutable repository descriptor."""

    repository_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    root: Path
    provider: RepositoryProviderType = RepositoryProviderType.GIT
    state: RepositoryState = RepositoryState.UNINITIALIZED
    branch: str = "main"
    head: str = ""
    metadata: Mapping[str, str] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        if not isinstance(self.root, Path):
            raise TypeError("root must be a Path")
        if not isinstance(self.provider, RepositoryProviderType):
            raise TypeError("provider must be a RepositoryProviderType")
        if not isinstance(self.state, RepositoryState):
            raise TypeError("state must be a RepositoryState")
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class FileChange:
    """A single file change in the repository."""

    path: str
    status: FileStatus
    old_path: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, FileStatus):
            raise TypeError("status must be a FileStatus")


@dataclass(frozen=True, slots=True, kw_only=True)
class Commit:
    """A normalized commit object."""

    commit_id: str
    author: str
    timestamp: datetime
    message: str
    parents: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class RepositoryMetrics:
    """Metrics collected during repository operations."""

    commits: int = 0
    branches: int = 0
    checkouts: int = 0
    tags: int = 0
    failures: int = 0
    rollbacks: int = 0


@dataclass(frozen=True, slots=True, kw_only=True)
class RepositoryHealth:
    """Health status of the repository runtime."""

    state: RepositoryState
    provider: RepositoryProviderType
    branch: str
    head: str
    is_detached: bool = False
    summary: str = "Repository is healthy."
