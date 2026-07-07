"""EAG kernel lifecycle management."""

from structlog.typing import FilteringBoundLogger

from eag.config import Settings
from eag.events import EventBus
from eag.kernel.state import KernelState
from eag.logging import get_logger
from eag.registry import CapabilityRegistry


class Kernel:
    """Coordinate the lifecycle of the EAG platform."""

    def __init__(
        self,
        settings: Settings,
        event_bus: EventBus,
        capability_registry: CapabilityRegistry,
        logger: FilteringBoundLogger | None = None,
    ) -> None:
        self._settings = settings
        self._event_bus = event_bus
        self._capability_registry = capability_registry
        self._state = KernelState.CREATED
        self._logger = logger or get_logger(component="kernel")

    @property
    def settings(self) -> Settings:
        """Return the kernel configuration."""
        return self._settings

    @property
    def state(self) -> KernelState:
        """Return the current kernel state."""
        return self._state

    @property
    def is_ready(self) -> bool:
        """Return whether the kernel is ready to accept work."""
        return self._state is KernelState.READY

    @property
    def capability_registry(self) -> CapabilityRegistry:
        """Return the capability registry."""
        return self._capability_registry

    def boot(self) -> None:
        """Boot the EAG kernel."""
        if self._state is KernelState.READY:
            return

        if self._state not in {
            KernelState.CREATED,
            KernelState.STOPPED,
        }:
            raise RuntimeError(
                f"Cannot boot kernel from state: {self._state.value}"
            )

        self._logger.info(
            "kernel_boot_started",
            previous_state=self._state.value,
        )

        self._state = KernelState.BOOTING

        try:
            # Subsystem initialization will be added incrementally.
            self._state = KernelState.READY

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
            raise RuntimeError(
                f"Cannot shut down kernel from state: {self._state.value}"
            )

        self._logger.info(
            "kernel_shutdown_started",
            previous_state=self._state.value,
        )

        self._state = KernelState.SHUTTING_DOWN

        try:
            # Subsystem shutdown will be added in reverse boot order.
            self._state = KernelState.STOPPED

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
