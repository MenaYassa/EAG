"""Tests for the EAG capability registry."""

import pytest

from eag.events import (
    CapabilityRegistered,
    CapabilityUnregistered,
    EventBus,
)
from eag.registry import (
    Capability,
    CapabilityAlreadyRegisteredError,
    CapabilityNotFoundError,
    CapabilityRegistration,
    CapabilityRegistry,
)


def example_handler() -> str:
    """Return a test result."""
    return "ok"


def alternate_handler() -> str:
    """Return an alternate test result."""
    return "alternate"


def test_capability_identifier() -> None:
    capability = Capability(
        namespace="git",
        name="status",
    )

    assert capability.identifier == "git.status"
    assert str(capability) == "git.status"


def test_capability_parse() -> None:
    capability = Capability.parse("git.status")

    assert capability.namespace == "git"
    assert capability.name == "status"


def test_invalid_capability_identifier() -> None:
    with pytest.raises(ValueError):
        Capability.parse("invalid")


def test_register_and_resolve() -> None:
    registry = CapabilityRegistry()

    capability = Capability.parse("git.status")

    registration = CapabilityRegistration(
        capability=capability,
        provider="native-git",
        handler=example_handler,
    )

    registry.register(registration)

    resolved = registry.resolve(capability)

    assert resolved == registration
    assert resolved.handler() == "ok"


def test_multiple_providers() -> None:
    registry = CapabilityRegistry()

    capability = Capability.parse("git.status")

    first = CapabilityRegistration(
        capability=capability,
        provider="native-git",
        handler=example_handler,
    )

    second = CapabilityRegistration(
        capability=capability,
        provider="remote-git",
        handler=alternate_handler,
    )

    registry.register(first)
    registry.register(second)

    assert registry.provider_count(capability) == 2
    assert registry.resolve(capability) == first
    assert registry.resolve_all(capability) == (
        first,
        second,
    )


def test_duplicate_provider_is_rejected() -> None:
    registry = CapabilityRegistry()

    capability = Capability.parse("git.status")

    registration = CapabilityRegistration(
        capability=capability,
        provider="native-git",
        handler=example_handler,
    )

    registry.register(registration)

    with pytest.raises(CapabilityAlreadyRegisteredError):
        registry.register(registration)


def test_missing_capability_raises() -> None:
    registry = CapabilityRegistry()

    capability = Capability.parse("git.status")

    with pytest.raises(CapabilityNotFoundError):
        registry.resolve(capability)


def test_unregister() -> None:
    registry = CapabilityRegistry()

    capability = Capability.parse("git.status")

    registration = CapabilityRegistration(
        capability=capability,
        provider="native-git",
        handler=example_handler,
    )

    registry.register(registration)

    registry.unregister(
        capability,
        provider="native-git",
    )

    assert registry.has(capability) is False


def test_registry_publishes_registration_event() -> None:
    event_bus = EventBus()
    registry = CapabilityRegistry(
        event_bus=event_bus,
    )

    received: list[CapabilityRegistered] = []

    def handler(
        event: CapabilityRegistered,
    ) -> None:
        received.append(event)

    event_bus.subscribe(
        CapabilityRegistered,
        handler,
    )

    registry.register(
        CapabilityRegistration(
            capability=Capability.parse("git.status"),
            provider="native-git",
            handler=example_handler,
        )
    )

    assert len(received) == 1
    assert received[0].capability == "git.status"
    assert received[0].provider == "native-git"


def test_registry_publishes_unregistration_event() -> None:
    event_bus = EventBus()
    registry = CapabilityRegistry(
        event_bus=event_bus,
    )

    received: list[CapabilityUnregistered] = []

    def handler(
        event: CapabilityUnregistered,
    ) -> None:
        received.append(event)

    event_bus.subscribe(
        CapabilityUnregistered,
        handler,
    )

    capability = Capability.parse("git.status")

    registry.register(
        CapabilityRegistration(
            capability=capability,
            provider="native-git",
            handler=example_handler,
        )
    )

    registry.unregister(
        capability,
        provider="native-git",
    )

    assert len(received) == 1
    assert received[0].capability == "git.status"


def test_unregister_unknown_provider_emits_no_event() -> None:
    event_bus = EventBus()
    registry = CapabilityRegistry(
        event_bus=event_bus,
    )

    received: list[CapabilityUnregistered] = []

    def handler(
        event: CapabilityUnregistered,
    ) -> None:
        received.append(event)

    event_bus.subscribe(
        CapabilityUnregistered,
        handler,
    )

    capability = Capability.parse("git.status")

    registry.register(
        CapabilityRegistration(
            capability=capability,
            provider="native-git",
            handler=example_handler,
        )
    )

    registry.unregister(
        capability,
        provider="unknown-provider",
    )

    assert received == []
    assert registry.has(capability) is True
