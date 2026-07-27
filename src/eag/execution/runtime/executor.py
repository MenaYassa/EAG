"""Execution protocol for EAG."""

from typing import Any, Protocol, runtime_checkable

from eag.execution.models import ExecutionContext, ExecutionResult


@runtime_checkable
class Executor(Protocol):
    """The contract for an operation executor."""

    @property
    def name(self) -> str: ...

    def supports(self, operation: Any) -> bool: ...

    def execute(self, operation: Any, task: Any, context: ExecutionContext) -> ExecutionResult: ...
