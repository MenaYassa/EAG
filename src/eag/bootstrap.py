"""Application bootstrap orchestration."""

from eag.kernel import Kernel


def bootstrap() -> Kernel:
    """Create and boot the EAG kernel."""
    kernel = Kernel()
    kernel.boot()
    return kernel