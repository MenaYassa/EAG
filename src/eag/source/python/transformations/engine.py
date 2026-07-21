"""Transformation engine for EAG."""

from __future__ import annotations

from eag.planner.enums import RiskLevel
from eag.source.python.transformations.models import (
    TransformationContext,
    TransformationPreview,
    TransformationResult,
)
from eag.source.python.transformations.registry import TransformationRegistry


class TransformationEngine:
    """Orchestrates transformation execution."""

    transformation_name: str = "unknown"
    success: bool = False
    files_modified: tuple[str, ...] = ()
    duration: float = 0.0
    summary: str = ""
    old_name: str = ""
    new_name: str = ""

    def __init__(self, registry: TransformationRegistry | None = None) -> None:
        self._registry = registry or TransformationRegistry()

    def explain(self) -> str:
        return (
            f"Transformation: {self.transformation_name}\n"
            f"Validation: {'Passed' if self.success else 'Failed'}\n"
            f"Files Affected: {len(self.files_modified)}\n"
            f"Duration: {self.duration:.2f}s\n"
            f"Summary: {self.summary}"
        )

    def preview(self, context: TransformationContext) -> TransformationPreview:
        """Computes a rich preview of the transformation impact."""
        # 1. Find symbols matching the target name in the current document/context
        matching_symbols = [
            s
            for s in getattr(context.document, "symbols", [])
            if s.name == self.old_name or getattr(s, "qualified_name", "") == self.old_name
        ]

        # 2. Count references if available
        total_references = sum(len(getattr(s, "references", [])) for s in matching_symbols)

        # 3. Assess Risk Level based on scope
        risk = RiskLevel.LOW
        if total_references > 10:
            risk = RiskLevel.MEDIUM
        if total_references > 25 or len(matching_symbols) > 5:
            risk = RiskLevel.HIGH

        # 4. Construct the rich preview payload
        return TransformationPreview(
            transformation_name="rename_symbol",
            can_apply=len(matching_symbols) > 0,
            summary=(
                f"Will rename '{self.old_name}' to '{self.new_name}' "
                f"across {len(matching_symbols)} symbols."
            ),
            affected_files=(
                (str(context.document.path),) if hasattr(context.document, "path") else ()
            ),
            affected_symbols=tuple(s.name for s in matching_symbols),
            risk=risk,  # Use the evaluated variable here instead of hardcoding RiskLevel.LOW!
            estimated_duration_ms=1.5,
            rollback_complexity="MEDIUM" if total_references > 5 else "LOW",
        )

    def execute(self, name: str, context: TransformationContext) -> TransformationResult:
        """Execute a transformation by name."""
        transformation = self._registry.find(name, context)

        if not transformation.supports(context):
            return TransformationResult(
                success=False,
                transformation_name=name,
                summary="Transformation not supported for this context.",
            )

        # In a real engine, we might intercept preview/validate here
        # but for the skeleton, we delegate directly to apply
        return transformation.apply(context)
