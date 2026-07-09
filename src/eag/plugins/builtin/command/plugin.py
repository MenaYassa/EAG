"""Command execution plugin for EAG."""

from eag.core import (
    ComponentMetadata,
    Plugin,
    RuntimeContext,
)
from eag.execution import CommandExecutor
from eag.plugins.builtin.command.tool import (
    COMMAND_RUN,
    COMMAND_WHICH,
    CommandTool,
)
from eag.registry import CapabilityRegistration


class CommandPlugin(Plugin):
    """Register safe command execution capabilities."""

    PROVIDER_NAME = "builtin-command"

    def __init__(self) -> None:
        super().__init__()
        self._tool: CommandTool | None = None

    @property
    def metadata(self) -> ComponentMetadata:
        """Return command plugin metadata."""
        return ComponentMetadata(
            name="command",
            version="0.1.0",
            description=("Safe structured command execution"),
        )

    def load(
        self,
        context: RuntimeContext,
    ) -> None:
        """Register command capabilities."""
        executor = CommandExecutor(
            workspace=(context.settings.kernel.workspace),
            event_bus=context.event_bus,
        )

        tool = CommandTool(executor=executor)

        registrations = (
            (
                COMMAND_RUN,
                tool.run,
            ),
            (
                COMMAND_WHICH,
                tool.which,
            ),
        )

        for capability, handler in registrations:
            context.capability_registry.register(
                CapabilityRegistration(
                    capability=capability,
                    provider=self.PROVIDER_NAME,
                    handler=handler,
                )
            )

        self._tool = tool

    def unload(
        self,
        context: RuntimeContext,
    ) -> None:
        """Unregister command capabilities."""
        for capability in (
            COMMAND_RUN,
            COMMAND_WHICH,
        ):
            context.capability_registry.unregister(
                capability,
                provider=self.PROVIDER_NAME,
            )

        self._tool = None
