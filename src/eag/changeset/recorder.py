"""ChangeSet recorder subsystem."""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime, timedelta
from typing import Any

from eag.changeset.builder import ChangeSetBuilder
from eag.changeset.errors import (
    ChangeSetFinalizedError,
    RecorderNotAttachedError,
)
from eag.changeset.events import (
    ChangeSetCompleted,
    ChangeSetRecordingStarted,
)
from eag.changeset.models import ChangeIdentity, ChangeSet, CommandRecord
from eag.events import EventBus, Subscription
from eag.execution.events import (
    CommandExecutionCompleted,
    CommandExecutionRejected,
    CommandExecutionTimedOut,
)


class ChangeSetRecorder:
    """Build ChangeSets automatically from runtime events."""

    def __init__(
        self,
        *,
        event_bus: EventBus,
        identity: ChangeIdentity | None = None,
    ) -> None:
        self._event_bus = event_bus
        self._builder = ChangeSetBuilder(identity=identity, event_bus=event_bus)
        self._attached = False
        self._subscriptions: list[Subscription] = []

    @property
    def identity(self) -> ChangeIdentity:
        """Return the identity of the ChangeSet being built."""
        return self._builder._identity

    def attach(self) -> None:
        """Subscribe to runtime events."""
        if self._attached:
            return
        self._subscriptions = [
            self._event_bus.subscribe(CommandExecutionCompleted, self._on_command_completed),
            self._event_bus.subscribe(CommandExecutionTimedOut, self._on_command_timed_out),
            self._event_bus.subscribe(CommandExecutionRejected, self._on_command_rejected),
        ]
        self._attached = True
        self._event_bus.publish(ChangeSetRecordingStarted(identity_id=self.identity.id))

    def detach(self) -> None:
        """Unsubscribe from runtime events."""
        if not self._attached:
            return
        for sub in self._subscriptions:
            sub.unsubscribe()
        self._subscriptions = []
        self._attached = False

    def finalize(self) -> ChangeSet:
        """Return the completed ChangeSet."""
        if not self._attached:
            raise RecorderNotAttachedError("Recorder has not been attached to the event bus.")

        changeset = self._builder.finalize()
        self._event_bus.publish(ChangeSetCompleted(changeset=changeset))
        return changeset

    def _reset_builder(self) -> None:
        """Reset the builder for a new ChangeSet."""
        raise NotImplementedError("Resetting builder is not implemented yet.")

    def _record_command(self, record: CommandRecord) -> None:
        """Record a command and publish the event."""
        with contextlib.suppress(ChangeSetFinalizedError):
            self._builder.record_command(record)

    def _on_command_completed(self, event: CommandExecutionCompleted) -> None:
        record = self._create_command_record(event)
        self._record_command(record)

    def _on_command_timed_out(self, event: CommandExecutionTimedOut) -> None:
        record = self._create_command_record(event)
        self._record_command(record)

    def _on_command_rejected(self, event: CommandExecutionRejected) -> None:
        record = self._create_command_record(event)
        self._record_command(record)

    def _create_command_record(self, event: Any) -> CommandRecord:
        """Map an execution event to a CommandRecord."""
        now = datetime.now(UTC)

        if isinstance(event, CommandExecutionRejected):
            request = event.request
            duration = timedelta(0)
            exit_code = -1
            started_at = now
            completed_at = now
        else:
            result = event.result
            request = result.request
            duration = getattr(result, "duration", timedelta(0))
            exit_code = getattr(result, "exit_code", 0)
            started_at = getattr(result, "started_at", now - duration)
            completed_at = getattr(result, "completed_at", now)

        return CommandRecord(
            request=request,
            started_at=started_at,
            completed_at=completed_at,
            exit_code=exit_code,
            duration=duration,
        )


__all__ = [
    "ChangeSetRecorder",
]
