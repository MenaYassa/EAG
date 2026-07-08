"""Plugin runtime health models."""

from dataclasses import dataclass
from enum import StrEnum

from eag.plugins.policy import PluginPolicy


class PluginRuntimeStatus(StrEnum):
    """Runtime availability state of a plugin."""

    REGISTERED = "registered"
    LOADED = "loaded"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
)
class PluginHealth:
    """Describe the runtime health of one plugin."""

    name: str
    policy: PluginPolicy
    status: PluginRuntimeStatus
    error_type: str | None = None
    error_message: str | None = None

    @property
    def available(self) -> bool:
        """Return whether the plugin is available."""
        return self.status is PluginRuntimeStatus.LOADED
