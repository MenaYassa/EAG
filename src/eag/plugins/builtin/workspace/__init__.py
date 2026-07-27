"""Built-in workspace intelligence plugin."""

from eag.plugins.builtin.workspace.models import (
    LanguageStat,
    SearchMatch,
    WorkspaceEntry,
    WorkspaceInspection,
    WorkspaceProfile,
)
from eag.plugins.builtin.workspace.plugin import (
    WorkspacePlugin,
)
from eag.plugins.builtin.workspace.tool import (
    WORKSPACE_INSPECT,
    WORKSPACE_PROFILE,
    WORKSPACE_SEARCH,
    WORKSPACE_TREE,
    WorkspaceTool,
)

__all__ = [
    "LanguageStat",
    "SearchMatch",
    "WORKSPACE_INSPECT",
    "WORKSPACE_PROFILE",
    "WORKSPACE_SEARCH",
    "WORKSPACE_TREE",
    "WorkspaceEntry",
    "WorkspaceInspection",
    "WorkspacePlugin",
    "WorkspaceProfile",
    "WorkspaceTool",
]
