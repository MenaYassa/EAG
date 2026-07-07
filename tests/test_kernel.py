"""Tests for the EAG kernel."""

import pytest

from eag.core import RuntimeContext
from eag.kernel import Kernel
from eag.kernel.state import KernelState


class TestKernelLifecycle:
    """Test kernel lifecycle management."""

    def test_initial_state(
        self,
        runtime_context: RuntimeContext,
    ) -> None:
        """Test that kernel starts in CREATED state."""
        kernel = Kernel(context=runtime_context)
        assert kernel.state == KernelState.CREATED
        assert not kernel.is_ready

    def test_boot_success(
        self,
        runtime_context: RuntimeContext,
    ) -> None:
        """Test successful kernel boot."""
        kernel = Kernel(context=runtime_context)
        kernel.boot()
        assert kernel.state == KernelState.READY
        assert kernel.is_ready

    def test_boot_idempotent(
        self,
        runtime_context: RuntimeContext,
    ) -> None:
        """Test that booting an already-ready kernel does nothing."""
        kernel = Kernel(context=runtime_context)
        kernel.boot()
        assert kernel.state == KernelState.READY
        kernel.boot()
        assert kernel.state == KernelState.READY

    def test_shutdown_success(
        self,
        runtime_context: RuntimeContext,
    ) -> None:
        """Test successful kernel shutdown."""
        kernel = Kernel(context=runtime_context)
        kernel.boot()
        assert kernel.state == KernelState.READY
        kernel.shutdown()
        assert kernel.state == KernelState.STOPPED

    def test_shutdown_idempotent(
        self,
        runtime_context: RuntimeContext,
    ) -> None:
        """Test that shutting down an already-stopped kernel does nothing."""
        kernel = Kernel(context=runtime_context)
        kernel.boot()
        kernel.shutdown()
        assert kernel.state == KernelState.STOPPED
        kernel.shutdown()
        assert kernel.state == KernelState.STOPPED

    def test_boot_from_stopped(
        self,
        runtime_context: RuntimeContext,
    ) -> None:
        """Test that a stopped kernel can be booted again."""
        kernel = Kernel(context=runtime_context)
        kernel.boot()
        kernel.shutdown()
        assert kernel.state == KernelState.STOPPED
        kernel.boot()
        assert kernel.state == KernelState.READY

    def test_shutdown_from_created_fails(
        self,
        runtime_context: RuntimeContext,
    ) -> None:
        """Test that shutting down a kernel that hasn't booted fails."""
        kernel = Kernel(context=runtime_context)
        with pytest.raises(RuntimeError, match="Cannot shut down kernel from state: created"):
            kernel.shutdown()

    def test_boot_from_invalid_state(
        self,
        runtime_context: RuntimeContext,
    ) -> None:
        """Test that booting from invalid state fails."""
        kernel = Kernel(context=runtime_context)
        kernel._state = KernelState.BOOTING
        with pytest.raises(RuntimeError, match="Cannot boot kernel from state: booting"):
            kernel.boot()

    def test_shutdown_from_invalid_state(
        self,
        runtime_context: RuntimeContext,
    ) -> None:
        """Test that shutting down from invalid state fails."""
        kernel = Kernel(context=runtime_context)
        kernel._state = KernelState.CREATED
        with pytest.raises(RuntimeError, match="Cannot shut down kernel from state: created"):
            kernel.shutdown()

    def test_settings_property(
        self,
        runtime_context: RuntimeContext,
    ) -> None:
        """Test that settings property returns the correct instance."""
        kernel = Kernel(context=runtime_context)
        assert kernel.settings is runtime_context.settings

    def test_state_property(
        self,
        runtime_context: RuntimeContext,
    ) -> None:
        """Test that state property returns the current state."""
        kernel = Kernel(context=runtime_context)
        assert kernel.state == KernelState.CREATED
        kernel.boot()
        assert kernel.state == KernelState.READY
        kernel.shutdown()
        assert kernel.state == KernelState.STOPPED

    def test_kernel_exposes_runtime_context(
        self,
        runtime_context: RuntimeContext,
    ) -> None:
        """Test that kernel exposes the runtime context."""
        kernel = Kernel(context=runtime_context)
        assert kernel.context is runtime_context
        assert kernel.settings is runtime_context.settings
        assert kernel.event_bus is runtime_context.event_bus
        assert kernel.capability_registry is runtime_context.capability_registry
