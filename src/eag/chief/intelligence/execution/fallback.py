"""Fallback engine for EAG."""

from eag.chief.intelligence.execution.models import (
    ExecutionContext,
    ExecutionResult,
    FallbackReport,
)


class FallbackExecutor:
    """Manages fallback execution across multiple providers."""

    def execute_with_fallback(
        self,
        primary_context: ExecutionContext,
        fallback_contexts: list[ExecutionContext],
        executor_func,
    ) -> tuple[ExecutionResult, FallbackReport]:
        """Executes the primary context, falling back to alternatives on failure."""
        contexts = [primary_context] + fallback_contexts
        attempts = 0

        for i, ctx in enumerate(contexts):
            attempts += 1
            result = executor_func(ctx)
            if result.success:
                report = FallbackReport(
                    primary_provider=primary_context.provider_id,
                    fallback_provider=ctx.provider_id if i > 0 else primary_context.provider_id,
                    success=True,
                    attempts=attempts,
                )
                return result, report

        # All failed
        report = FallbackReport(
            primary_provider=primary_context.provider_id,
            fallback_provider=contexts[-1].provider_id,
            success=False,
            attempts=attempts,
        )
        # Return the last failure result
        return result, report
