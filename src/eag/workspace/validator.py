"""Workspace validator for EAG."""

from pathlib import Path

from eag.workspace.enums import WorkspaceMode
from eag.workspace.errors import WorkspaceValidationError


class WorkspaceValidator:
    """Validates workspace roots and permissions."""

    def validate(self, root: Path, mode: WorkspaceMode) -> None:
        if not root.exists():
            raise WorkspaceValidationError(f"Workspace root does not exist: {root}")
        if not root.is_dir():
            raise WorkspaceValidationError(f"Workspace root is not a directory: {root}")

        if mode == WorkspaceMode.LIVE or mode == WorkspaceMode.DRY_RUN:
            # Check write permissions
            try:
                test_file = root / ".eag_write_test"
                test_file.touch()
                test_file.unlink()
            except OSError as e:
                raise WorkspaceValidationError(f"Workspace root is not writable: {e}") from e
