"""Kernel lifecycle states."""

from enum import Enum


class KernelState(str, Enum):
    """Possible lifecycle states of the EAG kernel."""

    CREATED = "created"
    BOOTING = "booting"
    READY = "ready"
    SHUTTING_DOWN = "shutting_down"
    STOPPED = "stopped"
    FAILED = "failed"