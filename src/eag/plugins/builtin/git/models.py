"""Data models for Git capabilities."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class GitFileStatus:
    """Describe the Git state of one path."""

    path: str
    index_status: str
    worktree_status: str


@dataclass(frozen=True, slots=True, kw_only=True)
class GitStatus:
    """Describe repository working-tree state."""

    branch: str | None
    detached: bool
    files: tuple[GitFileStatus, ...]

    @property
    def clean(self) -> bool:
        """Return whether the working tree is clean."""
        return not self.files


@dataclass(frozen=True, slots=True, kw_only=True)
class GitDiff:
    """Describe a Git diff result."""

    patch: str
    staged: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class GitCommit:
    """Describe one Git commit."""

    commit_hash: str
    author_name: str
    author_email: str
    authored_at: str
    subject: str
