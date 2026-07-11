"""Safety backends."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from eag.safety.models import Checkpoint, SafetyBackend, WorkspaceStatus


class GitSafetyBackend:
    """A Git-based safety backend using subprocess."""

    def __init__(self, workspace: Path) -> None:
        self._workspace = workspace
        self._refs: dict[str, str] = {}

    def _run(self, *args: str, check: bool = True) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=self._workspace,
            capture_output=True,
            text=True,
            check=check,
        )
        return result.stdout.strip()

    def inspect(self) -> WorkspaceStatus:
        try:
            self._run("rev-parse", "--is-inside-work-tree")
        except subprocess.CalledProcessError:
            return WorkspaceStatus(
                workspace=PurePosixPath(self._workspace),
                backend=SafetyBackend.UNKNOWN,
                branch=None,
                head=None,
                dirty=False,
                has_untracked=False,
                has_conflicts=False,
                detached_head=False,
            )

        branch = self._run("branch", "--show-current")
        head = self._run("rev-parse", "HEAD")
        detached_head = not bool(branch)

        status = self._run("status", "--porcelain")
        dirty = False
        has_untracked = False
        has_conflicts = False

        for line in status.splitlines():
            if line.startswith("??"):
                has_untracked = True
            elif "U" in line[:2]:
                has_conflicts = True
            else:
                dirty = True

        return WorkspaceStatus(
            workspace=PurePosixPath(self._workspace),
            backend=SafetyBackend.GIT,
            branch=branch or None,
            head=head or None,
            dirty=dirty,
            has_untracked=has_untracked,
            has_conflicts=has_conflicts,
            detached_head=detached_head,
        )

    def create(self, checkpoint_id: str, description: str) -> Checkpoint:
        self._run("add", "-A")
        # Use --allow-empty to guarantee a checkpoint can always be created,
        # even if the workspace is completely clean.
        self._run("commit", "--allow-empty", "-m", f"{checkpoint_id}: {description}")
        ref = self._run("rev-parse", "HEAD")
        self._refs[checkpoint_id] = ref
        return Checkpoint(
            id=checkpoint_id,
            created_at=datetime.now(UTC),
            description=description,
            backend=SafetyBackend.GIT,
            backend_reference=ref,
        )

    def rollback(self, checkpoint_id: str) -> None:
        ref = self._refs.get(checkpoint_id)
        if not ref:
            raise ValueError(f"Unknown checkpoint ID: {checkpoint_id}")
        self._run("reset", "--hard", ref)

    def latest(self) -> Checkpoint | None:
        return None  # Handled by SafetyRuntime internally

    def exists(self, checkpoint_id: str) -> bool:
        return checkpoint_id in self._refs


__all__ = [
    "GitSafetyBackend",
]
