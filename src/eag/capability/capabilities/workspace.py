"""Workspace capability for EAG."""

from pathlib import Path

from eag.capability.enums import CapabilityKind, CapabilityOutcome, CapabilityState, CapabilityStatus
from eag.capability.models import (
    CapabilityContext,
    CapabilityEstimate,
    CapabilityHealth,
    CapabilityMetadata,
    CapabilityRequest,
    CapabilityResult,
)
from eag.workspace.runtime import WorkspaceRuntime


class WorkspaceCapability:
    """Capability for interacting with the Workspace Platform."""
    
    def __init__(self, workspace_runtime: WorkspaceRuntime) -> None:
        self._runtime = workspace_runtime

    @property
    def metadata(self) -> CapabilityMetadata:
        return CapabilityMetadata(
            id="workspace",
            name="Workspace Operations",
            kind=CapabilityKind.WORKSPACE,
            description="Read, write, and manage files in the workspace."
        )

    def supports(self, request: CapabilityRequest) -> bool:
        return request.capability_id == "workspace"

    def estimate(self, request: CapabilityRequest) -> CapabilityEstimate:
        return CapabilityEstimate(capability_id="workspace", estimated_duration_ms=100.0)

    def execute(self, request: CapabilityRequest, context: CapabilityContext) -> CapabilityResult:
        operation = request.parameters.get("operation")
        
        if operation == "write":
            path = request.parameters.get("path")
            content = request.parameters.get("content", "")
            if not path:
                return CapabilityResult(
                    request_id=request.request_id, capability_id="workspace",
                    outcome=CapabilityOutcome.FAILURE, state=CapabilityState.FAILED,
                    error="Missing 'path' parameter"
                )
            self._runtime.write(Path(path), content)
            return CapabilityResult(
                request_id=request.request_id, capability_id="workspace",
                outcome=CapabilityOutcome.SUCCESS, state=CapabilityState.COMPLETED,
                output=f"Wrote to {path}"
            )
        elif operation == "read":
            path = request.parameters.get("path")
            if not path:
                return CapabilityResult(
                    request_id=request.request_id, capability_id="workspace",
                    outcome=CapabilityOutcome.FAILURE, state=CapabilityState.FAILED,
                    error="Missing 'path' parameter"
                )
            content = self._runtime.read(Path(path))
            return CapabilityResult(
                request_id=request.request_id, capability_id="workspace",
                outcome=CapabilityOutcome.SUCCESS, state=CapabilityState.COMPLETED,
                output=content
            )
        
        return CapabilityResult(
            request_id=request.request_id, capability_id="workspace",
            outcome=CapabilityOutcome.FAILURE, state=CapabilityState.FAILED,
            error=f"Unsupported operation: {operation}"
        )

    def health(self) -> CapabilityHealth:
        return CapabilityHealth(capability_id="workspace", status=CapabilityStatus.READY)