"""Tests for EAG core contracts."""

from collections.abc import Mapping
from typing import Any

import pytest

from eag.config import Settings
from eag.core import (
    ComponentMetadata,
    Plugin,
    PluginState,
    Provider,
    RuntimeContext,
    Tool,
    Worker,
)
from eag.registry import Capability


class ExampleTool(Tool):
    """Concrete tool used for contract tests."""

    @property
    def metadata(self) -> ComponentMetadata:
        return ComponentMetadata(
            name="example-tool",
            version="1.0.0",
        )

    @property
    def capabilities(self) -> tuple[Capability, ...]:
        return (Capability.parse("example.run"),)

    def execute(
        self,
        capability: Capability,
        arguments: Mapping[str, Any],
    ) -> Any:
        del capability
        return arguments["value"]


class ExampleProvider(Provider):
    @property
    def metadata(self) -> ComponentMetadata:
        return ComponentMetadata(
            name="example-provider",
            version="1.0.0",
        )

    def health(self) -> bool:
        return True


class ExampleWorker(Worker):
    @property
    def metadata(self) -> ComponentMetadata:
        return ComponentMetadata(
            name="example-worker",
            version="1.0.0",
        )

    def run(self, task: Any) -> Any:
        return task


class ExamplePlugin(Plugin):
    @property
    def metadata(self) -> ComponentMetadata:
        return ComponentMetadata(
            name="example-plugin",
            version="1.0.0",
        )

    def load(self, context: RuntimeContext) -> None:
        del context
        self._state = PluginState.LOADED

    def unload(self, context: RuntimeContext) -> None:
        del context
        self._state = PluginState.UNLOADED


def test_component_metadata() -> None:
    metadata = ComponentMetadata(
        name="filesystem",
        version="1.0.0",
        description="Filesystem capabilities",
    )
    assert metadata.name == "filesystem"
    assert metadata.version == "1.0.0"


def test_empty_component_name_is_rejected() -> None:
    with pytest.raises(ValueError):
        ComponentMetadata(name=" ", version="1.0.0")


def test_empty_component_version_is_rejected() -> None:
    with pytest.raises(ValueError):
        ComponentMetadata(name="example", version=" ")


def test_tool_contract() -> None:
    tool = ExampleTool()
    capability = Capability.parse("example.run")
    result = tool.execute(capability, {"value": 42})
    assert result == 42
    assert tool.health() is True
    assert tool.capabilities == (capability,)


def test_provider_contract() -> None:
    provider = ExampleProvider()
    assert provider.health() is True
    assert provider.metadata.name == "example-provider"


def test_worker_contract() -> None:
    worker = ExampleWorker()
    assert worker.run("task") == "task"
    assert worker.metadata.name == "example-worker"


def test_plugin_initial_state() -> None:
    plugin = ExamplePlugin()
    assert plugin.state is PluginState.CREATED
    assert plugin.health() is False


def test_runtime_context_is_immutable(
    runtime_context: RuntimeContext,
) -> None:
    with pytest.raises(AttributeError):
        runtime_context.settings = Settings()  # type: ignore[misc]
