"""Command execution plugin for EAG."""

from eag.core import (
    ComponentMetadata,
    Plugin,
    PluginState,
    RuntimeContext,
)
from eag.execution import CommandExecutor
from eag.plugins.builtin.command.tool import (
    COMMAND_EVALUATE,
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
            description="Safe structured command execution",
        )

    def load(
        self,
        context: RuntimeContext,
    ) -> None:
        """Register command capabilities."""
        executor = CommandExecutor(
            workspace=context.settings.kernel.workspace,
            event_bus=context.event_bus,
            approval_manager=context.approval_manager,
        )

        tool = CommandTool(executor=executor)

        registrations = (
            (COMMAND_RUN, tool.run),
            (COMMAND_WHICH, tool.which),
            (COMMAND_EVALUATE, tool.evaluate),
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
        self._state = PluginState.LOADED

    def unload(
        self,
        context: RuntimeContext,
    ) -> None:
        """Unregister command capabilities."""
        for capability in (
            COMMAND_RUN,
            COMMAND_WHICH,
            COMMAND_EVALUATE,
        ):
            context.capability_registry.unregister(
                capability,
                provider=self.PROVIDER_NAME,
            )

        self._tool = None
        self._state = PluginState.UNLOADED
