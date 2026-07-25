"""Goal domain models for EAG Chief Engineer."""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any

from eag.chief.goals.enums import (
    GoalCategory,
    GoalComplexity,
    GoalIntent,
    GoalPriority,
)


def _validate_mapping(value: Mapping[str, Any], field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a Mapping")
    return MappingProxyType(dict(value))


def _validate_confidence(value: float) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TypeError("confidence must be a float")
    if not (0.0 <= value <= 1.0):
        raise ValueError("confidence must be between 0.0 and 1.0")
    return float(value)


@dataclass(frozen=True, slots=True, kw_only=True)
class Requirement:
    """A specific engineering requirement extracted from a goal."""

    key: str
    value: str | None = None
    is_missing: bool = False
    confidence: float = 1.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "confidence", _validate_confidence(self.confidence))


@dataclass(frozen=True, slots=True, kw_only=True)
class Constraint:
    """A technical constraint placed on the goal."""

    key: str
    value: str
    confidence: float = 1.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "confidence", _validate_confidence(self.confidence))


@dataclass(frozen=True, slots=True, kw_only=True)
class Assumption:
    """An assumption made by the Chief Engineer."""

    key: str
    value: str


@dataclass(frozen=True, slots=True, kw_only=True)
class Clarification:
    """A question generated to resolve missing information or ambiguity."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    question: str
    intent: GoalIntent
    priority: int = 0
    related_requirement: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class ChiefGoal:
    """The raw user-provided goal."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    raw_text: str
    priority: GoalPriority = GoalPriority.NORMAL
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not isinstance(self.raw_text, str) or not self.raw_text.strip():
            raise ValueError("raw_text cannot be empty")
        if not isinstance(self.priority, GoalPriority):
            raise TypeError("priority must be a GoalPriority")


@dataclass(frozen=True, slots=True, kw_only=True)
class GoalAnalysis:
    """The intermediate result of analyzing a goal."""

    goal: ChiefGoal
    intents: tuple[GoalIntent, ...] = ()
    primary_intent: GoalIntent = GoalIntent.UNKNOWN
    confidence: float = 0.0
    is_ambiguous: bool = False
    requirements: tuple[Requirement, ...] = ()
    constraints: tuple[Constraint, ...] = ()
    assumptions: tuple[Assumption, ...] = ()
    complexity: GoalComplexity = GoalComplexity.SMALL
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "confidence", _validate_confidence(self.confidence))
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class EngineeringGoal:
    """The final, canonical engineering goal ready for planning."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    original_goal: ChiefGoal
    canonical_text: str
    intents: tuple[GoalIntent, ...]
    primary_intent: GoalIntent
    category: GoalCategory
    complexity: GoalComplexity
    confidence: float
    is_ambiguous: bool
    requirements: tuple[Requirement, ...] = ()
    constraints: tuple[Constraint, ...] = ()
    assumptions: tuple[Assumption, ...] = ()
    missing_requirements: tuple[Requirement, ...] = ()
    clarifications: tuple[Clarification, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "confidence", _validate_confidence(self.confidence))
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))
