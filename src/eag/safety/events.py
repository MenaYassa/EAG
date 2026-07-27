"""Safety subsystem events."""

from dataclasses import dataclass

from eag.events import Event
from eag.safety.models import WorkspaceHealth, WorkspaceStatus


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkspaceInspected(Event):
    """Published after workspace inspection."""

    workspace: str
    health: WorkspaceHealth
    status: WorkspaceStatus


@dataclass(frozen=True, slots=True, kw_only=True)
class CheckpointCreated(Event):
    """Published when a checkpoint is created."""

    checkpoint_id: str
    description: str


@dataclass(frozen=True, slots=True, kw_only=True)
class CheckpointDeleted(Event):
    """Published when a checkpoint is deleted."""

    checkpoint_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class RollbackStarted(Event):
    """Published when a rollback starts."""

    checkpoint_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class RollbackCompleted(Event):
    """Published when a rollback completes."""

    checkpoint_id: str


__all__ = [
    "CheckpointCreated",
    "CheckpointDeleted",
    "RollbackCompleted",
    "RollbackStarted",
    "WorkspaceInspected",
]
