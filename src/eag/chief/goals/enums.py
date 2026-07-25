"""Goal domain vocabulary for EAG Chief Engineer."""

from enum import StrEnum


class GoalIntent(StrEnum):
    """The underlying engineering intent of a user's request."""

    BUILD = "build"
    REFACTOR = "refactor"
    BUGFIX = "bugfix"
    MIGRATION = "migration"
    ANALYSIS = "analysis"
    REVIEW = "review"
    DOCUMENTATION = "documentation"
    UNKNOWN = "unknown"


class GoalCategory(StrEnum):
    """The domain category of the engineering work."""

    APPLICATION = "application"
    LIBRARY = "library"
    INFRASTRUCTURE = "infrastructure"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    MIGRATION = "migration"
    ANALYSIS = "analysis"
    UNKNOWN = "unknown"


class GoalComplexity(StrEnum):
    """Estimated complexity of the engineering goal."""

    TRIVIAL = "trivial"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    MASSIVE = "massive"


class GoalPriority(StrEnum):
    """Priority level of the engineering goal."""

    URGENT = "urgent"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
