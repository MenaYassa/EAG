"""Tests for the EAG kernel lifecycle."""

import pytest

from eag.config import Settings
from eag.kernel import Kernel, KernelState


@pytest.fixture
def settings() -> Settings:
    """Create test settings."""
    return Settings(
        kernel={
            "environment": "testing",
        }
    )


def test_kernel_initial_state(settings: Settings) -> None:
    kernel = Kernel(settings=settings)

    assert kernel.state is KernelState.CREATED
    assert kernel.is_ready is False


def test_kernel_boot(settings: Settings) -> None:
    kernel = Kernel(settings=settings)

    kernel.boot()

    assert kernel.state is KernelState.READY
    assert kernel.is_ready is True


def test_kernel_boot_is_idempotent_when_ready(
    settings: Settings,
) -> None:
    kernel = Kernel(settings=settings)

    kernel.boot()
    kernel.boot()

    assert kernel.state is KernelState.READY


def test_kernel_shutdown(settings: Settings) -> None:
    kernel = Kernel(settings=settings)

    kernel.boot()
    kernel.shutdown()

    assert kernel.state is KernelState.STOPPED
    assert kernel.is_ready is False


def test_kernel_can_restart_after_shutdown(
    settings: Settings,
) -> None:
    kernel = Kernel(settings=settings)

    kernel.boot()
    kernel.shutdown()
    kernel.boot()

    assert kernel.state is KernelState.READY


def test_kernel_cannot_shutdown_before_boot(
    settings: Settings,
) -> None:
    kernel = Kernel(settings=settings)

    with pytest.raises(RuntimeError):
        kernel.shutdown()