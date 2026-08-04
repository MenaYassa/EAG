"""Delegation engine for EAG Worker Collaboration."""

from eag.workers.enums import WorkerHealth, WorkerState
from eag.workers.manager import WorkerManager
from eag.workers.matcher import CapabilityMatcher, CapabilityScore
from eag.workers.models import WorkerTask
from eag.workers.protocol import Worker


class DelegationEngine:
    """Selects the best available specialist for a task."""

    def __init__(self, matcher: CapabilityMatcher, manager: WorkerManager) -> None:
        self._matcher = matcher
        self._manager = manager

    def delegate(self, task: WorkerTask) -> tuple[Worker, CapabilityScore] | None:
        """Finds the best available worker for a task based on capability and health."""
        available_workers = []
        
        for w in self._manager._registry.list():
            state = self._manager.get_state(w.profile.id)
            health = self._manager._health.get_health(w.profile.id)
            
            if state == WorkerState.IDLE and health in [WorkerHealth.HEALTHY, WorkerHealth.DEGRADED]:
                available_workers.append(w)
                
        return self._matcher.best_worker(tuple(available_workers), task)