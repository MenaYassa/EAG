"""EAG kernel lifecycle management."""

from structlog.typing import FilteringBoundLogger

from eag.config import Settings
from eag.core import RuntimeContext
from eag.events import (
    EventBus,
    KernelBootCompleted,
    KernelBootStarted,
    KernelShutdownCompleted,
    KernelShutdownStarted,
)
from eag.kernel.state import KernelState
from eag.logging import get_logger
from eag.plugins import PluginManager
from eag.registry import CapabilityRegistry


class Kernel:
    """Coordinate the lifecycle of the EAG platform."""

    def __init__(
        self,
        context: RuntimeContext,
        plugin_manager: PluginManager,
        logger: FilteringBoundLogger | None = None,
    ) -> None:
        self._context = context
        self._plugin_manager = plugin_manager
        self._state = KernelState.CREATED
        self._logger = logger or get_logger(component="kernel")

    @property
    def context(self) -> RuntimeContext:
        """Return the EAG runtime context."""
        return self._context

    @property
    def plugin_manager(self) -> PluginManager:
        """Return the kernel plugin manager."""
        return self._plugin_manager

    @property
    def settings(self) -> Settings:
        """Return the kernel settings."""
        return self._context.settings

    @property
    def event_bus(self) -> EventBus:
        """Return the event bus."""
        return self._context.event_bus

    @property
    def capability_registry(self) -> CapabilityRegistry:
        """Return the capability registry."""
        return self._context.capability_registry

    @property
    def state(self) -> KernelState:
        """Return the current kernel state."""
        return self._state

    @property
    def is_ready(self) -> bool:
        """Return whether the kernel is ready to accept work."""
        return self._state is KernelState.READY

    def boot(self) -> None:
        """Boot the EAG kernel."""
        if self._state is KernelState.READY:
            return

        if self._state not in {
            KernelState.CREATED,
            KernelState.STOPPED,
        }:
            raise RuntimeError(f"Cannot boot kernel from state: {self._state.value}")

        self._logger.info(
            "kernel_boot_started",
            previous_state=self._state.value,
        )

        # Publish boot started event
        self.event_bus.publish(
            KernelBootStarted(
                previous_state=self._state.value,
            )
        )

        self._state = KernelState.BOOTING

        try:
            # Load all plugins
            self._plugin_manager.load_all()

            # Mark kernel as ready
            self._state = KernelState.READY

            # Publish boot completed event
            self.event_bus.publish(
                KernelBootCompleted(
                    state=self._state.value,
                )
            )

            self._logger.info(
                "kernel_boot_completed",
                state=self._state.value,
            )
        except Exception:
            self._state = KernelState.FAILED

            self._logger.exception(
                "kernel_boot_failed",
                state=self._state.value,
            )

            raise

    def shutdown(self) -> None:
        """Shut down the EAG kernel."""
        if self._state is KernelState.STOPPED:
            return

        if self._state is not KernelState.READY:
            raise RuntimeError(f"Cannot shut down kernel from state: {self._state.value}")

        self._logger.info(
            "kernel_shutdown_started",
            previous_state=self._state.value,
        )

        # Publish shutdown started event
        self.event_bus.publish(
            KernelShutdownStarted(
                previous_state=self._state.value,
            )
        )

        self._state = KernelState.SHUTTING_DOWN

        try:
            # Unload all plugins (reverse boot order)
            self._plugin_manager.unload_all()

            # Mark kernel as stopped
            self._state = KernelState.STOPPED

            # Publish shutdown completed event
            self.event_bus.publish(
                KernelShutdownCompleted(
                    state=self._state.value,
                )
            )

            self._logger.info(
                "kernel_shutdown_completed",
                state=self._state.value,
            )
        except Exception:
            self._state = KernelState.FAILED

            self._logger.exception(
                "kernel_shutdown_failed",
                state=self._state.value,
            )

            raise
