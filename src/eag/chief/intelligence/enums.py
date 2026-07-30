"""AI Intelligence domain vocabulary for EAG."""

from enum import StrEnum


class AIReasoningLevel(StrEnum):
    """graded characteristic for reasoning."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


class AISpeed(StrEnum):
    """graded characteristic for speed."""

    SLOW = "slow"
    MEDIUM = "medium"
    FAST = "fast"
    REALTIME = "realtime"


class AICost(StrEnum):
    """graded characteristic for cost."""

    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class AIContextSize(StrEnum):
    """graded characteristic for context size."""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    HUGE = "huge"


class ModelStatus(StrEnum):
    """Lifecycle status of an AI model."""

    AVAILABLE = "available"
    DISABLED = "disabled"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"


class ProviderStatus(StrEnum):
    """Lifecycle status of an AI provider."""

    ONLINE = "online"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"


class RoutingPolicy(StrEnum):
    """Policies for selecting AI models."""

    LOW_COST = "low_cost"
    BALANCED = "balanced"
    HIGH_QUALITY = "high_quality"
    FASTEST = "fastest"
    LOCAL_ONLY = "local_only"
    CLOUD_ONLY = "cloud_only"
    CUSTOM = "custom"


class SelectionReason(StrEnum):
    """Reasons for selecting a specific model."""

    EXACT_MATCH = "exact_match"
    FALLBACK = "fallback"
    POLICY_MATCH = "policy_match"
    TRAIT_MATCH = "trait_match"
    CAPABILITY_MATCH = "capability_match"
    COST_MATCH = "cost_match"
    SPEED_MATCH = "speed_match"


class RuntimeState(StrEnum):
    """Lifecycle state of the intelligence runtime."""

    UNINITIALIZED = "uninitialized"
    READY = "ready"
    SELECTING = "selecting"
    ROUTING = "routing"
    COMPLETE = "complete"
    FAILED = "failed"
