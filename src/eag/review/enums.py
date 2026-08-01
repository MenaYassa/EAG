"""Engineering Review domain vocabulary for EAG."""

from enum import StrEnum


class ReviewState(StrEnum):
    """Lifecycle state of an engineering review."""

    CREATED = "created"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ReviewDecision(StrEnum):
    """The final decision of an engineering review."""

    APPROVED = "approved"
    APPROVED_WITH_WARNINGS = "approved_with_warnings"
    CHANGES_REQUESTED = "changes_requested"
    REJECTED = "rejected"


class Severity(StrEnum):
    """Severity levels for review issues."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class IssueCategory(StrEnum):
    """Engineering categories assessed during review."""

    CORRECTNESS = "correctness"
    ARCHITECTURE = "architecture"
    DESIGN = "design"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    PERFORMANCE = "performance"
    SECURITY = "security"
    STYLE = "style"
    MAINTAINABILITY = "maintainability"
    COMPLEXITY = "complexity"
    DEPENDENCIES = "dependencies"


class SuggestionPriority(StrEnum):
    """Priority levels for review suggestions."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
