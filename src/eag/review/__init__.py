"""Engineering Review Platform for EAG."""

from eag.review.analyzers import (
    CorrectnessAnalyzer,
    DocumentationAnalyzer,
    TestingAnalyzer,
)
from eag.review.enums import (
    IssueCategory,
    ReviewDecision,
    ReviewState,
    Severity,
    SuggestionPriority,
)
from eag.review.errors import (
    AnalyzerError,
    ReflectionError,
    ReviewError,
    ReviewValidationError,
)
from eag.review.events import (
    IssueDetected,
    ReflectionCompleted,
    ReflectionStarted,
    ReviewCompleted,
    ReviewEvent,
    ReviewStarted,
    SuggestionGenerated,
)
from eag.review.models import (
    Reflection,
    ReviewContext,
    ReviewFinding,
    ReviewIssue,
    ReviewMetrics,
    ReviewReport,
    ReviewSuggestion,
)
from eag.review.reflection import ReflectionEngine
from eag.review.registry import AnalyzerRegistry
from eag.review.runtime import ReviewRuntime

__all__ = [
    # Enums
    "IssueCategory",
    "ReviewDecision",
    "ReviewState",
    "Severity",
    "SuggestionPriority",
    # Errors
    "AnalyzerError",
    "ReflectionError",
    "ReviewError",
    "ReviewValidationError",
    # Events
    "IssueDetected",
    "ReflectionCompleted",
    "ReflectionStarted",
    "ReviewCompleted",
    "ReviewEvent",
    "ReviewStarted",
    "SuggestionGenerated",
    # Models
    "Reflection",
    "ReviewContext",
    "ReviewFinding",
    "ReviewIssue",
    "ReviewMetrics",
    "ReviewReport",
    "ReviewSuggestion",
    # Components
    "AnalyzerRegistry",
    "CorrectnessAnalyzer",
    "DocumentationAnalyzer",
    "ReflectionEngine",
    "ReviewRuntime",
    "TestingAnalyzer",
]