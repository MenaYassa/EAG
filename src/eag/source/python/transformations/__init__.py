"""Source Transformation Framework for EAG."""

from eag.source.python.transformations.engine import TransformationEngine
from eag.source.python.transformations.models import (
    SourceEdit,
    TextEdit,
    TransformationContext,
    TransformationPreview,
    TransformationResult,
)
from eag.source.python.transformations.protocol import Transformation
from eag.source.python.transformations.registry import TransformationRegistry
from eag.source.python.transformations.rename import RenameTransformation
from eag.source.python.transformations.text_applier import apply_text_edits
from eag.source.python.transformations.validator import TransformationValidator
from eag.source.python.transformations.visitor import RenameVisitor

__all__ = [
    "TransformationEngine",
    "SourceEdit",
    "TextEdit",
    "TransformationContext",
    "TransformationPreview",
    "TransformationResult",
    "Transformation",
    "TransformationRegistry",
    "TransformationValidator",
    "RenameTransformation",
    "RenameVisitor",
    "apply_text_edits",
]
