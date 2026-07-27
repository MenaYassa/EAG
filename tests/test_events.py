"""Tests for the built-in command plugin."""

import sys
from pathlib import Path

import pytest
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
from eag.registry import Capability


def test_command_tool_capabilities(tmp_path: Path) -> None:
    executor = CommandExecutor(
        workspace=tmp_path,
        policy=permissive_python_policy(tmp_path),
    )
    tool = CommandTool(executor=executor)
    assert tool.capabilities == (COMMAND_RUN, COMMAND_WHICH, COMMAND_EVALUATE)


def test_command_tool_which(tmp_path: Path) -> None:
    executor = CommandExecutor(
        workspace=tmp_path,
        policy=permissive_python_policy(tmp_path),
    )
    tool = CommandTool(executor=executor)
    resolved = tool.which("python")
    assert resolved is not None
    assert resolved.is_absolute()


def test_command_tool_run(tmp_path: Path) -> None:
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


def test_tool_execute_which(tmp_path: Path) -> None:
    """Test tool.execute with COMMAND_WHICH capability."""
    executor = CommandExecutor(
        workspace=tmp_path,
        policy=permissive_python_policy(tmp_path),
    )
    tool = CommandTool(executor=executor)
    result = tool.execute(
        capability=COMMAND_WHICH,
        arguments={"executable": "python"},
    )
    assert result is not None
    assert isinstance(result, Path)
    assert result.is_absolute()


def test_tool_execute_run(tmp_path: Path) -> None:
    """Test tool.execute with COMMAND_RUN capability."""
    executor = CommandExecutor(
        workspace=tmp_path,
        policy=permissive_python_policy(tmp_path),
    )
    tool = CommandTool(executor=executor)
    result = tool.execute(
        capability=COMMAND_RUN,
        arguments={
            "executable": "python",
            "arguments": ("-c", "print('hello')"),
        },
    )
    assert result.succeeded is True
    assert result.stdout.strip() == "hello"


def test_tool_execute_working_directory(tmp_path: Path) -> None:
    """Test tool.execute with custom working directory."""
    executor = CommandExecutor(
        workspace=tmp_path,
        policy=permissive_python_policy(tmp_path),
    )
    tool = CommandTool(executor=executor)
    subdir = tmp_path / "subdir"
    subdir.mkdir()

    result = tool.execute(
        capability=COMMAND_RUN,
        arguments={
            "executable": "python",
            "arguments": ("-c", "import os; print(os.getcwd())"),
            "working_directory": str(subdir),
        },
    )
    assert result.succeeded is True
    assert str(subdir) in result.stdout


def test_tool_execute_timeout(tmp_path: Path) -> None:
    """Test tool.execute with a timeout."""
    executor = CommandExecutor(
        workspace=tmp_path,
        policy=permissive_python_policy(tmp_path),
    )
    tool = CommandTool(executor=executor)

    result = tool.execute(
        capability=COMMAND_RUN,
        arguments={
            "executable": "python",
            "arguments": ("-c", "import time; time.sleep(2)"),
            "timeout_seconds": 0.1,
        },
    )
    assert result.succeeded is False
    assert result.timed_out is True


def test_tool_execute_environment(tmp_path: Path) -> None:
    """Test tool.execute with custom environment variables."""
    executor = CommandExecutor(
        workspace=tmp_path,
        policy=permissive_python_policy(tmp_path),
    )
    tool = CommandTool(executor=executor)

    result = tool.execute(
        capability=COMMAND_RUN,
        arguments={
            "executable": "python",
            "arguments": (
                "-c",
                "import os; print(os.environ.get('TEST_VAR', 'missing'))",
            ),
            "environment": {"TEST_VAR": "hello"},
        },
    )
    assert result.succeeded is True
    assert result.stdout.strip() == "hello"


def test_tool_execute_unknown_capability(tmp_path: Path) -> None:
    """Test tool.execute with an unknown capability."""
    executor = CommandExecutor(
        workspace=tmp_path,
        policy=permissive_python_policy(tmp_path),
    )
    tool = CommandTool(executor=executor)
    unknown = Capability.parse("command.unknown")

    with pytest.raises(ValueError, match="Unsupported capability"):
        tool.execute(capability=unknown, arguments={})


def test_command_plugin_registers_capabilities(runtime_context: RuntimeContext) -> None:
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
        arguments=("-c", "print('through registry')"),
    )
    assert result.succeeded is True
    assert result.stdout.strip() == "through registry"


def test_command_plugin_unload_removes_capabilities(runtime_context: RuntimeContext) -> None:
    manager = PluginManager(context=runtime_context)
    manager.register(CommandPlugin())
    manager.load("command")
    manager.unload("command")

    registry = runtime_context.capability_registry
    assert not registry.has(COMMAND_RUN)
    assert not registry.has(COMMAND_WHICH)
