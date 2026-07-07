"""Tests for the EAG kernel lifecycle."""

import pytest

from eag.kernel import Kernel, KernelState


def test_kernel_initial_state() -> None:
    kernel = Kernel()

    assert kernel.state is KernelState.CREATED
    assert kernel.is_ready is False


def test_kernel_boot() -> None:
    kernel = Kernel()

    kernel.boot()

    assert kernel.state is KernelState.READY
    assert kernel.is_ready is True


def test_kernel_boot_is_idempotent_when_ready() -> None:
    kernel = Kernel()

    kernel.boot()
    kernel.boot()

    assert kernel.state is KernelState.READY


def test_kernel_shutdown() -> None:
    kernel = Kernel()

    kernel.boot()
    kernel.shutdown()

    assert kernel.state is KernelState.STOPPED
    assert kernel.is_ready is False


def test_kernel_can_restart_after_shutdown() -> None:
    kernel = Kernel()

    kernel.boot()
    kernel.shutdown()
    kernel.boot()

    assert kernel.state is KernelState.READY


def test_kernel_cannot_shutdown_before_boot() -> None:
    kernel = Kernel()

    with pytest.raises(RuntimeError):
        kernel.shutdown()
