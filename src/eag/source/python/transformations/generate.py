"""Generate Symbol transformation for EAG."""

import ast
import keyword
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


class GenerateSymbolTransformation:
    """Generates a new symbol (function, class, etc.) with a placeholder body."""

    def __init__(self, symbol_name: str, kind: str = "function") -> None:
        self._symbol_name = symbol_name
        self._kind = kind

    @property
    def descriptor(self) -> TransformationDescriptor:
        return TransformationDescriptor(
            name="generate_symbol",
            category=TransformationCategory.STRUCTURAL,
            supported_languages=(Language.PYTHON,),
            risk=RiskLevel.LOW,
            produces_edits=("TextEdit",),
        )

    @property
    def name(self) -> str:
        return self.descriptor.name

    def supports(self, context: TransformationContext) -> bool:
        # Check if document has language attribute
        if not hasattr(context.document, 'language'):
            return False
        
        # Check if language is Python
        if hasattr(context.document.language, 'value'):
            return context.document.language.value == "python"
        return context.document.language in self.descriptor.supported_languages

    def preview(self, context: TransformationContext) -> TransformationPreview:
        return TransformationPreview(
            transformation_name=self.name,
            affected_files=(str(context.document.path),),
            affected_symbols=(self._symbol_name,),
            risk=RiskLevel.LOW,
            summary=f"Generate {self._kind} '{self._symbol_name}'.",
        )

    def validate(self, context: TransformationContext) -> tuple[str, ...]:
        errors: list[str] = []
        if not self._symbol_name.isidentifier():
            errors.append(f"'{self._symbol_name}' is not a valid identifier.")
        elif keyword.iskeyword(self._symbol_name):
            errors.append(f"'{self._symbol_name}' is not a valid identifier (it is a Python keyword).")
        if self._kind not in ("function", "class", "async_function"):
            errors.append(f"Unsupported symbol kind: '{self._kind}'.")
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

        if self._kind == "function":
            snippet = f"\ndef {self._symbol_name}():\n    pass\n"
        elif self._kind == "async_function":
            snippet = f"\nasync def {self._symbol_name}():\n    pass\n"
        elif self._kind == "class":
            snippet = f"\nclass {self._symbol_name}:\n    pass\n"
        else:
            return TransformationResult(
                success=False, transformation_name=self.name, summary="Invalid kind."
            )

        new_content = context.content + snippet

        try:
            ast.parse(new_content)
        except SyntaxError as e:
            return TransformationResult(
                success=False, transformation_name=self.name, summary=f"Generated code invalid: {e}"
            )

        edit = SourceEdit(path=context.document.path, new_content=new_content)
        return TransformationResult(
            success=True,
            transformation_name=self.name,
            edits=(edit,),
            files_modified=(str(context.document.path),),
            undo_metadata={"timestamp": datetime.now(UTC).isoformat(), "original": context.content},
            summary=f"Generated {self._kind} '{self._symbol_name}'.",
        )

    def undo(
        self, context: TransformationContext, result: TransformationResult
    ) -> TransformationResult:
        original = result.undo_metadata.get("original")
        if original:
            return TransformationResult(
                success=True,
                transformation_name=f"undo_{self.name}",
                edits=(SourceEdit(path=context.document.path, new_content=original),),
                summary=f"Undo simulated for {self.name}.",
            )
        return TransformationResult(
            success=False, transformation_name=f"undo_{self.name}", summary="Missing undo metadata."
        )
