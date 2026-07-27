"""Safe Replace transformation for EAG."""

import ast
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


class SafeReplaceTransformation:
    """Replaces an AST expression with a new expression."""

    def __init__(self, target_code: str, replacement_code: str) -> None:
        self._target_code = target_code
        self._replacement_code = replacement_code

    @property
    def descriptor(self) -> TransformationDescriptor:
        return TransformationDescriptor(
            name="safe_replace",
            category=TransformationCategory.SEMANTIC,
            supported_languages=(Language.PYTHON,),
            risk=RiskLevel.MEDIUM,
            produces_edits=("TextEdit",),
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
            risk=RiskLevel.MEDIUM,
            summary=f"Replace '{self._target_code}' with '{self._replacement_code}'.",
        )

    def validate(self, context: TransformationContext) -> tuple[str, ...]:
        errors: list[str] = []
        try:
            ast.parse(self._target_code)
        except SyntaxError:
            errors.append("Target code is not valid Python.")
        try:
            ast.parse(self._replacement_code)
        except SyntaxError:
            errors.append("Replacement code is not valid Python.")
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

        try:
            # Count occurrences
            count = context.content.count(self._target_code)

            if count == 0:
                return TransformationResult(
                    success=True,
                    transformation_name=self.name,
                    edits=(SourceEdit(path=context.document.path, new_content=context.content),),
                    summary="No matching expressions found to replace.",
                )

            # Replace all occurrences
            new_content = context.content.replace(self._target_code, self._replacement_code)

            try:
                ast.parse(new_content)
            except SyntaxError as e:
                return TransformationResult(
                    success=False,
                    transformation_name=self.name,
                    summary=f"Generated code invalid: {e}",
                )

            edit = SourceEdit(path=context.document.path, new_content=new_content)
            return TransformationResult(
                success=True,
                transformation_name=self.name,
                edits=(edit,),
                files_modified=(str(context.document.path),),
                undo_metadata={
                    "timestamp": datetime.now(UTC).isoformat(),
                    "original": context.content,
                    "old_code": self._target_code,
                    "new_code": self._replacement_code,
                },
                summary=f"Replaced {count} occurrences.",  # Count in summary
            )
        except Exception as e:
            return TransformationResult(
                success=False, transformation_name=self.name, summary=f"Transformation failed: {e}"
            )

    def undo(
        self, context: TransformationContext, result: TransformationResult
    ) -> TransformationResult:
        # Check if we have edits
        if not result.edits:
            return TransformationResult(
                success=False, transformation_name=f"undo_{self.name}", summary="No edits to undo."
            )

        original = result.undo_metadata.get("original")
        if original:
            return TransformationResult(
                success=True,
                transformation_name=f"undo_{self.name}",
                edits=(SourceEdit(path=context.document.path, new_content=original),),
                summary="Restored original content.",
            )

        # Try to reverse the replacement
        old_code = result.undo_metadata.get("old_code")
        new_code = result.undo_metadata.get("new_code")

        if old_code and new_code:
            current_content = result.edits[0].new_content
            restored_content = current_content.replace(new_code, old_code)
            return TransformationResult(
                success=True,
                transformation_name=f"undo_{self.name}",
                edits=(SourceEdit(path=context.document.path, new_content=restored_content),),
                summary=f"Restored '{old_code}'.",
            )

        return TransformationResult(
            success=False, transformation_name=f"undo_{self.name}", summary="Missing undo metadata."
        )
