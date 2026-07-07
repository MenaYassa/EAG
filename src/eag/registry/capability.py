"""Capability definitions for EAG."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

# Define the handler type at module level
CapabilityHandler = Callable[..., Any]


@dataclass(frozen=True, slots=True, order=True)
class Capability:
    """Describe a capability available to EAG."""

    namespace: str
    name: str

    def __post_init__(self) -> None:
        """Validate capability components."""
        if not self.namespace.strip():
            raise ValueError("Capability namespace cannot be empty")

        if not self.name.strip():
            raise ValueError("Capability name cannot be empty")

        if "." in self.namespace:
            raise ValueError("Capability namespace cannot contain '.'")

        if "." in self.name:
            raise ValueError("Capability name cannot contain '.'")

    @property
    def identifier(self) -> str:
        """Return the canonical capability identifier."""
        return f"{self.namespace}.{self.name}"

    @classmethod
    def parse(cls, identifier: str) -> "Capability":
        """Create a capability from its canonical identifier."""
        parts = identifier.split(".")

        if len(parts) != 2:
            raise ValueError("Capability identifier must use 'namespace.name' format")

        namespace, name = parts

        return cls(
            namespace=namespace,
            name=name,
        )

    def __str__(self) -> str:
        """Return the canonical capability identifier."""
        return self.identifier


@dataclass(frozen=True, slots=True)
class CapabilityRegistration:
    """Bind a capability to its implementation."""

    capability: Capability
    provider: str
    handler: CapabilityHandler

    @property
    def identifier(self) -> str:
        """Return the registration identifier."""
        return f"{self.capability.identifier}@{self.provider}"
