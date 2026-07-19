"""Repository provider protocol for EAG."""

from pathlib import Path
from typing import Protocol, runtime_checkable

from eag.vcs.models import Commit, FileChange, RepositoryDescriptor


@runtime_checkable
class RepositoryProvider(Protocol):
    """The contract for a version control provider."""

    def init(self, root: Path) -> RepositoryDescriptor: ...

    def status(self, repo: RepositoryDescriptor) -> tuple[FileChange, ...]: ...

    def commit(self, repo: RepositoryDescriptor, message: str) -> str: ...

    def create_branch(self, repo: RepositoryDescriptor, name: str) -> None: ...

    def checkout(self, repo: RepositoryDescriptor, name: str) -> None: ...

    def tag(self, repo: RepositoryDescriptor, name: str, message: str) -> None: ...

    def history(self, repo: RepositoryDescriptor, limit: int) -> tuple[Commit, ...]: ...
