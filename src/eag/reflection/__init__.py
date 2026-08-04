"""Reflection Platform for EAG."""

from eag.reflection.default_engine import DefaultReflectionEngine
from eag.reflection.enums import FindingCategory, RecommendationPriority, Severity
from eag.reflection.errors import EngineNotFoundError, ReflectionError, ReflectionValidationError
from eag.reflection.events import (
    ReflectionCompleted,
    ReflectionEvent,
    ReflectionFailed,
    ReflectionStarted,
)
from eag.reflection.models import (
    ReflectionContext,
    ReflectionFinding,
    ReflectionMetrics,
    ReflectionRecommendation,
    ReflectionReport,
    ReflectionSummary,
)
from eag.reflection.protocol import ReflectionEngine
from eag.reflection.registry import ReflectionRegistry
from eag.reflection.runtime import ReflectionRuntime

__all__ = [
    # Enums
    "FindingCategory",
    "RecommendationPriority",
    "Severity",
    # Errors
    "EngineNotFoundError",
    "ReflectionError",
    "ReflectionValidationError",
    # Events
    "ReflectionCompleted",
    "ReflectionEvent",
    "ReflectionFailed",
    "ReflectionStarted",
    # Models
    "ReflectionContext",
    "ReflectionFinding",
    "ReflectionMetrics",
    "ReflectionRecommendation",
    "ReflectionReport",
    "ReflectionSummary",
    # Components
    "DefaultReflectionEngine",
    "ReflectionEngine",
    "ReflectionRegistry",
    "ReflectionRuntime",
]
