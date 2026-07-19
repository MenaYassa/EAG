"""Repository validator for EAG."""

from eag.vcs.errors import RepositoryValidationError
from eag.vcs.models import RepositoryDescriptor
from eag.vcs.providers.git import GitProvider


class RepositoryValidator:
    """Validates repository state and permissions."""

    def __init__(self, provider: GitProvider) -> None:
        self._provider = provider

    def validate(self, repo: RepositoryDescriptor) -> None:
        git_dir = repo.root / ".git"
        if not git_dir.exists():
            raise RepositoryValidationError(f"Not a valid Git repository: {repo.root}")

    def is_detached(self, repo: RepositoryDescriptor) -> bool:
        branch = self._provider.current_branch(repo)
        return branch == "HEAD"
