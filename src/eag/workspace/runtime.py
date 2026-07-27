"""Workspace runtime for EAG."""

from pathlib import Path

from eag.events import EventBus
from eag.workspace.enums import WorkspaceMode
from eag.workspace.filesystem import LocalFilesystem
from eag.workspace.locker import WorkspaceLocker
from eag.workspace.manager import WorkspaceManager
from eag.workspace.manifest import ManifestBuilder
from eag.workspace.models import Workspace, WorkspaceHealth, WorkspaceMetrics
from eag.workspace.resolver import PathResolver
from eag.workspace.snapshot import SnapshotEngine
from eag.workspace.validator import WorkspaceValidator


class WorkspaceRuntime:
    """The public API for the Workspace Platform."""

    def __init__(self, root: Path, mode: WorkspaceMode, event_bus: EventBus) -> None:
        self._workspace = Workspace(root=root.resolve(), mode=mode)
        self._event_bus = event_bus

        fs = LocalFilesystem()
        self._manager = WorkspaceManager(
            workspace=self._workspace,
            event_bus=event_bus,
            filesystem=fs,
            resolver=PathResolver(root),
            validator=WorkspaceValidator(),
            locker=WorkspaceLocker(),
            snapshot_engine=SnapshotEngine(fs, ManifestBuilder(fs)),
        )

    def open(self) -> None:
        self._manager.open()

    def close(self) -> None:
        self._manager.close()

    def read(self, path: str) -> str:
        return self._manager.read(path)

    def write(self, path: str, content: str) -> None:
        self._manager.write(path, content)

    def health(self) -> WorkspaceHealth:
        return WorkspaceHealth(state=self._manager.state)

    def metrics(self) -> WorkspaceMetrics:
        return self._manager._metrics

    def explain(self) -> str:
        return f"Workspace Root: {self._workspace.root}\nState: {self._manager.state.value}"
