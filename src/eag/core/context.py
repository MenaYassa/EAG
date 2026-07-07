"""Runtime context for EAG."""

from dataclasses import dataclass

from eag.config import Settings
from eag.events import EventBus
from eag.registry import CapabilityRegistry


@dataclass(frozen=True)
class RuntimeContext:
    """Immutable runtime context for the EAG kernel."""

    settings: Settings
    event_bus: EventBus
    capability_registry: CapabilityRegistry
