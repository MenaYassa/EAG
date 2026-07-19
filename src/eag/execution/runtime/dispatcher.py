"""Execution dispatcher for EAG."""

from typing import Any

from eag.execution.models import ExecutionContext, ExecutionResult
from eag.execution.runtime.registry import ExecutorRegistry


class Dispatcher:
    """Routes operations to the appropriate executor via the registry."""

    def __init__(self, registry: ExecutorRegistry) -> None:
        self._registry = registry

    def dispatch(self, task: Any, context: ExecutionContext) -> ExecutionResult:
        operation = context.approved_plan.engineering_goal.operation
        executor = self._registry.find(operation)
        return executor.execute(operation, task, context)
