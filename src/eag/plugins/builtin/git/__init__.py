"""Built-in Git plugin."""

from eag.plugins.builtin.git.errors import (
    GitCommandError,
    GitError,
    GitNotAvailableError,
    NotGitRepositoryError,
)
from eag.plugins.builtin.git.models import (
    GitCommit,
    GitDiff,
    GitFileStatus,
    GitStatus,
)
from eag.plugins.builtin.git.plugin import GitPlugin
from eag.plugins.builtin.git.tool import (
    GIT_BRANCH,
    GIT_DIFF,
    GIT_LOG,
    GIT_STATUS,
    GitTool,
)

__all__ = [
    "GIT_BRANCH",
    "GIT_DIFF",
    "GIT_LOG",
    "GIT_STATUS",
    "GitCommandError",
    "GitCommit",
    "GitDiff",
    "GitError",
    "GitFileStatus",
    "GitNotAvailableError",
    "GitPlugin",
    "GitStatus",
    "GitTool",
    "NotGitRepositoryError",
]
