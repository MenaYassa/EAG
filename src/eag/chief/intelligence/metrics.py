"""AI Intelligence metrics for EAG."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class IntelligenceMetrics:
    """Metrics tracking the health and usage of the AI Intelligence platform."""
    registered_models: int = 0
    registered_providers: int = 0
    selection_count: int = 0
    fallback_count: int = 0
    average_selection_time_ms: float = 0.0
    average_confidence: float = 0.0