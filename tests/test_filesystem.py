"""Tests for the built-in filesystem plugin."""

from pathlib import Path

import pytest

from eag.core import RuntimeContext
from eag.plugins import PluginManager
from eag.plugins.builtin.filesystem import (
    FILESYSTEM_EXISTS,
    FILESYSTEM_LIST,
    FILESYSTEM_READ,
    FilesystemPlugin,
    FilesystemTool,
    WorkspaceBoundaryError,
)
from eag.plugins.builtin.filesystem.errors import (
    UnsupportedFilesystemCapabilityError,
)
from eag.registry import Capability


def test_filesystem_tool_capabilities(
    tmp_path: Path,
) -> None:
    tool = FilesystemTool(workspace=tmp_path)

    assert tool.capabilities == (
        FILESYSTEM_READ,
        FILESYSTEM_LIST,
        FILESYSTEM_EXISTS,
    )


def test_read_file(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "example.txt"
    file_path.write_text(
        "EAG is eager for knowledge",
        encoding="utf-8",
    )

    tool = FilesystemTool(workspace=tmp_path)

    result = tool.read("example.txt")

    assert result == "EAG is eager for knowledge"


def test_read_nested_file(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "src"
    directory.mkdir()

    file_path = directory / "main.py"
    file_path.write_text(
        "print('hello')",
        encoding="utf-8",
    )

    tool = FilesystemTool(workspace=tmp_path)

    result = tool.read("src/main.py")

    assert result == "print('hello')"


def test_list_directory(
    tmp_path: Path,
) -> None:
    (tmp_path / "b.txt").touch()
    (tmp_path / "a.txt").touch()
    (tmp_path / "src").mkdir()

    tool = FilesystemTool(workspace=tmp_path)

    result = tool.list_directory()

    assert result == (
        "a.txt",
        "b.txt",
        "src",
    )


def test_exists(
    tmp_path: Path,
) -> None:
    (tmp_path / "example.txt").touch()

    tool = FilesystemTool(workspace=tmp_path)

    assert tool.exists("example.txt") is True
    assert tool.exists("missing.txt") is False


def test_path_traversal_is_rejected(
    tmp_path: Path,
) -> None:
    tool = FilesystemTool(workspace=tmp_path)

    with pytest.raises(WorkspaceBoundaryError):
        tool.read("../outside.txt")


def test_absolute_path_escape_is_rejected(
    tmp_path: Path,
) -> None:
    tool = FilesystemTool(workspace=tmp_path)

    with pytest.raises(WorkspaceBoundaryError):
        tool.exists("/etc/passwd")


def test_symlink_escape_is_rejected(
    tmp_path: Path,
) -> None:
    outside = tmp_path.parent / "outside.txt"
    outside.write_text(
        "outside",
        encoding="utf-8",
    )

    link = tmp_path / "escape.txt"
    link.symlink_to(outside)

    tool = FilesystemTool(workspace=tmp_path)

    with pytest.raises(WorkspaceBoundaryError):
        tool.read("escape.txt")


def test_execute_read_capability(
    tmp_path: Path,
) -> None:
    (tmp_path / "example.txt").write_text(
        "content",
        encoding="utf-8",
    )

    tool = FilesystemTool(workspace=tmp_path)

    result = tool.execute(
        FILESYSTEM_READ,
        {"path": "example.txt"},
    )

    assert result == "content"


def test_unsupported_capability(
    tmp_path: Path,
) -> None:
    tool = FilesystemTool(workspace=tmp_path)

    with pytest.raises(UnsupportedFilesystemCapabilityError):
        tool.execute(
            Capability.parse("git.status"),
            {},
        )


def test_plugin_registers_capabilities(
    runtime_context: RuntimeContext,
    plugin_manager: PluginManager,
) -> None:
    plugin_manager.register(FilesystemPlugin())

    plugin_manager.load("filesystem")

    registry = runtime_context.capability_registry

    assert registry.has(FILESYSTEM_READ)
    assert registry.has(FILESYSTEM_LIST)
    assert registry.has(FILESYSTEM_EXISTS)


def test_registered_read_handler_executes(
    tmp_path: Path,
    runtime_context: RuntimeContext,
    plugin_manager: PluginManager,
) -> None:
    test_file = tmp_path / "knowledge.txt"
    test_file.write_text(
        "EAG knows something.",
        encoding="utf-8",
    )

    settings = runtime_context.settings.model_copy(
        update={
            "kernel": (
                runtime_context.settings.kernel.model_copy(
                    update={
                        "workspace": tmp_path,
                    }
                )
            )
        }
    )

    context = RuntimeContext(
        settings=settings,
        event_bus=runtime_context.event_bus,
        capability_registry=runtime_context.capability_registry,
        approval_manager=runtime_context.approval_manager,
        approval_coordinator=runtime_context.approval_coordinator,
    )

    manager = PluginManager(
        context=context,
    )

    manager.register(FilesystemPlugin())

    manager.load("filesystem")

    registration = context.capability_registry.resolve(FILESYSTEM_READ)

    result = registration.handler("knowledge.txt")

    assert result == "EAG knows something."


def test_plugin_unregisters_capabilities(
    runtime_context: RuntimeContext,
    plugin_manager: PluginManager,
) -> None:
    plugin_manager.register(FilesystemPlugin())

    plugin_manager.load("filesystem")
    plugin_manager.unload("filesystem")

    registry = runtime_context.capability_registry

    assert registry.has(FILESYSTEM_READ) is False
    assert registry.has(FILESYSTEM_LIST) is False
    assert registry.has(FILESYSTEM_EXISTS) is False
