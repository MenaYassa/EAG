"""AI Intelligence domain models for EAG."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from eag.chief.intelligence.capabilities import AICapabilities
from eag.chief.intelligence.enums import (
    AIContextSize,
    AICost,
    AIReasoningLevel,
    AISpeed,
    ModelStatus,
    ProviderStatus,
    RoutingPolicy,
    SelectionReason,
)
from eag.chief.intelligence.traits import AITraits


def _validate_mapping(value: Mapping[str, Any], field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a Mapping")
    return MappingProxyType(dict(value))


@dataclass(frozen=True, slots=True, kw_only=True)
class ProviderProfile:
    """Metadata representing an AI provider."""

    id: str
    name: str
    status: ProviderStatus = ProviderStatus.ONLINE
    latency_ms: float = 0.0
    supports_batch: bool = False
    supports_tools: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("id cannot be empty")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name cannot be empty")
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class ModelProfile:
    """Metadata representing an AI model."""

    id: str
    provider_id: str
    name: str
    traits: AITraits
    capabilities: AICapabilities
    max_context_tokens: int = 0
    max_output_tokens: int = 0
    estimated_cost: AICost = AICost.MEDIUM
    status: ModelStatus = ModelStatus.AVAILABLE
    metadata: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("id cannot be empty")
        if not isinstance(self.provider_id, str) or not self.provider_id.strip():
            raise ValueError("provider_id cannot be empty")
        if not isinstance(self.traits, AITraits):
            raise TypeError("traits must be AITraits")
        if not isinstance(self.capabilities, AICapabilities):
            raise TypeError("capabilities must be AICapabilities")
        object.__setattr__(self, "metadata", _validate_mapping(self.metadata, "metadata"))


@dataclass(frozen=True, slots=True, kw_only=True)
class AIRequirements:
    """Desired AI characteristics for a specific task."""

    minimum_reasoning: AIReasoningLevel = AIReasoningLevel.LOW
    minimum_context: AIContextSize = AIContextSize.MEDIUM
    requires_structured_output: bool = False
    requires_tool_calling: bool = False
    requires_streaming: bool = False
    maximum_cost: AICost = AICost.HIGH
    preferred_speed: AISpeed = AISpeed.MEDIUM


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionRequest:
    """The structured request sent to the intelligence runtime."""

    capability: str
    requirements: AIRequirements
    policy: RoutingPolicy = RoutingPolicy.BALANCED
    estimated_tokens: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.capability, str) or not self.capability.strip():
            raise ValueError("capability cannot be empty")
        if not isinstance(self.requirements, AIRequirements):
            raise TypeError("requirements must be AIRequirements")
        if not isinstance(self.policy, RoutingPolicy):
            raise TypeError("policy must be RoutingPolicy")


# Append to src/eag/chief/intelligence/models.py


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchResult:
    """The explainable result of matching requirements against a model."""

    compatible: bool
    matched: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    rejected: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class ScoreBreakdown:
    """Detailed breakdown of a model's score."""

    total: float
    reasoning: float = 0.0
    context: float = 0.0
    coding: float = 0.0
    speed: float = 0.0
    cost: float = 0.0


@dataclass(frozen=True, slots=True, kw_only=True)
class SelectionDecision:
    """The explainable output of the model selector."""

    model: ModelProfile
    provider: ProviderProfile
    confidence: float
    score: float
    reasons: tuple[SelectionReason, ...] = ()
    alternatives: tuple[ModelProfile, ...] = ()
    match_result: MatchResult | None = None
    score_breakdown: ScoreBreakdown | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.model, ModelProfile):
            raise TypeError("model must be ModelProfile")
        if not isinstance(self.provider, ProviderProfile):
            raise TypeError("provider must be ProviderProfile")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")
