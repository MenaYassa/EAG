"""Text Edit application engine for EAG."""

from eag.source.python.transformations.models import TextEdit


def apply_text_edits(content: str, edits: list[TextEdit]) -> str:
    """Applies a list of text edits to the source content safely.

    Sorts edits in reverse order so that line/column offsets are not
    invalidated by previous edits in the same file.
    """
    lines = content.splitlines(keepends=True)
    # Sort edits bottom-to-top, right-to-left
    edits.sort(key=lambda e: (e.start_line, e.start_col), reverse=True)

    for edit in edits:
        start_idx = edit.start_line - 1
        end_idx = edit.end_line - 1

        if start_idx >= len(lines) or end_idx >= len(lines):
            continue  # Out of bounds, skip

        if start_idx == end_idx:
            # Single line edit (standard for identifiers)
            line = lines[start_idx]
            start_col = min(edit.start_col, len(line))
            end_col = min(edit.end_col, len(line))
            new_line = line[:start_col] + edit.new_text + line[end_col:]
            lines[start_idx] = new_line
        else:
            # Multi-line edit (rare for identifiers, but handle it)
            first_line = lines[start_idx]
            last_line = lines[end_idx]
            start_col = min(edit.start_col, len(first_line))
            end_col = min(edit.end_col, len(last_line))

            combined = first_line[:start_col] + edit.new_text + last_line[end_col:]
            lines[start_idx : end_idx + 1] = [combined]

    return "".join(lines)
