"""Structured Diff Engine for EAG transformations."""

from dataclasses import dataclass
from eag.source.python.transformations.edits import Edit, TextEdit


@dataclass(frozen=True)
class StructuredDiff:
    """A structured diff for a single file."""
    file: str
    changes: tuple[str, ...]


class DiffEngine:
    """Generates structured diffs from edit sets."""

    def create_diff(self, file: str, edits: list[TextEdit]) -> StructuredDiff:
        """Creates a structured diff for a file based on text edits."""
        changes: list[str] = []
        for edit in edits:
            change = f"Lines {edit.start_line}-{edit.end_line}: Replace with '{edit.new_text}'"
            changes.append(change)
        return StructuredDiff(file=file, changes=tuple(changes))