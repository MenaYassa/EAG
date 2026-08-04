"""Engineering Memory domain vocabulary for EAG."""

from enum import StrEnum


class MemoryCategory(StrEnum):
    """Categories of engineering memory."""
    PLANNING = "planning"
    EXECUTION = "execution"
    TESTING = "testing"
    ARCHITECTURE = "architecture"
    REVIEW = "review"
    BENCHMARK = "benchmark"
    WORKER = "worker"
    CAPABILITY = "capability"


class KnowledgeLevel(StrEnum):
    """The evolutionary level of knowledge."""
    OBSERVATION = "observation"
    LESSON = "lesson"
    PATTERN = "pattern"
    RULE = "rule"