"""Workspace intelligence plugin for EAG."""

from eag.core import (
    ComponentMetadata,
    Plugin,
    RuntimeContext,
)
from eag.plugins.builtin.workspace.tool import (
    WORKSPACE_INSPECT,
    WORKSPACE_PROFILE,
    WORKSPACE_SEARCH,
    WORKSPACE_TREE,
    WorkspaceTool,
)
from eag.registry import CapabilityRegistration


class WorkspacePlugin(Plugin):
    """Register workspace intelligence capabilities."""

    PROVIDER_NAME = "builtin-workspace"

    def __init__(self) -> None:
        super().__init__()
        self._tool: WorkspaceTool | None = None

    @property
    def metadata(self) -> ComponentMetadata:
        """Return workspace plugin metadata."""
        return ComponentMetadata(
            name="workspace",
            version="0.1.0",
            description=("Workspace inspection, profiling, and search"),
        )

    def load(
        self,
        context: RuntimeContext,
    ) -> None:
        """Register workspace capabilities."""
        tool = WorkspaceTool(
            workspace=context.settings.kernel.workspace,
        )

        registrations = (
            (
                WORKSPACE_TREE,
                tool.tree,
            ),
            (
                WORKSPACE_SEARCH,
                tool.search,
            ),
            (
                WORKSPACE_PROFILE,
                tool.profile,
            ),
            (
                WORKSPACE_INSPECT,
                tool.inspect,
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
        """Unregister workspace capabilities."""
        for capability in (
            WORKSPACE_TREE,
            WORKSPACE_SEARCH,
            WORKSPACE_PROFILE,
            WORKSPACE_INSPECT,
        ):
            context.capability_registry.unregister(
                capability,
                provider=self.PROVIDER_NAME,
            )

        self._tool = None
