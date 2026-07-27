"""Execution lifecycle manager for EAG."""

from eag.execution.enums import ExecutionState
from eag.execution.errors import InvalidExecutionTransition


class LifecycleManager:
    """Manages the state machine for an execution."""

    def __init__(self) -> None:
        self._state = ExecutionState.CREATED

    @property
    def state(self) -> ExecutionState:
        return self._state

    def transition_to(self, target: ExecutionState) -> None:
        if not self._state.can_transition_to(target):
            raise InvalidExecutionTransition(
                f"Cannot transition from {self._state.value} to {target.value}"
            )
        self._state = target
