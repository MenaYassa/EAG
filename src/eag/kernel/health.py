"""Runtime health models for EAG."""

from dataclasses import dataclass

from eag.kernel.state import KernelState
from eag.plugins import PluginHealth


@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
)
class RuntimeHealth:
    """Describe current EAG runtime health."""

    kernel_state: KernelState
    plugins: tuple[PluginHealth, ...]
    capability_count: int

    @property
    def degraded(self) -> bool:
        """Return whether runtime is degraded."""
        return self.kernel_state is KernelState.READY_DEGRADED

    @property
    def healthy(self) -> bool:
        """Return whether runtime is operational."""
        return self.kernel_state in {
            KernelState.READY,
            KernelState.READY_DEGRADED,
        }

    @property
    def available_plugins(
        self,
    ) -> tuple[PluginHealth, ...]:
        """Return available plugins."""
        return tuple(plugin for plugin in self.plugins if plugin.available)

    @property
    def unavailable_plugins(
        self,
    ) -> tuple[PluginHealth, ...]:
        """Return unavailable plugins."""
        return tuple(plugin for plugin in self.plugins if not plugin.available)
