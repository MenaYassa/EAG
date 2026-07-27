"""Tests for the engineering safety domain models."""

from dataclasses import FrozenInstanceError
from datetime import datetime
from pathlib import PurePosixPath

import pytest

from eag.safety import (
    Checkpoint,
    RollbackError,
    SafetyBackend,
    SafetyError,
    SafetyErrorRecord,
    SafetyReport,
    SafetyState,
    SafetyWarning,
    UnsupportedBackendError,
    WorkspaceHealth,
    WorkspaceStatus,
    WorkspaceUnsafeError,
)
from eag.safety.errors import CheckpointError


@pytest.fixture
def valid_checkpoint() -> Checkpoint:
    return Checkpoint(
        id="cp-001",
        created_at=datetime(2023, 1, 1, 12, 0, 0),
        description="Initial checkpoint",
        backend=SafetyBackend.GIT,
        backend_reference="abc123",
    )


@pytest.fixture
def valid_status() -> WorkspaceStatus:
    return WorkspaceStatus(
        workspace=PurePosixPath("/workspace"),
        backend=SafetyBackend.GIT,
        branch="main",
        head="abc123",
        dirty=False,
        has_untracked=False,
        has_conflicts=False,
        detached_head=False,
    )


class TestCheckpoint:
    def test_valid_checkpoint(self, valid_checkpoint: Checkpoint) -> None:
        assert valid_checkpoint.id == "cp-001"

    def test_empty_id_raises(self) -> None:
        with pytest.raises(ValueError, match="ID cannot be empty"):
            Checkpoint(
                id="",
                created_at=datetime.now(),
                description="Test",
                backend=SafetyBackend.GIT,
                backend_reference="abc",
            )

    def test_empty_description_raises(self) -> None:
        with pytest.raises(ValueError, match="description cannot be empty"):
            Checkpoint(
                id="cp-1",
                created_at=datetime.now(),
                description="",
                backend=SafetyBackend.GIT,
                backend_reference="abc",
            )

    def test_empty_backend_reference_raises(self) -> None:
        with pytest.raises(ValueError, match="backend reference cannot be empty"):
            Checkpoint(
                id="cp-1",
                created_at=datetime.now(),
                description="Test",
                backend=SafetyBackend.GIT,
                backend_reference="",
            )

    def test_immutability(self, valid_checkpoint: Checkpoint) -> None:
        with pytest.raises(FrozenInstanceError):
            valid_checkpoint.id = "new"  # type: ignore[misc]

    def test_hashing(self, valid_checkpoint: Checkpoint) -> None:
        assert hash(valid_checkpoint) == hash(
            Checkpoint(
                id="cp-001",
                created_at=datetime(2023, 1, 1, 12, 0, 0),
                description="Initial checkpoint",
                backend=SafetyBackend.GIT,
                backend_reference="abc123",
            )
        )

    def test_equality(self, valid_checkpoint: Checkpoint) -> None:
        assert valid_checkpoint == Checkpoint(
            id="cp-001",
            created_at=datetime(2023, 1, 1, 12, 0, 0),
            description="Initial checkpoint",
            backend=SafetyBackend.GIT,
            backend_reference="abc123",
        )


class TestWorkspaceStatus:
    def test_valid_status(self, valid_status: WorkspaceStatus) -> None:
        assert valid_status.branch == "main"

    def test_immutability(self, valid_status: WorkspaceStatus) -> None:
        with pytest.raises(FrozenInstanceError):
            valid_status.dirty = True  # type: ignore[misc]

    def test_hashing(self, valid_status: WorkspaceStatus) -> None:
        assert hash(valid_status) == hash(
            WorkspaceStatus(
                workspace=PurePosixPath("/workspace"),
                backend=SafetyBackend.GIT,
                branch="main",
                head="abc123",
                dirty=False,
                has_untracked=False,
                has_conflicts=False,
                detached_head=False,
            )
        )

    def test_equality(self, valid_status: WorkspaceStatus) -> None:
        assert valid_status == WorkspaceStatus(
            workspace=PurePosixPath("/workspace"),
            backend=SafetyBackend.GIT,
            branch="main",
            head="abc123",
            dirty=False,
            has_untracked=False,
            has_conflicts=False,
            detached_head=False,
        )


class TestSafetyWarning:
    def test_valid_warning(self) -> None:
        warning = SafetyWarning(message="Dirty tree", code="DIRTY_TREE")
        assert warning.code == "DIRTY_TREE"

    def test_empty_message_raises(self) -> None:
        with pytest.raises(ValueError):
            SafetyWarning(message="", code="ERR")

    def test_empty_code_raises(self) -> None:
        with pytest.raises(ValueError):
            SafetyWarning(message="Err", code="")

    def test_hashing(self) -> None:
        warning1 = SafetyWarning(message="Dirty", code="DIRTY")
        warning2 = SafetyWarning(message="Dirty", code="DIRTY")
        assert hash(warning1) == hash(warning2)


class TestSafetyErrorRecord:
    def test_valid_error(self) -> None:
        error = SafetyErrorRecord(message="Merge conflict", code="MERGE_CONFLICT")
        assert error.code == "MERGE_CONFLICT"

    def test_empty_message_raises(self) -> None:
        with pytest.raises(ValueError):
            SafetyErrorRecord(message="", code="ERR")

    def test_empty_code_raises(self) -> None:
        with pytest.raises(ValueError):
            SafetyErrorRecord(message="Err", code="")

    def test_hashing(self) -> None:
        err1 = SafetyErrorRecord(message="Conflict", code="CONFLICT")
        err2 = SafetyErrorRecord(message="Conflict", code="CONFLICT")
        assert hash(err1) == hash(err2)


class TestSafetyReport:
    def test_empty_warnings(self, valid_status: WorkspaceStatus) -> None:
        report = SafetyReport(
            workspace=PurePosixPath("/ws"),
            backend=SafetyBackend.GIT,
            health=WorkspaceHealth.HEALTHY,
            status=valid_status,
            state=SafetyState.READY,
        )
        assert report.warnings == ()
        assert report.errors == ()
        assert report.checkpoint is None

    def test_populated_warnings(self, valid_status: WorkspaceStatus) -> None:
        report = SafetyReport(
            workspace=PurePosixPath("/ws"),
            backend=SafetyBackend.GIT,
            health=WorkspaceHealth.UNSAFE,
            status=valid_status,
            state=SafetyState.UNKNOWN,
            warnings=(SafetyWarning(message="Dirty", code="DIRTY"),),
            errors=(SafetyErrorRecord(message="Conflict", code="CONFLICT"),),
            checkpoint=Checkpoint(
                id="cp-1",
                created_at=datetime.now(),
                description="Test",
                backend=SafetyBackend.GIT,
                backend_reference="abc",
            ),
        )
        assert len(report.warnings) == 1
        assert len(report.errors) == 1
        assert report.checkpoint is not None

    def test_checkpoint_optional(self, valid_status: WorkspaceStatus) -> None:
        report = SafetyReport(
            workspace=PurePosixPath("/ws"),
            backend=SafetyBackend.GIT,
            health=WorkspaceHealth.HEALTHY,
            status=valid_status,
            state=SafetyState.READY,
        )
        assert report.checkpoint is None

    def test_immutability(self, valid_status: WorkspaceStatus) -> None:
        report = SafetyReport(
            workspace=PurePosixPath("/ws"),
            backend=SafetyBackend.GIT,
            health=WorkspaceHealth.HEALTHY,
            status=valid_status,
            state=SafetyState.READY,
        )
        with pytest.raises(FrozenInstanceError):
            report.health = WorkspaceHealth.UNSAFE  # type: ignore[misc]


class TestSafetyState:
    def test_enum_values(self) -> None:
        assert SafetyState.UNKNOWN == "unknown"
        assert SafetyState.READY == "ready"
        assert SafetyState.CHECKPOINT_CREATED == "checkpoint_created"
        assert SafetyState.EXECUTING == "executing"
        assert SafetyState.ROLLBACK_AVAILABLE == "rollback_available"
        assert SafetyState.ROLLING_BACK == "rolling_back"
        assert SafetyState.ROLLED_BACK == "rolled_back"
        assert SafetyState.COMPLETED == "completed"


class TestErrors:
    def test_hierarchy(self) -> None:
        assert issubclass(WorkspaceUnsafeError, SafetyError)
        assert issubclass(CheckpointError, SafetyError)
        assert issubclass(RollbackError, SafetyError)
        assert issubclass(UnsupportedBackendError, SafetyError)
