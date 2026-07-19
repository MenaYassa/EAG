"""Dummy executor for testing and dry runs."""

from typing import Any

from eag.execution.models import ExecutionContext, ExecutionResult


class DummyExecutor:
    """A no-op executor that always succeeds. Used for runtime testing."""

    @property
    def name(self) -> str:
        return "DummyExecutor"

    def supports(self, operation: Any) -> bool:
        return True

    def execute(self, operation: Any, task: Any, context: ExecutionContext) -> ExecutionResult:
        task_title = getattr(task, "title", "Unknown Task")
        return ExecutionResult(success=True, summary=f"Simulated execution of '{task_title}'")
