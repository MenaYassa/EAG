"""Git plugin for EAG."""

from eag.core import (
    ComponentMetadata,
    Plugin,
    RuntimeContext,
)
from eag.plugins.builtin.git.tool import (
    GIT_BRANCH,
    GIT_DIFF,
    GIT_LOG,
    GIT_STATUS,
    GitTool,
)
from eag.registry import CapabilityRegistration


class GitPlugin(Plugin):
    """Register read-only Git capabilities."""

    PROVIDER_NAME = "builtin-git"

    def __init__(self) -> None:
        super().__init__()
        self._tool: GitTool | None = None

    @property
    def metadata(self) -> ComponentMetadata:
        """Return Git plugin metadata."""
        return ComponentMetadata(
            name="git",
            version="0.1.0",
            description=("Read-only Git repository capabilities"),
        )

    def load(
        self,
        context: RuntimeContext,
    ) -> None:
        """Register Git capabilities."""
        tool = GitTool(
            workspace=context.settings.kernel.workspace,
        )

        registrations = (
            (
                GIT_STATUS,
                tool.status,
            ),
            (
                GIT_DIFF,
                tool.diff,
            ),
            (
                GIT_BRANCH,
                tool.branch,
            ),
            (
                GIT_LOG,
                tool.log,
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
        """Unregister Git capabilities."""
        for capability in (
            GIT_STATUS,
            GIT_DIFF,
            GIT_BRANCH,
            GIT_LOG,
        ):
            context.capability_registry.unregister(
                capability,
                provider=self.PROVIDER_NAME,
            )

        self._tool = None
