"""Worker Domain for EAG."""

from eag.workers.enums import (
    ExperienceLevel,
    TaskPriority,
    WorkerHealth,
    WorkerRole,
    WorkerState,
)
from eag.workers.errors import (
    WorkerAssignmentError,
    WorkerBusyError,
    WorkerCapabilityError,
    WorkerError,
    WorkerNotFoundError,
    WorkerUnavailableError,
)
from eag.workers.events import (
    WorkerAssigned,
    WorkerCompleted,
    WorkerEvent,
    WorkerFailed,
    WorkerRecovered,
    WorkerRegistered,
    WorkerReleased,
    WorkerStarted,
)
from eag.workers.health import WorkerHealthManager
from eag.workers.manager import WorkerManager
from eag.workers.metrics import WorkerRuntimeMetrics
from eag.workers.models import (
    WorkerAssignment,
    WorkerContext,
    WorkerMetrics,
    WorkerProfile,
    WorkerResult,
    WorkerTask,
)
from eag.workers.protocol import Worker
from eag.workers.registry import WorkerRegistry
from eag.workers.runtime import WorkerRuntime

__all__ = [
    # Enums
    "ExperienceLevel",
    "TaskPriority",
    "WorkerHealth",
    "WorkerRole",
    "WorkerState",
    # Errors
    "WorkerAssignmentError",
    "WorkerBusyError",
    "WorkerCapabilityError",
    "WorkerError",
    "WorkerNotFoundError",
    "WorkerUnavailableError",
    # Events
    "WorkerAssigned",
    "WorkerCompleted",
    "WorkerEvent",
    "WorkerFailed",
    "WorkerRecovered",
    "WorkerRegistered",
    "WorkerReleased",
    "WorkerStarted",
    # Metrics
    "WorkerRuntimeMetrics",
    # Models
    "Worker",
    "WorkerAssignment",
    "WorkerContext",
    "WorkerMetrics",
    "WorkerProfile",
    "WorkerResult",
    "WorkerTask",
    # Components
    "WorkerHealthManager",
    "WorkerManager",
    "WorkerRegistry",
    "WorkerRuntime",
]
