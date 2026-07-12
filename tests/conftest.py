"""Shared pytest fixtures for EAG tests."""

import io
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import structlog

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
from eag.safety import SafetyRuntime


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
def settings(tmp_path: Path) -> Settings:
    """Create test settings."""
    from eag.config import KernelSettings, LoggingSettings

    return Settings(
        kernel=KernelSettings(
            name="EAG",
            environment="testing",
            workspace=tmp_path,
        ),
        logging=LoggingSettings(level="INFO", json_output=False),
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

    # Build safety runtime with mocked dependencies
    safety_runtime = SafetyRuntime(
        workspace=settings.kernel.workspace,
        inspector=MagicMock(),
        checkpoint_manager=MagicMock(),
        rollback_engine=MagicMock(),
        event_bus=event_bus,
    )

    return RuntimeContext(
        settings=settings,
        event_bus=event_bus,
        capability_registry=capability_registry,
        approval_manager=approval_manager,
        approval_coordinator=approval_coordinator,
        safety_runtime=safety_runtime,
        repository_runtime=MagicMock(),
    )


@pytest.fixture
def plugin_manager(
    runtime_context: RuntimeContext,
) -> PluginManager:
    """Create an isolated plugin manager."""
    return PluginManager(
        context=runtime_context,
    )
