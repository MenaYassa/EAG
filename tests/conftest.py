"""Shared pytest fixtures for EAG tests."""

import pytest

from eag.config import Settings
from eag.core import RuntimeContext
from eag.events import EventBus
from eag.registry import CapabilityRegistry


@pytest.fixture
def settings() -> Settings:
    """Create isolated test settings."""
    return Settings(
        kernel={
            "environment": "testing",
        }
    )


@pytest.fixture
def event_bus() -> EventBus:
    """Create an isolated event bus."""
    return EventBus()


@pytest.fixture
def capability_registry(
    event_bus: EventBus,
) -> CapabilityRegistry:
    """Create an isolated capability registry."""
    return CapabilityRegistry(
        event_bus=event_bus,
    )


@pytest.fixture
def runtime_context(
    settings: Settings,
    event_bus: EventBus,
    capability_registry: CapabilityRegistry,
) -> RuntimeContext:
    """Create an isolated runtime context."""
    return RuntimeContext(
        settings=settings,
        event_bus=event_bus,
        capability_registry=capability_registry,
    )
