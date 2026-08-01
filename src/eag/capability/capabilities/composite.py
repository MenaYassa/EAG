"""Composite capability for EAG."""

from eag.capability.enums import (
    CapabilityKind,
    CapabilityOutcome,
    CapabilityState,
    CapabilityStatus,
)
from eag.capability.models import (
    CapabilityContext,
    CapabilityEstimate,
    CapabilityHealth,
    CapabilityMetadata,
    CapabilityRequest,
    CapabilityResult,
)
from eag.capability.runtime import CapabilityRuntime


class CompositeCapability:
    """Orchestrates multiple capabilities to achieve a higher-level goal."""

    def __init__(self, capability_runtime: CapabilityRuntime) -> None:
        self._runtime = capability_runtime

    @property
    def metadata(self) -> CapabilityMetadata:
        return CapabilityMetadata(
            id="composite",
            name="Composite Workflow",
            kind=CapabilityKind.COMPOSITE,
            description="Orchestrates multiple capabilities into a single workflow.",
        )

    def supports(self, request: CapabilityRequest) -> bool:
        return request.capability_id == "composite"

    def estimate(self, request: CapabilityRequest) -> CapabilityEstimate:
        return CapabilityEstimate(capability_id="composite", estimated_duration_ms=1000.0)

    def execute(self, request: CapabilityRequest, context: CapabilityContext) -> CapabilityResult:
        workflow = request.parameters.get("workflow", [])
        results = []

        for step in workflow:
            step_req = CapabilityRequest(
                capability_id=step.get("capability_id"),
                goal_text=step.get("goal_text", ""),
                parameters=step.get("parameters", {}),
            )
            result = self._runtime.execute(step_req, context)
            results.append(result)

            if not result.success:
                return CapabilityResult(
                    request_id=request.request_id,
                    capability_id="composite",
                    outcome=CapabilityOutcome.FAILURE,
                    state=CapabilityState.FAILED,
                    error=f"Workflow failed at step {step.get('capability_id')}: {result.error}",
                    metadata={"results": [r.metadata for r in results]},
                )

        return CapabilityResult(
            request_id=request.request_id,
            capability_id="composite",
            outcome=CapabilityOutcome.SUCCESS,
            state=CapabilityState.COMPLETED,
            output="Workflow completed successfully",
            metadata={"results": [r.metadata for r in results]},
        )

    def health(self) -> CapabilityHealth:
        return CapabilityHealth(capability_id="composite", status=CapabilityStatus.READY)
