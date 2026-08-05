"""Adaptive Planning domain vocabulary for EAG."""

from enum import StrEnum


class InsightCategory(StrEnum):
    """Categories of planning insights."""

    PLANNING = "planning"
    TESTING = "testing"
    ARCHITECTURE = "architecture"
    WORKERS = "workers"
    BENCHMARKS = "benchmarks"
    QUALITY = "quality"


class RulePriority(StrEnum):
    """Priority levels for planning rules."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class PlanningStrategyType(StrEnum):
    """Available planning strategies."""

    DEFAULT = "default"
    QUALITY_FIRST = "quality_first"
    PERFORMANCE_FIRST = "performance_first"
    COST_FIRST = "cost_first"
    RISK_AVERSE = "risk_averse"
    ADAPTIVE = "adaptive"
