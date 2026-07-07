"""Built-in EAG domain event types."""

from dataclasses import dataclass

from eag.events.event import Event
from eag.kernel.state import KernelState


@dataclass(frozen=True, slots=True, kw_only=True)
class KernelBootStarted(Event):
    """Published when kernel boot begins."""

    previous_state: KernelState


@dataclass(frozen=True, slots=True, kw_only=True)
class KernelBootCompleted(Event):
    """Published when kernel boot completes successfully."""

    state: KernelState


@dataclass(frozen=True, slots=True, kw_only=True)
class KernelBootFailed(Event):
    """Published when kernel boot fails."""

    state: KernelState
    error_type: str
    error_message: str


@dataclass(frozen=True, slots=True, kw_only=True)
class KernelShutdownStarted(Event):
    """Published when kernel shutdown begins."""

    previous_state: KernelState


@dataclass(frozen=True, slots=True, kw_only=True)
class KernelShutdownCompleted(Event):
    """Published when kernel shutdown completes successfully."""

    state: KernelState


@dataclass(frozen=True, slots=True, kw_only=True)
class KernelShutdownFailed(Event):
    """Published when kernel shutdown fails."""

    state: KernelState
    error_type: str
    error_message: str