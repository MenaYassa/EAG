"""Capability domain models for EAG Chief Engineer."""

import dataclasses
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Protocol, runtime_checkable

from eag.chief.capabilities.enums import (
    CapabilityCategory,
    CapabilityCost,
    CapabilityRequirement,
    CapabilityRisk,
    CapabilityRuntimeState,
    CapabilityStatus,
)
from eag.chief.goals.models import EngineeringGoal


def _validate_mapping(value: Mapping[str, Any], field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a Mapping")
    return MappingProxyType(dict(value))


@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityMetadata:
    """The 'business card' for a capability."""
    id: str
    name: str
    description: str = ""
    version: str = "1.0.0"
    category: CapabilityCategory = CapabilityCategory.UNKNOWN
    supported_languages: tuple[str, ...] = ()
    requires_llm: bool = False
    supports_preview: bool = True
    supports_rollback: bool = True
    estimated_cost: CapabilityCost = CapabilityCost.LOW
    estimated_risk: CapabilityRisk = CapabilityRisk.LOW
    tags: tuple[str, ...] = ()
    
    # Hardening additions
    dependencies: tuple[str, ...] = ()
    status: CapabilityStatus = CapabilityStatus.STABLE
    enabled: bool = True
    latency_ms: float = 0.0
    token_cost: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("id cannot be empty")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name cannot be empty")

    def to_dict(self) -> dict[str, Any]:
        """Serialize metadata to a dictionary."""
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CapabilityMetadata":
        """Deserialize metadata from a dictionary."""
        def parse_enum(val, enum_cls):
            return enum_cls(val) if isinstance(val, str) else val
        
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            category=parse_enum(data.get("category", "unknown"), CapabilityCategory),
            supported_languages=tuple(data.get("supported_languages", ())),
            requires_llm=data.get("requires_llm", False),
            supports_preview=data.get("supports_preview", True),
            supports_rollback=data.get("supports_rollback", True),
            estimated_cost=parse_enum(data.get("estimated_cost", "low"), CapabilityCost),
            estimated_risk=parse_enum(data.get("estimated_risk", "low"), CapabilityRisk),
            tags=tuple(data.get("tags", ())),
            dependencies=tuple(data.get("dependencies", ())),
            status=parse_enum(data.get("status", "stable"), CapabilityStatus),
            enabled=data.get("enabled", True),
            latency_ms=data.get("latency_ms", 0.0),
            token_cost=data.get("token_cost", 0.0)
        )


@runtime_checkable
class Capability(Protocol):
    """The contract for an engineering capability."""
    @property
    def metadata(self) -> CapabilityMetadata: ...
    
    def supports(self, goal: EngineeringGoal) -> bool: ...
    
    def score(self, goal: EngineeringGoal) -> float: ...
    
    def requirements(self) -> tuple[CapabilityRequirement, ...]: ...


@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityMatch:
    """A capability that matched a goal, along with its score."""
    capability: Capability
    score: float
    reason: str = ""
    reason_parts: tuple[str, ...] = ()
    matched_requirements: tuple[CapabilityRequirement, ...] = ()
    missing_requirements: tuple[CapabilityRequirement, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityRecommendation:
    """The final recommendation produced by the runtime."""
    winner: CapabilityMatch | None
    alternatives: tuple[CapabilityMatch, ...] = ()
    confidence: float = 0.0
    explanation: str = ""
    warnings: tuple[str, ...] = ()
    rejected: tuple[CapabilityMatch, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityMetrics:
    """Metrics collected during capability analysis."""
    registry_size: int = 0
    matching_time_ms: float = 0.0
    ranking_time_ms: float = 0.0
    recommendation_time_ms: float = 0.0
    candidates_count: int = 0
    rejected_count: int = 0
    confidence: float = 0.0


@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityAnalysis:
    """The final artifact produced by the CapabilityRuntime."""
    goal: EngineeringGoal
    candidates: tuple[CapabilityMatch, ...] = ()
    recommendation: CapabilityRecommendation | None = None
    metrics: CapabilityMetrics = field(default_factory=CapabilityMetrics)
    state: CapabilityRuntimeState = CapabilityRuntimeState.UNINITIALIZED