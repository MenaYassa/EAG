"""Git plugin errors."""


class GitError(Exception):
    """Base exception for Git capability failures."""


class GitNotAvailableError(GitError):
    """Raised when the Git executable is unavailable."""


class NotGitRepositoryError(GitError):
    """Raised when the workspace is not a Git repository."""


class GitCommandError(GitError):
    """Raised when a Git command fails."""

    def __init__(
        self,
        *,
        command: tuple[str, ...],
        return_code: int,
        stderr: str,
    ) -> None:
        self.command = command
        self.return_code = return_code
        self.stderr = stderr

        command_text = " ".join(command)

        super().__init__(
            f"Git command failed with exit code {return_code}: {command_text}\n{stderr}"
        )
