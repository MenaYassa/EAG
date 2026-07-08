"""Tests for the EAG kernel."""

import pytest

from eag.core import ComponentMetadata, Plugin, RuntimeContext
from eag.kernel import Kernel
from eag.kernel.state import KernelState
from eag.plugins import (
    PluginManager,
    PluginPolicy,
)


class HealthyTestPlugin(Plugin):
    """Minimal healthy plugin used for kernel tests."""

    @property
    def metadata(self) -> ComponentMetadata:
        """Return test plugin metadata."""
        return ComponentMetadata(
            name="healthy-test-plugin",
            version="1.0.0",
        )

    def load(
        self,
        context: RuntimeContext,
    ) -> None:
        """Load the test plugin."""
        del context

    def unload(
        self,
        context: RuntimeContext,
    ) -> None:
        """Unload the test plugin."""
        del context


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

    def test_kernel_boots_degraded_when_optional_plugin_fails(
        self,
        runtime_context: RuntimeContext,
    ) -> None:
        class FailingOptionalPlugin(Plugin):
            @property
            def metadata(self) -> ComponentMetadata:
                return ComponentMetadata(
                    name="optional-failure",
                    version="1.0.0",
                )

            def load(
                self,
                context: RuntimeContext,
            ) -> None:
                del context
                raise RuntimeError("optional dependency unavailable")

            def unload(
                self,
                context: RuntimeContext,
            ) -> None:
                del context

        manager = PluginManager(context=runtime_context)

        manager.register(
            FailingOptionalPlugin(),
            policy=PluginPolicy.OPTIONAL,
        )

        kernel = Kernel(
            context=runtime_context,
            plugin_manager=manager,
        )

        kernel.boot()

        assert kernel.state is KernelState.READY_DEGRADED

    def test_kernel_fails_when_required_plugin_fails(
        self,
        runtime_context: RuntimeContext,
    ) -> None:
        class FailingRequiredPlugin(Plugin):
            @property
            def metadata(self) -> ComponentMetadata:
                return ComponentMetadata(
                    name="required-failure",
                    version="1.0.0",
                )

            def load(
                self,
                context: RuntimeContext,
            ) -> None:
                del context
                raise RuntimeError("required dependency unavailable")

            def unload(
                self,
                context: RuntimeContext,
            ) -> None:
                del context

        manager = PluginManager(context=runtime_context)

        manager.register(
            FailingRequiredPlugin(),
            policy=PluginPolicy.REQUIRED,
        )

        kernel = Kernel(
            context=runtime_context,
            plugin_manager=manager,
        )

        with pytest.raises(
            RuntimeError,
            match="required dependency unavailable",
        ):
            kernel.boot()

        assert kernel.state is KernelState.FAILED

    def test_runtime_health_reports_loaded_plugins(
        self,
        runtime_context: RuntimeContext,
    ) -> None:
        """Runtime health reports successfully loaded plugins."""
        manager = PluginManager(context=runtime_context)

        manager.register(HealthyTestPlugin())

        kernel = Kernel(
            context=runtime_context,
            plugin_manager=manager,
        )

        kernel.boot()

        health = kernel.health()

        assert health.healthy is True
        assert health.degraded is False
        assert len(health.available_plugins) == 1
        assert health.unavailable_plugins == ()

    def test_degraded_kernel_can_shutdown(
        self,
        runtime_context: RuntimeContext,
    ) -> None:
        """A degraded but operational kernel can shut down cleanly."""

        class FailingOptionalPlugin(Plugin):
            @property
            def metadata(self) -> ComponentMetadata:
                return ComponentMetadata(
                    name="optional-failure",
                    version="1.0.0",
                )

            def load(
                self,
                context: RuntimeContext,
            ) -> None:
                del context
                raise RuntimeError("optional dependency unavailable")

            def unload(
                self,
                context: RuntimeContext,
            ) -> None:
                del context

        manager = PluginManager(
            context=runtime_context,
        )

        manager.register(
            FailingOptionalPlugin(),
            policy=PluginPolicy.OPTIONAL,
        )

        kernel = Kernel(
            context=runtime_context,
            plugin_manager=manager,
        )

        kernel.boot()

        assert kernel.state is KernelState.READY_DEGRADED

        kernel.shutdown()

        assert kernel.state is KernelState.STOPPED
