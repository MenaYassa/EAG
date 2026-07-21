"""Source Transformation Framework for EAG."""
from eag.source.python.transformations.diff import DiffEngine, StructuredDiff
from eag.source.python.transformations.batch import TransformationBatch
from eag.source.python.transformations.conflicts import ConflictDetector
from eag.source.python.transformations.edit_engine import EditEngine
from eag.source.python.transformations.edits import (
    CompositeEdit,
    Edit,
    EditType,
    ImportEdit,
    SymbolEdit,
    TextEdit,
)
from eag.source.python.transformations.engine import TransformationEngine
from eag.source.python.transformations.errors import TransactionError
from eag.source.python.transformations.models import (
    SourceEdit,
    TransformationContext,
    TransformationPreview,
    TransformationResult,
)
from eag.source.python.transformations.protocol import Transformation
from eag.source.python.transformations.registry import TransformationRegistry
from eag.source.python.transformations.rename import RenameTransformation
from eag.source.python.transformations.text_applier import apply_text_edits
from eag.source.python.transformations.transaction import (
    EditTransaction,
    TransactionState,
)
from eag.source.python.transformations.validator import TransformationValidator
from eag.source.python.transformations.visitor import RenameVisitor

__all__ = [
    "TransformationEngine",
    "SourceEdit",
    "TextEdit",
    "Edit",
    "EditType",
    "SymbolEdit",
    "ImportEdit",
    "CompositeEdit",
    "TransformationContext",
    "TransformationPreview",
    "TransformationResult",
    "Transformation",
    "TransformationRegistry",
    "TransformationValidator",
    "RenameTransformation",
    "RenameVisitor",
    "apply_text_edits",
    "ConflictDetector",
    "EditEngine",
    "TransformationBatch",
    "EditTransaction",
    "TransactionState",
    "TransactionError",
    "DiffEngine",
    "StructuredDiff",
]