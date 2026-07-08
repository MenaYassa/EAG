"""EAG bootstrap: initialise the kernel and platform state."""

from pathlib import Path

from eag.config import load_settings
from eag.core import RuntimeContext
from eag.events import EventBus
from eag.kernel import Kernel
from eag.logging import get_logger
from eag.plugins import (
    PluginManager,
    PluginPolicy,
)
from eag.plugins.builtin.filesystem import (
    FilesystemPlugin,
)
from eag.plugins.builtin.git import GitPlugin
from eag.plugins.builtin.workspace import (
    WorkspacePlugin,
)
from eag.registry import CapabilityRegistry


def bootstrap(config_path: Path | None = None) -> Kernel:
    """Bootstrap the EAG platform.

    Args:
        config_path: Optional path to a configuration file.

    Returns:
        A booted Kernel instance.
    """
    logger = get_logger(component="bootstrap")

    # Load and resolve settings.
    resolved_settings = load_settings()

    logger.info(
        "bootstrap_started",
        environment=resolved_settings.kernel.environment,
        workspace=str(resolved_settings.kernel.workspace),
    )

    # Create infrastructure.
    event_bus = EventBus()
    capability_registry = CapabilityRegistry(event_bus=event_bus)

    # Create runtime context.
    runtime_context = RuntimeContext(
        settings=resolved_settings,
        event_bus=event_bus,
        capability_registry=capability_registry,
    )

    # Create plugin manager with the full context.
    plugin_manager = PluginManager(context=runtime_context)

    # Create and boot the kernel.
    plugin_manager = PluginManager(
        context=runtime_context,
    )

    plugin_manager.register(
        FilesystemPlugin(),
        policy=PluginPolicy.REQUIRED,
    )

    plugin_manager.register(
        WorkspacePlugin(),
        policy=PluginPolicy.REQUIRED,
    )

    plugin_manager.register(
        GitPlugin(),
        policy=PluginPolicy.OPTIONAL,
    )

    kernel = Kernel(
        context=runtime_context,
        plugin_manager=plugin_manager,
    )
    kernel.boot()

    logger.info(
        "bootstrap_completed",
        kernel_state=kernel.state.value,
    )

    return kernel
