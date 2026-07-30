"""Retry engine for EAG."""

import time

from eag.chief.intelligence.execution.enums import RetryStrategy
from eag.chief.intelligence.execution.models import (
    ExecutionContext,
    ExecutionResult,
    RetryDecision,
)


class RetryEngine:
    """Handles retry logic based on execution options."""

    def should_retry(
        self, context: ExecutionContext, result: ExecutionResult, attempt: int
    ) -> RetryDecision:
        if result.success:
            return RetryDecision(should_retry=False, attempt=attempt)

        max_retries = context.options.retry_count
        if attempt > max_retries:
            return RetryDecision(should_retry=False, attempt=attempt, reason="Max retries exceeded")

        strategy = context.options.retry_strategy
        delay = self._calculate_delay(strategy, attempt)

        return RetryDecision(
            should_retry=True,
            delay_ms=delay,
            attempt=attempt,
            reason=f"Retry {attempt}/{max_retries} using {strategy.value} strategy",
        )

    def wait(self, delay_ms: float) -> None:
        if delay_ms > 0:
            time.sleep(delay_ms / 1000.0)

    def _calculate_delay(self, strategy: RetryStrategy, attempt: int) -> float:
        if strategy == RetryStrategy.NONE:
            return 0.0
        elif strategy == RetryStrategy.FIXED:
            return 1000.0  # 1 second
        elif strategy == RetryStrategy.EXPONENTIAL:
            return (2**attempt) * 1000.0  # 2^attempt seconds
        return 0.0
