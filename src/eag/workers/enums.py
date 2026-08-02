"""Worker domain vocabulary for EAG."""

from enum import StrEnum


class WorkerRole(StrEnum):
    """Engineering roles a worker can assume."""

    GENERAL = "general"
    BACKEND = "backend"
    FRONTEND = "frontend"
    DATABASE = "database"
    TESTING = "testing"
    REVIEW = "review"
    DOCUMENTATION = "documentation"
    DEVOPS = "devops"
    SECURITY = "security"
    AI = "ai"


class WorkerState(StrEnum):
    """Lifecycle state of a worker."""

    IDLE = "idle"
    ASSIGNED = "assigned"
    PLANNING = "planning"
    EXECUTING = "executing"
    WAITING = "waiting"
    REVIEWING = "reviewing"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkerHealth(StrEnum):
    """Health status of a worker."""

    HEALTHY = "healthy"
    BUSY = "busy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class ExperienceLevel(StrEnum):
    """Experience level of a worker."""

    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    EXPERT = "expert"


class TaskPriority(StrEnum):
    """Priority levels for worker tasks."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"
