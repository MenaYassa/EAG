"""Plugin base classes."""

from abc import ABC, abstractmethod
from enum import Enum, auto

from eag.core.context import RuntimeContext
from eag.core.metadata import ComponentMetadata


class PluginState(Enum):
    """Plugin lifecycle states."""

    CREATED = auto()
    LOADED = auto()
    UNLOADED = auto()


class Plugin(ABC):
    """Base class for all plugins."""

    def __init__(self) -> None:
        self._state = PluginState.CREATED

    @property
    def state(self) -> PluginState:
        """Return current plugin state."""
        return self._state

    @property
    @abstractmethod
    def metadata(self) -> ComponentMetadata:
        """Return component metadata."""

    @abstractmethod
    def load(self, context: RuntimeContext) -> None:
        """Load the plugin with the given context."""

    @abstractmethod
    def unload(self, context: RuntimeContext) -> None:
        """Unload the plugin."""

    def health(self) -> bool:
        """Return whether the plugin is healthy."""
        return self.state is PluginState.LOADED
