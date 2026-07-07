"""Application bootstrap orchestration."""

from eag.config import Settings, load_settings
from eag.kernel import Kernel
from eag.logging import configure_logging, get_logger


def bootstrap(settings: Settings | None = None) -> Kernel:
    """Create and boot the EAG kernel."""
    resolved_settings = settings or load_settings()

    configure_logging(resolved_settings.logging)

    logger = get_logger(component="bootstrap")

    logger.info(
        "bootstrap_started",
        environment=resolved_settings.kernel.environment,
        workspace=str(resolved_settings.kernel.workspace),
    )

    kernel = Kernel(settings=resolved_settings)
    kernel.boot()

    logger.info(
        "bootstrap_completed",
        kernel_state=kernel.state.value,
    )

    return kernel