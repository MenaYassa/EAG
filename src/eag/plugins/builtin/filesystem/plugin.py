"""Filesystem plugin for EAG."""

from eag.core import (
    ComponentMetadata,
    Plugin,
    RuntimeContext,
)
from eag.plugins.builtin.filesystem.tool import (
    FILESYSTEM_EXISTS,
    FILESYSTEM_LIST,
    FILESYSTEM_READ,
    FilesystemTool,
)
from eag.registry import CapabilityRegistration


class FilesystemPlugin(Plugin):
    """Register safe read-only filesystem capabilities."""

    PROVIDER_NAME = "builtin-filesystem"

    def __init__(self) -> None:
        super().__init__()
        self._tool: FilesystemTool | None = None

    @property
    def metadata(self) -> ComponentMetadata:
        """Return filesystem plugin metadata."""
        return ComponentMetadata(
            name="filesystem",
            version="0.1.0",
            description=("Safe read-only workspace filesystem access"),
        )

    def load(
        self,
        context: RuntimeContext,
    ) -> None:
        """Register filesystem capabilities."""
        tool = FilesystemTool(
            workspace=context.settings.kernel.workspace,
        )

        context.capability_registry.register(
            CapabilityRegistration(
                capability=FILESYSTEM_READ,
                provider=self.PROVIDER_NAME,
                handler=tool.read,
            )
        )

        context.capability_registry.register(
            CapabilityRegistration(
                capability=FILESYSTEM_LIST,
                provider=self.PROVIDER_NAME,
                handler=tool.list_directory,
            )
        )

        context.capability_registry.register(
            CapabilityRegistration(
                capability=FILESYSTEM_EXISTS,
                provider=self.PROVIDER_NAME,
                handler=tool.exists,
            )
        )

        self._tool = tool

    def unload(
        self,
        context: RuntimeContext,
    ) -> None:
        """Unregister filesystem capabilities."""
        for capability in (
            FILESYSTEM_READ,
            FILESYSTEM_LIST,
            FILESYSTEM_EXISTS,
        ):
            context.capability_registry.unregister(
                capability,
                provider=self.PROVIDER_NAME,
            )

        self._tool = None
