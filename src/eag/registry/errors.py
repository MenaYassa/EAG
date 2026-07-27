"""Capability registry errors."""


class RegistryError(Exception):
    """Base exception for capability registry failures."""


class CapabilityAlreadyRegisteredError(RegistryError):
    """Raised when a provider is registered twice."""


class CapabilityNotFoundError(RegistryError):
    """Raised when no provider exists for a capability."""
