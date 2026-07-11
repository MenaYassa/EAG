"""Tests for the ChangeSetBuilder."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from pathlib import PurePosixPath
from uuid import uuid4

import pytest

from eag.changeset import (
    ChangedFile,
    ChangeIdentity,
    ChangeRecorded,
    ChangeRisk,
    ChangeSet,
    ChangeSetBuilder,
    ChangeSetBuilderStarted,
    ChangeSetBuilderState,
    ChangeSetFinalized,
    ChangeSetFinalizedError,
    ChangeSummary,
    CommandRecord,
    FileChangeType,
    GitSnapshot,
    TestRecord,
)
from eag.events import EventBus
from eag.execution import CommandRequest


@pytest.fixture
def valid_identity() -> ChangeIdentity:
    return ChangeIdentity(
        id=str(uuid4()),
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def valid_file() -> ChangedFile:
    return ChangedFile(
        path=PurePosixPath("src/main.py"),
        change_type=FileChangeType.ADDED,
        checksum_after="hash",
    )


@pytest.fixture
def valid_command() -> CommandRecord:
    start = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
    end = datetime(2023, 1, 1, 12, 0, 5, tzinfo=UTC)
    return CommandRecord(
        request=CommandRequest(executable="python"),
        started_at=start,
        completed_at=end,
        exit_code=0,
        duration=timedelta(seconds=5),
    )


@pytest.fixture
def valid_test() -> TestRecord:
    return TestRecord(
        suite="tests/test_main.py",
        passed=10,
        failed=0,
        skipped=0,
        duration=timedelta(seconds=2),
    )


@pytest.fixture
def valid_git() -> GitSnapshot:
    return GitSnapshot(
        branch="main",
        commit="abcdef123",
        dirty=False,
        diff_hash=None,
    )


@pytest.fixture
def valid_summary() -> ChangeSummary:
    return ChangeSummary(
        summary="Fixed a bug",
        risk=ChangeRisk.LOW,
    )


class TestChangeSetBuilderInitialization:
    def test_generates_identity(self) -> None:
        builder = ChangeSetBuilder()
        assert builder._identity.id is not None
        assert builder._identity.created_at is not None

    def test_accepts_existing_identity(self, valid_identity: ChangeIdentity) -> None:
        builder = ChangeSetBuilder(identity=valid_identity)
        assert builder._identity.id == valid_identity.id

    def test_initial_state_is_building(self) -> None:
        builder = ChangeSetBuilder()
        assert builder._state == ChangeSetBuilderState.BUILDING

    def test_publishes_started_event(self) -> None:
        event_bus = EventBus()
        received = []
        event_bus.subscribe(ChangeSetBuilderStarted, lambda e: received.append(e))

        builder = ChangeSetBuilder(event_bus=event_bus)

        assert len(received) == 1
        assert received[0].identity_id == builder._identity.id


class TestChangeSetBuilderRecording:
    def test_record_file_appends(self, valid_file: ChangedFile) -> None:
        builder = ChangeSetBuilder()
        builder.record_file(valid_file)
        assert builder._data.files == [valid_file]

    def test_record_command_appends(self, valid_command: CommandRecord) -> None:
        builder = ChangeSetBuilder()
        builder.record_command(valid_command)
        assert builder._data.commands == [valid_command]

    def test_record_test_appends(self, valid_test: TestRecord) -> None:
        builder = ChangeSetBuilder()
        builder.record_test(valid_test)
        assert builder._data.tests == [valid_test]

    def test_record_artifact_appends(self) -> None:
        builder = ChangeSetBuilder()
        builder.record_artifact(PurePosixPath("report.html"))
        assert builder._data.artifacts == [PurePosixPath("report.html")]

    def test_record_git_overwrites(self, valid_git: GitSnapshot) -> None:
        builder = ChangeSetBuilder()
        builder.record_git(valid_git)
        new_git = GitSnapshot(branch="dev", commit="123", dirty=True, diff_hash="hash")
        builder.record_git(new_git)
        assert builder._data.git == new_git

    def test_record_summary_overwrites(self, valid_summary: ChangeSummary) -> None:
        builder = ChangeSetBuilder()
        builder.record_summary(valid_summary)
        new_summary = ChangeSummary(summary="New", risk=ChangeRisk.HIGH)
        builder.record_summary(new_summary)
        assert builder._data.summary == new_summary

    def test_publishes_change_recorded(self, valid_file: ChangedFile) -> None:
        event_bus = EventBus()
        received = []
        event_bus.subscribe(ChangeRecorded, lambda e: received.append(e))

        builder = ChangeSetBuilder(event_bus=event_bus)
        builder.record_file(valid_file)

        assert len(received) == 1
        assert received[0].kind == "file"
        assert received[0].payload == valid_file


class TestChangeSetBuilderFinalization:
    def test_finalize_returns_immutable_changeset(
        self, valid_identity: ChangeIdentity
    ) -> None:
        builder = ChangeSetBuilder(identity=valid_identity)
        changeset = builder.finalize()

        assert isinstance(changeset, ChangeSet)
        with pytest.raises(FrozenInstanceError):
            changeset.files = ()  # type: ignore[misc]

    def test_finalize_preserves_identity(
        self, valid_identity: ChangeIdentity
    ) -> None:
        builder = ChangeSetBuilder(identity=valid_identity)
        changeset = builder.finalize()
        assert changeset.identity == valid_identity

    def test_finalize_converts_lists_to_tuples(
        self,
        valid_identity: ChangeIdentity,
        valid_file: ChangedFile,
        valid_command: CommandRecord,
    ) -> None:
        builder = ChangeSetBuilder(identity=valid_identity)
        builder.record_file(valid_file)
        builder.record_command(valid_command)

        changeset = builder.finalize()
        assert isinstance(changeset.files, tuple)
        assert isinstance(changeset.commands, tuple)

    def test_finalize_auto_generates_metrics(
        self,
        valid_identity: ChangeIdentity,
        valid_file: ChangedFile,
        valid_command: CommandRecord,
        valid_test: TestRecord,
    ) -> None:
        builder = ChangeSetBuilder(identity=valid_identity)
        builder.record_file(valid_file)
        builder.record_command(valid_command)
        builder.record_test(valid_test)

        changeset = builder.finalize()
        assert changeset.metrics is not None
        assert changeset.metrics.commands == 1
        assert changeset.metrics.changed_files == 1
        assert changeset.metrics.tests == 1
        assert changeset.metrics.duration == timedelta(seconds=5)

    def test_finalize_transitions_state(
        self, valid_identity: ChangeIdentity
    ) -> None:
        builder = ChangeSetBuilder(identity=valid_identity)
        builder.finalize()
        assert builder._state == ChangeSetBuilderState.FINALIZED

    def test_finalize_publishes_event(
        self, valid_identity: ChangeIdentity
    ) -> None:
        event_bus = EventBus()
        received = []
        event_bus.subscribe(ChangeSetFinalized, lambda e: received.append(e))

        builder = ChangeSetBuilder(identity=valid_identity, event_bus=event_bus)
        builder.finalize()

        assert len(received) == 1
        assert received[0].changeset_id == valid_identity.id

    def test_finalize_empty_builder(
        self, valid_identity: ChangeIdentity
    ) -> None:
        builder = ChangeSetBuilder(identity=valid_identity)
        changeset = builder.finalize()
        assert changeset.files == ()
        assert changeset.metrics is not None
        assert changeset.metrics.commands == 0


class TestChangeSetBuilderLifecycle:
    def test_record_file_after_finalize_raises(
        self, valid_identity: ChangeIdentity, valid_file: ChangedFile
    ) -> None:
        builder = ChangeSetBuilder(identity=valid_identity)
        builder.finalize()
        with pytest.raises(ChangeSetFinalizedError):
            builder.record_file(valid_file)

    def test_record_command_after_finalize_raises(
        self, valid_identity: ChangeIdentity, valid_command: CommandRecord
    ) -> None:
        builder = ChangeSetBuilder(identity=valid_identity)
        builder.finalize()
        with pytest.raises(ChangeSetFinalizedError):
            builder.record_command(valid_command)

    def test_record_test_after_finalize_raises(
        self, valid_identity: ChangeIdentity, valid_test: TestRecord
    ) -> None:
        builder = ChangeSetBuilder(identity=valid_identity)
        builder.finalize()
        with pytest.raises(ChangeSetFinalizedError):
            builder.record_test(valid_test)

    def test_record_git_after_finalize_raises(
        self, valid_identity: ChangeIdentity, valid_git: GitSnapshot
    ) -> None:
        builder = ChangeSetBuilder(identity=valid_identity)
        builder.finalize()
        with pytest.raises(ChangeSetFinalizedError):
            builder.record_git(valid_git)

    def test_record_summary_after_finalize_raises(
        self, valid_identity: ChangeIdentity, valid_summary: ChangeSummary
    ) -> None:
        builder = ChangeSetBuilder(identity=valid_identity)
        builder.finalize()
        with pytest.raises(ChangeSetFinalizedError):
            builder.record_summary(valid_summary)

    def test_record_artifact_after_finalize_raises(
        self, valid_identity: ChangeIdentity
    ) -> None:
        builder = ChangeSetBuilder(identity=valid_identity)
        builder.finalize()
        with pytest.raises(ChangeSetFinalizedError):
            builder.record_artifact(PurePosixPath("report.html"))

    def test_double_finalize_raises(
        self, valid_identity: ChangeIdentity
    ) -> None:
        builder = ChangeSetBuilder(identity=valid_identity)
        builder.finalize()
        with pytest.raises(ChangeSetFinalizedError):
            builder.finalize()
