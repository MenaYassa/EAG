"""Worker protocol for EAG."""

from typing import Protocol, runtime_checkable

from eag.workers.models import (
    WorkerContext,
    WorkerProfile,
    WorkerResult,
    WorkerTask,
)

@runtime_checkable
class Worker(Protocol):
    """The contract for an engineering worker."""

    @property
    def profile(self) -> WorkerProfile: ...

    def supports(self, task: WorkerTask) -> bool: ...

    def estimate(self, task: WorkerTask) -> float: ...

    def execute(self, task: WorkerTask, context: WorkerContext) -> WorkerResult: ...
