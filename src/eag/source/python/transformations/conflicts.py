"""Conflict detection for EAG transformations."""

from eag.source.python.transformations.edits import (
    CompositeEdit,
    Edit,
    ImportEdit,
    SymbolEdit,
    TextEdit,
)


class ConflictDetector:
    """Detects conflicts between a set of edits."""

    def check(self, edits: list[Edit]) -> list[str]:
        conflicts: list[str] = []

        # Flatten composite edits
        flat_edits: list[Edit] = []
        for edit in edits:
            if isinstance(edit, CompositeEdit):
                flat_edits.extend(edit.edits)
            else:
                flat_edits.append(edit)

        text_edits = [e for e in flat_edits if isinstance(e, TextEdit)]
        symbol_edits = [e for e in flat_edits if isinstance(e, SymbolEdit)]
        import_edits = [e for e in flat_edits if isinstance(e, ImportEdit)]

        # Check Text overlaps
        for i in range(len(text_edits)):
            for j in range(i + 1, len(text_edits)):
                e1 = text_edits[i]
                e2 = text_edits[j]
                if e1.file == e2.file and self._overlaps(e1, e2):
                    conflicts.append(f"Overlap conflict between edit {e1.id} and {e2.id}")

        # Check Symbol conflicts
        for i in range(len(symbol_edits)):
            for j in range(i + 1, len(symbol_edits)):
                e1 = symbol_edits[i]
                e2 = symbol_edits[j]
                if e1.symbol_id == e2.symbol_id and e1.new_name != e2.new_name:
                    conflicts.append(
                        f"Symbol conflict on {e1.symbol_id}: cannot rename to both '{e1.new_name}' and '{e2.new_name}'"
                    )

        # Check Import conflicts
        for i in range(len(import_edits)):
            for j in range(i + 1, len(import_edits)):
                e1 = import_edits[i]
                e2 = import_edits[j]
                if (
                    e1.module == e2.module
                    and e1.old_import == e2.old_import
                    and e1.new_import != e2.new_import
                ):
                    conflicts.append(
                        f"Import conflict on {e1.module}.{e1.old_import}: cannot update to both '{e1.new_import}' and '{e2.new_import}'"
                    )

        return conflicts

    def _overlaps(self, e1: TextEdit, e2: TextEdit) -> bool:
        start1 = (e1.start_line, e1.start_col)
        end1 = (e1.end_line, e1.end_col)
        start2 = (e2.start_line, e2.start_col)
        end2 = (e2.end_line, e2.end_col)

        # Strict overlap (adjacent edits do not conflict)
        if start1 < start2 < end1:
            return True
        if start2 < start1 < end2:
            return True
        return start1 == start2
