"""Plugin contract for EAG."""

from abc import ABC, abstractmethod
from enum import StrEnum

from eag.core.context import RuntimeContext
from eag.core.metadata import ComponentMetadata


class PluginState(StrEnum):
    """Lifecycle states of an EAG plugin."""

    CREATED = "created"
    LOADING = "loading"
    LOADED = "loaded"
    UNLOADING = "unloading"
    UNLOADED = "unloaded"
    FAILED = "failed"


class Plugin(ABC):
    """Base contract for EAG plugins."""

    def __init__(self) -> None:
        self._state = PluginState.CREATED

    @property
    @abstractmethod
    def metadata(self) -> ComponentMetadata:
        """Return plugin metadata."""

    @property
    def state(self) -> PluginState:
        """Return the current plugin state."""
        return self._state

    def _set_state(self, state: PluginState) -> None:
        """Set plugin lifecycle state.

        This method is intended for lifecycle coordinators such as the
        PluginManager. Plugin implementations should not manage their own
        lifecycle transitions.
        """
        self._state = state

    @abstractmethod
    def load(self, context: RuntimeContext) -> None:
        """Load the plugin into the EAG runtime."""

    @abstractmethod
    def unload(self, context: RuntimeContext) -> None:
        """Unload the plugin from the EAG runtime."""

    def health(self) -> bool:
        """Return whether the plugin is operational."""
        return self._state is PluginState.LOADED
