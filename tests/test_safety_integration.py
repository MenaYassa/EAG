"""End-to-end integration tests for the Safety subsystem."""

import subprocess
from pathlib import Path

import pytest

from eag.events import EventBus
from eag.safety import (
    CheckpointManager,
    GitSafetyBackend,
    RollbackEngine,
    SafetyRuntime,
    WorkspaceHealth,
    WorkspaceInspector,
)
from eag.safety.errors import WorkspaceUnsafeError
from eag.safety.events import (
    CheckpointCreated,
    RollbackCompleted,
    WorkspaceInspected,
)


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a temporary Git repository."""
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True)
    return tmp_path


@pytest.fixture
def event_bus() -> EventBus:
    return EventBus()


@pytest.fixture
def safety_runtime(git_repo: Path, event_bus: EventBus) -> SafetyRuntime:
    backend = GitSafetyBackend(workspace=git_repo)
    inspector = WorkspaceInspector(backend=backend)
    manager = CheckpointManager(backend=backend, event_bus=event_bus)
    engine = RollbackEngine(backend=backend, event_bus=event_bus)
    return SafetyRuntime(
        workspace=git_repo,
        inspector=inspector,
        checkpoint_manager=manager,
        rollback_engine=engine,
        event_bus=event_bus,
    )


class TestSafetyIntegration:
    def test_full_git_workflow_safety(self, safety_runtime: SafetyRuntime, git_repo: Path) -> None:
        """Test the full safety workflow against a real Git repository."""
        # 1. Inspect initially (should be HEALTHY, albeit an empty repo)
        # Note: An empty git repo has no HEAD, so our backend treats it as detached.
        # For a robust test, let's make an initial commit first.
        (git_repo / "file.txt").write_text("initial")
        subprocess.run(["git", "add", "-A"], cwd=git_repo, check=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=git_repo, check=True)

        report = safety_runtime.inspect()
        assert report.health == WorkspaceHealth.HEALTHY

        # 2. Create a checkpoint
        safety_runtime.create_checkpoint("Pre-execution checkpoint")

        # 3. Modify file -> Should become WARNING (dirty)
        (git_repo / "file.txt").write_text("modified")
        report = safety_runtime.inspect()
        assert report.health == WorkspaceHealth.WARNING
        assert report.status.dirty is True

        # 4. Rollback
        safety_runtime.rollback()

        # 5. Inspect again -> Should be HEALTHY
        report = safety_runtime.inspect()
        assert report.health == WorkspaceHealth.HEALTHY
        assert report.status.dirty is False
        assert (git_repo / "file.txt").read_text() == "initial"

    def test_non_git_prepare_raises(self, tmp_path: Path) -> None:
        """Test that preparing in a non-Git directory raises an error."""
        backend = GitSafetyBackend(workspace=tmp_path)
        event_bus = EventBus()
        inspector = WorkspaceInspector(backend=backend)
        manager = CheckpointManager(backend=backend, event_bus=event_bus)
        engine = RollbackEngine(backend=backend, event_bus=event_bus)
        runtime = SafetyRuntime(
            workspace=tmp_path,
            inspector=inspector,
            checkpoint_manager=manager,
            rollback_engine=engine,
            event_bus=event_bus,
        )

        with pytest.raises(WorkspaceUnsafeError):
            runtime.prepare()

    def test_safety_events(
        self, safety_runtime: SafetyRuntime, git_repo: Path, event_bus: EventBus
    ) -> None:
        """Test that safety operations publish the correct events."""
        received = []
        event_bus.subscribe(WorkspaceInspected, lambda e: received.append(e))
        event_bus.subscribe(CheckpointCreated, lambda e: received.append(e))
        event_bus.subscribe(RollbackCompleted, lambda e: received.append(e))

        # Need an initial commit so the repo isn't detached/unsafe
        (git_repo / "file.txt").write_text("initial")
        subprocess.run(["git", "add", "-A"], cwd=git_repo, check=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=git_repo, check=True)

        safety_runtime.prepare()
        safety_runtime.rollback()

        event_types = [type(e) for e in received]
        assert WorkspaceInspected in event_types
        assert CheckpointCreated in event_types
        assert RollbackCompleted in event_types
