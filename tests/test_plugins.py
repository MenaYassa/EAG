"""Tests for EAG plugin lifecycle management."""

import pytest

from eag.core import (
    ComponentMetadata,
    Plugin,
    PluginState,
    RuntimeContext,
)
from eag.events import (
    PluginLoadCompleted,
    PluginLoadFailed,
    PluginLoadStarted,
    PluginUnloadCompleted,
    PluginUnloadStarted,
)
from eag.plugins import (
    PluginAlreadyRegisteredError,
    PluginLifecycleError,
    PluginManager,
    PluginNotFoundError,
    PluginPolicy,
    PluginRuntimeStatus,
)


class ExamplePlugin(Plugin):
    """Plugin used for lifecycle tests."""

    def __init__(
        self,
        name: str = "example-plugin",
        fail_load: bool = False,
        fail_unload: bool = False,
        calls: list[str] | None = None,
    ) -> None:
        super().__init__()
        self._name = name
        self._fail_load = fail_load
        self._fail_unload = fail_unload
        self._calls = calls

    @property
    def metadata(self) -> ComponentMetadata:
        """Return plugin metadata."""
        return ComponentMetadata(
            name=self._name,
            version="1.0.0",
        )

    def load(
        self,
        context: RuntimeContext,
    ) -> None:
        """Load the test plugin."""
        del context

        if self._calls is not None:
            self._calls.append(f"load:{self._name}")

        if self._fail_load:
            raise RuntimeError("load failed")

    def unload(
        self,
        context: RuntimeContext,
    ) -> None:
        """Unload the test plugin."""
        del context

        if self._calls is not None:
            self._calls.append(f"unload:{self._name}")

        if self._fail_unload:
            raise RuntimeError("unload failed")


def test_register_plugin(
    plugin_manager: PluginManager,
) -> None:
    plugin = ExamplePlugin()

    plugin_manager.register(plugin)

    assert plugin_manager.count() == 1
    assert plugin_manager.names() == ("example-plugin",)
    assert plugin_manager.get("example-plugin") is plugin


def test_duplicate_plugin_is_rejected(
    plugin_manager: PluginManager,
) -> None:
    plugin_manager.register(ExamplePlugin())

    with pytest.raises(PluginAlreadyRegisteredError):
        plugin_manager.register(ExamplePlugin())


def test_unknown_plugin_raises(
    plugin_manager: PluginManager,
) -> None:
    with pytest.raises(PluginNotFoundError):
        plugin_manager.get("missing")


def test_load_plugin(
    plugin_manager: PluginManager,
) -> None:
    plugin = ExamplePlugin()
    plugin_manager.register(plugin)

    plugin_manager.load("example-plugin")

    assert plugin.state is PluginState.LOADED
    assert plugin.health() is True


def test_load_is_idempotent_when_loaded(
    plugin_manager: PluginManager,
) -> None:
    calls: list[str] = []
    plugin = ExamplePlugin(calls=calls)

    plugin_manager.register(plugin)
    plugin_manager.load("example-plugin")
    plugin_manager.load("example-plugin")

    assert calls == ["load:example-plugin"]


def test_unload_plugin(
    plugin_manager: PluginManager,
) -> None:
    plugin = ExamplePlugin()

    plugin_manager.register(plugin)
    plugin_manager.load("example-plugin")
    plugin_manager.unload("example-plugin")

    assert plugin.state is PluginState.UNLOADED
    assert plugin.health() is False


def test_load_failure_sets_failed_state(
    plugin_manager: PluginManager,
) -> None:
    plugin = ExamplePlugin(fail_load=True)
    plugin_manager.register(plugin)

    with pytest.raises(RuntimeError, match="load failed"):
        plugin_manager.load("example-plugin")

    assert plugin.state is PluginState.FAILED


def test_unload_failure_sets_failed_state(
    plugin_manager: PluginManager,
) -> None:
    plugin = ExamplePlugin(fail_unload=True)

    plugin_manager.register(plugin)
    plugin_manager.load("example-plugin")

    with pytest.raises(
        RuntimeError,
        match="unload failed",
    ):
        plugin_manager.unload("example-plugin")

    assert plugin.state is PluginState.FAILED


def test_cannot_load_failed_plugin(
    plugin_manager: PluginManager,
) -> None:
    plugin = ExamplePlugin(fail_load=True)
    plugin_manager.register(plugin)

    with pytest.raises(RuntimeError):
        plugin_manager.load("example-plugin")

    with pytest.raises(PluginLifecycleError):
        plugin_manager.load("example-plugin")


def test_load_all_uses_registration_order(
    plugin_manager: PluginManager,
) -> None:
    calls: list[str] = []

    plugin_manager.register(ExamplePlugin(name="first", calls=calls))
    plugin_manager.register(ExamplePlugin(name="second", calls=calls))

    plugin_manager.load_all()

    assert calls == [
        "load:first",
        "load:second",
    ]


def test_unload_all_uses_reverse_order(
    plugin_manager: PluginManager,
) -> None:
    calls: list[str] = []

    plugin_manager.register(ExamplePlugin(name="first", calls=calls))
    plugin_manager.register(ExamplePlugin(name="second", calls=calls))

    plugin_manager.load_all()
    calls.clear()

    plugin_manager.unload_all()

    assert calls == [
        "unload:second",
        "unload:first",
    ]


def test_load_publishes_lifecycle_events(
    runtime_context: RuntimeContext,
    plugin_manager: PluginManager,
) -> None:
    received: list[object] = []

    def on_started(
        event: PluginLoadStarted,
    ) -> None:
        received.append(event)

    def on_completed(
        event: PluginLoadCompleted,
    ) -> None:
        received.append(event)

    runtime_context.event_bus.subscribe(
        PluginLoadStarted,
        on_started,
    )
    runtime_context.event_bus.subscribe(
        PluginLoadCompleted,
        on_completed,
    )

    plugin_manager.register(ExamplePlugin())
    plugin_manager.load("example-plugin")

    assert len(received) == 2
    assert isinstance(received[0], PluginLoadStarted)
    assert isinstance(received[1], PluginLoadCompleted)


def test_load_failure_publishes_failure_event(
    runtime_context: RuntimeContext,
    plugin_manager: PluginManager,
) -> None:
    received: list[PluginLoadFailed] = []

    def handler(
        event: PluginLoadFailed,
    ) -> None:
        received.append(event)

    runtime_context.event_bus.subscribe(
        PluginLoadFailed,
        handler,
    )

    plugin_manager.register(ExamplePlugin(fail_load=True))

    with pytest.raises(RuntimeError):
        plugin_manager.load("example-plugin")

    assert len(received) == 1
    assert received[0].plugin_name == "example-plugin"
    assert received[0].error_type == "RuntimeError"
    assert received[0].error_message == "load failed"


def test_unload_publishes_lifecycle_events(
    runtime_context: RuntimeContext,
    plugin_manager: PluginManager,
) -> None:
    received: list[object] = []

    def on_started(
        event: PluginUnloadStarted,
    ) -> None:
        received.append(event)

    def on_completed(
        event: PluginUnloadCompleted,
    ) -> None:
        received.append(event)

    runtime_context.event_bus.subscribe(
        PluginUnloadStarted,
        on_started,
    )
    runtime_context.event_bus.subscribe(
        PluginUnloadCompleted,
        on_completed,
    )

    plugin_manager.register(ExamplePlugin())
    plugin_manager.load("example-plugin")

    received.clear()
    plugin_manager.unload("example-plugin")

    assert len(received) == 2
    assert isinstance(
        received[0],
        PluginUnloadStarted,
    )
    assert isinstance(
        received[1],
        PluginUnloadCompleted,
    )


def test_plugin_default_policy_is_required(
    plugin_manager: PluginManager,
) -> None:
    plugin_manager.register(ExamplePlugin())

    registration = plugin_manager.registration("example-plugin")

    assert registration.policy is PluginPolicy.REQUIRED


def test_optional_plugin_failure_is_recorded(
    plugin_manager: PluginManager,
) -> None:
    plugin_manager.register(
        ExamplePlugin(fail_load=True),
        policy=PluginPolicy.OPTIONAL,
    )

    plugin_manager.load_all()

    health = plugin_manager.health("example-plugin")

    assert health.status is PluginRuntimeStatus.UNAVAILABLE
    assert health.error_type == "RuntimeError"
    assert health.error_message == "load failed"


def test_required_plugin_failure_aborts_load_all(
    plugin_manager: PluginManager,
) -> None:
    plugin_manager.register(
        ExamplePlugin(fail_load=True),
        policy=PluginPolicy.REQUIRED,
    )

    with pytest.raises(
        RuntimeError,
        match="load failed",
    ):
        plugin_manager.load_all()

    health = plugin_manager.health("example-plugin")

    assert health.status is PluginRuntimeStatus.FAILED


def test_optional_failure_does_not_block_next_plugin(
    plugin_manager: PluginManager,
) -> None:
    calls: list[str] = []

    plugin_manager.register(
        ExamplePlugin(
            name="broken",
            fail_load=True,
            calls=calls,
        ),
        policy=PluginPolicy.OPTIONAL,
    )

    plugin_manager.register(
        ExamplePlugin(
            name="working",
            calls=calls,
        ),
        policy=PluginPolicy.REQUIRED,
    )

    plugin_manager.load_all()

    assert calls == [
        "load:broken",
        "load:working",
    ]

    assert plugin_manager.health("broken").status is PluginRuntimeStatus.UNAVAILABLE

    assert plugin_manager.health("working").status is PluginRuntimeStatus.LOADED


def test_manager_reports_degraded_state(
    plugin_manager: PluginManager,
) -> None:
    plugin_manager.register(
        ExamplePlugin(fail_load=True),
        policy=PluginPolicy.OPTIONAL,
    )

    plugin_manager.load_all()

    assert plugin_manager.degraded() is True


def test_manager_not_degraded_when_all_plugins_load(
    plugin_manager: PluginManager,
) -> None:
    plugin_manager.register(ExamplePlugin())

    plugin_manager.load_all()

    assert plugin_manager.degraded() is False
