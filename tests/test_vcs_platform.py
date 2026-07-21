"""Comprehensive tests for the Repository (VCS) Platform."""

from pathlib import Path

import pytest

from eag.events import EventBus
from eag.vcs.enums import FileStatus, RepositoryState, TransactionState
from eag.vcs.enums import RepositoryProviderType as VCSProvider
from eag.vcs.errors import RepositoryValidationError as VCSValidationError
from eag.vcs.errors import TransactionError
from eag.vcs.events import CommitCreated, RepositoryOpened
from eag.vcs.models import Commit, RepositoryHealth
from eag.vcs.models import RepositoryDescriptor as Repository
from eag.vcs.providers.git import GitProvider
from eag.vcs.runtime import RepositoryRuntime as VCSRuntime
from eag.vcs.transaction import TransactionManager


@pytest.fixture
def temp_repo_root(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def event_bus() -> EventBus:
    return EventBus()


@pytest.fixture
def runtime(temp_repo_root: Path, event_bus: EventBus) -> VCSRuntime:
    rt = VCSRuntime(root=temp_repo_root, event_bus=event_bus)
    rt.open()
    # Create an initial commit so the repo is valid and has a HEAD
    (temp_repo_root / "README.md").write_text("# Test Repo")
    rt.commit("Initial commit")
    return rt


class TestVCSEnums:
    def test_provider_values(self) -> None:
        assert VCSProvider.GIT == "git"

    def test_state_values(self) -> None:
        assert RepositoryState.READY == "ready"

    def test_file_status_values(self) -> None:
        assert FileStatus.MODIFIED == "modified"


class TestVCSModels:
    def test_repository_is_immutable(self, temp_repo_root: Path) -> None:
        repo = Repository(root=temp_repo_root)
        with pytest.raises(Exception, match="."):
            repo.branch = "dev"  # type: ignore[misc]

    def test_commit_creation(self) -> None:
        from datetime import UTC, datetime

        c = Commit(commit_id="abc", author="EAG", timestamp=datetime.now(UTC), message="Test")
        assert c.commit_id == "abc"


class TestGitProvider:
    def test_git_not_found(self, tmp_path: Path) -> None:
        provider = GitProvider()
        # Mock subprocess.run to simulate missing git
        import eag.vcs.providers.git as git_mod

        original_run = git_mod.subprocess.run

        def mock_run(*args, **kwargs):
            raise FileNotFoundError("Git not found")

        git_mod.subprocess.run = mock_run
        try:
            with pytest.raises(Exception, match="Git executable not found"):
                provider.init(tmp_path)
        finally:
            git_mod.subprocess.run = original_run


class TestTransactionManager:
    def test_begin_and_commit(self) -> None:
        tm = TransactionManager()
        tm.begin()
        assert tm.state == TransactionState.ACTIVE
        tm.commit()
        assert tm.state == TransactionState.COMMITTED

    def test_double_begin_raises(self) -> None:
        tm = TransactionManager()
        tm.begin()
        with pytest.raises(TransactionError):
            tm.begin()

    def test_rollback_without_active_raises(self) -> None:
        tm = TransactionManager()
        with pytest.raises(TransactionError):
            tm.rollback()


class TestVCSRuntime:
    def test_open_initializes_repo(self, temp_repo_root: Path, event_bus: EventBus) -> None:
        from unittest.mock import MagicMock

        # This line is crucial! It overrides the real method with the mock recorder.
        event_bus.publish = MagicMock()

        rt = VCSRuntime(root=temp_repo_root, event_bus=event_bus)
        repo = rt.open()

        assert repo.state == RepositoryState.READY
        assert (temp_repo_root / ".git").exists()
        assert any(
            isinstance(call.args[0], RepositoryOpened)
            for call in event_bus.publish.call_args_list
            if call.args
        )

    def test_validate_fails_if_not_repo(self, temp_repo_root: Path, event_bus: EventBus) -> None:
        rt = VCSRuntime(root=temp_repo_root, event_bus=event_bus)
        with pytest.raises(VCSValidationError):
            # Try to validate without calling open() first
            rt._validator.validate(Repository(root=temp_repo_root))

    def test_commit_creates_history(self, runtime: VCSRuntime) -> None:
        history = runtime.history(limit=5)
        assert len(history) >= 1
        assert "Initial commit" in history[0].message

    def test_status_detects_changes(self, runtime: VCSRuntime, temp_repo_root: Path) -> None:
        (temp_repo_root / "new_file.py").write_text("print('hello')")
        status = runtime.status()
        assert any(c.path == "new_file.py" and c.status == FileStatus.UNTRACKED for c in status)

    def test_branch_and_checkout(self, runtime: VCSRuntime) -> None:
        runtime.create_branch("feature-branch")
        runtime.checkout("feature-branch")
        # No exception means success. Git checkout is silent on success.
        assert runtime.health().provider == VCSProvider.GIT

    def test_commit_event_published(
        self, runtime: VCSRuntime, temp_repo_root: Path, event_bus: EventBus
    ) -> None:
        from unittest.mock import MagicMock

        event_bus.publish = MagicMock()

        (temp_repo_root / "app.py").write_text("print('app')")
        runtime.commit("Add app")

        # Verify that CommitCreated was passed into publish()
        assert any(
            isinstance(call.args[0], CommitCreated)
            for call in event_bus.publish.call_args_list
            if call.args
        )

    def test_health_returns_status(self, runtime: VCSRuntime) -> None:
        health = runtime.health()
        assert isinstance(health, RepositoryHealth)
        assert health.provider == VCSProvider.GIT

    def test_explain_returns_string(self, runtime: VCSRuntime) -> None:
        explanation = runtime.explain()
        assert "Repository Platform" in explanation
        assert "Provider: git" in explanation
