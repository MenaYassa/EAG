"""Reflection domain vocabulary for EAG."""

from enum import StrEnum


class FindingCategory(StrEnum):
    """Categories of reflection findings."""

    PLANNING = "planning"
    EXECUTION = "execution"
    WORKER = "worker"
    SCHEDULER = "scheduler"
    REVIEW = "review"
    BENCHMARK = "benchmark"
    ARCHITECTURE = "architecture"
    TESTING = "testing"


class Severity(StrEnum):
    """Severity levels for findings."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecommendationPriority(StrEnum):
    """Priority levels for recommendations."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
