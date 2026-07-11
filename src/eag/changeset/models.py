"""ChangeSet domain models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import PurePosixPath

from eag.execution import CommandRequest


class FileChangeType(StrEnum):
    """Type of file change."""

    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


class ChangeRisk(StrEnum):
    """Risk levels for a change set."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True, kw_only=True)
class ChangeIdentity:
    """Identity metadata for a ChangeSet."""

    id: str
    created_at: datetime
    parent_id: str | None = None

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("ChangeSet ID cannot be empty.")
        if self.parent_id == "":
            raise ValueError("Parent ID cannot be empty.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ChangedFile:
    """Represents a single file change within a ChangeSet."""

    path: PurePosixPath
    change_type: FileChangeType
    lines_added: int = 0
    lines_removed: int = 0
    checksum_before: str | None = None
    checksum_after: str | None = None

    def __post_init__(self) -> None:
        if self.lines_added < 0:
            raise ValueError("lines_added cannot be negative.")
        if self.lines_removed < 0:
            raise ValueError("lines_removed cannot be negative.")

        if self.change_type == FileChangeType.ADDED:
            if self.checksum_before is not None or self.checksum_after is None:
                raise ValueError("ADDED file must have no checksum_before and a checksum_after.")
        elif self.change_type == FileChangeType.DELETED:
            if self.checksum_before is None or self.checksum_after is not None:
                raise ValueError("DELETED file must have a checksum_before and no checksum_after.")
        elif self.change_type in (FileChangeType.MODIFIED, FileChangeType.RENAMED) and (
            self.checksum_before is None or self.checksum_after is None
        ):
            raise ValueError(
                f"{self.change_type.value.upper()} file must have "
                "both checksum_before and checksum_after."
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class CommandRecord:
    """A historical record of a command execution."""

    request: CommandRequest
    started_at: datetime
    completed_at: datetime
    exit_code: int
    duration: timedelta

    def __post_init__(self) -> None:
        if self.duration.total_seconds() < 0:
            raise ValueError("Duration cannot be negative.")
        if self.completed_at - self.started_at != self.duration:
            raise ValueError(
                "Duration does not match the difference between completed_at and started_at."
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class TestRecord:
    """A historical record of a test suite execution."""

    __test__ = False  # Prevent pytest from collecting this as a test class

    suite: str
    passed: int
    failed: int
    skipped: int
    duration: timedelta

    def __post_init__(self) -> None:
        if self.passed < 0 or self.failed < 0 or self.skipped < 0:
            raise ValueError("Test counts cannot be negative.")

    @property
    def successful(self) -> bool:
        """Return True if no tests failed."""
        return self.failed == 0


@dataclass(frozen=True, slots=True, kw_only=True)
class GitSnapshot:
    """A snapshot of the Git state at a point in time."""

    branch: str
    commit: str | None
    dirty: bool
    diff_hash: str | None

    def __post_init__(self) -> None:
        if not self.branch.strip():
            raise ValueError("Branch cannot be empty.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionMetrics:
    """Aggregate metrics for a ChangeSet execution."""

    commands: int
    changed_files: int
    tests: int
    duration: timedelta
    warnings: int
    errors: int

    def __post_init__(self) -> None:
        if (
            self.commands < 0
            or self.changed_files < 0
            or self.tests < 0
            or self.warnings < 0
            or self.errors < 0
        ):
            raise ValueError("Metrics counts cannot be negative.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ChangeSummary:
    """AI-generated or manually attached summary of a ChangeSet."""

    summary: str
    risk: ChangeRisk
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.summary.strip():
            raise ValueError("Summary cannot be empty.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ChangeSet:
    """The core, immutable domain object representing an engineering change."""

    identity: ChangeIdentity
    files: tuple[ChangedFile, ...]
    commands: tuple[CommandRecord, ...]
    tests: tuple[TestRecord, ...]
    git: GitSnapshot | None = None
    metrics: ExecutionMetrics | None = None
    summary: ChangeSummary | None = None
    artifacts: tuple[PurePosixPath, ...] = ()

    def __post_init__(self) -> None:
        if self.metrics is not None:
            if self.metrics.commands != len(self.commands):
                raise ValueError("Metrics commands count does not match actual commands.")
            if self.metrics.changed_files != len(self.files):
                raise ValueError("Metrics changed_files count does not match actual files.")
            if self.metrics.tests != len(self.tests):
                raise ValueError("Metrics tests count does not match actual tests.")


__all__ = [
    "ChangeIdentity",
    "ChangeRisk",
    "ChangeSet",
    "ChangeSummary",
    "ChangedFile",
    "CommandRecord",
    "ExecutionMetrics",
    "FileChangeType",
    "GitSnapshot",
    "TestRecord",
]
