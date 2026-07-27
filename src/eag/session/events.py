"""Execution Session events."""

from dataclasses import dataclass

from eag.events import Event
from eag.session.models import SessionMetrics


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionCreated(Event):
    session_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionStarted(Event):
    session_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionPaused(Event):
    session_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionResumed(Event):
    session_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionCompleted(Event):
    session_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionCancelled(Event):
    session_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionFailed(Event):
    session_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ChangeSetAttached(Event):
    session_id: str
    changeset_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class FailureRecorded(Event):
    session_id: str
    failure_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class MetricsUpdated(Event):
    session_id: str
    metrics: SessionMetrics
