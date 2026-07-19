"""Comprehensive hardening tests for the Repository Platform."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from eag.vcs.enums import FileStatus, RepositoryProviderType, RepositoryState, TransactionState
from eag.vcs.errors import RepositoryError, RepositoryValidationError, TransactionError
from eag.vcs.events import BranchCreated, CheckoutCompleted, CommitCreated, RepositoryOpened
from eag.vcs.models import RepositoryDescriptor
from eag.vcs.providers.git import GitProvider
from eag.vcs.runtime import RepositoryRuntime
from eag.vcs.transaction import TransactionManager
from eag.vcs.validator import RepositoryValidator


@dataclass
class MockEventBus:
    """Mock EventBus to record published events for testing."""

    published_events: list[Any] = field(default_factory=list)

    def publish(self, event: Any) -> None:
        self.published_events.append(event)


@pytest.fixture
def temp_repo_root(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def event_bus() -> MockEventBus:
    return MockEventBus()


@pytest.fixture
def runtime(temp_repo_root: Path, event_bus: MockEventBus) -> RepositoryRuntime:
    rt = RepositoryRuntime(root=temp_repo_root, event_bus=event_bus)
    rt.open()
    (temp_repo_root / "README.md").write_text("# Test Repo")
    rt.commit("Initial commit")
    return rt


class TestRepositoryEnums:
    def test_provider_values(self) -> None:
        assert RepositoryProviderType.GIT == "git"

    def test_state_values(self) -> None:
        assert RepositoryState.READY == "ready"

    def test_file_status_values(self) -> None:
        assert FileStatus.MODIFIED == "modified"


class TestRepositoryValidator:
    def test_invalid_git_directory(self, temp_repo_root: Path) -> None:
        provider = GitProvider()
        validator = RepositoryValidator(provider)
        fake_repo = RepositoryDescriptor(root=temp_repo_root)
        with pytest.raises(RepositoryValidationError, match="Not a valid Git repository"):
            validator.validate(fake_repo)

    def test_detached_head_detection(
        self, runtime: RepositoryRuntime, temp_repo_root: Path
    ) -> None:
        head_commit = runtime._provider._run(["rev-parse", "HEAD"], cwd=temp_repo_root)
        runtime._provider._run(["checkout", head_commit], cwd=temp_repo_root)

        assert runtime._validator.is_detached(runtime.repository) is True
        health = runtime.health()
        assert health.is_detached is True
        assert health.branch == "HEAD"


class TestGitProvider:
    def test_provider_init(self, temp_repo_root: Path) -> None:
        provider = GitProvider()
        repo = provider.init(temp_repo_root)
        assert (temp_repo_root / ".git").exists()
        assert repo.provider == RepositoryProviderType.GIT
        assert repo.branch == "main"

    def test_provider_error_translation(self, temp_repo_root: Path) -> None:
        provider = GitProvider()
        with pytest.raises(RepositoryError, match="Git command failed"):
            provider.commit(RepositoryDescriptor(root=temp_repo_root), "fail")


class TestRepositoryTransactions:
    def test_begin_and_commit(self) -> None:
        tm = TransactionManager()
        tm.begin()
        assert tm.state == TransactionState.ACTIVE
        tm.commit()
        assert tm.state == TransactionState.COMMITTED

    def test_nested_transaction_blocked(self) -> None:
        tm = TransactionManager()
        tm.begin()
        with pytest.raises(TransactionError, match="already active"):
            tm.begin()

    def test_commit_without_begin(self) -> None:
        tm = TransactionManager()
        with pytest.raises(TransactionError, match="No active transaction"):
            tm.commit()

    def test_rollback_without_active(self) -> None:
        tm = TransactionManager()
        with pytest.raises(TransactionError, match="No active transaction"):
            tm.rollback()


class TestRepositoryHistory:
    def test_empty_history(self, temp_repo_root: Path) -> None:
        rt = RepositoryRuntime(root=temp_repo_root, event_bus=MockEventBus())
        rt.open()
        assert rt.history(limit=5) == ()

    def test_single_commit(self, runtime: RepositoryRuntime) -> None:
        history = runtime.history(limit=5)
        assert len(history) == 1
        assert "Initial commit" in history[0].message

    def test_multiple_commits_and_ordering(
        self, runtime: RepositoryRuntime, temp_repo_root: Path
    ) -> None:
        (temp_repo_root / "file2.txt").write_text("content")
        runtime.commit("Second commit")

        history = runtime.history(limit=10)
        assert len(history) == 2
        assert history[0].message == "Second commit"
        assert history[1].message == "Initial commit"

    def test_history_limit(self, runtime: RepositoryRuntime, temp_repo_root: Path) -> None:
        for i in range(5):
            (temp_repo_root / f"file_{i}.txt").write_text(str(i))
            runtime.commit(f"Commit {i}")

        history = runtime.history(limit=3)
        assert len(history) == 3


class TestBranchManagement:
    def test_create_branch(self, runtime: RepositoryRuntime) -> None:
        runtime.create_branch("feature")
        branches = runtime._provider.list_branches(runtime.repository)
        assert "feature" in branches

    def test_duplicate_branch_raises(self, runtime: RepositoryRuntime) -> None:
        runtime.create_branch("feature")
        with pytest.raises(RepositoryError):
            runtime.create_branch("feature")

    def test_checkout_missing_branch(self, runtime: RepositoryRuntime) -> None:
        with pytest.raises(RepositoryError):
            runtime.checkout("nonexistent-branch")

    def test_current_branch(self, runtime: RepositoryRuntime) -> None:
        assert runtime._provider.current_branch(runtime.repository) == "main"

        runtime.create_branch("dev")
        runtime.checkout("dev")
        assert runtime._provider.current_branch(runtime.repository) == "dev"

    def test_list_branches(self, runtime: RepositoryRuntime) -> None:
        runtime.create_branch("b1")
        runtime.create_branch("b2")
        branches = runtime._provider.list_branches(runtime.repository)
        assert len(branches) >= 3  # main, b1, b2


class TestStatusEngine:
    def test_clean_repository(self, runtime: RepositoryRuntime) -> None:
        status = runtime.status()
        assert len(status) == 0

    def test_modified_file(self, runtime: RepositoryRuntime, temp_repo_root: Path) -> None:
        (temp_repo_root / "README.md").write_text("# Modified")
        status = runtime.status()
        assert any(c.path == "README.md" and c.status == FileStatus.MODIFIED for c in status)

    def test_added_file(self, runtime: RepositoryRuntime, temp_repo_root: Path) -> None:
        (temp_repo_root / "new.txt").write_text("new")
        runtime._provider._run(["add", "new.txt"], cwd=temp_repo_root)
        status = runtime.status()
        assert any(c.path == "new.txt" and c.status == FileStatus.ADDED for c in status)

    def test_untracked_file(self, runtime: RepositoryRuntime, temp_repo_root: Path) -> None:
        (temp_repo_root / "untracked.py").write_text("print('hi')")
        status = runtime.status()
        assert any(c.path == "untracked.py" and c.status == FileStatus.UNTRACKED for c in status)

    def test_deleted_file(self, runtime: RepositoryRuntime, temp_repo_root: Path) -> None:
        (temp_repo_root / "temp.txt").write_text("temp")
        runtime.commit("Add temp")
        (temp_repo_root / "temp.txt").unlink()
        status = runtime.status()
        assert any(c.path == "temp.txt" and c.status == FileStatus.DELETED for c in status)


class TestRepositoryEvents:
    def test_repository_opened(self, temp_repo_root: Path, event_bus: MockEventBus) -> None:
        rt = RepositoryRuntime(root=temp_repo_root, event_bus=event_bus)
        rt.open()
        assert any(isinstance(e, RepositoryOpened) for e in event_bus.published_events)

    def test_commit_created(
        self, runtime: RepositoryRuntime, temp_repo_root: Path, event_bus: MockEventBus
    ) -> None:
        (temp_repo_root / "file.txt").write_text("test")
        runtime.commit("Add file")
        assert any(isinstance(e, CommitCreated) for e in event_bus.published_events)

    def test_branch_created(self, runtime: RepositoryRuntime, event_bus: MockEventBus) -> None:
        runtime.create_branch("feature")
        assert any(isinstance(e, BranchCreated) for e in event_bus.published_events)

    def test_checkout_completed(self, runtime: RepositoryRuntime, event_bus: MockEventBus) -> None:
        runtime.create_branch("feature")
        runtime.checkout("feature")
        assert any(isinstance(e, CheckoutCompleted) for e in event_bus.published_events)

    def test_event_order(self, temp_repo_root: Path, event_bus: MockEventBus) -> None:
        rt = RepositoryRuntime(root=temp_repo_root, event_bus=event_bus)
        rt.open()
        (temp_repo_root / "f.txt").write_text("data")
        rt.commit("Commit 1")

        event_types = [type(e) for e in event_bus.published_events]
        assert event_types == [RepositoryOpened, CommitCreated]


class TestRuntimeMetrics:
    def test_commit_count(self, runtime: RepositoryRuntime, temp_repo_root: Path) -> None:
        (temp_repo_root / "f1.txt").write_text("1")
        runtime.commit("C1")
        (temp_repo_root / "f2.txt").write_text("2")
        runtime.commit("C2")
        assert runtime.metrics().commits == 3  # 1 initial + 2 new

    def test_branch_count(self, runtime: RepositoryRuntime) -> None:
        runtime.create_branch("b1")
        runtime.create_branch("b2")
        assert runtime.metrics().branches == 2

    def test_checkout_count(self, runtime: RepositoryRuntime) -> None:
        runtime.create_branch("b1")
        runtime.checkout("b1")
        runtime.checkout("main")
        assert runtime.metrics().checkouts == 2

    def test_failure_count(self, runtime: RepositoryRuntime) -> None:
        with pytest.raises(Exception, match="."):
            runtime.checkout("nonexistent")
        assert runtime.metrics().failures == 1


class TestExplainability:
    def test_contains_branch(self, runtime: RepositoryRuntime) -> None:
        assert "Branch: main" in runtime.explain()

    def test_contains_provider(self, runtime: RepositoryRuntime) -> None:
        assert "Provider: git" in runtime.explain()

    def test_contains_state(self, runtime: RepositoryRuntime) -> None:
        assert "State: ready" in runtime.explain()

    def test_contains_modified_count(
        self, runtime: RepositoryRuntime, temp_repo_root: Path
    ) -> None:
        # 1. Create and commit a file so Git tracks it
        f_path = temp_repo_root / "f.txt"
        f_path.write_text("initial")
        runtime.commit("Initial commit")
        
        # 2. Modify the tracked file
        f_path.write_text("modified")
        
        explanation = runtime.explain()
        assert "Modified files: 1" in explanation

    def test_deterministic(self, runtime: RepositoryRuntime) -> None:
        exp1 = runtime.explain()
        exp2 = runtime.explain()
        assert exp1 == exp2


class TestIntegration:
    def test_workspace_write_then_repo_commit(
        self, runtime: RepositoryRuntime, temp_repo_root: Path
    ) -> None:
        from eag.events import EventBus as RealEventBus
        from eag.workspace.enums import WorkspaceMode
        from eag.workspace.runtime import WorkspaceRuntime

        ws_rt = WorkspaceRuntime(
            root=temp_repo_root, mode=WorkspaceMode.LIVE, event_bus=RealEventBus()
        )
        ws_rt.open()
        ws_rt.write("app.py", "print('hello')")

        status = runtime.status()
        assert any(c.path == "app.py" for c in status)

        runtime.commit("Add app.py")
        assert len(runtime.status()) == 0  # Clean after commit
