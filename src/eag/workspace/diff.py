"""Workspace diff engine for EAG."""

from eag.workspace.enums import DiffType
from eag.workspace.models import DiffEntry, Manifest


class DiffEngine:
    """Compares two manifests to identify changes."""

    def diff(self, old: Manifest, new: Manifest) -> tuple[DiffEntry, ...]:
        old_files = {f.path: f for f in old.files}
        new_files = {f.path: f for f in new.files}

        changes: list[DiffEntry] = []

        # Added or Modified
        for path, new_file in new_files.items():
            if path not in old_files:
                changes.append(DiffEntry(path=path, type=DiffType.ADDED))
            elif old_files[path].hash != new_file.hash:
                changes.append(DiffEntry(path=path, type=DiffType.MODIFIED))

        # Removed
        for path in old_files:
            if path not in new_files:
                changes.append(DiffEntry(path=path, type=DiffType.REMOVED))

        return tuple(changes)
