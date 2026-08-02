"""Transformation capability for EAG."""

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
from eag.source.python import RenameTransformation, TransformationContext
from eag.source.runtime import SourceRuntime


class TransformationCapability:
    """Capability for performing semantic source code transformations."""

    def __init__(self, source_runtime: SourceRuntime) -> None:
        self._source = source_runtime

    @property
    def metadata(self) -> CapabilityMetadata:
        return CapabilityMetadata(
            id="transformation",
            name="Code Transformation",
            kind=CapabilityKind.TRANSFORMATION,
            description="Rename, move, or modify source code symbols.",
        )

    def supports(self, request: CapabilityRequest) -> bool:
        return request.capability_id == "transformation"

    def estimate(self, request: CapabilityRequest) -> CapabilityEstimate:
        return CapabilityEstimate(capability_id="transformation", estimated_duration_ms=200.0)

    def execute(self, request: CapabilityRequest, context: CapabilityContext) -> CapabilityResult:
        operation = request.parameters.get("operation")
        file_path = request.parameters.get("file_path")

        if not file_path:
            return CapabilityResult(
                request_id=request.request_id,
                capability_id="transformation",
                outcome=CapabilityOutcome.FAILURE,
                state=CapabilityState.FAILED,
                error="Missing 'file_path' parameter",
            )

        full_path = context.workspace_path / file_path
        content = full_path.read_text()
        doc = self._source.parse(full_path, content)

        if operation == "rename":
            target = request.parameters.get("target")
            new_name = request.parameters.get("new_name")
            if not target or not new_name:
                return CapabilityResult(
                    request_id=request.request_id,
                    capability_id="transformation",
                    outcome=CapabilityOutcome.FAILURE,
                    state=CapabilityState.FAILED,
                    error="Missing 'target' or 'new_name' for rename",
                )

            transform = RenameTransformation(target, new_name)
            ctx = TransformationContext(document=doc, content=content)
            result = transform.apply(ctx)

            if result.success and result.edits:
                new_content = result.edits[0].new_content
                full_path.write_text(new_content)
                return CapabilityResult(
                    request_id=request.request_id,
                    capability_id="transformation",
                    outcome=CapabilityOutcome.SUCCESS,
                    state=CapabilityState.COMPLETED,
                    output=result.summary,
                )
            else:
                return CapabilityResult(
                    request_id=request.request_id,
                    capability_id="transformation",
                    outcome=CapabilityOutcome.FAILURE,
                    state=CapabilityState.FAILED,
                    error=result.summary,
                )

        return CapabilityResult(
            request_id=request.request_id,
            capability_id="transformation",
            outcome=CapabilityOutcome.FAILURE,
            state=CapabilityState.FAILED,
            error=f"Unsupported operation: {operation}",
        )

    def health(self) -> CapabilityHealth:
        return CapabilityHealth(capability_id="transformation", status=CapabilityStatus.READY)
