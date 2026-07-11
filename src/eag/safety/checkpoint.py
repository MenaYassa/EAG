"""Checkpoint manager and backend protocol."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from eag.events import EventBus
from eag.safety.events import CheckpointCreated, RollbackCompleted, RollbackStarted
from eag.safety.models import Checkpoint


class CheckpointBackend(Protocol):
    """Protocol for checkpoint backends."""

    def create(self, checkpoint_id: str, description: str) -> Checkpoint:
        """Create a new checkpoint."""
        ...

    def rollback(self, checkpoint_id: str) -> None:
        """Rollback to a specific checkpoint."""
        ...

    def latest(self) -> Checkpoint | None:
        """Return the latest checkpoint."""
        ...

    def exists(self, checkpoint_id: str) -> bool:
        """Check if a checkpoint exists."""
        ...


class CheckpointManager:
    """Manages engineering checkpoints."""

    def __init__(
        self,
        backend: CheckpointBackend,
        event_bus: EventBus,
    ) -> None:
        self._backend = backend
        self._event_bus = event_bus
        self._counter = 1

    def create(self, description: str) -> Checkpoint:
        """Create a new checkpoint."""
        checkpoint_id = f"CP-{datetime.now(UTC).strftime('%Y%m%d')}-{self._counter:04d}"
        self._counter += 1
        checkpoint = self._backend.create(checkpoint_id, description)
        self._event_bus.publish(
            CheckpointCreated(
                checkpoint_id=checkpoint.id,
                description=checkpoint.description,
            )
        )
        return checkpoint

    def latest(self) -> Checkpoint | None:
        """Return the latest checkpoint."""
        return self._backend.latest()

    def exists(self, checkpoint_id: str) -> bool:
        """Check if a checkpoint exists."""
        return self._backend.exists(checkpoint_id)

    def rollback(self, checkpoint_id: str) -> None:
        """Rollback to a specific checkpoint."""
        self._event_bus.publish(RollbackStarted(checkpoint_id=checkpoint_id))
        self._backend.rollback(checkpoint_id)
        self._event_bus.publish(RollbackCompleted(checkpoint_id=checkpoint_id))


__all__ = [
    "CheckpointBackend",
    "CheckpointManager",
]
