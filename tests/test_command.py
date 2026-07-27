"""Tests for the built-in command plugin."""

import sys
from pathlib import Path

from helpers import permissive_python_policy

from eag.core import RuntimeContext
from eag.execution import CommandExecutor
from eag.plugins import PluginManager
from eag.plugins.builtin.command import (
    COMMAND_EVALUATE,
    COMMAND_RUN,
    COMMAND_WHICH,
    CommandPlugin,
    CommandTool,
)


def test_command_tool_capabilities(
    tmp_path: Path,
) -> None:
    executor = CommandExecutor(
        workspace=tmp_path,
        policy=permissive_python_policy(tmp_path),
    )
    tool = CommandTool(executor=executor)

    # Now we have 3 capabilities
    assert tool.capabilities == (
        COMMAND_RUN,
        COMMAND_WHICH,
        COMMAND_EVALUATE,
    )


def test_command_tool_which(
    tmp_path: Path,
) -> None:
    executor = CommandExecutor(
        workspace=tmp_path,
        policy=permissive_python_policy(tmp_path),
    )
    tool = CommandTool(executor=executor)

    resolved = tool.which("python")
    assert resolved is not None
    assert resolved.is_absolute()


def test_command_tool_run(
    tmp_path: Path,
) -> None:
    executor = CommandExecutor(
        workspace=tmp_path,
        policy=permissive_python_policy(tmp_path),
    )
    tool = CommandTool(executor=executor)

    result = tool.run(
        executable="python",
        arguments=("-c", "print('command plugin')"),
    )

    assert result.succeeded is True
    assert result.stdout.strip() == "command plugin"


def test_command_plugin_registers_capabilities(
    runtime_context: RuntimeContext,
) -> None:
    manager = PluginManager(context=runtime_context)

    manager.register(CommandPlugin())

    manager.load("command")

    registry = runtime_context.capability_registry

    assert registry.has(COMMAND_RUN)
    assert registry.has(COMMAND_WHICH)


def test_resolved_command_run_executes(
    runtime_context: RuntimeContext,
    monkeypatch,
) -> None:
    workspace = runtime_context.settings.kernel.workspace
    executor = CommandExecutor(
        workspace=workspace,
        policy=permissive_python_policy(workspace),
    )

    class PermissiveCommandTool(CommandTool):
        def __init__(self, *args, **kwargs):
            kwargs["executor"] = executor
            super().__init__(*args, **kwargs)

    plugin_module = sys.modules[CommandPlugin.__module__]
    monkeypatch.setattr(plugin_module, "CommandTool", PermissiveCommandTool)

    manager = PluginManager(context=runtime_context)

    manager.register(CommandPlugin())

    manager.load("command")

    registration = runtime_context.capability_registry.resolve(COMMAND_RUN)

    result = registration.handler(
        executable="python",
        arguments=(
            "-c",
            "print('through registry')",
        ),
    )

    assert result.succeeded is True
    assert result.stdout.strip() == "through registry"


def test_command_plugin_unload_removes_capabilities(
    runtime_context: RuntimeContext,
) -> None:
    manager = PluginManager(context=runtime_context)

    manager.register(CommandPlugin())

    manager.load("command")
    manager.unload("command")

    registry = runtime_context.capability_registry

    assert not registry.has(COMMAND_RUN)
    assert not registry.has(COMMAND_WHICH)
