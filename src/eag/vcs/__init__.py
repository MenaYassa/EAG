"""Repository Platform for EAG."""

from eag.vcs.enums import (
    FileStatus,
    RepositoryProviderType,
    RepositoryState,
    TransactionState,
)
from eag.vcs.errors import (
    GitError,
    RepositoryError,
    RepositoryValidationError,
    TransactionError,
)
from eag.vcs.events import (
    BranchCreated,
    CheckoutCompleted,
    CommitCreated,
    RepositoryEvent,
    RepositoryOpened,
)
from eag.vcs.models import (
    Commit,
    FileChange,
    RepositoryDescriptor,
    RepositoryHealth,
    RepositoryMetrics,
)
from eag.vcs.protocol import RepositoryProvider
from eag.vcs.providers.git import GitProvider
from eag.vcs.runtime import RepositoryRuntime
from eag.vcs.transaction import TransactionManager
from eag.vcs.validator import RepositoryValidator

__all__ = [
    # Enums
    "FileStatus",
    "RepositoryProviderType",
    "RepositoryState",
    "TransactionState",
    # Errors
    "GitError",
    "RepositoryError",
    "RepositoryValidationError",
    "TransactionError",
    # Events
    "BranchCreated",
    "CheckoutCompleted",
    "CommitCreated",
    "RepositoryEvent",
    "RepositoryOpened",
    # Models
    "Commit",
    "FileChange",
    "RepositoryDescriptor",
    "RepositoryHealth",
    "RepositoryMetrics",
    # Runtime & Providers
    "GitProvider",
    "RepositoryProvider",
    "RepositoryRuntime",
    "TransactionManager",
    "RepositoryValidator",
]
