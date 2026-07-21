"""Unified Edit models for EAG transformations."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Any


class EditType(StrEnum):
    TEXT = "text"
    SYMBOL = "symbol"
    IMPORT = "import"
    COMPOSITE = "composite"


def _validate_mapping(value: Mapping[str, Any], field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a Mapping")
    return MappingProxyType(dict(value))


@dataclass(frozen=True, slots=True, kw_only=True)
class Edit:
    """Base abstraction for a source edit."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    edit_type: EditType
    file: Path
    priority: int = 100
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        if not isinstance(self.edit_type, EditType):
            raise TypeError("edit_type must be an EditType")
        if not isinstance(self.file, Path):
            raise TypeError("file must be a Path")
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class TextEdit:
    """A precise source code edit to be applied to a specific span."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()), compare=False)
    file: Path = field(default_factory=Path)
    start_line: int
    start_col: int
    end_line: int
    end_col: int
    new_text: str
    priority: int = 100  # <-- Set default to 100
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.file, Path):
            raise TypeError("file must be a Path")
        if not isinstance(self.priority, int):
            raise TypeError("priority must be an int")
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))

    def __lt__(self, other: TextEdit) -> bool:
        return (self.start_line, self.start_col) < (other.start_line, other.start_col)


@dataclass(frozen=True, slots=True, kw_only=True)
class SymbolEdit(Edit):
    """A high-level symbol rename edit."""

    edit_type: EditType = EditType.SYMBOL
    symbol_id: str
    old_name: str
    new_name: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ImportEdit(Edit):
    """An import modification edit."""

    edit_type: EditType = EditType.IMPORT
    module: str
    old_import: str
    new_import: str


@dataclass(frozen=True, slots=True, kw_only=True)
class CompositeEdit(Edit):
    """A collection of edits that should be applied together."""

    edit_type: EditType = EditType.COMPOSITE
    edits: tuple[Edit, ...] = ()
