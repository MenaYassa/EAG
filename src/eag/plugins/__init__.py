"""Plugin management for EAG."""

from eag.plugins.errors import (
    PluginAlreadyRegisteredError,
    PluginError,
    PluginLifecycleError,
    PluginNotFoundError,
)
from eag.plugins.manager import PluginManager

__all__ = [
    "PluginAlreadyRegisteredError",
    "PluginError",
    "PluginLifecycleError",
    "PluginManager",
    "PluginNotFoundError",
]
