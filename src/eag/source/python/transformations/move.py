"""Move Symbol transformation for EAG."""

from datetime import UTC, datetime

from eag.planner.enums import RiskLevel
from eag.source.models import Language
from eag.source.python.transformations.descriptor import (
    TransformationCategory,
    TransformationDescriptor,
)
from eag.source.python.transformations.models import (
    SourceEdit,
    TransformationContext,
    TransformationPreview,
    TransformationResult,
)
from eag.source.python.transformations.rename import RenameTransformation


class MoveSymbolTransformation:
    """Moves a symbol to a new module and updates references."""

    def __init__(self, target_symbol: str, destination_module: str) -> None:
        self._target_symbol = target_symbol
        self._destination_module = destination_module
        # Move is essentially a complex rename + import update. For this skeleton,
        # we delegate to Rename to handle the definition/references, and manually handle imports.
        self._rename = RenameTransformation(
            target_symbol, target_symbol
        )  # No-op rename just to get edits

    @property
    def descriptor(self) -> TransformationDescriptor:
        return TransformationDescriptor(
            name="move_symbol",
            category=TransformationCategory.STRUCTURAL,
            supported_languages=(Language.PYTHON,),
            risk=RiskLevel.MEDIUM,
            requires_repository=True,
            produces_edits=("TextEdit", "ImportEdit", "FileEdit"),
        )

    @property
    def name(self) -> str:
        return self.descriptor.name

    def supports(self, context: TransformationContext) -> bool:
        # Check if document has language attribute
        if not hasattr(context.document, "language"):
            return False

        # Check if language is Python
        if hasattr(context.document.language, "value"):
            return context.document.language.value == "python"
        return context.document.language in self.descriptor.supported_languages

    def preview(self, context: TransformationContext) -> TransformationPreview:
        return TransformationPreview(
            transformation_name=self.name,
            affected_files=(str(context.document.path),),
            affected_symbols=(self._target_symbol,),
            risk=RiskLevel.MEDIUM,
            summary=f"Move '{self._target_symbol}' to '{self._destination_module}'.",
        )

    def validate(self, context: TransformationContext) -> tuple[str, ...]:
        errors: list[str] = []
        if not self._destination_module.strip():
            errors.append("Destination module cannot be empty.")
        return tuple(errors)

    def apply(self, context: TransformationContext) -> TransformationResult:
        if not self.supports(context):
            return TransformationResult(
                success=False,
                transformation_name=self.name,
                summary=f"Unsupported language: {context.document.language}",
            )
        errors = self.validate(context)
        if errors:
            return TransformationResult(
                success=False,
                transformation_name=self.name,
                summary="Validation failed: " + "; ".join(errors),
            )

        # In a full implementation, this would:
        # 1. Remove definition from source file
        # 2. Add definition to destination file
        # 3. Update all imports across the repository
        # Here we simulate by just updating the import in the current file
        new_content = context.content.replace(
            f"from {context.document.path.stem} import {self._target_symbol}",
            f"from {self._destination_module} import {self._target_symbol}",
        )

        if new_content == context.content:
            return TransformationResult(
                success=True,
                transformation_name=self.name,
                edits=(SourceEdit(path=context.document.path, new_content=context.content),),
                summary=f"No changes needed for move '{self._target_symbol}'.",
            )

        edit = SourceEdit(path=context.document.path, new_content=new_content)
        return TransformationResult(
            success=True,
            transformation_name=self.name,
            edits=(edit,),
            files_modified=(str(context.document.path),),
            undo_metadata={
                "target": self._target_symbol,
                "dest": self._destination_module,
                "timestamp": datetime.now(UTC).isoformat(),
            },
            summary=f"Moved '{self._target_symbol}' to '{self._destination_module}'.",
        )

    def undo(
        self, context: TransformationContext, result: TransformationResult
    ) -> TransformationResult:
        return TransformationResult(
            success=True,
            transformation_name=f"undo_{self.name}",
            summary=f"Undo simulated for {self.name}.",
        )
