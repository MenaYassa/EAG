"""Adaptive Planning domain models for EAG."""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any

from eag.adaptive.enums import InsightCategory, PlanningStrategyType, RulePriority
from eag.chief.runtime.models import Plan
from eag.memory.models import EngineeringExperience


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


def _validate_non_empty_str(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} cannot be empty or whitespace")
    return value.strip()


def _validate_tuple(value: tuple, expected_type: type, field_name: str) -> tuple:
    if not isinstance(value, tuple):
        raise TypeError(f"{field_name} must be a tuple")
    for item in value:
        if not isinstance(item, expected_type):
            raise TypeError(f"{field_name} must contain only {expected_type.__name__} instances")
    return value


@dataclass(frozen=True, slots=True, kw_only=True)
class PlanningInsight:
    """An insight extracted from engineering experience."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: str
    category: InsightCategory
    description: str
    confidence: float = 1.0
    evidence: str = ""
    recommendation: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "source", _validate_non_empty_str(self.source, "source"))
        if not isinstance(self.category, InsightCategory):
            raise TypeError("category must be an InsightCategory")
        object.__setattr__(
            self, "description", _validate_non_empty_str(self.description, "description")
        )
        object.__setattr__(self, "confidence", _validate_confidence(self.confidence))
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class PlanningRule:
    """A deterministic rule that modifies a plan."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    condition: str
    action: str
    priority: RulePriority = RulePriority.NORMAL
    confidence: float = 1.0
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "condition", _validate_non_empty_str(self.condition, "condition"))
        object.__setattr__(self, "action", _validate_non_empty_str(self.action, "action"))
        if not isinstance(self.priority, RulePriority):
            raise TypeError("priority must be a RulePriority")
        object.__setattr__(self, "confidence", _validate_confidence(self.confidence))
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class AdaptivePlanningContext:
    """Context provided to the adaptive planner."""

    goal: str
    experiences: tuple[EngineeringExperience, ...] = ()
    insights: tuple[PlanningInsight, ...] = ()
    rules: tuple[PlanningRule, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "experiences",
            _validate_tuple(self.experiences, EngineeringExperience, "experiences"),
        )
        object.__setattr__(
            self, "insights", _validate_tuple(self.insights, PlanningInsight, "insights")
        )
        object.__setattr__(self, "rules", _validate_tuple(self.rules, PlanningRule, "rules"))
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class AdaptivePlan:
    """A plan modified by adaptive rules."""

    base_plan: Plan
    final_plan: Plan
    applied_rules: tuple[PlanningRule, ...] = ()
    ignored_rules: tuple[PlanningRule, ...] = ()
    confidence: float = 1.0
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        if not isinstance(self.base_plan, Plan):
            raise TypeError("base_plan must be a Plan")
        if not isinstance(self.final_plan, Plan):
            raise TypeError("final_plan must be a Plan")
        object.__setattr__(
            self,
            "applied_rules",
            _validate_tuple(self.applied_rules, PlanningRule, "applied_rules"),
        )
        object.__setattr__(
            self,
            "ignored_rules",
            _validate_tuple(self.ignored_rules, PlanningRule, "ignored_rules"),
        )
        object.__setattr__(self, "confidence", _validate_confidence(self.confidence))
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class PlanningDecision:
    """Explainable record of why a plan was chosen."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal: str
    selected_strategy: PlanningStrategyType
    applied_rules: tuple[PlanningRule, ...] = ()
    ignored_rules: tuple[PlanningRule, ...] = ()
    reasoning: str = ""
    confidence: float = 1.0
    expected_improvement: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        if not isinstance(self.selected_strategy, PlanningStrategyType):
            raise TypeError("selected_strategy must be a PlanningStrategyType")
        object.__setattr__(
            self,
            "applied_rules",
            _validate_tuple(self.applied_rules, PlanningRule, "applied_rules"),
        )
        object.__setattr__(
            self,
            "ignored_rules",
            _validate_tuple(self.ignored_rules, PlanningRule, "ignored_rules"),
        )
        object.__setattr__(self, "confidence", _validate_confidence(self.confidence))
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))
