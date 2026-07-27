"""Workspace manifest builder for EAG."""

from datetime import UTC, datetime
from pathlib import Path

from eag.workspace.filesystem import LocalFilesystem
from eag.workspace.models import FileEntry, Manifest


class ManifestBuilder:
    """Builds an immutable manifest of the workspace."""

    def __init__(self, filesystem: LocalFilesystem) -> None:
        self._fs = filesystem

    def build(self, root: Path) -> Manifest:
        files: list[FileEntry] = []
        dirs: list[str] = []

        for p in root.rglob("*"):
            rel_path = str(p.relative_to(root))
            if ".git" in p.parts:
                continue
            if p.is_dir():
                dirs.append(rel_path)
            elif p.is_file():
                files.append(
                    FileEntry(
                        path=rel_path,
                        size=p.stat().st_size,
                        hash=self._fs.hash_file(p),
                        modified_at=datetime.fromtimestamp(p.stat().st_mtime, tz=UTC),
                    )
                )

        return Manifest(
            root=root,
            files=tuple(files),
            directories=tuple(dirs),
        )
