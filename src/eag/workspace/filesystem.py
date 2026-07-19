"""Local filesystem implementation for EAG workspace."""

import hashlib
import shutil
from pathlib import Path

from eag.workspace.errors import FilesystemError


class LocalFilesystem:
    """A safe abstraction over raw filesystem IO."""

    def read(self, path: Path) -> str:
        if not path.exists():
            raise FilesystemError(f"File not found: {path}")
        return path.read_text(encoding="utf-8")

    def write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def copy(self, src: Path, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)

    def move(self, src: Path, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))

    def delete(self, path: Path) -> None:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink(missing_ok=True)

    def mkdir(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)

    def exists(self, path: Path) -> bool:
        return path.exists()

    def list_files(self, root: Path) -> list[Path]:
        if not root.exists():
            return []
        return [p for p in root.rglob("*") if p.is_file()]

    def hash_file(self, path: Path) -> str:
        """Calculate SHA256 hash of a file."""
        sha256 = hashlib.sha256()
        with path.open("rb") as f:
            for block in iter(lambda: f.read(4096), b""):
                sha256.update(block)
        return sha256.hexdigest()
