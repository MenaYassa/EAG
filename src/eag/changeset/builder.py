"""ChangeSet builder subsystem."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import PurePosixPath
from uuid import uuid4

from eag.changeset.errors import ChangeSetFinalizedError
from eag.changeset.events import (
    ChangeRecorded,
    ChangeSetBuilderStarted,
    ChangeSetFinalized,
)
from eag.changeset.models import (
    ChangedFile,
    ChangeIdentity,
    ChangeSet,
    ChangeSummary,
    CommandRecord,
    ExecutionMetrics,
    GitSnapshot,
    TestRecord,
)
from eag.changeset.state import ChangeSetBuilderState
from eag.events import EventBus


@dataclass(slots=True)
class _BuilderData:
    """Mutable internal state for the ChangeSetBuilder."""

    files: list[ChangedFile] = field(default_factory=list)
    commands: list[CommandRecord] = field(default_factory=list)
    tests: list[TestRecord] = field(default_factory=list)
    artifacts: list[PurePosixPath] = field(default_factory=list)
    git: GitSnapshot | None = None
    summary: ChangeSummary | None = None


class ChangeSetBuilder:
    """Builds immutable ChangeSet objects progressively."""

    def __init__(
        self,
        identity: ChangeIdentity | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self._identity = identity or ChangeIdentity(
            id=str(uuid4()),
            created_at=datetime.now(UTC),
        )
        self._event_bus = event_bus
        self._state = ChangeSetBuilderState.BUILDING
        self._data = _BuilderData()

        if self._event_bus:
            self._event_bus.publish(
                ChangeSetBuilderStarted(identity_id=self._identity.id)
            )

    def _ensure_building(self) -> None:
        """Ensure the builder is still in the BUILDING state."""
        if self._state != ChangeSetBuilderState.BUILDING:
            raise ChangeSetFinalizedError(
                "Cannot modify a finalized ChangeSetBuilder."
            )

    def record_file(self, file: ChangedFile) -> None:
        """Record a file change."""
        self._ensure_building()
        self._data.files.append(file)
        self._publish("file", file)

    def record_command(self, command: CommandRecord) -> None:
        """Record a command execution."""
        self._ensure_building()
        self._data.commands.append(command)
        self._publish("command", command)

    def record_test(self, test: TestRecord) -> None:
        """Record a test execution."""
        self._ensure_building()
        self._data.tests.append(test)
        self._publish("test", test)

    def record_git(self, git: GitSnapshot) -> None:
        """Record a Git snapshot. Overwrites existing snapshot."""
        self._ensure_building()
        self._data.git = git
        self._publish("git", git)

    def record_summary(self, summary: ChangeSummary) -> None:
        """Record a summary. Overwrites existing summary."""
        self._ensure_building()
        self._data.summary = summary
        self._publish("summary", summary)

    def record_artifact(self, artifact: PurePosixPath) -> None:
        """Record an artifact path."""
        self._ensure_building()
        self._data.artifacts.append(artifact)
        self._publish("artifact", artifact)

    def finalize(self) -> ChangeSet:
        """Finalize the builder and return an immutable ChangeSet."""
        self._ensure_building()

        # Compute metrics automatically
        metrics = ExecutionMetrics(
            commands=len(self._data.commands),
            changed_files=len(self._data.files),
            tests=len(self._data.tests),
            duration=sum(
                (cmd.duration for cmd in self._data.commands),
                start=timedelta(0),
            ),
            warnings=0,
            errors=0,
        )

        changeset = ChangeSet(
            identity=self._identity,
            files=tuple(self._data.files),
            commands=tuple(self._data.commands),
            tests=tuple(self._data.tests),
            git=self._data.git,
            metrics=metrics,
            summary=self._data.summary,
            artifacts=tuple(self._data.artifacts),
        )

        # Transition state AFTER successful construction
        self._state = ChangeSetBuilderState.FINALIZED

        if self._event_bus:
            self._event_bus.publish(
                ChangeSetFinalized(changeset_id=self._identity.id)
            )

        return changeset

    def _publish(self, kind: str, payload: object) -> None:
        """Publish a ChangeRecorded event if event bus is present."""
        if self._event_bus:
            self._event_bus.publish(
                ChangeRecorded(
                    changeset_id=self._identity.id,
                    kind=kind,
                    payload=payload,
                )
            )


__all__ = [
    "ChangeSetBuilder",
]