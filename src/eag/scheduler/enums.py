"""Scheduler domain vocabulary for EAG."""

from enum import StrEnum


class SchedulingPolicy(StrEnum):
    """Policies for assigning workers to tasks."""

    BEST_CAPABILITY = "best_capability"
    FIRST_AVAILABLE = "first_available"
    LOWEST_LOAD = "lowest_load"
    ROUND_ROBIN = "round_robin"
    PRIORITY_FIRST = "priority_first"
