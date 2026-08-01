"""Chief Runtime for EAG."""

import time
from eag.capability import CapabilityRuntime
from eag.chief.runtime.coordinator import Coordinator
from eag.chief.runtime.enums import RunOutcome, RunState
from eag.chief.runtime.errors import ChiefRuntimeError
from eag.chief.runtime.models import ChiefRun, RunContext, RunResult
from eag.chief.runtime.registry import RuntimeRegistry
from eag.events import EventBus


class ChiefRuntime:
    """The central orchestrator for EAG engineering workflows."""

    def __init__(
        self,
        registry: RuntimeRegistry | None = None,
        event_bus: EventBus | None = None
    ) -> None:
        self._registry = registry or RuntimeRegistry()
        self._event_bus = event_bus or EventBus()
        self._state = RunState.CREATED

    @property
    def state(self) -> RunState:
        return self._state

    @property
    def registry(self) -> RuntimeRegistry:
        return self._registry

    def execute_goal(
        self, 
        context: RunContext, 
        planner_name: str = "default", 
        capability_runtime: CapabilityRuntime | None = None, 
        validator_name: str = "default"
    ) -> RunResult:
        """Execute a goal through the full Chief pipeline."""
        
        # 1. PRESERVED FIX: Catch illegal terminal states on brand-new runs
        if self._state.is_terminal:
            if not getattr(self, "_has_run", False):
                raise ChiefRuntimeError(f"Runtime is in terminal state: {self._state.value}")
                
        # 2. PRESERVED FIX: Mark that this runtime has officially executed a run
        self._has_run = True
        
        # 3. Reset state for the new run 
        self._state = RunState.CREATED

        planner = self._registry.get_planner(planner_name)
        validator = self._registry.get_validator(validator_name)
        
        # NEW LOGIC: Require CapabilityRuntime
        if capability_runtime is None:
            raise ChiefRuntimeError("CapabilityRuntime must be provided")

        # NEW LOGIC: Pass capability_runtime instead of executor
        coordinator = Coordinator(
            planner=planner,
            capability_runtime=capability_runtime,
            validator=validator,
            event_bus=self._event_bus
        )

        self._state = RunState.EXECUTING
        result = coordinator.run(context)
        self._state = RunState.COMPLETED if result.outcome == RunOutcome.SUCCESS else RunState.FAILED
        return result