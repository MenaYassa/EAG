"""Plugin management for EAG."""

from eag.plugins.errors import (
    PluginAlreadyRegisteredError,
    PluginError,
    PluginLifecycleError,
    PluginNotFoundError,
)
from eag.plugins.health import (
    PluginHealth,
    PluginRuntimeStatus,
)
from eag.plugins.manager import PluginManager
from eag.plugins.policy import PluginPolicy
from eag.plugins.registration import (
    PluginRegistration,
)

__all__ = [
    "PluginAlreadyRegisteredError",
    "PluginError",
    "PluginLifecycleError",
    "PluginManager",
    "PluginNotFoundError",
    "PluginHealth",
    "PluginPolicy",
    "PluginRegistration",
    "PluginRuntimeStatus",
]
