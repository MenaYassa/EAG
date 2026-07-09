"""Tests for the built-in command plugin."""

from pathlib import Path

from eag.core import RuntimeContext
from eag.execution import CommandExecutor
from eag.plugins import PluginManager
from eag.plugins.builtin.command import (
    COMMAND_RUN,
    COMMAND_WHICH,
    CommandPlugin,
    CommandTool,
)


def test_command_tool_capabilities(
    tmp_path: Path,
) -> None:
    executor = CommandExecutor(workspace=tmp_path)

    tool = CommandTool(executor=executor)

    assert tool.capabilities == (
        COMMAND_RUN,
        COMMAND_WHICH,
    )


def test_command_tool_which(
    tmp_path: Path,
) -> None:
    executor = CommandExecutor(workspace=tmp_path)

    tool = CommandTool(executor=executor)

    resolved = tool.which("python")

    assert resolved is not None
    assert resolved.is_absolute()


def test_command_tool_run(
    tmp_path: Path,
) -> None:
    executor = CommandExecutor(workspace=tmp_path)

    tool = CommandTool(executor=executor)

    result = tool.run(
        executable="python",
        arguments=(
            "-c",
            "print('command plugin')",
        ),
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
) -> None:
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
