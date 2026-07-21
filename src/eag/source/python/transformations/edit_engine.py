"""Edit Engine for EAG transformations."""

from eag.source.python.transformations.edits import TextEdit
from eag.source.python.transformations.text_applier import apply_text_edits


class EditEngine:
    """Engine for applying text and structural edits safely."""

    def apply(self, content: str, edits: list[TextEdit]) -> str:
        """Apply a list of edits to the content string."""
        # Delegate directly to apply_text_edits to ensure consistent behavior
        return apply_text_edits(content, edits)
