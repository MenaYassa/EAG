"""Capability registry for EAG Chief Engineer."""

from eag.chief.capabilities.enums import CapabilityStatus
from eag.chief.capabilities.errors import CapabilityNotFound, DuplicateCapability
from eag.chief.capabilities.models import Capability


class CapabilityRegistry:
    """Discovers and manages available capabilities."""

    def __init__(self) -> None:
        self._capabilities: dict[str, Capability] = {}

    def register(self, capability: Capability) -> None:
        cap_id = capability.metadata.id
        if cap_id in self._capabilities:
            raise DuplicateCapability(f"Capability '{cap_id}' is already registered.")
        self._capabilities[cap_id] = capability

    def unregister(self, cap_id: str) -> bool:
        return self._capabilities.pop(cap_id, None) is not None

    def find(self, cap_id: str) -> Capability:
        if cap_id not in self._capabilities:
            raise CapabilityNotFound(f"Capability '{cap_id}' not found.")
        return self._capabilities[cap_id]

    def list(self) -> tuple[Capability, ...]:
        """List all registered capabilities, sorted by ID for determinism."""
        return tuple(sorted(self._capabilities.values(), key=lambda c: c.metadata.id))

    def list_active(self) -> tuple[Capability, ...]:
        """List only enabled and non-deprecated capabilities."""
        return tuple(
            c for c in self.list() 
            if c.metadata.enabled and c.metadata.status != CapabilityStatus.DEPRECATED
        )

    def search(self, query: str) -> tuple[Capability, ...]:
        """Search capabilities by name, id, or tag. Returns deterministic order."""
        query = query.lower()
        matches = [
            c for c in self._capabilities.values()
            if query in c.metadata.name.lower() 
            or query in c.metadata.id.lower() 
            or any(query in t.lower() for t in c.metadata.tags)
        ]
        return tuple(sorted(matches, key=lambda c: c.metadata.id))