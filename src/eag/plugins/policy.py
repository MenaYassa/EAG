"""Plugin policy definitions for EAG."""

from enum import StrEnum


class PluginPolicy(StrEnum):
    """Define how plugin load failures affect runtime boot."""

    REQUIRED = "required"
    OPTIONAL = "optional"
