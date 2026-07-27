"""Workspace intelligence tool for EAG."""

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from eag.core import ComponentMetadata, Tool
from eag.plugins.builtin.filesystem import (
    WorkspaceBoundaryError,
)
from eag.plugins.builtin.workspace.ignore import (
    should_ignore_directory,
)
from eag.plugins.builtin.workspace.models import (
    SearchMatch,
    WorkspaceEntry,
    WorkspaceInspection,
    WorkspaceProfile,
)
from eag.plugins.builtin.workspace.profiler import (
    WorkspaceProfiler,
)
from eag.registry import Capability

WORKSPACE_TREE = Capability.parse("workspace.tree")
WORKSPACE_SEARCH = Capability.parse("workspace.search")
WORKSPACE_PROFILE = Capability.parse("workspace.profile")
WORKSPACE_INSPECT = Capability.parse("workspace.inspect")


class WorkspaceTool(Tool):
    """Inspect and search an engineering workspace."""

    def __init__(self, workspace: Path) -> None:
        self._workspace = workspace.resolve()
        self._profiler = WorkspaceProfiler(workspace=self._workspace)

    @property
    def metadata(self) -> ComponentMetadata:
        """Return workspace tool metadata."""
        return ComponentMetadata(
            name="workspace-tool",
            version="0.1.0",
            description="Workspace inspection and search",
        )

    @property
    def capabilities(self) -> tuple[Capability, ...]:
        """Return supported workspace capabilities."""
        return (
            WORKSPACE_TREE,
            WORKSPACE_SEARCH,
            WORKSPACE_PROFILE,
            WORKSPACE_INSPECT,
        )

    def execute(
        self,
        capability: Capability,
        arguments: Mapping[str, Any],
    ) -> Any:
        """Execute a workspace capability."""
        if capability == WORKSPACE_TREE:
            return self.tree(
                path=str(arguments.get("path", ".")),
                max_depth=int(arguments.get("max_depth", 4)),
            )

        if capability == WORKSPACE_SEARCH:
            return self.search(
                query=str(arguments["query"]),
                path=str(arguments.get("path", ".")),
                max_results=int(arguments.get("max_results", 100)),
            )

        if capability == WORKSPACE_PROFILE:
            return self.profile()

        if capability == WORKSPACE_INSPECT:
            return self.inspect()

        raise ValueError(f"Unsupported capability: '{capability.identifier}'")

    def tree(
        self,
        path: str = ".",
        max_depth: int = 4,
    ) -> tuple[WorkspaceEntry, ...]:
        """Build a filtered workspace tree."""
        root = self._resolve_safe_path(path)
        entries: list[WorkspaceEntry] = []

        for current_root, directories, files in os.walk(root):
            current = Path(current_root)
            relative_root = current.relative_to(root)
            depth = len(relative_root.parts)

            if relative_root == Path("."):
                depth = 0

            directories[:] = [name for name in directories if not should_ignore_directory(name)]

            if depth >= max_depth:
                directories[:] = []

            for directory in sorted(directories):
                entry_path = (current / directory).relative_to(self._workspace)

                entries.append(
                    WorkspaceEntry(
                        path=entry_path.as_posix(),
                        kind="directory",
                        depth=depth + 1,
                    )
                )

            for filename in sorted(files):
                entry_path = (current / filename).relative_to(self._workspace)

                entries.append(
                    WorkspaceEntry(
                        path=entry_path.as_posix(),
                        kind="file",
                        depth=depth + 1,
                    )
                )

        return tuple(entries)

    def search(
        self,
        query: str,
        path: str = ".",
        max_results: int = 100,
    ) -> tuple[SearchMatch, ...]:
        """Search text files for a literal query."""
        root = self._resolve_safe_path(path)
        matches: list[SearchMatch] = []

        for current_root, directories, files in os.walk(root):
            directories[:] = [name for name in directories if not should_ignore_directory(name)]

            current = Path(current_root)

            for filename in sorted(files):
                file_path = current / filename

                try:
                    content = file_path.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    continue

                for line_number, line in enumerate(
                    content.splitlines(),
                    start=1,
                ):
                    if query not in line:
                        continue

                    relative = file_path.relative_to(self._workspace)

                    matches.append(
                        SearchMatch(
                            path=relative.as_posix(),
                            line_number=line_number,
                            line=line.strip(),
                        )
                    )

                    if len(matches) >= max_results:
                        return tuple(matches)

        return tuple(matches)

    def profile(self) -> WorkspaceProfile:
        """Profile the workspace."""
        return self._profiler.profile()

    def inspect(self) -> WorkspaceInspection:
        """Build a high-level workspace inspection."""
        profile = self.profile()

        likely_entry_points = tuple(
            path
            for path in (
                "src/main.py",
                "src/app.py",
                "main.py",
                "app.py",
                "src/index.ts",
                "src/index.js",
                "index.ts",
                "index.js",
            )
            if (self._workspace / path).is_file()
        )

        important_files = tuple(
            filename
            for filename in (
                "README.md",
                "pyproject.toml",
                "package.json",
                "Cargo.toml",
                "go.mod",
                "Dockerfile",
                "compose.yaml",
                "docker-compose.yml",
            )
            if (self._workspace / filename).is_file()
        )

        return WorkspaceInspection(
            profile=profile,
            likely_entry_points=likely_entry_points,
            important_files=important_files,
        )

    def _resolve_safe_path(self, path: str) -> Path:
        """Resolve a path within the workspace."""
        candidate = (self._workspace / path).resolve()

        if not candidate.is_relative_to(self._workspace):
            raise WorkspaceBoundaryError(f"Path escapes workspace: '{path}'")

        return candidate
