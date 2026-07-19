"""VCS domain events for EAG."""

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class RepositoryEvent:
    repository_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True, kw_only=True)
class RepositoryOpened(RepositoryEvent):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class CommitCreated(RepositoryEvent):
    commit_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class BranchCreated(RepositoryEvent):
    branch_name: str


@dataclass(frozen=True, slots=True, kw_only=True)
class CheckoutCompleted(RepositoryEvent):
    branch_name: str
