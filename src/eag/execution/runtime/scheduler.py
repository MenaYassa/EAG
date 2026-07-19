"""Execution scheduler for EAG."""

from typing import Any


class Scheduler:
    """Determines the execution order of tasks."""

    def schedule(self, tasks: tuple[Any, ...]) -> tuple[Any, ...]:
        """Returns tasks in their dependency order.

        Currently, tasks are expected to be pre-sorted by the planner's
        dependency resolver, so this is a pass-through. Later sprints may
        introduce parallel scheduling or critical path optimization here.
        """
        return tasks
