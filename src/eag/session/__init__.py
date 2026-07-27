"""Execution Session subsystem."""

from eag.session.errors import (
    SessionError,
    SessionFinalizedError,
    SessionStateError,
)
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
from eag.session.failures import (
    FailureCategory,
    FailureRecord,
    FailureSeverity,
    FailureTracker,
)
from eag.session.metrics import SessionMetrics, SessionMetricsCalculator
from eag.session.models import (
    ExecutionSession,
    SessionIdentity,
    SessionResult,
    SessionSummary,
    TimelineEntry,
)
from eag.session.runtime import ExecutionSessionRuntime
from eag.session.state import SessionState
from eag.session.timeline import SessionTimeline, TimelineEventType

__all__ = [
    "ChangeSetAttached",
    "ExecutionSession",
    "ExecutionSessionRuntime",
    "FailureCategory",
    "FailureRecord",
    "FailureRecorded",
    "FailureSeverity",
    "FailureTracker",
    "MetricsUpdated",
    "SessionCancelled",
    "SessionCompleted",
    "SessionCreated",
    "SessionError",
    "SessionFailed",
    "SessionFinalizedError",
    "SessionIdentity",
    "SessionMetrics",
    "SessionMetricsCalculator",
    "SessionPaused",
    "SessionResumed",
    "SessionResult",
    "SessionStarted",
    "SessionState",
    "SessionStateError",
    "SessionSummary",
    "SessionTimeline",
    "TimelineEntry",
    "TimelineEventType",
]
