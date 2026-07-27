"""Execution Session runtime."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import PurePosixPath
from uuid import uuid4

from eag.changeset.models import ChangeSet
from eag.changeset.recorder import ChangeSetRecorder
from eag.events import EventBus
from eag.session.errors import SessionFinalizedError, SessionStateError
from eag.session.events import (
    ChangeSetAttached,
    FailureRecorded,
    MetricsUpdated,
    SessionCancelled,
    SessionCompleted,
    SessionCreated,
    SessionFailed,
    SessionPaused,
    SessionResumed,
    SessionStarted,
)
from eag.session.failures import FailureCategory, FailureSeverity, FailureTracker
from eag.session.metrics import SessionMetricsCalculator
from eag.session.models import (
    ExecutionSession,
    SessionIdentity,
    SessionResult,
    SessionSummary,
)
from eag.session.state import SessionState
from eag.session.timeline import SessionTimeline, TimelineEventType


class ExecutionSessionRuntime:
    """Mutable runtime for orchestrating an ExecutionSession."""

    def __init__(
        self,
        *,
        workspace: PurePosixPath,
        event_bus: EventBus,
        identity: SessionIdentity | None = None,
    ) -> None:
        self._identity = identity or SessionIdentity(
            id=str(uuid4()),
            created_at=datetime.now(UTC),
        )
        self._workspace = workspace
        self._event_bus = event_bus
        self._state = SessionState.CREATED

        self._started_at: datetime | None = None
        self._completed_at: datetime | None = None

        self._timeline = SessionTimeline()
        self._failures = FailureTracker()
        self._recorder = ChangeSetRecorder(event_bus=event_bus)
        self._changesets: list[ChangeSet] = []

        self._finalized = False

        self._publish(SessionCreated)
        self._timeline.record(
            TimelineEventType.SESSION_STARTED,
            "Session runtime created",
            reference_id=self._identity.id,
        )

    @property
    def identity(self) -> SessionIdentity:
        return self._identity

    @property
    def state(self) -> SessionState:
        return self._state

    @property
    def workspace(self) -> PurePosixPath:
        return self._workspace

    @property
    def current_changeset_id(self) -> str:
        return self._recorder.identity.id

    def _ensure_not_finalized(self) -> None:
        if self._finalized:
            raise SessionFinalizedError("Runtime has been finalized.")

    def _ensure_state(self, *allowed: SessionState) -> None:
        if self._state not in allowed:
            raise SessionStateError(
                f"Operation not allowed in state {self._state.value}. "
                f"Expected one of {[s.value for s in allowed]}."
            )

    def _publish(self, event_cls: type, **kwargs: object) -> None:
        self._event_bus.publish(event_cls(session_id=self._identity.id, **kwargs))

    def _update_metrics(self) -> None:
        duration = timedelta(0)
        if self._started_at:
            end = self._completed_at or datetime.now(UTC)
            duration = end - self._started_at

        metrics = SessionMetricsCalculator.calculate(
            changesets=tuple(self._changesets),
            failures=self._failures,
            duration=duration,
        )
        self._event_bus.publish(MetricsUpdated(session_id=self._identity.id, metrics=metrics))

    def start(self) -> None:
        self._ensure_not_finalized()
        self._ensure_state(SessionState.CREATED)
        self._state = SessionState.RUNNING
        self._started_at = datetime.now(UTC)
        self._timeline.record(TimelineEventType.SESSION_STARTED, "Session started")
        self._publish(SessionStarted)
        self._update_metrics()

    def pause(self) -> None:
        self._ensure_not_finalized()
        self._ensure_state(SessionState.RUNNING)
        self._state = SessionState.PAUSED
        self._timeline.record(TimelineEventType.SESSION_PAUSED, "Session paused")
        self._publish(SessionPaused)
        self._update_metrics()

    def resume(self) -> None:
        self._ensure_not_finalized()
        self._ensure_state(SessionState.PAUSED)
        self._state = SessionState.RUNNING
        self._timeline.record(TimelineEventType.SESSION_RESUMED, "Session resumed")
        self._publish(SessionResumed)
        self._update_metrics()

    def record_failure(
        self,
        *,
        component: str,
        message: str,
        recoverable: bool,
        category: FailureCategory = FailureCategory.UNKNOWN,
        severity: FailureSeverity = FailureSeverity.ERROR,
        exception_type: str | None = None,
        **details: str,
    ) -> None:
        self._ensure_not_finalized()
        self._ensure_state(SessionState.RUNNING, SessionState.PAUSED)

        failure = self._failures.record(
            component=component,
            message=message,
            recoverable=recoverable,
            category=category,
            severity=severity,
            exception_type=exception_type,
            **details,
        )
        self._timeline.record(
            TimelineEventType.FAILURE_RECORDED,
            f"Failure recorded: {message}",
            reference_id=str(failure.id),
        )
        self._publish(FailureRecorded, failure_id=str(failure.id))
        self._update_metrics()

    def attach_changeset(self, changeset: ChangeSet) -> None:
        self._ensure_not_finalized()
        self._ensure_state(SessionState.RUNNING, SessionState.PAUSED)

        self._changesets.append(changeset)
        self._timeline.record(
            TimelineEventType.CHANGESET_CREATED,
            "ChangeSet attached",
            reference_id=changeset.identity.id,
        )
        self._publish(ChangeSetAttached, changeset_id=changeset.identity.id)
        self._update_metrics()

    def complete(self) -> None:
        self._ensure_not_finalized()
        self._ensure_state(SessionState.RUNNING, SessionState.PAUSED)
        self._state = SessionState.COMPLETED
        self._completed_at = datetime.now(UTC)
        self._timeline.record(TimelineEventType.SESSION_COMPLETED, "Session completed")
        self._publish(SessionCompleted)
        self._update_metrics()

    def cancel(self) -> None:
        self._ensure_not_finalized()
        self._ensure_state(SessionState.RUNNING, SessionState.PAUSED)
        self._state = SessionState.CANCELLED
        self._completed_at = datetime.now(UTC)
        self._timeline.record(TimelineEventType.SESSION_COMPLETED, "Session cancelled")
        self._publish(SessionCancelled)
        self._update_metrics()

    def fail(self) -> None:
        self._ensure_not_finalized()
        self._ensure_state(SessionState.RUNNING, SessionState.PAUSED)
        self._state = SessionState.FAILED
        self._completed_at = datetime.now(UTC)
        self._timeline.record(TimelineEventType.SESSION_FAILED, "Session failed")
        self._publish(SessionFailed)
        self._update_metrics()

    def finalize(self) -> ExecutionSession:
        self._ensure_not_finalized()
        self._ensure_state(SessionState.COMPLETED, SessionState.FAILED, SessionState.CANCELLED)

        duration = timedelta(0)
        if self._started_at and self._completed_at:
            duration = self._completed_at - self._started_at

        metrics = SessionMetricsCalculator.calculate(
            changesets=tuple(self._changesets),
            failures=self._failures,
            duration=duration,
        )

        if self._state == SessionState.COMPLETED:
            result = (
                SessionResult.SUCCESS
                if not self._failures.has_unrecoverable()
                else SessionResult.PARTIAL_SUCCESS
            )
        elif self._state == SessionState.FAILED:
            result = SessionResult.FAILED
        else:
            result = SessionResult.CANCELLED

        summary = SessionSummary(result=result)

        session = ExecutionSession(
            identity=self._identity,
            state=self._state.value,
            workspace=self._workspace,
            started_at=self._started_at,
            completed_at=self._completed_at,
            changesets=tuple(self._changesets),
            timeline=self._timeline.entries,
            failures=self._failures.failures,
            metrics=metrics,
            summary=summary,
        )

        self._finalized = True
        return session
