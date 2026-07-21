"""Transformation protocol for EAG."""

from typing import Protocol, runtime_checkable

from eag.source.python.transformations.descriptor import TransformationDescriptor
from eag.source.python.transformations.models import (
    TransformationContext,
    TransformationPreview,
    TransformationResult,
)


@runtime_checkable
class Transformation(Protocol):
    """The contract for a source code transformation."""

    @property
    def descriptor(self) -> TransformationDescriptor: ...

    @property
    def name(self) -> str: ...

    def supports(self, context: TransformationContext) -> bool: ...

    def preview(self, context: TransformationContext) -> TransformationPreview: ...

    def validate(self, context: TransformationContext) -> tuple[str, ...]: ...

    def apply(self, context: TransformationContext) -> TransformationResult: ...

    def undo(
        self, context: TransformationContext, result: TransformationResult
    ) -> TransformationResult: ...
