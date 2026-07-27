"""Engineering operation vocabulary for EAG."""

from enum import StrEnum


class OperationCategory(StrEnum):
    """The category of an engineering operation."""

    CODE = "code"
    FILESYSTEM = "filesystem"
    REPOSITORY = "repository"
    VALIDATION = "validation"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    REFACTORING = "refactoring"
    ANALYSIS = "analysis"


class OperationComplexity(StrEnum):
    """Complexity levels for an engineering operation."""

    TRIVIAL = "trivial"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


class OperationSafety(StrEnum):
    """Safety classification for an engineering operation."""

    SAFE = "safe"
    CAUTION = "caution"
    DANGEROUS = "dangerous"
