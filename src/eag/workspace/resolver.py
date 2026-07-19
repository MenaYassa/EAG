"""Path resolver for EAG workspace."""

from pathlib import Path

from eag.workspace.errors import PathTraversalError


class PathResolver:
    """Validates and resolves paths within the workspace root."""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    @property
    def root(self) -> Path:
        return self._root

    def resolve(self, path: str | Path) -> Path:
        """Resolve a path relative to the workspace root and ensure it's safe."""
        p = Path(path)
        # Allow absolute paths only if they are already inside the root
        resolved = p.resolve() if p.is_absolute() else (self._root / p).resolve()

        # Prevent path traversal
        if self._root not in resolved.parents and resolved != self._root:
            raise PathTraversalError(f"Path '{path}' escapes workspace root '{self._root}'")

        return resolved
