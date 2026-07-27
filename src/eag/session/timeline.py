"""Session timeline runtime."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType

from eag.session.models import TimelineEntry


class TimelineEventType(StrEnum):
    SESSION_STARTED = "session_started"
    SESSION_PAUSED = "session_paused"
    SESSION_RESUMED = "session_resumed"
    SESSION_COMPLETED = "session_completed"
    SESSION_FAILED = "session_failed"
    CHANGESET_CREATED = "changeset_created"
    COMMAND_EXECUTED = "command_executed"
    TEST_EXECUTED = "test_executed"
    FILE_CHANGED = "file_changed"
    GIT_CHECKPOINT = "git_checkpoint"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_DENIED = "approval_denied"
    FAILURE_RECORDED = "failure_recorded"


class SessionTimeline:
    """Mutable runtime container for timeline entries."""

    def __init__(self) -> None:
        self._entries: list[TimelineEntry] = []

    def record(
        self,
        event_type: TimelineEventType | str,
        message: str,
        reference_id: str | None = None,
        **metadata: str,
    ) -> TimelineEntry:
        entry = TimelineEntry(
            timestamp=datetime.now(UTC),
            event_type=event_type.value
            if isinstance(event_type, TimelineEventType)
            else event_type,
            message=message,
            metadata=MappingProxyType(metadata),
            reference_id=reference_id,
        )
        self._entries.append(entry)
        return entry

    @property
    def entries(self) -> tuple[TimelineEntry, ...]:
        return tuple(self._entries)

    def count(self) -> int:
        return len(self._entries)

    def is_empty(self) -> bool:
        return not self._entries

    def last(self) -> TimelineEntry | None:
        return self._entries[-1] if self._entries else None
