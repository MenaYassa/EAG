"""Tests for the ExecutionSession subsystem."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from pathlib import PurePosixPath
from uuid import uuid4

import pytest

from eag.changeset.models import ChangeIdentity, ChangeSet
from eag.events import EventBus
from eag.session import (
    ExecutionSessionRuntime,
    FailureCategory,
    FailureSeverity,
    SessionIdentity,
    SessionState,
    SessionStateError,
    TimelineEntry,
)
from eag.session.errors import SessionFinalizedError


@pytest.fixture
def event_bus() -> EventBus:
    return EventBus()


@pytest.fixture
def workspace() -> PurePosixPath:
    return PurePosixPath("/tmp/workspace")


@pytest.fixture
def valid_identity() -> SessionIdentity:
    return SessionIdentity(
        id=str(uuid4()),
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def runtime(event_bus: EventBus, workspace: PurePosixPath) -> ExecutionSessionRuntime:
    return ExecutionSessionRuntime(event_bus=event_bus, workspace=workspace)


@pytest.fixture
def completed_changeset() -> ChangeSet:
    return ChangeSet(
        identity=ChangeIdentity(id="cs1", created_at=datetime.now(UTC)),
        files=(),
        commands=(),
        tests=(),
    )


class TestSessionModels:
    def test_session_identity_validation(self) -> None:
        with pytest.raises(ValueError, match="cannot be empty"):
            SessionIdentity(id="", created_at=datetime.now(UTC))

    def test_timeline_entry_immutable(self) -> None:
        entry = TimelineEntry(
            timestamp=datetime.now(UTC),
            event_type="test",
            message="test",
        )
        with pytest.raises(FrozenInstanceError):
            entry.message = "new"  # type: ignore[misc]


class TestSessionRuntimeInitialization:
    def test_initial_state(
        self,
        runtime: ExecutionSessionRuntime,
        workspace: PurePosixPath,
    ) -> None:
        assert runtime.state == SessionState.CREATED
        assert runtime.workspace == workspace
        assert runtime.identity.id is not None

    def test_current_changeset_id(
        self, runtime: ExecutionSessionRuntime
    ) -> None:
        assert runtime.current_changeset_id is not None


class TestSessionRuntimeTransitions:
    def test_start(
        self, runtime: ExecutionSessionRuntime
    ) -> None:
        runtime.start()
        assert runtime.state == SessionState.RUNNING

    def test_pause_and_resume(
        self, runtime: ExecutionSessionRuntime
    ) -> None:
        runtime.start()
        runtime.pause()
        assert runtime.state == SessionState.PAUSED
        runtime.resume()
        assert runtime.state == SessionState.RUNNING

    def test_complete(
        self, runtime: ExecutionSessionRuntime
    ) -> None:
        runtime.start()
        runtime.complete()
        assert runtime.state == SessionState.COMPLETED

    def test_fail(
        self, runtime: ExecutionSessionRuntime
    ) -> None:
        runtime.start()
        runtime.fail()
        assert runtime.state == SessionState.FAILED

    def test_cancel(
        self, runtime: ExecutionSessionRuntime
    ) -> None:
        runtime.start()
        runtime.cancel()
        assert runtime.state == SessionState.CANCELLED

    def test_illegal_start(
        self, runtime: ExecutionSessionRuntime
    ) -> None:
        runtime.start()
        with pytest.raises(SessionStateError):
            runtime.start()

    def test_illegal_complete(
        self, runtime: ExecutionSessionRuntime
    ) -> None:
        with pytest.raises(SessionStateError):
            runtime.complete()


class TestSessionRuntimeRecording:
    def test_record_failure(
        self, runtime: ExecutionSessionRuntime
    ) -> None:
        runtime.start()
        runtime.record_failure(
            component="executor",
            message="Timeout",
            recoverable=True,
            category=FailureCategory.EXECUTION,
            severity=FailureSeverity.ERROR,
        )
        assert runtime._failures.count() == 1
        assert runtime._failures.has_recoverable() is True

    def test_attach_changeset(
        self,
        runtime: ExecutionSessionRuntime,
        completed_changeset: ChangeSet,
    ) -> None:
        runtime.start()
        runtime.attach_changeset(completed_changeset)
        assert len(runtime._changesets) == 1
        assert runtime._changesets[0] == completed_changeset


class TestSessionRuntimeFinalization:
    def test_finalize(
        self,
        runtime: ExecutionSessionRuntime,
        completed_changeset: ChangeSet,
    ) -> None:
        runtime.start()
        runtime.attach_changeset(completed_changeset)
        runtime.complete()

        session = runtime.finalize()
        assert session.state == "completed"
        assert len(session.changesets) == 1
        assert session.metrics is not None
        assert session.metrics.changeset_count == 1
        assert session.summary is not None

    def test_finalize_illegal(
        self, runtime: ExecutionSessionRuntime
    ) -> None:
        runtime.start()
        with pytest.raises(SessionStateError):
            runtime.finalize()

    def test_finalize_twice(
        self, runtime: ExecutionSessionRuntime
    ) -> None:
        runtime.start()
        runtime.complete()
        runtime.finalize()
        with pytest.raises(SessionFinalizedError):
            runtime.finalize()


class TestSessionRuntimeIntegration:
    def test_full_flow(
        self,
        runtime: ExecutionSessionRuntime,
        completed_changeset: ChangeSet,
    ) -> None:
        runtime.start()
        runtime.attach_changeset(completed_changeset)
        runtime.record_failure(
            component="git",
            message="Merge conflict",
            recoverable=False,
        )
        runtime.complete()

        session = runtime.finalize()

        # 1: runtime created, 2: started, 3: changeset attached, 4: failure recorded, 5: completed
        assert len(session.timeline) == 5
        assert len(session.failures) == 1
        assert session.metrics.failure_count == 1
        assert session.metrics.unrecoverable_failures == 1
        assert session.metrics.health_score < 100