"""Repository runtime for EAG."""

from pathlib import Path
from typing import cast

from eag.events import EventBus
from eag.vcs.enums import FileStatus
from eag.vcs.errors import RepositoryError
from eag.vcs.events import BranchCreated, CheckoutCompleted, CommitCreated, RepositoryOpened
from eag.vcs.models import (
    Commit,
    FileChange,
    RepositoryDescriptor,
    RepositoryHealth,
    RepositoryMetrics,
)
from eag.vcs.protocol import RepositoryProvider
from eag.vcs.providers.git import GitProvider
from eag.vcs.transaction import TransactionManager
from eag.vcs.validator import RepositoryValidator


class RepositoryRuntime:
    """The public API for the Repository Platform."""

    def __init__(
        self, root: Path, event_bus: EventBus, provider: RepositoryProvider | None = None
    ) -> None:
        self._root = root
        self._event_bus = event_bus
        self._provider = provider or GitProvider()
        # Explicitly cast to GitProvider for internal Git-specific operations
        self._git_provider = cast(GitProvider, self._provider)
        self._validator = RepositoryValidator(self._git_provider)
        self._transaction = TransactionManager()
        self._repository: RepositoryDescriptor | None = None

        self._commit_count = 0
        self._branch_count = 0
        self._checkout_count = 0
        self._failure_count = 0

    def open(self) -> RepositoryDescriptor:
        repo = self._provider.init(self._root)
        self._validator.validate(repo)
        self._repository = repo
        self._event_bus.publish(
            RepositoryOpened(repository_id=repo.repository_id)  # type: ignore[arg-type]
        )
        return repo

    @property
    def repository(self) -> RepositoryDescriptor:
        if self._repository is None:
            raise RepositoryError("Repository not opened. Call open() first.")
        return self._repository

    def status(self) -> tuple[FileChange, ...]:
        return self._provider.status(self.repository)

    def commit(self, message: str) -> str:
        self._transaction.begin()
        try:
            commit_id = self._provider.commit(self.repository, message)
            self._transaction.commit()
            self._commit_count += 1
            self._event_bus.publish(
                CommitCreated(repository_id=self.repository.repository_id, commit_id=commit_id)  # type: ignore[arg-type]
            )
            return commit_id
        except Exception as e:
            self._transaction.rollback()
            self._failure_count += 1
            raise RepositoryError(f"Commit failed: {e}") from e
        finally:
            self._transaction.reset()

    def create_branch(self, name: str) -> None:
        try:
            self._provider.create_branch(self.repository, name)
            self._branch_count += 1
            self._event_bus.publish(
                BranchCreated(repository_id=self.repository.repository_id, branch_name=name)  # type: ignore[arg-type]
            )
        except Exception:
            self._failure_count += 1
            raise

    def checkout(self, name: str) -> None:
        try:
            self._provider.checkout(self.repository, name)
            self._checkout_count += 1
            self._event_bus.publish(
                CheckoutCompleted(repository_id=self.repository.repository_id, branch_name=name)  # type: ignore[arg-type]
            )
        except Exception:
            self._failure_count += 1
            raise

    def history(self, limit: int = 10) -> tuple[Commit, ...]:
        return self._provider.history(self.repository, limit)

    def health(self) -> RepositoryHealth:
        is_detached = self._validator.is_detached(self.repository)
        return RepositoryHealth(
            state=self.repository.state,
            provider=self.repository.provider,
            branch="HEAD" if is_detached else self._git_provider.current_branch(self.repository),
            head=self._git_provider._run(["rev-parse", "HEAD"], cwd=self.repository.root, check=False),
            is_detached=is_detached,
        )

    def metrics(self) -> RepositoryMetrics:
        return RepositoryMetrics(
            commits=self._commit_count,
            branches=self._branch_count,
            checkouts=self._checkout_count,
            failures=self._failure_count,
        )

    def explain(self) -> str:
        health = self.health()
        status = self.status()
        
        # Use explicit Enums instead of strings to ensure accurate counting
        modified = sum(1 for s in status if s.status == FileStatus.MODIFIED)
        untracked = sum(1 for s in status if s.status == FileStatus.UNTRACKED)

        return (
            f"Repository Platform\n"
            f"────────────────────────────────\n"
            f"Provider: {health.provider.value}\n"
            f"Branch: {health.branch}\n"
            f"HEAD: {health.head[:7]}\n"
            f"State: {health.state.value}\n"
            f"Detached: {health.is_detached}\n"
            f"Modified files: {modified}\n"
            f"Untracked files: {untracked}\n"
        )