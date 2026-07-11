"""Tests for the ChangeSet domain models."""

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta
from pathlib import PurePosixPath

import pytest

from eag.changeset import (
    ChangedFile,
    ChangeIdentity,
    ChangeRisk,
    ChangeSet,
    ChangeSummary,
    CommandRecord,
    ExecutionMetrics,
    FileChangeType,
    GitSnapshot,
    TestRecord,
)
from eag.execution import CommandRequest


@pytest.fixture
def valid_identity() -> ChangeIdentity:
    return ChangeIdentity(
        id="change-123",
        created_at=datetime(2023, 1, 1, 12, 0, 0),
        parent_id="change-122",
    )


@pytest.fixture
def valid_file() -> ChangedFile:
    return ChangedFile(
        path=PurePosixPath("src/main.py"),
        change_type=FileChangeType.MODIFIED,
        lines_added=10,
        lines_removed=5,
        checksum_before="abc",
        checksum_after="def",
    )


@pytest.fixture
def valid_command() -> CommandRecord:
    start = datetime(2023, 1, 1, 12, 0, 0)
    end = datetime(2023, 1, 1, 12, 0, 5)
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
        skipped=1,
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
def valid_metrics() -> ExecutionMetrics:
    return ExecutionMetrics(
        commands=1,
        changed_files=1,
        tests=1,
        duration=timedelta(seconds=10),
        warnings=0,
        errors=0,
    )


@pytest.fixture
def valid_summary() -> ChangeSummary:
    return ChangeSummary(
        summary="Fixed a bug",
        risk=ChangeRisk.LOW,
        notes=("Note 1",),
    )


class TestChangeIdentity:
    def test_valid_identity(self, valid_identity: ChangeIdentity) -> None:
        assert valid_identity.id == "change-123"

    def test_empty_id_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot be empty"):
            ChangeIdentity(id="", created_at=datetime.now())

    def test_empty_parent_id_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot be empty"):
            ChangeIdentity(id="123", created_at=datetime.now(), parent_id="")

    def test_immutability(self, valid_identity: ChangeIdentity) -> None:
        with pytest.raises(FrozenInstanceError):
            valid_identity.id = "new-id"  # type: ignore[misc]

    def test_hashing(self, valid_identity: ChangeIdentity) -> None:
        assert hash(valid_identity) == hash(
            ChangeIdentity(
                id="change-123",
                created_at=datetime(2023, 1, 1, 12, 0, 0),
                parent_id="change-122",
            )
        )


class TestChangedFile:
    @pytest.mark.parametrize(
        "change_type",
        [
            FileChangeType.ADDED,
            FileChangeType.MODIFIED,
            FileChangeType.DELETED,
            FileChangeType.RENAMED,
        ],
    )
    def test_enum_values(self, change_type: FileChangeType) -> None:
        assert isinstance(change_type, str)

    def test_added_valid(self) -> None:
        file = ChangedFile(
            path=PurePosixPath("new.py"),
            change_type=FileChangeType.ADDED,
            checksum_after="new_hash",
        )
        assert file.change_type == FileChangeType.ADDED

    def test_added_with_before_raises(self) -> None:
        with pytest.raises(ValueError):
            ChangedFile(
                path=PurePosixPath("new.py"),
                change_type=FileChangeType.ADDED,
                checksum_before="old_hash",
                checksum_after="new_hash",
            )

    def test_added_without_after_raises(self) -> None:
        with pytest.raises(ValueError):
            ChangedFile(
                path=PurePosixPath("new.py"),
                change_type=FileChangeType.ADDED,
                checksum_after=None,
            )

    def test_deleted_valid(self) -> None:
        file = ChangedFile(
            path=PurePosixPath("old.py"),
            change_type=FileChangeType.DELETED,
            checksum_before="old_hash",
        )
        assert file.change_type == FileChangeType.DELETED

    def test_deleted_with_after_raises(self) -> None:
        with pytest.raises(ValueError):
            ChangedFile(
                path=PurePosixPath("old.py"),
                change_type=FileChangeType.DELETED,
                checksum_before="old_hash",
                checksum_after="new_hash",
            )

    def test_deleted_without_before_raises(self) -> None:
        with pytest.raises(ValueError):
            ChangedFile(
                path=PurePosixPath("old.py"),
                change_type=FileChangeType.DELETED,
                checksum_before=None,
            )

    def test_modified_valid(self) -> None:
        file = ChangedFile(
            path=PurePosixPath("mod.py"),
            change_type=FileChangeType.MODIFIED,
            checksum_before="old",
            checksum_after="new",
        )
        assert file.change_type == FileChangeType.MODIFIED

    def test_modified_without_before_raises(self) -> None:
        with pytest.raises(ValueError):
            ChangedFile(
                path=PurePosixPath("mod.py"),
                change_type=FileChangeType.MODIFIED,
                checksum_after="new",
            )

    def test_renamed_valid(self) -> None:
        file = ChangedFile(
            path=PurePosixPath("renamed.py"),
            change_type=FileChangeType.RENAMED,
            checksum_before="old",
            checksum_after="new",
        )
        assert file.change_type == FileChangeType.RENAMED

    def test_negative_lines_added_raises(self) -> None:
        with pytest.raises(ValueError):
            ChangedFile(
                path=PurePosixPath("mod.py"),
                change_type=FileChangeType.MODIFIED,
                lines_added=-1,
                checksum_before="old",
                checksum_after="new",
            )

    def test_negative_lines_removed_raises(self) -> None:
        with pytest.raises(ValueError):
            ChangedFile(
                path=PurePosixPath("mod.py"),
                change_type=FileChangeType.MODIFIED,
                lines_removed=-1,
                checksum_before="old",
                checksum_after="new",
            )

    def test_immutability(self, valid_file: ChangedFile) -> None:
        with pytest.raises(FrozenInstanceError):
            valid_file.lines_added = 20  # type: ignore[misc]

    def test_hashing(self, valid_file: ChangedFile) -> None:
        assert hash(valid_file) == hash(
            ChangedFile(
                path=PurePosixPath("src/main.py"),
                change_type=FileChangeType.MODIFIED,
                lines_added=10,
                lines_removed=5,
                checksum_before="abc",
                checksum_after="def",
            )
        )


class TestCommandRecord:
    def test_valid_timestamps(self, valid_command: CommandRecord) -> None:
        assert valid_command.duration == timedelta(seconds=5)

    def test_mismatched_timestamps_raises(self) -> None:
        start = datetime(2023, 1, 1, 12, 0, 0)
        end = datetime(2023, 1, 1, 12, 0, 5)
        with pytest.raises(ValueError, match="Duration does not match"):
            CommandRecord(
                request=CommandRequest(executable="python"),
                started_at=start,
                completed_at=end,
                exit_code=0,
                duration=timedelta(seconds=10),
            )

    def test_negative_duration_raises(self) -> None:
        start = datetime(2023, 1, 1, 12, 0, 5)
        end = datetime(2023, 1, 1, 12, 0, 0)
        with pytest.raises(ValueError, match="Duration cannot be negative"):
            CommandRecord(
                request=CommandRequest(executable="python"),
                started_at=start,
                completed_at=end,
                exit_code=0,
                duration=timedelta(seconds=-5),
            )

    def test_immutability(self, valid_command: CommandRecord) -> None:
        with pytest.raises(FrozenInstanceError):
            valid_command.exit_code = 1  # type: ignore[misc]

    def test_equality(self, valid_command: CommandRecord) -> None:
        start = datetime(2023, 1, 1, 12, 0, 0)
        end = datetime(2023, 1, 1, 12, 0, 5)
        assert valid_command == CommandRecord(
            request=CommandRequest(executable="python"),
            started_at=start,
            completed_at=end,
            exit_code=0,
            duration=timedelta(seconds=5),
        )


class TestTestRecord:
    def test_negative_passed_raises(self) -> None:
        with pytest.raises(ValueError):
            TestRecord(suite="t", passed=-1, failed=0, skipped=0, duration=timedelta(0))

    def test_negative_failed_raises(self) -> None:
        with pytest.raises(ValueError):
            TestRecord(suite="t", passed=0, failed=-1, skipped=0, duration=timedelta(0))

    def test_negative_skipped_raises(self) -> None:
        with pytest.raises(ValueError):
            TestRecord(suite="t", passed=0, failed=0, skipped=-1, duration=timedelta(0))

    def test_successful_property(self, valid_test: TestRecord) -> None:
        assert valid_test.successful is True

    def test_unsuccessful_property(self) -> None:
        test = TestRecord(suite="t", passed=5, failed=1, skipped=0, duration=timedelta(0))
        assert test.successful is False

    def test_immutability(self, valid_test: TestRecord) -> None:
        with pytest.raises(FrozenInstanceError):
            valid_test.passed = 100  # type: ignore[misc]

    def test_hashing(self, valid_test: TestRecord) -> None:
        assert hash(valid_test) == hash(
            TestRecord(
                suite="tests/test_main.py",
                passed=10,
                failed=0,
                skipped=1,
                duration=timedelta(seconds=2),
            )
        )


class TestGitSnapshot:
    def test_valid_snapshot(self, valid_git: GitSnapshot) -> None:
        assert valid_git.branch == "main"

    def test_empty_branch_raises(self) -> None:
        with pytest.raises(ValueError, match="Branch cannot be empty"):
            GitSnapshot(branch="   ", commit=None, dirty=True, diff_hash=None)

    def test_immutability(self, valid_git: GitSnapshot) -> None:
        with pytest.raises(FrozenInstanceError):
            valid_git.branch = "dev"  # type: ignore[misc]

    def test_hashing(self, valid_git: GitSnapshot) -> None:
        assert hash(valid_git) == hash(
            GitSnapshot(branch="main", commit="abcdef123", dirty=False, diff_hash=None)
        )


class TestExecutionMetrics:
    def test_valid_metrics(self, valid_metrics: ExecutionMetrics) -> None:
        assert valid_metrics.commands == 1

    @pytest.mark.parametrize(
        "field", ["commands", "changed_files", "tests", "warnings", "errors"]
    )
    def test_negative_counts_raises(self, field: str) -> None:
        kwargs = {
            "commands": 0,
            "changed_files": 0,
            "tests": 0,
            "duration": timedelta(0),
            "warnings": 0,
            "errors": 0,
        }
        kwargs[field] = -1
        with pytest.raises(ValueError):
            ExecutionMetrics(**kwargs)

    def test_immutability(self, valid_metrics: ExecutionMetrics) -> None:
        with pytest.raises(FrozenInstanceError):
            valid_metrics.commands = 99  # type: ignore[misc]

    def test_hashing(self, valid_metrics: ExecutionMetrics) -> None:
        assert hash(valid_metrics) == hash(
            ExecutionMetrics(
                commands=1,
                changed_files=1,
                tests=1,
                duration=timedelta(seconds=10),
                warnings=0,
                errors=0,
            )
        )


class TestChangeSummary:
    def test_valid_summary(self, valid_summary: ChangeSummary) -> None:
        assert valid_summary.risk == ChangeRisk.LOW

    def test_empty_summary_raises(self) -> None:
        with pytest.raises(ValueError, match="Summary cannot be empty"):
            ChangeSummary(summary="  ", risk=ChangeRisk.LOW)

    def test_enum_values(self) -> None:
        assert ChangeRisk.LOW == "low"
        assert ChangeRisk.MEDIUM == "medium"
        assert ChangeRisk.HIGH == "high"
        assert ChangeRisk.CRITICAL == "critical"

    def test_immutability(self, valid_summary: ChangeSummary) -> None:
        with pytest.raises(FrozenInstanceError):
            valid_summary.summary = "New summary"  # type: ignore[misc]

    def test_hashing(self, valid_summary: ChangeSummary) -> None:
        assert hash(valid_summary) == hash(
            ChangeSummary(summary="Fixed a bug", risk=ChangeRisk.LOW, notes=("Note 1",))
        )


class TestChangeSet:
    def test_empty_changeset(self, valid_identity: ChangeIdentity) -> None:
        cs = ChangeSet(
            identity=valid_identity,
            files=(),
            commands=(),
            tests=(),
        )
        assert cs.metrics is None
        assert cs.summary is None
        assert cs.artifacts == ()

    def test_populated_changeset(
        self,
        valid_identity: ChangeIdentity,
        valid_file: ChangedFile,
        valid_command: CommandRecord,
        valid_test: TestRecord,
        valid_metrics: ExecutionMetrics,
        valid_summary: ChangeSummary,
    ) -> None:
        cs = ChangeSet(
            identity=valid_identity,
            files=(valid_file,),
            commands=(valid_command,),
            tests=(valid_test,),
            metrics=valid_metrics,
            summary=valid_summary,
            artifacts=(PurePosixPath("report.html"),),
        )
        assert len(cs.files) == 1
        assert cs.metrics.commands == 1
        assert cs.artifacts[0] == PurePosixPath("report.html")

    def test_metrics_mismatch_commands_raises(
        self, valid_identity: ChangeIdentity
    ) -> None:
        with pytest.raises(ValueError, match="commands count does not match"):
            ChangeSet(
                identity=valid_identity,
                files=(),
                commands=(),
                tests=(),
                metrics=ExecutionMetrics(
                    commands=1,
                    changed_files=0,
                    tests=0,
                    duration=timedelta(0),
                    warnings=0,
                    errors=0,
                ),
            )

    def test_metrics_mismatch_files_raises(
        self, valid_identity: ChangeIdentity
    ) -> None:
        with pytest.raises(ValueError, match="changed_files count does not match"):
            ChangeSet(
                identity=valid_identity,
                files=(),
                commands=(),
                tests=(),
                metrics=ExecutionMetrics(
                    commands=0,
                    changed_files=1,
                    tests=0,
                    duration=timedelta(0),
                    warnings=0,
                    errors=0,
                ),
            )

    def test_metrics_mismatch_tests_raises(
        self, valid_identity: ChangeIdentity
    ) -> None:
        with pytest.raises(ValueError, match="tests count does not match"):
            ChangeSet(
                identity=valid_identity,
                files=(),
                commands=(),
                tests=(),
                metrics=ExecutionMetrics(
                    commands=0,
                    changed_files=0,
                    tests=1,
                    duration=timedelta(0),
                    warnings=0,
                    errors=0,
                ),
            )

    def test_immutability(
        self, valid_identity: ChangeIdentity, valid_file: ChangedFile
    ) -> None:
        cs = ChangeSet(
            identity=valid_identity,
            files=(valid_file,),
            commands=(),
            tests=(),
        )
        with pytest.raises(FrozenInstanceError):
            cs.files = ()  # type: ignore[misc]

    def test_hashing(
        self, valid_identity: ChangeIdentity, valid_file: ChangedFile
    ) -> None:
        cs1 = ChangeSet(
            identity=valid_identity,
            files=(valid_file,),
            commands=(),
            tests=(),
        )
        cs2 = ChangeSet(
            identity=valid_identity,
            files=(valid_file,),
            commands=(),
            tests=(),
        )
        assert hash(cs1) == hash(cs2)

    def test_equality(
        self, valid_identity: ChangeIdentity, valid_file: ChangedFile
    ) -> None:
        cs1 = ChangeSet(
            identity=valid_identity,
            files=(valid_file,),
            commands=(),
            tests=(),
        )
        cs2 = ChangeSet(
            identity=valid_identity,
            files=(valid_file,),
            commands=(),
            tests=(),
        )
        assert cs1 == cs2