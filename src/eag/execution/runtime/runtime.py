"""Execution runtime for EAG."""

import uuid

from eag.events import EventBus
from eag.execution.enums import ExecutionState, RollbackStrategy, StepState
from eag.execution.events import (
    ExecutionCompleted,
    ExecutionFailed,
    ExecutionStarted,
    ExecutionStepCompleted,
    ExecutionStepStarted,
)
from eag.execution.models import (
    ExecutionContext,
    ExecutionMetrics,
    ExecutionReport,
    ExecutionResult,
    ExecutionRuntimeHealth,
    ExecutionStep,
    RollbackPoint,
)
from eag.execution.runtime import MetricsRuntime
from eag.execution.runtime.dispatcher import Dispatcher
from eag.execution.runtime.lifecycle import LifecycleManager
from eag.execution.runtime.scheduler import Scheduler


class ExecutionRuntime:
    """The central orchestrator for engineering execution."""

    def __init__(
        self,
        event_bus: EventBus,
        dispatcher: Dispatcher,
        scheduler: Scheduler | None = None,
        metrics: MetricsRuntime | None = None,
        lifecycle: LifecycleManager | None = None,
    ) -> None:
        self._event_bus = event_bus
        self._dispatcher = dispatcher
        self._scheduler = scheduler or Scheduler()
        self._metrics = metrics or MetricsRuntime()
        self._lifecycle = lifecycle or LifecycleManager()

    def execute(self, context: ExecutionContext) -> ExecutionReport:
        """Execute an approved plan within a given context."""
        self._lifecycle.transition_to(ExecutionState.READY)
        self._lifecycle.transition_to(ExecutionState.RUNNING)
        self._event_bus.publish(
            ExecutionStarted(execution_id=context.execution_id)  # type: ignore[arg-type]
        )

        tasks = self._scheduler.schedule(context.approved_plan.tasks)
        self._metrics.set_total(len(tasks))

        steps: list[ExecutionStep] = []

        for task in tasks:
            # Check for cancellation or pause before starting step
            if self._lifecycle.state == ExecutionState.CANCELLED:
                break
            while self._lifecycle.state == ExecutionState.PAUSED:
                pass  # In async runtime, this would await. Here it blocks.

            step_id = str(uuid.uuid4())
            self._event_bus.publish(
                ExecutionStepStarted(execution_id=context.execution_id, step_id=step_id)  # type: ignore[arg-type]
            )

            result = self._dispatcher.dispatch(task, context)

            step_state = StepState.SUCCESS if result.success else StepState.FAILED
            step = ExecutionStep(
                step_id=step_id,
                task=task,
                operation=context.approved_plan.engineering_goal.operation,
                state=step_state,
                duration=result.metrics.execution_time,
            )
            steps.append(step)

            if result.success:
                self._metrics.record_success(step.duration)
            else:
                self._metrics.record_failure(step.duration)

            self._event_bus.publish(
                ExecutionStepCompleted(
                    execution_id=context.execution_id,
                    step_id=step_id,
                    success=result.success,
                )  # type: ignore[arg-type]
            )

            if not result.success:
                self._lifecycle.transition_to(ExecutionState.FAILED)
                self._event_bus.publish(
                    ExecutionFailed(
                        execution_id=context.execution_id,
                        error=result.summary or "Step execution failed.",
                    )  # type: ignore[arg-type]
                )
                break

        if self._lifecycle.state == ExecutionState.RUNNING:
            self._lifecycle.transition_to(ExecutionState.COMPLETED)

        success = self._lifecycle.state == ExecutionState.COMPLETED
        if success:
            self._event_bus.publish(
                ExecutionCompleted(
                    execution_id=context.execution_id,
                    success=True,
                )  # type: ignore[arg-type]
            )

        return ExecutionReport(
            state=self._lifecycle.state,
            steps=tuple(steps),
            metrics=self._metrics.get_metrics(),
            result=ExecutionResult(
                success=success,
                summary=f"Execution finished with state: {self._lifecycle.state.value}",
            ),
            summary=f"Execution finished with state: {self._lifecycle.state.value}",
        )

    def validate(self, context: ExecutionContext) -> bool:
        return True

    def checkpoint(self, context: ExecutionContext, name: str) -> RollbackPoint:
        return RollbackPoint(strategy=RollbackStrategy.NONE)

    def rollback(self, context: ExecutionContext, rollback_point: RollbackPoint) -> ExecutionResult:
        return ExecutionResult(success=True, summary="Rollback not fully implemented yet.")

    def dry_run(self, context: ExecutionContext) -> ExecutionReport:
        return self.execute(context)

    def metrics(self) -> "ExecutionMetrics":
        """Return the current live execution metrics."""
        return self._metrics.get_metrics()

    def health(self) -> ExecutionRuntimeHealth:
        """Return the current health status of the runtime and subsystems."""
        state = self._lifecycle.state
        if state == ExecutionState.FAILED:
            summary = "Runtime encountered a failure."
        elif state == ExecutionState.RUNNING:
            summary = "Runtime is currently executing."
        else:
            summary = "Runtime is healthy."

        return ExecutionRuntimeHealth(state=state, summary=summary)

    def explain(self, report: ExecutionReport | None = None) -> str:
        """Provide a human-readable explanation of the execution state or report."""
        if report:
            # Safely check if the result exists before reading .success
            is_success = report.result.success if report.result else False

            return (
                f"Execution Report\n"
                f"────────────────────────────────\n"
                f"State: {report.state.value.upper()}\n"
                f"Success: {is_success}\n"  # <--- Use the safe variable here
                f"Steps Completed: {report.metrics.steps_completed} "
                f"/ {report.metrics.steps_total}\n"
                f"Elapsed: {report.metrics.execution_time:.2f}s\n"
                f"Summary: {report.summary}"
            )

        metrics = self.metrics()
        health = self.health()
        return (
            f"Execution Runtime Status\n"
            f"────────────────────────────────\n"
            f"State: {health.state.value.upper()}\n"
            f"Progress: {metrics.steps_completed} / {metrics.steps_total}\n"
            f"Failed: {metrics.steps_failed}\n"
            f"Elapsed: {metrics.execution_time:.2f}s\n"
            f"Status: {health.summary}"
        )

    def pause(self) -> None:
        """Pause the execution runtime."""
        if self._lifecycle.state == ExecutionState.RUNNING:
            self._lifecycle.transition_to(ExecutionState.PAUSED)

    def resume(self) -> None:
        """Resume a paused execution runtime."""
        if self._lifecycle.state == ExecutionState.PAUSED:
            self._lifecycle.transition_to(ExecutionState.RUNNING)

    def cancel(self) -> None:
        """Cancel the execution runtime."""
        if self._lifecycle.state not in [
            ExecutionState.COMPLETED,
            ExecutionState.FAILED,
            ExecutionState.CANCELLED,
        ]:
            self._lifecycle.transition_to(ExecutionState.CANCELLED)
