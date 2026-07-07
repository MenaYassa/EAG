"""EAG kernel lifecycle management."""

from eag.kernel.state import KernelState


class Kernel:
    """Coordinate the lifecycle of the EAG platform."""

    def __init__(self) -> None:
        self._state = KernelState.CREATED

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
            raise RuntimeError(
                f"Cannot boot kernel from state: {self._state.value}"
            )

        self._state = KernelState.BOOTING

        try:
            # Subsystem initialization will be added incrementally.
            self._state = KernelState.READY
        except Exception:
            self._state = KernelState.FAILED
            raise

    def shutdown(self) -> None:
        """Shut down the EAG kernel."""
        if self._state is KernelState.STOPPED:
            return

        if self._state is not KernelState.READY:
            raise RuntimeError(
                f"Cannot shut down kernel from state: {self._state.value}"
            )

        self._state = KernelState.SHUTTING_DOWN

        try:
            # Subsystem shutdown will be added in reverse boot order.
            self._state = KernelState.STOPPED
        except Exception:
            self._state = KernelState.FAILED
            raise