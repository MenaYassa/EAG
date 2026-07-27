"""Capability Discovery Platform for EAG Chief Engineer."""

from eag.chief.capabilities.enums import (
    CapabilityCategory,
    CapabilityCost,
    CapabilityRequirement,
    CapabilityRisk,
    CapabilityRuntimeState,
)
from eag.chief.capabilities.errors import (
    CapabilityError,
    CapabilityNotFound,
    DuplicateCapability,
    RankingFailure,
    RequirementMissing,
)
from eag.chief.capabilities.events import (
    CapabilityEvent,
    CapabilityMatched,
    CapabilityRanked,
    CapabilityRegistered,
    RecommendationProduced,
)
from eag.chief.capabilities.matcher import CapabilityMatcher
from eag.chief.capabilities.models import (
    Capability,
    CapabilityAnalysis,
    CapabilityMatch,
    CapabilityMetadata,
    CapabilityMetrics,
    CapabilityRecommendation,
)
from eag.chief.capabilities.ranker import CapabilityRanker
from eag.chief.capabilities.recommender import Recommender
from eag.chief.capabilities.registry import CapabilityRegistry
from eag.chief.capabilities.runtime import CapabilityRuntime

__all__ = [
    # Enums
    "CapabilityCategory",
    "CapabilityCost",
    "CapabilityRequirement",
    "CapabilityRisk",
    "CapabilityRuntimeState",
    # Errors
    "CapabilityError",
    "CapabilityNotFound",
    "DuplicateCapability",
    "RankingFailure",
    "RequirementMissing",
    # Events
    "CapabilityEvent",
    "CapabilityMatched",
    "CapabilityRanked",
    "CapabilityRegistered",
    "RecommendationProduced",
    # Models
    "Capability",
    "CapabilityAnalysis",
    "CapabilityMatch",
    "CapabilityMetadata",
    "CapabilityMetrics",
    "CapabilityRecommendation",
    # Components
    "CapabilityMatcher",
    "CapabilityRanker",
    "Recommender",
    "CapabilityRegistry",
    "CapabilityRuntime",
]
