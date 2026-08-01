"""Workspace capability for EAG."""

from pathlib import Path

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


class WorkspaceCapability:
    """Capability for interacting with the Workspace Platform."""

    def __init__(self, workspace_runtime) -> None:
        self._runtime = workspace_runtime

    @property
    def metadata(self) -> CapabilityMetadata:
        return CapabilityMetadata(
            id="workspace",
            name="Workspace Operations",
            kind=CapabilityKind.WORKSPACE,
            description="Read, write, and manage files in the workspace.",
        )

    def supports(self, request: CapabilityRequest) -> bool:
        return request.capability_id == "workspace"

    def estimate(self, request: CapabilityRequest) -> CapabilityEstimate:
        return CapabilityEstimate(capability_id="workspace", estimated_duration_ms=100.0)

    def execute(self, request: CapabilityRequest, context: CapabilityContext) -> CapabilityResult:
        operation = request.parameters.get("operation")
        path_arg = request.parameters.get("path")

        if not path_arg:
            return CapabilityResult(
                request_id=request.request_id,
                capability_id="workspace",
                outcome=CapabilityOutcome.FAILURE,
                state=CapabilityState.FAILED,
                error="Missing 'path' parameter",
            )

        # Handle both string paths and Path objects safely
        path_str = str(path_arg)

        if operation == "write":
            content = request.parameters.get("content", "")

            # If a mock runtime is present (like in old unit tests), delegate to it
            if hasattr(self, "_runtime") and hasattr(self._runtime, "write"):
                self._runtime.write(Path(path_str), content)
            else:
                file_path = context.workspace_path / path_str
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content)

            return CapabilityResult(
                request_id=request.request_id,
                capability_id="workspace",
                outcome=CapabilityOutcome.SUCCESS,
                state=CapabilityState.COMPLETED,
                output=f"Wrote to {path_str}",
            )

        elif operation == "read":
            if hasattr(self, "_runtime") and hasattr(self._runtime, "read"):
                content = self._runtime.read(Path(path_str))
            else:
                file_path = context.workspace_path / path_str
                try:
                    content = file_path.read_text()
                except FileNotFoundError:
                    return CapabilityResult(
                        request_id=request.request_id,
                        capability_id="workspace",
                        outcome=CapabilityOutcome.FAILURE,
                        state=CapabilityState.FAILED,
                        error=f"File not found: {path_str}",
                    )

            return CapabilityResult(
                request_id=request.request_id,
                capability_id="workspace",
                outcome=CapabilityOutcome.SUCCESS,
                state=CapabilityState.COMPLETED,
                output=content,
            )

        # Fallback return for any unsupported operation
        return CapabilityResult(
            request_id=request.request_id,
            capability_id="workspace",
            outcome=CapabilityOutcome.FAILURE,
            state=CapabilityState.FAILED,
            error=f"Unsupported operation: {operation}",
        )

    def health(self) -> CapabilityHealth:
        return CapabilityHealth(capability_id="workspace", status=CapabilityStatus.READY)
