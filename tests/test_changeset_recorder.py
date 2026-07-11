"""Tests for the ChangeSetRecorder."""

from dataclasses import FrozenInstanceError, dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from eag.changeset.errors import ChangeSetFinalizedError, RecorderNotAttachedError
from eag.changeset.events import (
    ChangeRecorded,
    ChangeSetCompleted,
    ChangeSetRecordingStarted,
)
from eag.changeset.models import ChangeIdentity
from eag.changeset.recorder import ChangeSetRecorder
from eag.events import EventBus
from eag.execution import CommandRequest
from eag.execution.events import (
    CommandExecutionCompleted,
    CommandExecutionRejected,
    CommandExecutionTimedOut,
)


@dataclass(frozen=True)
class MockCommandResult:
    request: CommandRequest
    exit_code: int
    duration: timedelta
    started_at: datetime
    completed_at: datetime


@pytest.fixture
def event_bus() -> EventBus:
    return EventBus()


@pytest.fixture
def valid_identity() -> ChangeIdentity:
    return ChangeIdentity(
        id=str(uuid4()),
        created_at=datetime.now(UTC),
    )


class TestRecorderInitialization:
    def test_builder_exists(self, event_bus: EventBus) -> None:
        recorder = ChangeSetRecorder(event_bus=event_bus)
        assert recorder._builder is not None

    def test_identity_injection(self, event_bus: EventBus, valid_identity: ChangeIdentity) -> None:
        recorder = ChangeSetRecorder(event_bus=event_bus, identity=valid_identity)
        assert recorder.identity == valid_identity

    def test_starts_detached(self, event_bus: EventBus) -> None:
        recorder = ChangeSetRecorder(event_bus=event_bus)
        assert recorder._attached is False


class TestRecorderAttach:
    def test_attach_works(self, event_bus: EventBus) -> None:
        recorder = ChangeSetRecorder(event_bus=event_bus)
        recorder.attach()
        assert recorder._attached is True
        assert len(recorder._subscriptions) == 3

    def test_attach_twice_ignored(self, event_bus: EventBus) -> None:
        recorder = ChangeSetRecorder(event_bus=event_bus)
        recorder.attach()
        subs = recorder._subscriptions
        recorder.attach()
        assert recorder._subscriptions == subs

    def test_publishes_started_event(self, event_bus: EventBus) -> None:
        received = []
        event_bus.subscribe(ChangeSetRecordingStarted, lambda e: received.append(e))

        recorder = ChangeSetRecorder(event_bus=event_bus)
        recorder.attach()

        assert len(received) == 1
        assert received[0].identity_id == recorder.identity.id


class TestRecorderDetach:
    def test_detach_works(self, event_bus: EventBus) -> None:
        recorder = ChangeSetRecorder(event_bus=event_bus)
        recorder.attach()
        recorder.detach()
        assert recorder._attached is False
        assert len(recorder._subscriptions) == 0

    def test_detach_twice_ignored(self, event_bus: EventBus) -> None:
        recorder = ChangeSetRecorder(event_bus=event_bus)
        recorder.attach()
        recorder.detach()
        recorder.detach()
        assert recorder._attached is False


class TestRecorderRecording:
    def _publish_completed(self, event_bus: EventBus, exit_code: int = 0) -> None:
        request = CommandRequest(executable="python")
        now = datetime.now(UTC)
        result = MockCommandResult(
            request=request,
            exit_code=exit_code,
            duration=timedelta(seconds=5),
            started_at=now - timedelta(seconds=5),
            completed_at=now,
        )
        event = CommandExecutionCompleted(result=result)  # type: ignore[arg-type]
        event_bus.publish(event)

    def test_completed_command_becomes_record(self, event_bus: EventBus) -> None:
        recorder = ChangeSetRecorder(event_bus=event_bus)
        recorder.attach()
        self._publish_completed(event_bus)

        changeset = recorder.finalize()
        assert len(changeset.commands) == 1
        assert changeset.commands[0].exit_code == 0

    def test_timeout_becomes_record(self, event_bus: EventBus) -> None:
        recorder = ChangeSetRecorder(event_bus=event_bus)
        recorder.attach()

        request = CommandRequest(executable="python")
        now = datetime.now(UTC)
        result = MockCommandResult(
            request=request,
            exit_code=-1,
            duration=timedelta(seconds=1),
            started_at=now - timedelta(seconds=1),
            completed_at=now,
        )
        event = CommandExecutionTimedOut(result=result)  # type: ignore[arg-type]
        event_bus.publish(event)

        changeset = recorder.finalize()
        assert len(changeset.commands) == 1
        assert changeset.commands[0].exit_code == -1

    def test_rejection_becomes_record(self, event_bus: EventBus) -> None:
        recorder = ChangeSetRecorder(event_bus=event_bus)
        recorder.attach()

        request = CommandRequest(executable="python")
        event = CommandExecutionRejected(
            request=request,
            error_type="ValueError",
            error_message="Bad request",
        )
        event_bus.publish(event)

        changeset = recorder.finalize()
        assert len(changeset.commands) == 1
        assert changeset.commands[0].exit_code == -1

    def test_publishes_change_recorded(self, event_bus: EventBus) -> None:
        received = []
        event_bus.subscribe(ChangeRecorded, lambda e: received.append(e))

        recorder = ChangeSetRecorder(event_bus=event_bus)
        recorder.attach()
        self._publish_completed(event_bus)

        assert len(received) == 1
        assert received[0].kind == "command"


class TestRecorderFinalization:
    def test_returns_immutable_changeset(self, event_bus: EventBus) -> None:
        recorder = ChangeSetRecorder(event_bus=event_bus)
        recorder.attach()
        changeset = recorder.finalize()

        with pytest.raises(FrozenInstanceError):
            changeset.commands = ()

    def test_publishes_completed_event(self, event_bus: EventBus) -> None:
        received = []
        event_bus.subscribe(ChangeSetCompleted, lambda e: received.append(e))

        recorder = ChangeSetRecorder(event_bus=event_bus)
        recorder.attach()
        recorder.finalize()

        assert len(received) == 1

    def test_builder_finalized(self, event_bus: EventBus) -> None:
        recorder = ChangeSetRecorder(event_bus=event_bus)
        recorder.attach()
        recorder.finalize()
        assert recorder._builder._state.value == "finalized"

    def test_cannot_finalize_twice(self, event_bus: EventBus) -> None:
        recorder = ChangeSetRecorder(event_bus=event_bus)
        recorder.attach()
        recorder.finalize()

        with pytest.raises(ChangeSetFinalizedError):
            recorder.finalize()

    def test_finalize_without_attach_raises(self, event_bus: EventBus) -> None:
        recorder = ChangeSetRecorder(event_bus=event_bus)
        with pytest.raises(RecorderNotAttachedError):
            recorder.finalize()
