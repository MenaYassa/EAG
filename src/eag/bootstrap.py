"""Application bootstrap orchestration."""

from eag.config import Settings, load_settings
from eag.kernel import Kernel


def bootstrap(settings: Settings | None = None) -> Kernel:
    """Create and boot the EAG kernel."""
    resolved_settings = settings or load_settings()

    kernel = Kernel(settings=resolved_settings)
    kernel.boot()

    return kernel