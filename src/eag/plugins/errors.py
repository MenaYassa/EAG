"""Plugin management errors for EAG."""


class PluginError(Exception):
    """Base exception for plugin management failures."""


class PluginAlreadyRegisteredError(PluginError):
    """Raised when a plugin name is already registered."""


class PluginNotFoundError(PluginError):
    """Raised when a requested plugin is not registered."""


class PluginLifecycleError(PluginError):
    """Raised when a plugin lifecycle transition is invalid."""
