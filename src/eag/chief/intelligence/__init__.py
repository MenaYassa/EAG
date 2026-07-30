"""AI Intelligence Domain for EAG Chief Engineer."""

from eag.chief.intelligence.capabilities import AICapabilities
from eag.chief.intelligence.enums import (
    AIContextSize,
    AICost,
    AIReasoningLevel,
    AISpeed,
    ModelStatus,
    ProviderStatus,
    RoutingPolicy,
    RuntimeState,
    SelectionReason,
)
from eag.chief.intelligence.errors import (
    IntelligenceError,
    ModelNotFoundError,
    NoMatchingModelError,
    ProviderError,
    ProviderNotFoundError,
    RoutingPolicyError,
    SelectionError,
)
from eag.chief.intelligence.events import (
    FallbackTriggered,
    IntelligenceEvent,
    ModelRegistered,
    ProviderRegistered,
    ProviderUnavailable,
    SelectionCompleted,
    SelectionStarted,
)
from eag.chief.intelligence.matcher import RequirementMatcher
from eag.chief.intelligence.metrics import IntelligenceMetrics
from eag.chief.intelligence.model_registry import ModelRegistry
from eag.chief.intelligence.models import (
    AIRequirements,
    ExecutionRequest,
    MatchResult,
    ModelProfile,
    ProviderProfile,
    ScoreBreakdown,
    SelectionDecision,
)
from eag.chief.intelligence.provider_registry import ProviderRegistry
from eag.chief.intelligence.runtime import IntelligenceRuntime
from eag.chief.intelligence.scorer import TraitScorer
from eag.chief.intelligence.selector import ModelSelector
from eag.chief.intelligence.traits import AITraits

__all__ = [
    # Enums
    "AICost",
    "AIContextSize",
    "AIReasoningLevel",
    "AISpeed",
    "ModelStatus",
    "ProviderStatus",
    "RoutingPolicy",
    "RuntimeState",
    "SelectionReason",
    # Errors
    "IntelligenceError",
    "ModelNotFoundError",
    "NoMatchingModelError",
    "ProviderError",
    "ProviderNotFoundError",
    "RoutingPolicyError",
    "SelectionError",
    # Events
    "FallbackTriggered",
    "IntelligenceEvent",
    "ModelRegistered",
    "ProviderRegistered",
    "ProviderUnavailable",
    "SelectionCompleted",
    "SelectionStarted",
    # Metrics
    "IntelligenceMetrics",
    # Models
    "AICapabilities",
    "AIRequirements",
    "AITraits",
    "ExecutionRequest",
    "ModelProfile",
    "ProviderProfile",
    "SelectionDecision",
    "MatchResult",
    "ScoreBreakdown",
    # Components
    "RequirementMatcher",
    "ModelRegistry",
    "ProviderRegistry",
    "ModelSelector",
    "TraitScorer",
    # Runtime
    "IntelligenceRuntime",
]
