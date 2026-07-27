"""Execution runtime for EAG."""

import time
from eag.chief.intelligence.execution.enums import ExecutionState, TraceEventType
from eag.chief.intelligence.execution.errors import ExecutionFailedError, ProviderUnavailableError
from eag.chief.intelligence.execution.models import (
    ExecutionContext,
    ExecutionResult,
    ExecutionTrace,
    TraceEvent,
    UsageMetrics,
)
from eag.chief.intelligence.execution.registry import ProviderRegistry


class ExecutionRuntime:
    """Orchestrates the execution of AI requests against providers."""

    def __init__(self, registry: ProviderRegistry | None = None) -> None:
        self._registry = registry or ProviderRegistry()

    @property
    def registry(self) -> ProviderRegistry:
        return self._registry

    def execute(self, context: ExecutionContext) -> ExecutionResult:
        """Executes a request against the selected provider."""
        start_time = time.monotonic()
        
        trace = context.trace.add_event(TraceEvent(type=TraceEventType.STARTED))
        trace = trace.add_event(TraceEvent(
            type=TraceEventType.PROVIDER_SELECTED, 
            metadata={"provider": context.provider_id}
        ))

        provider = self._registry.find(context.provider_id)
        
        health = provider.health()
        if not health.is_available:
            raise ProviderUnavailableError(f"Provider '{context.provider_id}' is unavailable.")

        trace = trace.add_event(TraceEvent(type=TraceEventType.REQUEST_SENT))
        
        try:
            result = provider.execute(context)
            duration = (time.monotonic() - start_time) * 1000
            
            trace = trace.add_event(TraceEvent(type=TraceEventType.RESPONSE_RECEIVED))
            trace = trace.add_event(TraceEvent(type=TraceEventType.COMPLETED))
            
            return ExecutionResult(
                success=True,
                content=result.content,
                usage=result.usage if result.usage else UsageMetrics(),
                duration_ms=duration,
                provider_id=context.provider_id,
                model_id=context.model_id,
                state=ExecutionState.SUCCESS,
                trace=trace
            )
        except Exception as e:
            duration = (time.monotonic() - start_time) * 1000
            trace = trace.add_event(TraceEvent(type=TraceEventType.FAILED, message=str(e)))
            return ExecutionResult(
                success=False,
                duration_ms=duration,
                provider_id=context.provider_id,
                model_id=context.model_id,
                state=ExecutionState.FAILED,
                trace=trace,
                error=str(e)
            )