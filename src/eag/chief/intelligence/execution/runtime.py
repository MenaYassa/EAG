"""Execution runtime for EAG."""

import time
from eag.chief.intelligence.execution.enums import ExecutionState, TraceEventType

from eag.chief.intelligence.execution.errors import (
    ExecutionFailedError,
    ProviderNotFoundError,
    ProviderUnavailableError
)
from eag.chief.intelligence.execution.fallback import FallbackExecutor
from eag.chief.intelligence.execution.health import HealthManager
from eag.chief.intelligence.execution.middleware import MiddlewarePipeline
from eag.chief.intelligence.execution.models import (
    ExecutionContext,
    ExecutionResult,
    ExecutionTrace,
    TraceEvent,
    UsageMetrics,
    ProviderHealth,
    ProviderHealthStatus,
)
from eag.chief.intelligence.execution.errors import ProviderNotFoundError, ProviderUnavailableError
from eag.chief.intelligence.execution.pricing import PricingCatalog
from eag.chief.intelligence.execution.registry import ProviderRegistry
from eag.chief.intelligence.execution.retry import RetryEngine
from dataclasses import replace

class ExecutionRuntime:
    """Orchestrates the execution of AI requests against providers."""

    def __init__(
        self, 
        registry: ProviderRegistry | None = None,
        health_manager: HealthManager | None = None,
        pricing_catalog: PricingCatalog | None = None,
        middleware: MiddlewarePipeline | None = None,
        retry_engine: RetryEngine | None = None,
        fallback_executor: FallbackExecutor | None = None
    ) -> None:
        self._registry = registry or ProviderRegistry()
        self._health = health_manager or HealthManager()
        self._pricing = pricing_catalog or PricingCatalog()
        self._middleware = middleware or MiddlewarePipeline()
        self._retry = retry_engine or RetryEngine()
        self._fallback = fallback_executor or FallbackExecutor()

    @property
    def registry(self) -> ProviderRegistry:
        return self._registry

    @property
    def health(self) -> HealthManager:
        return self._health

    @property
    def pricing(self) -> PricingCatalog:
        return self._pricing

    @property
    def middleware(self) -> MiddlewarePipeline:
        return self._middleware

    def execute(self, context: ExecutionContext, fallback_contexts: list[ExecutionContext] | None = None) -> ExecutionResult:
        """Executes a request against the selected provider, with retry and fallback."""
        
        def executor_func(ctx: ExecutionContext) -> ExecutionResult:
            return self._execute_with_retry(ctx)

        if fallback_contexts:
            result, report = self._fallback.execute_with_fallback(context, fallback_contexts, executor_func)
            
            if report.fallback_used:
                new_trace = result.trace.add_event(TraceEvent(
                    type=TraceEventType.FALLBACK_COMPLETED,
                    metadata={"fallback_provider": report.fallback_provider}
                ))
                # Use replace() to safely update the frozen ExecutionResult
                # We also ensure result.fallback_used is set to True here!
                result = replace(result, trace=new_trace, fallback_used=True)
                
            return result
        else:
            return executor_func(context)

    def _execute_with_retry(self, context: ExecutionContext) -> ExecutionResult:
        attempt = 1
        start_time = time.monotonic()
        
        # This will naturally raise ProviderNotFoundError if it doesn't exist
        provider = self._registry.find(context.provider_id)
        
        health = self._health.health(context.provider_id)
        if health.status == ProviderHealthStatus.UNHEALTHY: 
            raise ProviderUnavailableError(f"Provider '{context.provider_id}' is unavailable.")
            
        while True:
            try:
                result = self._middleware.execute(context, self._execute_provider)
                if result.success:
                    return result
                
                decision = self._retry.should_retry(context, result, attempt)
                if not decision.should_retry:
                    return result
                
                self._retry.wait(decision.delay_ms)
                attempt += 1
                
            except (ProviderNotFoundError, ProviderUnavailableError):
                raise  # Let these bubble up for the tests (and caller) to handle
            except Exception as e:
                # Create a failed result for the retry engine to evaluate
                failed_result = ExecutionResult(
                    success=False,
                    error=str(e),
                    state=ExecutionState.FAILED,
                    provider_id=context.provider_id,
                    model_id=context.model_id,
                    trace=context.trace  # <-- Fix 2: Preserve the context trace ID here
                )
                
                decision = self._retry.should_retry(context, failed_result, attempt)
                if not decision.should_retry:
                    return failed_result  # <-- FIX: Return the fully built object, no '...'
                
                self._retry.wait(decision.delay_ms)
                attempt += 1

    def _execute_provider(self, context: ExecutionContext) -> ExecutionResult:
        start_time = time.monotonic()
        
        provider = self._registry.find(context.provider_id)
        health = self._health.health(context.provider_id)
        
        # FIX 1: Change 'not health.is_available' to check explicitly for UNHEALTHY.
        # This was the bug blocking all 'UNKNOWN' providers!
        if health.status == ProviderHealthStatus.UNHEALTHY:
            raise ProviderUnavailableError(f"Provider '{context.provider_id}' is unavailable.")
            
        # FIX 2: Trigger the provider's internal health check (Required for the health_checked test)
        if provider.health().status == ProviderHealthStatus.UNHEALTHY:
            raise ProviderUnavailableError(f"Provider '{context.provider_id}' is unavailable.")

        trace = context.trace.add_event(TraceEvent(type=TraceEventType.STARTED))
        trace = trace.add_event(TraceEvent(
            type=TraceEventType.PROVIDER_SELECTED, 
            metadata={"provider": context.provider_id}
        ))
        trace = trace.add_event(TraceEvent(type=TraceEventType.REQUEST_SENT))

        try:
            result = provider.execute(context)
            duration = (time.monotonic() - start_time) * 1000
            
            self._health.record_success(context.provider_id, duration)
            
            trace = trace.add_event(TraceEvent(type=TraceEventType.RESPONSE_RECEIVED))
            trace = trace.add_event(TraceEvent(type=TraceEventType.COMPLETED))
            
            # Calculate cost
            cost = self._pricing.calculate_cost(context.model_id, result.usage)
            usage = UsageMetrics(
                prompt_tokens=result.usage.prompt_tokens,
                completion_tokens=result.usage.completion_tokens,
                total_tokens=result.usage.total_tokens,
                estimated_cost=cost
            )
            
            return ExecutionResult(
                success=True,
                content=result.content,
                usage=usage,
                duration_ms=duration,
                provider_id=context.provider_id,
                model_id=context.model_id,
                state=ExecutionState.SUCCESS,
                trace=trace,  # FIX 3: This was 'context.trace', which discarded all the events!
            )
        except Exception as e:
            duration = (time.monotonic() - start_time) * 1000
            self._health.record_failure(context.provider_id)
            trace = trace.add_event(TraceEvent(type=TraceEventType.FAILED, message=str(e)))
            
            # FIX 4: Instead of raising an error and crashing, return a failed result 
            # so the Retry engine can handle it and preserve the trace data!
            return ExecutionResult(
                success=False,
                error=f"Execution failed: {e}",
                state=ExecutionState.FAILED,
                provider_id=context.provider_id,
                model_id=context.model_id,
                trace=trace,
                duration_ms=duration
            )


    def execute_stream(self, context: ExecutionContext):
        """Executes a streaming request against the selected provider."""
        provider = self._registry.find(context.provider_id)
        # In a real implementation, this would yield chunks from the provider
        yield from provider.stream(context)