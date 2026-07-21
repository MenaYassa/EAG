"""Transformation domain models for EAG."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any

from eag.planner.enums import RiskLevel
from eag.source.models import Diagnostic, SourceDocument


def _validate_mapping(value: Mapping[str, Any], field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a Mapping")
    return MappingProxyType(dict(value))


def apply_text_edits(content: str, edits: list["TextEdit"]) -> str:
    """
    Apply a list of TextEdits to a source string.

    Edits must be sorted in reverse order (by start position) to avoid
    invalidating positions of subsequent edits.
    """
    if not edits:
        return content

    # Sort edits in reverse order (from end of file to beginning)
    sorted_edits = sorted(edits, key=lambda e: (e.start_line, e.start_col), reverse=True)

    lines = content.splitlines(keepends=True)
    result_lines = list(lines)

    for edit in sorted_edits:
        # Convert 0-based line/col to 0-based indices
        start_line = edit.start_line - 1
        end_line = edit.end_line - 1

        # Handle edits within a single line
        if start_line == end_line:
            line = result_lines[start_line]
            # Convert column to character index (0-based)
            start_idx = edit.start_col
            end_idx = edit.end_col
            new_line = line[:start_idx] + edit.new_text + line[end_idx:]
            result_lines[start_line] = new_line
        else:
            # Multi-line edit
            # Get the start of the first line up to the start column
            first_line = result_lines[start_line]
            start_part = first_line[: edit.start_col]

            # Get the end of the last line from the end column
            last_line = result_lines[end_line]
            end_part = last_line[edit.end_col :]

            # Replace the range with the new text
            # Split new_text by lines to handle multi-line replacements
            new_text_lines = edit.new_text.splitlines(keepends=True)

            # Build the new lines
            if new_text_lines:
                new_lines = [start_part + new_text_lines[0] if new_text_lines else start_part]
                new_lines.extend(new_text_lines[1:-1] if len(new_text_lines) > 1 else [])
                if len(new_text_lines) > 1:
                    new_lines.append(new_text_lines[-1] + end_part)
                else:
                    # If only one line, it already includes start_part
                    new_lines[-1] = new_lines[-1].rstrip("\n") + end_part
            else:
                new_lines = [start_part + end_part]

            # Replace the range of lines
            result_lines = result_lines[:start_line] + new_lines + result_lines[end_line + 1 :]

    return "".join(result_lines)


@dataclass(frozen=True, slots=True, kw_only=True)
class TextEdit:
    """A precise source code edit to be applied to a specific span."""

    start_line: int  # 1-based line number
    start_col: int  # 0-based column index (character offset)
    end_line: int  # 1-based line number (inclusive)
    end_col: int  # 0-based column index (character offset, exclusive)
    new_text: str  # The text to replace the span with

    def __post_init__(self) -> None:
        if not isinstance(self.start_line, int) or self.start_line < 1:
            raise ValueError("start_line must be a positive integer")
        if not isinstance(self.start_col, int) or self.start_col < 0:
            raise ValueError("start_col must be a non-negative integer")
        if not isinstance(self.end_line, int) or self.end_line < 1:
            raise ValueError("end_line must be a positive integer")
        if not isinstance(self.end_col, int) or self.end_col < 0:
            raise ValueError("end_col must be a non-negative integer")
        if self.start_line > self.end_line:
            raise ValueError("start_line must be <= end_line")
        if self.start_line == self.end_line and self.start_col > self.end_col:
            raise ValueError("start_col must be <= end_col when on same line")
        if not isinstance(self.new_text, str):
            raise TypeError("new_text must be a str")

    def apply_to(self, content: str) -> str:
        """Apply this single edit to the given content."""
        return apply_text_edits(content, [self])


@dataclass(frozen=True, slots=True, kw_only=True)
class TransformationContext:
    """Context required for a source transformation."""

    document: SourceDocument
    content: str
    workspace: Any = None
    repository: Any = None
    dry_run: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        if not isinstance(self.document, SourceDocument):
            raise TypeError("document must be a SourceDocument")
        if not isinstance(self.content, str):
            raise TypeError("content must be a str")
        if not isinstance(self.dry_run, bool):
            raise TypeError("dry_run must be a bool")
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceEdit:
    """A concrete source code edit to be applied to the workspace."""

    path: Path
    new_content: str
    text_edits: tuple[TextEdit, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.path, Path):
            raise TypeError("path must be a Path")
        if not isinstance(self.new_content, str):
            raise TypeError("new_content must be a str")
        if not isinstance(self.text_edits, tuple):
            object.__setattr__(self, "text_edits", tuple(self.text_edits))

    @classmethod
    def from_text_edits(
        cls, path: Path, original_content: str, edits: list[TextEdit]
    ) -> "SourceEdit":
        """Create a SourceEdit by applying TextEdits to original content."""
        new_content = apply_text_edits(original_content, edits)
        return cls(path=path, new_content=new_content, text_edits=tuple(edits))

    def apply_to_file(self, content: str) -> str:
        """Apply this edit to the given content (useful for testing)."""
        if self.text_edits:
            return apply_text_edits(content, list(self.text_edits))
        return self.new_content


@dataclass(frozen=True, slots=True, kw_only=True)
class TransformationPreview:
    """A preview of what a transformation will do before it is applied."""

    transformation_name: str
    target_symbol: str = ""
    affected_files: tuple[str, ...] = ()
    affected_symbols: tuple[str, ...] = ()
    affected_references: tuple[str, ...] = ()
    affected_imports: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    risk: RiskLevel = RiskLevel.NONE
    summary: str = ""

    # --- Step 4 Enhancements ---
    can_apply: bool = True
    affected_references_count: int = 0
    estimated_duration_ms: float = 0.0
    rollback_complexity: str = "LOW"
    details: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        if not isinstance(self.affected_files, tuple):
            object.__setattr__(self, "affected_files", tuple(self.affected_files))
        if not isinstance(self.affected_symbols, tuple):
            object.__setattr__(self, "affected_symbols", tuple(self.affected_symbols))
        if not isinstance(self.affected_references, tuple):
            object.__setattr__(self, "affected_references", tuple(self.affected_references))
        if not isinstance(self.affected_imports, tuple):
            object.__setattr__(self, "affected_imports", tuple(self.affected_imports))
        if not isinstance(self.warnings, tuple):
            object.__setattr__(self, "warnings", tuple(self.warnings))
        if not isinstance(self.details, Mapping):
            object.__setattr__(self, "details", MappingProxyType(dict(self.details)))


@dataclass(frozen=True, slots=True, kw_only=True)
class TransformationResult:
    """The outcome of an applied transformation."""

    success: bool
    transformation_name: str
    edits: tuple[SourceEdit, ...] = ()
    files_modified: tuple[str, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()
    duration: float = 0.0
    undo_metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)
    summary: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.success, bool):
            raise TypeError("success must be a bool")
        if not isinstance(self.edits, tuple):
            object.__setattr__(self, "edits", tuple(self.edits))
        if not isinstance(self.files_modified, tuple):
            object.__setattr__(self, "files_modified", tuple(self.files_modified))
        if not isinstance(self.diagnostics, tuple):
            object.__setattr__(self, "diagnostics", tuple(self.diagnostics))
        if not isinstance(self.duration, (int, float)):
            raise TypeError("duration must be a number")
        object.__setattr__(
            self, "undo_metadata", _validate_mapping(self.undo_metadata, "undo_metadata")
        )

    def explain(self) -> str:
        return (
            f"Transformation: {self.transformation_name}\n"
            f"Validation: {'Passed' if self.success else 'Failed'}\n"
            f"Files Affected: {len(self.files_modified)}\n"
            f"Duration: {self.duration:.2f}s\n"
            f"Summary: {self.summary}"
        )
