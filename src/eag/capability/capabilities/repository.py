"""Repository capability for EAG."""

from eag.capability.enums import CapabilityKind, CapabilityOutcome, CapabilityState, CapabilityStatus
from eag.capability.models import (
    CapabilityContext,
    CapabilityEstimate,
    CapabilityHealth,
    CapabilityMetadata,
    CapabilityRequest,
    CapabilityResult,
)

class RepositoryCapability:
    """Capability for interacting with the Repository (Git) Platform."""
    
    def __init__(self, vcs_runtime) -> None:
        self._runtime = vcs_runtime

    @property
    def metadata(self) -> CapabilityMetadata:
        return CapabilityMetadata(
            id="repository",
            name="Repository Operations",
            kind=CapabilityKind.REPOSITORY,
            description="Init, commit, branch, and manage Git operations."
        )

    def supports(self, request: CapabilityRequest) -> bool:
        return request.capability_id == "repository"

    def estimate(self, request: CapabilityRequest) -> CapabilityEstimate:
        return CapabilityEstimate(capability_id="repository", estimated_duration_ms=500.0)

    def execute(self, request: CapabilityRequest, context: CapabilityContext) -> CapabilityResult:
        operation = request.parameters.get("operation")
        
        if operation == "init":
            # VCSRuntime.open() handles initialization
            self._runtime.open()
            return CapabilityResult(
                request_id=request.request_id, capability_id="repository",
                outcome=CapabilityOutcome.SUCCESS, state=CapabilityState.COMPLETED,
                output="Repository initialized"
            )
        elif operation == "commit":
            message = request.parameters.get("message", "Automated EAG commit")
            commit_id = self._runtime.commit(message)
            return CapabilityResult(
                request_id=request.request_id, capability_id="repository",
                outcome=CapabilityOutcome.SUCCESS, state=CapabilityState.COMPLETED,
                output=commit_id
            )
        elif operation == "status":
            status = self._runtime.status()
            return CapabilityResult(
                request_id=request.request_id, capability_id="repository",
                outcome=CapabilityOutcome.SUCCESS, state=CapabilityState.COMPLETED,
                output=str(status)
            )
        
        return CapabilityResult(
            request_id=request.request_id, capability_id="repository",
            outcome=CapabilityOutcome.FAILURE, state=CapabilityState.FAILED,
            error=f"Unsupported operation: {operation}"
        )

    def health(self) -> CapabilityHealth:
        return CapabilityHealth(capability_id="repository", status=CapabilityStatus.READY)