"""Workspace inspector and safety report builder."""

from __future__ import annotations

from typing import Protocol

from eag.safety.models import (
    SafetyBackend,
    SafetyErrorRecord,
    SafetyReport,
    SafetyWarning,
    WorkspaceHealth,
    WorkspaceStatus,
)
from eag.safety.state import SafetyState


class WorkspaceBackend(Protocol):
    """Protocol for workspace inspection backends."""

    def inspect(self) -> WorkspaceStatus:
        """Return the current workspace status."""
        ...


class WorkspaceInspector:
    """Inspects the workspace to determine safety state."""

    def __init__(self, backend: WorkspaceBackend) -> None:
        self._backend = backend

    def inspect(self) -> WorkspaceStatus:
        """Return the current workspace status."""
        return self._backend.inspect()

    def health(self) -> WorkspaceHealth:
        """Determine the health of the workspace."""
        status = self.inspect()

        if status.has_conflicts or status.detached_head or status.backend == SafetyBackend.UNKNOWN:
            return WorkspaceHealth.UNSAFE

        if status.dirty or status.has_untracked:
            return WorkspaceHealth.WARNING

        return WorkspaceHealth.HEALTHY

    def is_safe(self) -> bool:
        """Return True if the workspace is safe for execution."""
        return self.health() != WorkspaceHealth.UNSAFE

    def current_checkpoint_available(self) -> bool:
        """Return True if a checkpoint is available."""
        status = self.inspect()
        return status.head is not None


class SafetyReportBuilder:
    """Builds immutable SafetyReport objects."""

    def build(self, status: WorkspaceStatus) -> SafetyReport:
        """Build a report from the given workspace status."""
        warnings: list[SafetyWarning] = []
        errors: list[SafetyErrorRecord] = []

        if status.backend == SafetyBackend.UNKNOWN:
            errors.append(
                SafetyErrorRecord(
                    message="Not a Git repository",
                    code="NO_REPO",
                )
            )
        if status.has_conflicts:
            errors.append(
                SafetyErrorRecord(
                    message="Merge conflicts present",
                    code="MERGE_CONFLICT",
                )
            )
        if status.detached_head:
            errors.append(
                SafetyErrorRecord(
                    message="Detached HEAD state",
                    code="DETACHED_HEAD",
                )
            )
        if status.dirty:
            warnings.append(
                SafetyWarning(
                    message="Dirty working tree",
                    code="DIRTY_TREE",
                )
            )
        if status.has_untracked:
            warnings.append(
                SafetyWarning(
                    message="Untracked files present",
                    code="UNTRACKED_FILES",
                )
            )

        health = (
            WorkspaceHealth.UNSAFE
            if errors
            else (WorkspaceHealth.WARNING if warnings else WorkspaceHealth.HEALTHY)
        )

        return SafetyReport(
            workspace=status.workspace,
            backend=status.backend,
            health=health,
            status=status,
            state=SafetyState.READY if health != WorkspaceHealth.UNSAFE else SafetyState.UNKNOWN,
            warnings=tuple(warnings),
            errors=tuple(errors),
        )


__all__ = [
    "SafetyReportBuilder",
    "WorkspaceBackend",
    "WorkspaceInspector",
]
