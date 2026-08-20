"""Chief Runtime for EAG."""

from eag.capability import CapabilityRuntime
from eag.chief.runtime.coordinator import Coordinator
from eag.chief.runtime.enums import RunOutcome, RunState
from eag.chief.runtime.errors import ChiefRuntimeError
from eag.chief.runtime.models import RunContext, RunResult
from eag.chief.runtime.registry import RuntimeRegistry
from eag.events import EventBus


class ChiefRuntime:
    """The central orchestrator for EAG engineering workflows.

    A Chief may own a precomposed :class:`Coordinator` for the canonical
    autonomous path. Legacy direct callers may continue to provide a runtime
    registry and a per-call ``CapabilityRuntime``.
    """

    def __init__(
        self,
        registry: RuntimeRegistry | None = None,
        event_bus: EventBus | None = None,
        coordinator: Coordinator | None = None,
    ) -> None:
        self._registry = registry or RuntimeRegistry()
        self._event_bus = event_bus or EventBus()
        self._coordinator = coordinator
        self._state = RunState.CREATED

    @property
    def state(self) -> RunState:
        return self._state

    @property
    def registry(self) -> RuntimeRegistry:
        return self._registry

    @property
    def coordinator(self) -> Coordinator | None:
        """Return the publicly supplied canonical Coordinator, if any."""
        return self._coordinator

    def execute_goal(
        self,
        context: RunContext,
        planner_name: str = "default",
        capability_runtime: CapabilityRuntime | None = None,
        validator_name: str = "default",
    ) -> RunResult:
        """Execute a goal through the full Chief pipeline.

        A precomposed Coordinator takes precedence for the canonical
        autonomous route. Without one, the original registry-driven,
        per-call capability-runtime behavior is preserved.
        """

        if self._state.is_terminal and not getattr(self, "_has_run", False):
            raise ChiefRuntimeError(f"Runtime is in terminal state: {self._state.value}")

        self._has_run = True
        self._state = RunState.CREATED

        coordinator = self._coordinator
        if coordinator is None:
            planner = self._registry.get_planner(planner_name)
            validator = self._registry.get_validator(validator_name)
            if capability_runtime is None:
                raise ChiefRuntimeError("CapabilityRuntime must be provided")
            coordinator = Coordinator(
                planner=planner,
                capability_runtime=capability_runtime,
                validator=validator,
                event_bus=self._event_bus,
            )

        self._state = RunState.EXECUTING
        result = coordinator.run(context)
        self._state = (
            RunState.COMPLETED if result.outcome == RunOutcome.SUCCESS else RunState.FAILED
        )
        return result
