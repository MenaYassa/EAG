"""Workspace manager for EAG."""

from typing import Any

from eag.events import EventBus
from eag.workspace.enums import WorkspaceState
from eag.workspace.errors import WorkspaceLockedError
from eag.workspace.events import (
    FileRead,
    FileWritten,
    WorkspaceClosed,
    WorkspaceOpened,
    WorkspaceValidated,
)
from eag.workspace.filesystem import LocalFilesystem
from eag.workspace.locker import WorkspaceLocker
from eag.workspace.models import Workspace, WorkspaceMetrics
from eag.workspace.resolver import PathResolver
from eag.workspace.snapshot import SnapshotEngine
from eag.workspace.validator import WorkspaceValidator


class WorkspaceManager:
    """Manages the workspace lifecycle and operations."""

    def __init__(
        self,
        workspace: Workspace,
        event_bus: EventBus,
        filesystem: LocalFilesystem,
        resolver: PathResolver,
        validator: WorkspaceValidator,
        locker: WorkspaceLocker,
        snapshot_engine: SnapshotEngine,
    ) -> None:
        self._workspace = workspace
        self._event_bus = event_bus
        self._fs = filesystem
        self._resolver = resolver
        self._validator = validator
        self._locker = locker
        self._snapshot_engine = snapshot_engine

        self._metrics = WorkspaceMetrics()
        self._state = workspace.state

    @property
    def workspace(self) -> Workspace:
        return self._workspace

    @property
    def state(self) -> WorkspaceState:
        return self._state

    def open(self) -> None:
        self._validator.validate(self._workspace.root, self._workspace.mode)
        self._state = WorkspaceState.READY
        self._event_bus.publish(
            WorkspaceOpened(
                workspace_id=self._workspace.workspace_id, root=str(self._workspace.root)
            )  # type: ignore[arg-type]
        )
        self._event_bus.publish(
            WorkspaceValidated(workspace_id=self._workspace.workspace_id)  # type: ignore[arg-type]
        )

    def close(self) -> None:
        self._state = WorkspaceState.CLOSED
        self._event_bus.publish(
            WorkspaceClosed(workspace_id=self._workspace.workspace_id)  # type: ignore[arg-type]
        )

    def read(self, path: str) -> str:
        resolved = self._resolver.resolve(path)
        content = self._fs.read(resolved)
        self._event_bus.publish(
            FileRead(workspace_id=self._workspace.workspace_id, path=str(resolved))  # type: ignore[arg-type]
        )
        return content

    def write(self, path: str, content: str) -> None:
        if self._locker.state == "locked":
            raise WorkspaceLockedError("Cannot write to locked workspace.")
        resolved = self._resolver.resolve(path)
        self._fs.write(resolved, content)
        self._event_bus.publish(
            FileWritten(workspace_id=self._workspace.workspace_id, path=str(resolved))  # type: ignore[arg-type]
        )
        self._state = WorkspaceState.MODIFIED

    def snapshot(self) -> Any:
        snap = self._snapshot_engine.create(self._workspace.root)
        self._event_bus.publish(
            None  # type: ignore[arg-type]
        )
        return snap
