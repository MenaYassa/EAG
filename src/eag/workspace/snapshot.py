"""Workspace snapshot engine for EAG."""

from pathlib import Path

from eag.workspace.filesystem import LocalFilesystem
from eag.workspace.manifest import ManifestBuilder
from eag.workspace.models import Snapshot


class SnapshotEngine:
    """Creates and manages workspace snapshots."""

    def __init__(self, filesystem: LocalFilesystem, manifest_builder: ManifestBuilder) -> None:
        self._fs = filesystem
        self._manifest_builder = manifest_builder

    def create(self, root: Path) -> Snapshot:
        manifest = self._manifest_builder.build(root)
        return Snapshot(manifest=manifest)
