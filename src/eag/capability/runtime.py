"""Capability runtime for EAG."""

import time
from eag.capability.enums import CapabilityOutcome, CapabilityState
from eag.capability.models import (
    CapabilityContext,
    CapabilityRequest,
    CapabilityResult,
)
from eag.capability.registry import CapabilityRegistry


class CapabilityRuntime:
    """Orchestrates the execution of engineering capabilities."""

    def __init__(self, registry: CapabilityRegistry | None = None) -> None:
        self._registry = registry or CapabilityRegistry()

    @property
    def registry(self) -> CapabilityRegistry:
        return self._registry

    def execute(self, request: CapabilityRequest, context: CapabilityContext) -> CapabilityResult:
        """Executes a capability request."""
        start_time = time.monotonic()
        
        try:
            capability = self._registry.find(request.capability_id)
            result = capability.execute(request, context)
            
            duration = (time.monotonic() - start_time) * 1000
            # Enrich with actual duration if not set
            if result.duration_ms == 0.0:
                result = CapabilityResult(
                    request_id=result.request_id,
                    capability_id=result.capability_id,
                    outcome=result.outcome,
                    state=result.state,
                    output=result.output,
                    artifacts=result.artifacts,
                    error=result.error,
                    duration_ms=duration,
                    metadata=result.metadata
                )
            return result
            
        except Exception as e:
            duration = (time.monotonic() - start_time) * 1000
            return CapabilityResult(
                request_id=request.request_id,
                capability_id=request.capability_id,
                outcome=CapabilityOutcome.FAILURE,
                state=CapabilityState.FAILED,
                error=str(e),
                duration_ms=duration
            )