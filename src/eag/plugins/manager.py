"""Plugin lifecycle management for EAG."""

from eag.core import Plugin, PluginState, RuntimeContext
from eag.events import (
    PluginLoadCompleted,
    PluginLoadFailed,
    PluginLoadStarted,
    PluginRegistered,
    PluginUnloadCompleted,
    PluginUnloadFailed,
    PluginUnloadStarted,
)
from eag.logging import get_logger
from eag.plugins.errors import (
    PluginAlreadyRegisteredError,
    PluginLifecycleError,
    PluginNotFoundError,
)


class PluginManager:
    """Register plugins and coordinate their lifecycle."""

    def __init__(self, context: RuntimeContext) -> None:
        self._context = context
        self._plugins: dict[str, Plugin] = {}
        self._logger = get_logger(component="plugin_manager")

    def register(self, plugin: Plugin) -> None:
        """Register a plugin without loading it."""
        name = plugin.metadata.name

        if name in self._plugins:
            raise PluginAlreadyRegisteredError(f"Plugin '{name}' is already registered")

        self._plugins[name] = plugin

        self._context.event_bus.publish(
            PluginRegistered(
                plugin_name=name,
                plugin_version=plugin.metadata.version,
            )
        )

        self._logger.info(
            "plugin_registered",
            plugin_name=name,
            plugin_version=plugin.metadata.version,
        )

    def get(self, name: str) -> Plugin:
        """Return a registered plugin."""
        try:
            return self._plugins[name]
        except KeyError as exc:
            raise PluginNotFoundError(f"Plugin '{name}' is not registered") from exc

    def load(self, name: str) -> None:
        """Load a registered plugin."""
        plugin = self.get(name)

        if plugin.state is PluginState.LOADED:
            return

        if plugin.state not in {
            PluginState.CREATED,
            PluginState.UNLOADED,
        }:
            raise PluginLifecycleError(
                f"Cannot load plugin '{name}' from state '{plugin.state.value}'"
            )

        plugin._set_state(PluginState.LOADING)

        self._context.event_bus.publish(PluginLoadStarted(plugin_name=name))

        self._logger.info(
            "plugin_load_started",
            plugin_name=name,
        )

        try:
            plugin.load(self._context)
            plugin._set_state(PluginState.LOADED)

            self._context.event_bus.publish(PluginLoadCompleted(plugin_name=name))

            self._logger.info(
                "plugin_load_completed",
                plugin_name=name,
            )
        except Exception as exc:
            plugin._set_state(PluginState.FAILED)

            self._context.event_bus.publish(
                PluginLoadFailed(
                    plugin_name=name,
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )
            )

            self._logger.exception(
                "plugin_load_failed",
                plugin_name=name,
            )

            raise

    def unload(self, name: str) -> None:
        """Unload a loaded plugin."""
        plugin = self.get(name)

        if plugin.state is PluginState.UNLOADED:
            return

        if plugin.state is not PluginState.LOADED:
            raise PluginLifecycleError(
                f"Cannot unload plugin '{name}' from state '{plugin.state.value}'"
            )

        plugin._set_state(PluginState.UNLOADING)

        self._context.event_bus.publish(PluginUnloadStarted(plugin_name=name))

        self._logger.info(
            "plugin_unload_started",
            plugin_name=name,
        )

        try:
            plugin.unload(self._context)
            plugin._set_state(PluginState.UNLOADED)

            self._context.event_bus.publish(PluginUnloadCompleted(plugin_name=name))

            self._logger.info(
                "plugin_unload_completed",
                plugin_name=name,
            )
        except Exception as exc:
            plugin._set_state(PluginState.FAILED)

            self._context.event_bus.publish(
                PluginUnloadFailed(
                    plugin_name=name,
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )
            )

            self._logger.exception(
                "plugin_unload_failed",
                plugin_name=name,
            )

            raise

    def load_all(self) -> None:
        """Load all registered plugins in registration order."""
        for name in tuple(self._plugins):
            self.load(name)

    def unload_all(self) -> None:
        """Unload loaded plugins in reverse registration order."""
        for name in reversed(tuple(self._plugins)):
            plugin = self._plugins[name]

            if plugin.state is PluginState.LOADED:
                self.unload(name)

    def names(self) -> tuple[str, ...]:
        """Return registered plugin names."""
        return tuple(self._plugins)

    def count(self) -> int:
        """Return the number of registered plugins."""
        return len(self._plugins)
