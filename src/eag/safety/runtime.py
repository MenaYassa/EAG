"""Safety runtime."""

from __future__ import annotations

from pathlib import PurePosixPath

from eag.events import EventBus
from eag.safety.checkpoint import CheckpointManager
from eag.safety.errors import WorkspaceUnsafeError
from eag.safety.events import WorkspaceInspected
from eag.safety.inspector import SafetyReportBuilder, WorkspaceInspector
from eag.safety.models import Checkpoint, SafetyReport, WorkspaceHealth
from eag.safety.rollback import RollbackEngine
from eag.safety.state import SafetyState


class SafetyRuntime:
    """Orchestrates engineering safety operations."""

    def __init__(
        self,
        workspace: PurePosixPath,
        inspector: WorkspaceInspector,
        checkpoint_manager: CheckpointManager,
        rollback_engine: RollbackEngine,
        event_bus: EventBus,
    ) -> None:
        self._workspace = workspace
        self._inspector = inspector
        self._checkpoint_manager = checkpoint_manager
        self._rollback_engine = rollback_engine
        self._event_bus = event_bus
        self._report_builder = SafetyReportBuilder()
        self._state = SafetyState.UNKNOWN
        self._latest_checkpoint: Checkpoint | None = None

    def inspect(self) -> SafetyReport:
        """Inspect the workspace and return a safety report."""
        status = self._inspector.inspect()
        report = self._report_builder.build(status)

        # Only transition from UNKNOWN to READY if there are no errors
        if self._state == SafetyState.UNKNOWN and not report.errors:
            self._state = SafetyState.READY

        self._event_bus.publish(
            WorkspaceInspected(
                workspace=str(report.workspace),
                health=report.health,
                status=report.status,
            )
        )

        return SafetyReport(
            workspace=report.workspace,
            backend=report.backend,
            health=report.health,
            status=report.status,
            state=self._state,
            warnings=report.warnings,
            errors=report.errors,
            checkpoint=self._latest_checkpoint,
        )

    def prepare(self) -> SafetyReport:
        """Prepare the workspace for execution by creating a checkpoint."""
        report = self.inspect()
        if report.health == WorkspaceHealth.UNSAFE:
            raise WorkspaceUnsafeError("Workspace is unsafe for execution.")

        checkpoint = self._checkpoint_manager.create("Pre-execution checkpoint")
        self._latest_checkpoint = checkpoint
        self._state = SafetyState.CHECKPOINT_CREATED

        return SafetyReport(
            workspace=report.workspace,
            backend=report.backend,
            health=report.health,
            status=report.status,
            state=self._state,
            warnings=report.warnings,
            errors=report.errors,
            checkpoint=checkpoint,
        )

    def create_checkpoint(self, description: str) -> Checkpoint:
        """Create a new checkpoint."""
        checkpoint = self._checkpoint_manager.create(description)
        self._latest_checkpoint = checkpoint
        self._state = SafetyState.CHECKPOINT_CREATED
        return checkpoint

    def rollback(self) -> None:
        """Rollback to the latest checkpoint."""
        if self._latest_checkpoint is None:
            return
        self._state = SafetyState.ROLLING_BACK
        self._rollback_engine.rollback(self._latest_checkpoint.id)
        self._state = SafetyState.ROLLED_BACK


__all__ = [
    "SafetyRuntime",
]
