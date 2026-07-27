"""Read-only filesystem tool for EAG."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from eag.core import ComponentMetadata, Tool
from eag.plugins.builtin.filesystem.errors import (
    UnsupportedFilesystemCapabilityError,
    WorkspaceBoundaryError,
)
from eag.registry import Capability

FILESYSTEM_READ = Capability.parse("filesystem.read")
FILESYSTEM_LIST = Capability.parse("filesystem.list")
FILESYSTEM_EXISTS = Capability.parse("filesystem.exists")


class FilesystemTool(Tool):
    """Provide safe read-only access to an EAG workspace."""

    def __init__(self, workspace: Path) -> None:
        self._workspace = workspace.resolve()

    @property
    def metadata(self) -> ComponentMetadata:
        """Return filesystem tool metadata."""
        return ComponentMetadata(
            name="filesystem-tool",
            version="0.1.0",
            description="Safe read-only workspace access",
        )

    @property
    def capabilities(self) -> tuple[Capability, ...]:
        """Return supported filesystem capabilities."""
        return (
            FILESYSTEM_READ,
            FILESYSTEM_LIST,
            FILESYSTEM_EXISTS,
        )

    def execute(
        self,
        capability: Capability,
        arguments: Mapping[str, Any],
    ) -> Any:
        """Execute a filesystem capability."""
        if capability == FILESYSTEM_READ:
            return self.read(
                path=str(arguments["path"]),
            )

        if capability == FILESYSTEM_LIST:
            return self.list_directory(
                path=str(arguments.get("path", ".")),
            )

        if capability == FILESYSTEM_EXISTS:
            return self.exists(
                path=str(arguments["path"]),
            )

        raise UnsupportedFilesystemCapabilityError(
            f"Unsupported capability: '{capability.identifier}'"
        )

    def read(self, path: str) -> str:
        """Read a UTF-8 text file inside the workspace."""
        resolved = self._resolve_safe_path(path)

        if not resolved.is_file():
            raise FileNotFoundError(f"File does not exist: '{path}'")

        return resolved.read_text(encoding="utf-8")

    def list_directory(
        self,
        path: str = ".",
    ) -> tuple[str, ...]:
        """List entries in a workspace directory."""
        resolved = self._resolve_safe_path(path)

        if not resolved.is_dir():
            raise NotADirectoryError(f"Not a directory: '{path}'")

        return tuple(sorted(entry.name for entry in resolved.iterdir()))

    def exists(self, path: str) -> bool:
        """Return whether a workspace path exists."""
        resolved = self._resolve_safe_path(path)
        return resolved.exists()

    def _resolve_safe_path(self, path: str) -> Path:
        """Resolve a path and enforce the workspace boundary."""
        candidate = (self._workspace / path).resolve()

        if not candidate.is_relative_to(self._workspace):
            raise WorkspaceBoundaryError(f"Path escapes workspace: '{path}'")

        return candidate
