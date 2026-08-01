"""Validation engine for EAG Chief Runtime."""

from eag.chief.runtime.enums import ValidationDecision
from eag.chief.runtime.models import ChiefRun, PlanStep, StepResult


class DefaultValidator:
    """Default validator that makes decisions based on step results."""

    def __init__(self, max_retries: int = 2) -> None:
        self._max_retries = max_retries
        self._retry_counts: dict[str, int] = {}

    def validate(self, step: PlanStep, result: StepResult, run: ChiefRun) -> ValidationDecision:
        if result.success:
            self._retry_counts.pop(step.step_id, None)
            return ValidationDecision.CONTINUE

        retries = self._retry_counts.get(step.step_id, 0)
        if retries < self._max_retries:
            self._retry_counts[step.step_id] = retries + 1
            return ValidationDecision.RETRY

        return ValidationDecision.ABORT
