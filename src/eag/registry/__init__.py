"""EAG capability registry."""

from eag.registry.capability import (
    Capability,
    CapabilityHandler,
    CapabilityRegistration,
)
from eag.registry.errors import (
    CapabilityAlreadyRegisteredError,
    CapabilityNotFoundError,
    RegistryError,
)
from eag.registry.registry import CapabilityRegistry

__all__ = [
    "Capability",
    "CapabilityAlreadyRegisteredError",
    "CapabilityHandler",
    "CapabilityNotFoundError",
    "CapabilityRegistration",
    "CapabilityRegistry",
    "RegistryError",
]