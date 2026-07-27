"""Read-only Git tool for EAG."""

import shutil
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from eag.core import ComponentMetadata, Tool
from eag.plugins.builtin.git.errors import (
    GitCommandError,
    GitNotAvailableError,
    NotGitRepositoryError,
)
from eag.plugins.builtin.git.models import (
    GitCommit,
    GitDiff,
    GitFileStatus,
    GitStatus,
)
from eag.registry import Capability

GIT_STATUS = Capability.parse("git.status")
GIT_DIFF = Capability.parse("git.diff")
GIT_BRANCH = Capability.parse("git.branch")
GIT_LOG = Capability.parse("git.log")


class GitTool(Tool):
    """Provide read-only Git repository capabilities."""

    def __init__(self, workspace: Path) -> None:
        self._workspace = workspace.resolve()

        if shutil.which("git") is None:
            raise GitNotAvailableError("Git executable is not available")

        self._ensure_repository()

    @property
    def metadata(self) -> ComponentMetadata:
        """Return Git tool metadata."""
        return ComponentMetadata(
            name="git-tool",
            version="0.1.0",
            description="Read-only Git repository capabilities",
        )

    @property
    def capabilities(self) -> tuple[Capability, ...]:
        """Return supported Git capabilities."""
        return (
            GIT_STATUS,
            GIT_DIFF,
            GIT_BRANCH,
            GIT_LOG,
        )

    def execute(
        self,
        capability: Capability,
        arguments: Mapping[str, Any],
    ) -> Any:
        """Execute a Git capability."""
        if capability == GIT_STATUS:
            return self.status()

        if capability == GIT_DIFF:
            return self.diff(staged=bool(arguments.get("staged", False)))

        if capability == GIT_BRANCH:
            return self.branch()

        if capability == GIT_LOG:
            return self.log(limit=int(arguments.get("limit", 10)))

        raise ValueError(f"Unsupported capability: '{capability.identifier}'")

    def status(self) -> GitStatus:
        """Return structured repository status."""
        output = self._run(
            "status",
            "--porcelain=v1",
            "--branch",
        )

        lines = output.splitlines()

        branch: str | None = None
        detached = False

        if lines and lines[0].startswith("## "):
            branch_line = lines.pop(0)[3:]

            if branch_line.startswith("HEAD (no branch)"):
                detached = True
            else:
                branch = branch_line.split(
                    "...",
                    maxsplit=1,
                )[0]

        files: list[GitFileStatus] = []

        for line in lines:
            if len(line) < 3:
                continue

            index_status = line[0]
            worktree_status = line[1]
            path = line[3:]

            files.append(
                GitFileStatus(
                    path=path,
                    index_status=index_status,
                    worktree_status=worktree_status,
                )
            )

        return GitStatus(
            branch=branch,
            detached=detached,
            files=tuple(files),
        )

    def diff(
        self,
        staged: bool = False,
    ) -> GitDiff:
        """Return the repository patch."""
        arguments = ["diff"]

        if staged:
            arguments.append("--cached")

        patch = self._run(*arguments)

        return GitDiff(
            patch=patch,
            staged=staged,
        )

    def branch(self) -> str | None:
        """Return the current branch name."""
        result = self._run(
            "branch",
            "--show-current",
        ).strip()

        return result or None

    def log(
        self,
        limit: int = 10,
    ) -> tuple[GitCommit, ...]:
        """Return recent commits."""
        if limit < 1:
            raise ValueError("Git log limit must be at least 1")

        separator = "\x1f"
        record_separator = "\x1e"

        output = self._run(
            "log",
            f"-n{limit}",
            (
                "--format="
                f"%H{separator}"
                f"%an{separator}"
                f"%ae{separator}"
                f"%aI{separator}"
                f"%s{record_separator}"
            ),
        )

        commits: list[GitCommit] = []

        for record in output.split(record_separator):
            record = record.strip()

            if not record:
                continue

            fields = record.split(separator)

            if len(fields) != 5:
                continue

            commits.append(
                GitCommit(
                    commit_hash=fields[0],
                    author_name=fields[1],
                    author_email=fields[2],
                    authored_at=fields[3],
                    subject=fields[4],
                )
            )

        return tuple(commits)

    def _ensure_repository(self) -> None:
        """Verify that the workspace is a Git repository."""
        result = subprocess.run(
            [
                "git",
                "-C",
                str(self._workspace),
                "rev-parse",
                "--is-inside-work-tree",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0 or result.stdout.strip() != "true":
            raise NotGitRepositoryError(f"Not a Git repository: '{self._workspace}'")

    def _run(self, *arguments: str) -> str:
        """Run a Git command inside the workspace."""
        command = (
            "git",
            "-C",
            str(self._workspace),
            *arguments,
        )

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            raise GitCommandError(
                command=command,
                return_code=result.returncode,
                stderr=result.stderr.strip(),
            )

        return result.stdout
