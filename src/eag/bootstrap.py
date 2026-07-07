"""EAG bootstrap: initialise the kernel and platform state."""

from pathlib import Path

from eag.config import load_settings
from eag.events import EventBus
from eag.kernel import Kernel
from eag.logging import get_logger


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

    # Create event bus and kernel.
    event_bus = EventBus()
    kernel = Kernel(
        settings=resolved_settings,
        event_bus=event_bus,
    )
    kernel.boot()

    logger.info(
        "bootstrap_completed",
        kernel_state=kernel.state.value,
    )

    return kernel
