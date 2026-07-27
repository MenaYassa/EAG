"""Rollback engine."""

from __future__ import annotations

from datetime import UTC, datetime

from eag.events import EventBus
from eag.safety.checkpoint import CheckpointBackend
from eag.safety.errors import RollbackError
from eag.safety.events import RollbackCompleted, RollbackStarted
from eag.safety.models import RollbackResult, SafetyErrorRecord


class RollbackEngine:
    """Handles rolling back to checkpoints."""

    def __init__(
        self,
        backend: CheckpointBackend,
        event_bus: EventBus,
    ) -> None:
        self._backend = backend
        self._event_bus = event_bus

    def rollback_latest(self) -> RollbackResult:
        """Rollback to the latest checkpoint."""
        latest = self._backend.latest()
        if latest is None:
            raise RollbackError("No checkpoint available to rollback to.")
        return self.rollback(latest.id)

    def rollback(self, checkpoint_id: str) -> RollbackResult:
        """Rollback to a specific checkpoint."""
        start = datetime.now(UTC)
        self._event_bus.publish(RollbackStarted(checkpoint_id=checkpoint_id))
        try:
            self._backend.rollback(checkpoint_id)
            duration = datetime.now(UTC) - start
            self._event_bus.publish(RollbackCompleted(checkpoint_id=checkpoint_id))
            return RollbackResult(
                success=True,
                checkpoint_id=checkpoint_id,
                duration=duration,
            )
        except Exception as exc:
            duration = datetime.now(UTC) - start
            self._event_bus.publish(RollbackCompleted(checkpoint_id=checkpoint_id))
            return RollbackResult(
                success=False,
                checkpoint_id=checkpoint_id,
                duration=duration,
                errors=(
                    SafetyErrorRecord(
                        message=str(exc),
                        code="ROLLBACK_FAILED",
                    ),
                ),
            )


__all__ = [
    "RollbackEngine",
]
