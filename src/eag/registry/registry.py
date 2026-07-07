"""Capability registry for EAG."""

from collections import defaultdict

# EventBus is imported but not the concrete events
from eag.events import EventBus
from eag.registry.capability import (
    Capability,
    CapabilityRegistration,
)
from eag.registry.errors import (
    CapabilityAlreadyRegisteredError,
    CapabilityNotFoundError,
)


class CapabilityRegistry:
    """Register and resolve EAG capabilities."""

    def __init__(
        self,
        event_bus: EventBus | None = None,
    ) -> None:
        self._event_bus = event_bus
        self._registrations: dict[
            Capability,
            list[CapabilityRegistration],
        ] = defaultdict(list)

    def register(
        self,
        registration: CapabilityRegistration,
    ) -> None:
        """Register a capability implementation."""
        registrations = self._registrations[
            registration.capability
        ]

        if any(
            existing.provider == registration.provider
            for existing in registrations
        ):
            raise CapabilityAlreadyRegisteredError(
                "Capability "
                f"'{registration.capability.identifier}' "
                "is already registered by provider "
                f"'{registration.provider}'"
            )

        registrations.append(registration)

        # Publish event after successful registration
        if self._event_bus is not None:
            from eag.events import CapabilityRegistered
            self._event_bus.publish(
                CapabilityRegistered(
                    capability=registration.capability.identifier,
                    provider=registration.provider,
                )
            )

    def unregister(
        self,
        capability: Capability,
        provider: str,
    ) -> None:
        """Remove a capability implementation."""
        registrations = self._registrations.get(capability)

        if not registrations:
            return

        # Check whether the provider existed
        removed = any(
            registration.provider == provider
            for registration in registrations
        )

        remaining = [
            registration
            for registration in registrations
            if registration.provider != provider
        ]

        if remaining:
            self._registrations[capability] = remaining
        else:
            self._registrations.pop(capability, None)

        # Publish event if a provider was actually removed
        if removed and self._event_bus is not None:
            from eag.events import CapabilityUnregistered
            self._event_bus.publish(
                CapabilityUnregistered(
                    capability=capability.identifier,
                    provider=provider,
                )
            )

    def resolve(
        self,
        capability: Capability,
    ) -> CapabilityRegistration:
        """Resolve the default provider for a capability."""
        registrations = self._registrations.get(capability)

        if not registrations:
            raise CapabilityNotFoundError(
                "No provider registered for capability "
                f"'{capability.identifier}'"
            )

        return registrations[0]

    def resolve_all(
        self,
        capability: Capability,
    ) -> tuple[CapabilityRegistration, ...]:
        """Resolve all providers for a capability."""
        return tuple(
            self._registrations.get(capability, ())
        )

    def has(self, capability: Capability) -> bool:
        """Return whether a capability is registered."""
        return bool(
            self._registrations.get(capability)
        )

    def capabilities(self) -> tuple[Capability, ...]:
        """Return all registered capabilities."""
        return tuple(
            sorted(self._registrations)
        )

    def provider_count(
        self,
        capability: Capability,
    ) -> int:
        """Return provider count for a capability."""
        return len(
            self._registrations.get(capability, ())
        )

    def clear(self) -> None:
        """Remove all capability registrations."""
        self._registrations.clear()
