"""Executor registry for EAG."""

from typing import Any

from eag.execution.errors import ExecutionError
from eag.execution.runtime.executor import Executor


class ExecutorRegistry:
    """Discovers and manages available operation executors."""

    def __init__(self) -> None:
        self._executors: dict[str, Executor] = {}

    def register(self, executor: Executor) -> None:
        name = executor.name
        if name in self._executors:
            raise ExecutionError(f"Executor '{name}' is already registered.")
        self._executors[name] = executor

    def find(self, operation: Any) -> Executor:
        """Find an executor that supports the given operation."""
        for executor in self._executors.values():
            if executor.supports(operation):
                return executor
        raise ExecutionError(f"No executor supports operation: {operation}")

    def list(self) -> tuple[Executor, ...]:
        return tuple(self._executors.values())
