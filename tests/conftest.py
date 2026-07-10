"""Shared pytest fixtures for EAG tests."""

import io

import pytest
import structlog

# New imports for approval
from eag.approval import (
    ApprovalCoordinator,
    ApprovalManager,
    InMemoryApprovalStore,
)
from eag.config import Settings
from eag.core import RuntimeContext
from eag.events import EventBus
from eag.plugins import PluginManager
from eag.registry import CapabilityRegistry


@pytest.fixture(autouse=True)
def configure_structlog_for_tests() -> None:
    """Configure structlog to use a StringIO logger for all tests."""
    output = io.StringIO()
    structlog.configure(
        processors=[
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.PrintLoggerFactory(output),
    )
    yield
    # Reset to default after each test to avoid cross‑test pollution
    structlog.reset_defaults()


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
    """Create an isolated runtime context with shared approval components."""

    # Build approval components using the same event_bus
    approval_manager = ApprovalManager(
        store=InMemoryApprovalStore(),
        event_bus=event_bus,
    )
    approval_coordinator = ApprovalCoordinator(
        manager=approval_manager,
    )

    return RuntimeContext(
        settings=settings,
        event_bus=event_bus,
        capability_registry=capability_registry,
        approval_manager=approval_manager,
        approval_coordinator=approval_coordinator,
    )


@pytest.fixture
def plugin_manager(
    runtime_context: RuntimeContext,
) -> PluginManager:
    """Create an isolated plugin manager."""
    return PluginManager(
        context=runtime_context,
    )
