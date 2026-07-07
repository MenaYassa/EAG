"""Event types for EAG."""

from dataclasses import dataclass

from eag.events.event import Event


@dataclass(frozen=True, slots=True, kw_only=True)
class KernelBootStarted(Event):
    """Published when kernel boot begins."""

    previous_state: str


@dataclass(frozen=True, slots=True, kw_only=True)
class KernelBootCompleted(Event):
    """Published when kernel boot completes successfully."""

    state: str


@dataclass(frozen=True, slots=True, kw_only=True)
class KernelBootFailed(Event):
    """Published when kernel boot fails."""

    state: str


@dataclass(frozen=True, slots=True, kw_only=True)
class KernelShutdownStarted(Event):
    """Published when kernel shutdown begins."""

    previous_state: str


@dataclass(frozen=True, slots=True, kw_only=True)
class KernelShutdownCompleted(Event):
    """Published when kernel shutdown completes successfully."""

    state: str


@dataclass(frozen=True, slots=True, kw_only=True)
class KernelShutdownFailed(Event):
    """Published when kernel shutdown fails."""

    state: str


@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityRegistered(Event):
    """Published when a capability is registered."""

    capability: str
    provider: str


@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityUnregistered(Event):
    """Published when a capability is unregistered."""

    capability: str
    provider: str
