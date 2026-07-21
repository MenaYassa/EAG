"""Transformation descriptors for EAG."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any

from eag.planner.enums import RiskLevel
from eag.source.models import Language


class TransformationCategory(StrEnum):
    SEMANTIC = "semantic"
    SYNTACTIC = "syntactic"
    SYNTAX = "syntax"  # Alias for SYNTACTIC
    STRUCTURAL = "structural"
    ORGANIZATION = "organization"
    REFACTORING = "refactoring"


@dataclass(frozen=True, slots=True, kw_only=True)
class TransformationDescriptor:
    """Immutable metadata describing a transformation's capabilities."""

    name: str
    category: TransformationCategory
    version: str = "1.0.0"
    supported_languages: tuple[Language, ...] = (Language.PYTHON,)
    risk: RiskLevel = RiskLevel.LOW
    estimated_cost: float = 1.0  # Arbitrary unit for planner comparison
    requires_workspace: bool = True
    requires_repository: bool = False
    produces_edits: tuple[str, ...] = ()
    supports_preview: bool = True
    supports_undo: bool = True
    supports_batch: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name cannot be empty")
        if not isinstance(self.category, TransformationCategory):
            raise TypeError("category must be a TransformationCategory")
        if not isinstance(self.supported_languages, tuple):
            raise TypeError("supported_languages must be a tuple")
        if not isinstance(self.metadata, Mapping):
            raise TypeError("metadata must be a Mapping")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    def supports_language(self, language: Language) -> bool:
        return language in self.supported_languages
