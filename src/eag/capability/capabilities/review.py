"""Review capability for EAG."""


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
from eag.review.models import ReviewContext
from eag.review.runtime import ReviewRuntime


class ReviewCapability:
    """Capability for reviewing engineering work."""

    def __init__(self, review_runtime: ReviewRuntime) -> None:
        self._runtime = review_runtime

    @property
    def metadata(self) -> CapabilityMetadata:
        return CapabilityMetadata(
            id="review",
            name="Engineering Review",
            kind=CapabilityKind.REVIEW,
            description="Analyze workspace and generate a review report.",
        )

    def supports(self, request: CapabilityRequest) -> bool:
        return request.capability_id == "review"

    def estimate(self, request: CapabilityRequest) -> CapabilityEstimate:
        return CapabilityEstimate(capability_id="review", estimated_duration_ms=300.0)

    def execute(self, request: CapabilityRequest, context: CapabilityContext) -> CapabilityResult:
        # In a real scenario, we would inspect the workspace files here
        # For now, we rely on metadata passed in the request
        review_ctx = ReviewContext(
            workspace_path=context.workspace_path,
            execution_success=request.parameters.get("execution_success", True),
            metadata=request.parameters.get("review_metadata", {}),
        )

        report = self._runtime.review(review_ctx)

        return CapabilityResult(
            request_id=request.request_id,
            capability_id="review",
            outcome=CapabilityOutcome.SUCCESS
            if report.decision == "approved"
            else CapabilityOutcome.FAILURE,
            state=CapabilityState.COMPLETED,
            output=report.summary,
            metadata={"decision": report.decision.value, "score": report.overall_score},
        )

    def health(self) -> CapabilityHealth:
        return CapabilityHealth(capability_id="review", status=CapabilityStatus.READY)
