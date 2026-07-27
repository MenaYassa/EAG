"""Built-in filesystem plugin."""

from eag.plugins.builtin.filesystem.errors import (
    FilesystemError,
    UnsupportedFilesystemCapabilityError,
    WorkspaceBoundaryError,
)
from eag.plugins.builtin.filesystem.plugin import (
    FilesystemPlugin,
)
from eag.plugins.builtin.filesystem.tool import (
    FILESYSTEM_EXISTS,
    FILESYSTEM_LIST,
    FILESYSTEM_READ,
    FilesystemTool,
)

__all__ = [
    "FILESYSTEM_EXISTS",
    "FILESYSTEM_LIST",
    "FILESYSTEM_READ",
    "FilesystemError",
    "FilesystemPlugin",
    "FilesystemTool",
    "UnsupportedFilesystemCapabilityError",
    "WorkspaceBoundaryError",
]
