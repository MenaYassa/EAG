"""Built-in command execution plugin."""

from eag.plugins.builtin.command.plugin import CommandPlugin
from eag.plugins.builtin.command.tool import (
    COMMAND_EVALUATE,
    COMMAND_RUN,
    COMMAND_WHICH,
    CommandTool,
)

__all__ = [
    "COMMAND_RUN",
    "COMMAND_WHICH",
    "COMMAND_EVALUATE",
    "CommandPlugin",
    "CommandTool",
]
