"""Plugin registration models."""

from dataclasses import dataclass

from eag.core import Plugin
from eag.plugins.policy import PluginPolicy


@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
)
class PluginRegistration:
    """Bind a plugin instance to its runtime policy."""

    plugin: Plugin
    policy: PluginPolicy
