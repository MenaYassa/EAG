"""Execution Session domain models."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import PurePosixPath
from types import MappingProxyType
from uuid import UUID

from eag.changeset.models import ChangeSet


class SessionResult(StrEnum):
    """Result of an execution session."""

    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionIdentity:
    """Identity metadata for an ExecutionSession."""

    id: str
    created_at: datetime
    parent_session: str | None = None

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Session ID cannot be empty.")
        if self.parent_session == "":
            raise ValueError("Parent session cannot be empty.")


@dataclass(frozen=True, slots=True, kw_only=True)
class TimelineEntry:
    """An entry in the session timeline."""

    timestamp: datetime
    event_type: str
    message: str
    metadata: Mapping[str, str] = field(default_factory=dict)
    reference_id: str | None = None

    def __post_init__(self) -> None:
        if not self.message.strip():
            raise ValueError("Timeline message cannot be empty.")
        if not self.event_type.strip():
            raise ValueError("Timeline event type cannot be empty.")
        if not isinstance(self.metadata, MappingProxyType):
            object.__setattr__(
                self, "metadata", MappingProxyType(dict(self.metadata))
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class FailureRecord:
    """A record of a failure during the session."""

    id: UUID
    timestamp: datetime
    component: str
    category: str
    severity: str
    message: str
    recoverable: bool
    exception_type: str | None = None
    details: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.details, MappingProxyType):
            object.__setattr__(
                self, "details", MappingProxyType(dict(self.details))
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionMetrics:
    """Aggregate metrics for an ExecutionSession."""

    changeset_count: int
    command_count: int
    file_count: int
    test_count: int
    artifact_count: int
    failure_count: int
    recoverable_failures: int
    unrecoverable_failures: int
    warning_count: int
    error_count: int
    duration: timedelta
    health_score: int

    def __post_init__(self) -> None:
        if self.health_score < 0 or self.health_score > 100:
            raise ValueError("Health score must be between 0 and 100.")


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionSummary:
    """Summary of an execution session."""

    result: SessionResult
    notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionSession:
    """The core, immutable domain object representing an engineering task session."""

    identity: SessionIdentity
    state: str
    workspace: PurePosixPath
    started_at: datetime | None = None
    completed_at: datetime | None = None
    changesets: tuple[ChangeSet, ...] = ()
    timeline: tuple[TimelineEntry, ...] = ()
    failures: tuple[FailureRecord, ...] = ()
    metrics: SessionMetrics | None = None
    summary: SessionSummary | None = None

    def __post_init__(self) -> None:
        if self.state == "created":
            if self.started_at is not None or self.completed_at is not None:
                raise ValueError(
                    "CREATED state requires started_at and completed_at to be None."
                )
        elif self.state in ("running", "paused"):
            if self.started_at is None or self.completed_at is not None:
                raise ValueError(
                    f"{self.state.upper()} state requires started_at and no completed_at."
                )
        elif (
            self.state in ("completed", "failed", "cancelled")
            and (self.started_at is None or self.completed_at is None)
        ):
            raise ValueError(
                f"{self.state.upper()} state requires started_at and completed_at."
            )

        if self.metrics is not None:
            if self.metrics.changeset_count != len(self.changesets):
                raise ValueError(
                    "Metrics changeset_count does not match actual changesets."
                )
            if self.metrics.failure_count != len(self.failures):
                raise ValueError(
                    "Metrics failure_count does not match actual failures."
                )

        if self.timeline:
            for entry in self.timeline:
                if entry.timestamp < self.timeline[0].timestamp:
                    raise ValueError("Timeline must be chronological.")


__all__ = [
    "ExecutionSession",
    "FailureRecord",
    "SessionIdentity",
    "SessionMetrics",
    "SessionResult",
    "SessionSummary",
    "TimelineEntry",
]