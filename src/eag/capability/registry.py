"""Capability registry for EAG."""

from eag.capability.errors import CapabilityNotFoundError
from eag.capability.models import Capability, CapabilityRequest


class CapabilityRegistry:
    """Discovers and manages available engineering capabilities."""

    def __init__(self) -> None:
        self._capabilities: dict[str, Capability] = {}

    def register(self, capability: Capability) -> None:
        cap_id = capability.metadata.id
        if cap_id in self._capabilities:
            raise ValueError(f"Capability '{cap_id}' is already registered.")
        self._capabilities[cap_id] = capability

    def find(self, capability_id: str) -> Capability:
        if capability_id not in self._capabilities:
            raise CapabilityNotFoundError(f"Capability '{capability_id}' not found.")
        return self._capabilities[capability_id]

    def list(self) -> tuple[Capability, ...]:
        return tuple(self._capabilities.values())

    def discover(self, request: CapabilityRequest) -> tuple[Capability, ...]:
        """Finds all capabilities that support the given request."""
        return tuple(c for c in self._capabilities.values() if c.supports(request))