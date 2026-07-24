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

        text_edits: list[TextEdit] = []
        symbol_edits: list[SymbolEdit] = []
        import_edits: list[ImportEdit] = []
        for e in flat_edits:
            if isinstance(e, TextEdit):
                text_edits.append(e)
            elif isinstance(e, SymbolEdit):
                symbol_edits.append(e)
            elif isinstance(e, ImportEdit):
                import_edits.append(e)

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
                s1 = symbol_edits[i]
                s2 = symbol_edits[j]
                if s1.symbol_id == s2.symbol_id and s1.new_name != s2.new_name:
                    conflicts.append(
                        f"Symbol conflict on {s1.symbol_id}: cannot rename to both "
                        f"'{s1.new_name}' and '{s2.new_name}'"
                    )

        # Check Import conflicts
        for i in range(len(import_edits)):
            for j in range(i + 1, len(import_edits)):
                i1 = import_edits[i]
                i2 = import_edits[j]
                if (
                    i1.module == i2.module
                    and i1.old_import == i2.old_import
                    and i1.new_import != i2.new_import
                ):
                    conflicts.append(
                        f"Import conflict on {i1.module}.{i1.old_import}: cannot update "
            f"to both '{i1.new_import}' and '{i2.new_import}'"
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
