"""Task Graph domain vocabulary for EAG."""

from enum import StrEnum


class DependencyType(StrEnum):
    """Types of dependencies between tasks."""
    FINISH_TO_START = "finish_to_start"
    START_TO_START = "start_to_start"
    OPTIONAL = "optional"


class NodeState(StrEnum):
    """Lifecycle state of a task node."""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"