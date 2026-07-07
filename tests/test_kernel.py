"""Tests for the EAG kernel."""

import pytest

from eag.core import RuntimeContext
from eag.kernel import Kernel
from eag.kernel.state import KernelState
from eag.plugins import PluginManager


class TestKernelLifecycle:
    """Test kernel lifecycle management."""

    def test_initial_state(
        self,
        runtime_context: RuntimeContext,
        plugin_manager: PluginManager,
    ) -> None:
        kernel = Kernel(context=runtime_context, plugin_manager=plugin_manager)
        assert kernel.state == KernelState.CREATED
        assert not kernel.is_ready

    def test_boot_success(
        self,
        runtime_context: RuntimeContext,
        plugin_manager: PluginManager,
    ) -> None:
        kernel = Kernel(context=runtime_context, plugin_manager=plugin_manager)
        kernel.boot()
        assert kernel.state == KernelState.READY
        assert kernel.is_ready

    def test_boot_idempotent(
        self,
        runtime_context: RuntimeContext,
        plugin_manager: PluginManager,
    ) -> None:
        kernel = Kernel(context=runtime_context, plugin_manager=plugin_manager)
        kernel.boot()
        assert kernel.state == KernelState.READY
        kernel.boot()
        assert kernel.state == KernelState.READY

    def test_shutdown_success(
        self,
        runtime_context: RuntimeContext,
        plugin_manager: PluginManager,
    ) -> None:
        kernel = Kernel(context=runtime_context, plugin_manager=plugin_manager)
        kernel.boot()
        assert kernel.state == KernelState.READY
        kernel.shutdown()
        assert kernel.state == KernelState.STOPPED

    def test_shutdown_idempotent(
        self,
        runtime_context: RuntimeContext,
        plugin_manager: PluginManager,
    ) -> None:
        kernel = Kernel(context=runtime_context, plugin_manager=plugin_manager)
        kernel.boot()
        kernel.shutdown()
        assert kernel.state == KernelState.STOPPED
        kernel.shutdown()
        assert kernel.state == KernelState.STOPPED

    def test_boot_from_stopped(
        self,
        runtime_context: RuntimeContext,
        plugin_manager: PluginManager,
    ) -> None:
        kernel = Kernel(context=runtime_context, plugin_manager=plugin_manager)
        kernel.boot()
        kernel.shutdown()
        assert kernel.state == KernelState.STOPPED
        kernel.boot()
        assert kernel.state == KernelState.READY

    def test_shutdown_from_created_fails(
        self,
        runtime_context: RuntimeContext,
        plugin_manager: PluginManager,
    ) -> None:
        kernel = Kernel(context=runtime_context, plugin_manager=plugin_manager)
        with pytest.raises(RuntimeError, match="Cannot shut down kernel from state: created"):
            kernel.shutdown()

    def test_boot_from_invalid_state(
        self,
        runtime_context: RuntimeContext,
        plugin_manager: PluginManager,
    ) -> None:
        kernel = Kernel(context=runtime_context, plugin_manager=plugin_manager)
        kernel._state = KernelState.BOOTING
        with pytest.raises(RuntimeError, match="Cannot boot kernel from state: booting"):
            kernel.boot()

    def test_shutdown_from_invalid_state(
        self,
        runtime_context: RuntimeContext,
        plugin_manager: PluginManager,
    ) -> None:
        kernel = Kernel(context=runtime_context, plugin_manager=plugin_manager)
        kernel._state = KernelState.CREATED
        with pytest.raises(RuntimeError, match="Cannot shut down kernel from state: created"):
            kernel.shutdown()

    def test_settings_property(
        self,
        runtime_context: RuntimeContext,
        plugin_manager: PluginManager,
    ) -> None:
        kernel = Kernel(context=runtime_context, plugin_manager=plugin_manager)
        assert kernel.settings is runtime_context.settings

    def test_state_property(
        self,
        runtime_context: RuntimeContext,
        plugin_manager: PluginManager,
    ) -> None:
        kernel = Kernel(context=runtime_context, plugin_manager=plugin_manager)
        assert kernel.state == KernelState.CREATED
        kernel.boot()
        assert kernel.state == KernelState.READY
        kernel.shutdown()
        assert kernel.state == KernelState.STOPPED

    def test_kernel_exposes_runtime_context(
        self,
        runtime_context: RuntimeContext,
        plugin_manager: PluginManager,
    ) -> None:
        kernel = Kernel(context=runtime_context, plugin_manager=plugin_manager)
        assert kernel.context is runtime_context
        assert kernel.settings is runtime_context.settings
        assert kernel.event_bus is runtime_context.event_bus
        assert kernel.capability_registry is runtime_context.capability_registry

    def test_kernel_exposes_plugin_manager(
        self,
        runtime_context: RuntimeContext,
        plugin_manager: PluginManager,
    ) -> None:
        kernel = Kernel(context=runtime_context, plugin_manager=plugin_manager)
        assert kernel.plugin_manager is plugin_manager
