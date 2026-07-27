"""Tests for the Safety Runtime and Inspector."""

from datetime import UTC, datetime
from pathlib import PurePosixPath

import pytest

from eag.events import EventBus
from eag.safety import (
    Checkpoint,
    CheckpointManager,
    RollbackEngine,
    SafetyBackend,
    SafetyRuntime,
    WorkspaceInspector,
    WorkspaceStatus,
)
from eag.safety.errors import WorkspaceUnsafeError


class MockWorkspaceBackend:
    def __init__(self, status: WorkspaceStatus) -> None:
        self.status = status

    def inspect(self) -> WorkspaceStatus:
        return self.status


class MockCheckpointBackend:
    def __init__(self) -> None:
        self.checkpoints: dict[str, Checkpoint] = {}

    def create(self, checkpoint_id: str, description: str) -> Checkpoint:
        cp = Checkpoint(
            id=checkpoint_id,
            created_at=datetime.now(UTC),
            description=description,
            backend=SafetyBackend.GIT,
            backend_reference="abc123",
        )
        self.checkpoints[checkpoint_id] = cp
        return cp

    def rollback(self, checkpoint_id: str) -> None:
        pass

    def latest(self) -> Checkpoint | None:
        if not self.checkpoints:
            return None
        return list(self.checkpoints.values())[-1]

    def exists(self, checkpoint_id: str) -> bool:
        return checkpoint_id in self.checkpoints


@pytest.fixture
def event_bus() -> EventBus:
    return EventBus()


@pytest.fixture
def workspace() -> PurePosixPath:
    return PurePosixPath("/workspace")


@pytest.fixture
def mock_checkpoint_backend() -> MockCheckpointBackend:
    return MockCheckpointBackend()


@pytest.fixture
def checkpoint_manager(
    mock_checkpoint_backend: MockCheckpointBackend, event_bus: EventBus
) -> CheckpointManager:
    return CheckpointManager(mock_checkpoint_backend, event_bus)


@pytest.fixture
def rollback_engine(
    mock_checkpoint_backend: MockCheckpointBackend, event_bus: EventBus
) -> RollbackEngine:
    return RollbackEngine(mock_checkpoint_backend, event_bus)


@pytest.fixture
def dirty_status() -> WorkspaceStatus:
    return WorkspaceStatus(
        workspace=PurePosixPath("/workspace"),
        backend=SafetyBackend.GIT,
        branch="main",
        head="abc123",
        dirty=True,
        has_untracked=False,
        has_conflicts=False,
        detached_head=False,
    )


@pytest.fixture
def unsafe_status() -> WorkspaceStatus:
    return WorkspaceStatus(
        workspace=PurePosixPath("/workspace"),
        backend=SafetyBackend.GIT,
        branch="main",
        head="abc123",
        dirty=False,
        has_untracked=False,
        has_conflicts=True,
        detached_head=False,
    )


@pytest.fixture
def healthy_status() -> WorkspaceStatus:
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


@pytest.fixture
def dirty_inspector(dirty_status: WorkspaceStatus) -> WorkspaceInspector:
    return WorkspaceInspector(MockWorkspaceBackend(dirty_status))


@pytest.fixture
def unsafe_inspector(unsafe_status: WorkspaceStatus) -> WorkspaceInspector:
    return WorkspaceInspector(MockWorkspaceBackend(unsafe_status))


@pytest.fixture
def healthy_inspector(healthy_status: WorkspaceStatus) -> WorkspaceInspector:
    return WorkspaceInspector(MockWorkspaceBackend(healthy_status))


class TestWorkspaceInspector:
    def test_health_dirty(self, dirty_inspector: WorkspaceInspector) -> None:
        assert dirty_inspector.health().value == "warning"

    def test_health_unsafe(self, unsafe_inspector: WorkspaceInspector) -> None:
        assert unsafe_inspector.health().value == "unsafe"

    def test_health_healthy(self, healthy_inspector: WorkspaceInspector) -> None:
        assert healthy_inspector.health().value == "healthy"


class TestSafetyRuntime:
    def test_inspect_dirty(
        self,
        workspace: PurePosixPath,
        dirty_inspector: WorkspaceInspector,
        checkpoint_manager: CheckpointManager,
        rollback_engine: RollbackEngine,
        event_bus: EventBus,
    ) -> None:
        runtime = SafetyRuntime(
            workspace=workspace,
            inspector=dirty_inspector,
            checkpoint_manager=checkpoint_manager,
            rollback_engine=rollback_engine,
            event_bus=event_bus,
        )
        report = runtime.inspect()
        assert report.health.value == "warning"
        assert len(report.warnings) == 1

    def test_prepare_dirty(
        self,
        workspace: PurePosixPath,
        dirty_inspector: WorkspaceInspector,
        checkpoint_manager: CheckpointManager,
        rollback_engine: RollbackEngine,
        event_bus: EventBus,
    ) -> None:
        runtime = SafetyRuntime(
            workspace=workspace,
            inspector=dirty_inspector,
            checkpoint_manager=checkpoint_manager,
            rollback_engine=rollback_engine,
            event_bus=event_bus,
        )
        report = runtime.prepare()
        assert report.checkpoint is not None
        assert report.state.value == "checkpoint_created"

    def test_prepare_unsafe_raises(
        self,
        workspace: PurePosixPath,
        unsafe_inspector: WorkspaceInspector,
        checkpoint_manager: CheckpointManager,
        rollback_engine: RollbackEngine,
        event_bus: EventBus,
    ) -> None:
        runtime = SafetyRuntime(
            workspace=workspace,
            inspector=unsafe_inspector,
            checkpoint_manager=checkpoint_manager,
            rollback_engine=rollback_engine,
            event_bus=event_bus,
        )
        with pytest.raises(WorkspaceUnsafeError):
            runtime.prepare()

    def test_rollback(
        self,
        workspace: PurePosixPath,
        healthy_inspector: WorkspaceInspector,
        checkpoint_manager: CheckpointManager,
        rollback_engine: RollbackEngine,
        event_bus: EventBus,
    ) -> None:
        runtime = SafetyRuntime(
            workspace=workspace,
            inspector=healthy_inspector,
            checkpoint_manager=checkpoint_manager,
            rollback_engine=rollback_engine,
            event_bus=event_bus,
        )
        runtime.prepare()
        runtime.rollback()
        report = runtime.inspect()
        assert report.state.value == "rolled_back"
