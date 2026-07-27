"""Execution protocol for EAG."""

from typing import Protocol, runtime_checkable

from eag.execution.models import (
    ExecutionContext,
    ExecutionReport,
    ExecutionResult,
    RollbackPoint,
)


@runtime_checkable
class ExecutionRuntime(Protocol):
    """The contract for an execution runtime."""

    def execute(self, context: ExecutionContext) -> ExecutionReport: ...

    def validate(self, context: ExecutionContext) -> bool: ...

    def checkpoint(self, context: ExecutionContext, name: str) -> RollbackPoint: ...

    def rollback(
        self, context: ExecutionContext, rollback_point: RollbackPoint
    ) -> ExecutionResult: ...

    def dry_run(self, context: ExecutionContext) -> ExecutionReport: ...

    def explain(self, report: ExecutionReport) -> str: ...
