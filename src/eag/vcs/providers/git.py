"""Git provider implementation for EAG."""

import os
import subprocess
from datetime import datetime
from pathlib import Path

from eag.vcs.enums import FileStatus, RepositoryProviderType, RepositoryState
from eag.vcs.errors import RepositoryError
from eag.vcs.models import Commit, FileChange, RepositoryDescriptor


class GitProvider:
    """Concrete RepositoryProvider implementation using the Git CLI."""

    def _run(self, args: list[str], cwd: Path, check: bool = True) -> str:
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=cwd,
                capture_output=True,
                text=True,
                check=check,
            )
            # FIX: Use rstrip to remove newlines but preserve leading spaces!
            return result.stdout.rstrip("\r\n") 
        except subprocess.CalledProcessError as e:
            if check:
                raise RepositoryError(f"Git command failed: {e.stderr.strip()}") from e
            return ""
        except FileNotFoundError as e:
            raise RepositoryError("Git executable not found.") from e

    def init(self, root: Path) -> RepositoryDescriptor:
        # Force default branch to 'main' for consistency across environments
        self._run(["init", "--initial-branch=main"], cwd=root, check=False)
        self._run(["symbolic-ref", "HEAD", "refs/heads/main"], cwd=root, check=False)
        self._run(["config", "user.email", "eag@local"], cwd=root)
        self._run(["config", "user.name", "EAG Agent"], cwd=root)
        return RepositoryDescriptor(
            root=root,
            provider=RepositoryProviderType.GIT,
            state=RepositoryState.READY,
            branch="main",
        )

    def status(self, repo: RepositoryDescriptor) -> tuple[FileChange, ...]:
        output = self._run(["status", "--porcelain"], cwd=repo.root)
        changes: list[FileChange] = []
        for line in output.splitlines():
            if not line.strip():
                continue
            status_code = line[:2].strip()
            # Normalize path to remove any leading './'
            path = os.path.normpath(line[3:].strip()).replace("\\", "/")

            status_map = {
                "M": FileStatus.MODIFIED,
                "A": FileStatus.ADDED,
                "D": FileStatus.DELETED,
                "R": FileStatus.RENAMED,
                "??": FileStatus.UNTRACKED,
            }
            changes.append(
                FileChange(path=path, status=status_map.get(status_code, FileStatus.MODIFIED))
            )
        return tuple(changes)

    def commit(self, repo: RepositoryDescriptor, message: str) -> str:
        self._run(["add", "."], cwd=repo.root)
        # Use check=True to ensure commit succeeds
        self._run(["commit", "-m", message], cwd=repo.root)
        return self._run(["rev-parse", "HEAD"], cwd=repo.root)

    def create_branch(self, repo: RepositoryDescriptor, name: str) -> None:
        self._run(["branch", name], cwd=repo.root)

    def list_branches(self, repo: RepositoryDescriptor) -> tuple[str, ...]:
        output = self._run(["branch", "--list"], cwd=repo.root)
        branches = [b.strip().replace("*", "").strip() for b in output.splitlines() if b.strip()]
        return tuple(branches)

    def delete_branch(self, repo: RepositoryDescriptor, name: str) -> None:
        self._run(["branch", "-d", name], cwd=repo.root)

    def current_branch(self, repo: RepositoryDescriptor) -> str:
        return self._run(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo.root)

    def checkout(self, repo: RepositoryDescriptor, name: str) -> None:
        self._run(["checkout", name], cwd=repo.root)

    def tag(self, repo: RepositoryDescriptor, name: str, message: str) -> None:
        self._run(["tag", "-a", name, "-m", message], cwd=repo.root)

    def history(self, repo: RepositoryDescriptor, limit: int) -> tuple[Commit, ...]:
        fmt = "%H|%an|%aI|%s|%P"
        output = self._run(
            ["log", f"-{limit}", f"--pretty=format:{fmt}"], cwd=repo.root, check=False
        )
        commits: list[Commit] = []
        for line in output.splitlines():
            if not line.strip():
                continue
            parts = line.split("|")
            if len(parts) >= 4:
                commits.append(
                    Commit(
                        commit_id=parts[0],
                        author=parts[1],
                        timestamp=datetime.fromisoformat(parts[2]),
                        message=parts[3],
                        parents=tuple(parts[4].split()) if len(parts) > 4 and parts[4] else (),
                    )
                )
        return tuple(commits)
