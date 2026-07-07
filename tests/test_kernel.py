"""Tests for the EAG kernel."""

import pytest

from eag.config import Settings
from eag.events import EventBus
from eag.kernel import Kernel
from eag.kernel.state import KernelState
from eag.registry import CapabilityRegistry


@pytest.fixture
def settings() -> Settings:
    """Create a test settings instance."""
    return Settings()


@pytest.fixture
def event_bus() -> EventBus:
    """Create an isolated event bus."""
    return EventBus()


@pytest.fixture
def capability_registry(
    event_bus: EventBus,
) -> CapabilityRegistry:
    """Create an isolated capability registry."""
    return CapabilityRegistry(event_bus=event_bus)


class TestKernelLifecycle:
    """Test kernel lifecycle management."""

    def test_initial_state(
        self,
        settings: Settings,
        event_bus: EventBus,
        capability_registry: CapabilityRegistry,
    ) -> None:
        """Test that kernel starts in CREATED state."""
        kernel = Kernel(
            settings=settings,
            event_bus=event_bus,
            capability_registry=capability_registry,
        )
        assert kernel.state == KernelState.CREATED
        assert not kernel.is_ready

    def test_boot_success(
        self,
        settings: Settings,
        event_bus: EventBus,
        capability_registry: CapabilityRegistry,
    ) -> None:
        """Test successful kernel boot."""
        kernel = Kernel(
            settings=settings,
            event_bus=event_bus,
            capability_registry=capability_registry,
        )
        kernel.boot()
        assert kernel.state == KernelState.READY
        assert kernel.is_ready

    def test_boot_idempotent(
        self,
        settings: Settings,
        event_bus: EventBus,
        capability_registry: CapabilityRegistry,
    ) -> None:
        """Test that booting an already-ready kernel does nothing."""
        kernel = Kernel(
            settings=settings,
            event_bus=event_bus,
            capability_registry=capability_registry,
        )
        kernel.boot()
        assert kernel.state == KernelState.READY
        kernel.boot()  # Should do nothing
        assert kernel.state == KernelState.READY

    def test_shutdown_success(
        self,
        settings: Settings,
        event_bus: EventBus,
        capability_registry: CapabilityRegistry,
    ) -> None:
        """Test successful kernel shutdown."""
        kernel = Kernel(
            settings=settings,
            event_bus=event_bus,
            capability_registry=capability_registry,
        )
        kernel.boot()
        assert kernel.state == KernelState.READY
        kernel.shutdown()
        assert kernel.state == KernelState.STOPPED

    def test_shutdown_idempotent(
        self,
        settings: Settings,
        event_bus: EventBus,
        capability_registry: CapabilityRegistry,
    ) -> None:
        """Test that shutting down an already-stopped kernel does nothing."""
        kernel = Kernel(
            settings=settings,
            event_bus=event_bus,
            capability_registry=capability_registry,
        )
        kernel.boot()
        kernel.shutdown()
        assert kernel.state == KernelState.STOPPED
        kernel.shutdown()  # Should do nothing
        assert kernel.state == KernelState.STOPPED

    def test_boot_from_stopped(
        self,
        settings: Settings,
        event_bus: EventBus,
        capability_registry: CapabilityRegistry,
    ) -> None:
        """Test that a stopped kernel can be booted again."""
        kernel = Kernel(
            settings=settings,
            event_bus=event_bus,
            capability_registry=capability_registry,
        )
        kernel.boot()
        kernel.shutdown()
        assert kernel.state == KernelState.STOPPED
        kernel.boot()
        assert kernel.state == KernelState.READY

    def test_shutdown_from_created_fails(
        self,
        settings: Settings,
        event_bus: EventBus,
        capability_registry: CapabilityRegistry,
    ) -> None:
        """Test that shutting down a kernel that hasn't booted fails."""
        kernel = Kernel(
            settings=settings,
            event_bus=event_bus,
            capability_registry=capability_registry,
        )
        with pytest.raises(RuntimeError, match="Cannot shut down kernel from state: created"):
            kernel.shutdown()

    def test_boot_from_invalid_state(
        self,
        settings: Settings,
        event_bus: EventBus,
        capability_registry: CapabilityRegistry,
    ) -> None:
        """Test that booting from invalid state fails."""
        kernel = Kernel(
            settings=settings,
            event_bus=event_bus,
            capability_registry=capability_registry,
        )
        # Set internal state directly to test invalid transition
        kernel._state = KernelState.BOOTING
        with pytest.raises(RuntimeError, match="Cannot boot kernel from state: booting"):
            kernel.boot()

    def test_shutdown_from_invalid_state(
        self,
        settings: Settings,
        event_bus: EventBus,
        capability_registry: CapabilityRegistry,
    ) -> None:
        """Test that shutting down from invalid state fails."""
        kernel = Kernel(
            settings=settings,
            event_bus=event_bus,
            capability_registry=capability_registry,
        )
        # Set internal state directly to test invalid transition
        kernel._state = KernelState.CREATED
        with pytest.raises(RuntimeError, match="Cannot shut down kernel from state: created"):
            kernel.shutdown()

    def test_settings_property(
        self,
        settings: Settings,
        event_bus: EventBus,
        capability_registry: CapabilityRegistry,
    ) -> None:
        """Test that settings property returns the correct instance."""
        kernel = Kernel(
            settings=settings,
            event_bus=event_bus,
            capability_registry=capability_registry,
        )
        assert kernel.settings is settings

    def test_state_property(
        self,
        settings: Settings,
        event_bus: EventBus,
        capability_registry: CapabilityRegistry,
    ) -> None:
        """Test that state property returns the current state."""
        kernel = Kernel(
            settings=settings,
            event_bus=event_bus,
            capability_registry=capability_registry,
        )
        assert kernel.state == KernelState.CREATED
        kernel.boot()
        assert kernel.state == KernelState.READY
        kernel.shutdown()
        assert kernel.state == KernelState.STOPPED
