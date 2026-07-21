"""Safe Delete transformation for EAG."""

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
from eag.source.python.transformations.validator import TransformationValidator


class SafeDeleteTransformation:
    """Safely deletes a symbol only if it has no references."""

    def __init__(self, target_symbol: str) -> None:
        self._target_symbol = target_symbol
        self._validator = TransformationValidator()

    @property
    def descriptor(self) -> TransformationDescriptor:
        return TransformationDescriptor(
            name="safe_delete",
            category=TransformationCategory.SEMANTIC,
            supported_languages=(Language.PYTHON,),
            risk=RiskLevel.HIGH,
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
        target_sym = next(
            (
                s
                for s in context.document.symbols
                if s.qualified_name == self._target_symbol or s.name == self._target_symbol
            ),
            None,
        )
        if not target_sym:
            return TransformationPreview(
                transformation_name=self.name,
                warnings=(f"Symbol '{self._target_symbol}' not found.",),
                risk=RiskLevel.HIGH,
                summary="Preview failed: symbol missing.",
            )
        
        ref_count = sum(1 for ref in context.document.references 
                       if ref.target == target_sym.qualified_name or ref.target == target_sym.name)
        
        # Always return HIGH risk for deletion (matches descriptor)
        return TransformationPreview(
            transformation_name=self.name,
            affected_files=(str(context.document.path),),
            affected_symbols=(target_sym.qualified_name,),
            warnings=(f"Symbol '{self._target_symbol}' has {ref_count} references.",) if ref_count else (),
            risk=RiskLevel.HIGH,
            summary=f"Delete '{self._target_symbol}'" + (f" ({ref_count} references)" if ref_count else ""),
        )

    def validate(self, context: TransformationContext) -> tuple[str, ...]:
        errors: list[str] = []
        errors += self._validator.validate_symbol_exists(context, self._target_symbol)

        target_sym = next(
            (
                s
                for s in context.document.symbols
                if s.qualified_name == self._target_symbol or s.name == self._target_symbol
            ),
            None,
        )
        if target_sym:
            ref_count = sum(
                1
                for ref in context.document.references
                if ref.target == target_sym.qualified_name or ref.target == target_sym.name
            )
            if ref_count > 0:
                errors.append(
                    f"Cannot delete '{self._target_symbol}': still has {ref_count} references."
                )
        return tuple(errors)

    def apply(self, context: TransformationContext) -> TransformationResult:
        # Check if transformation supports this language
        if not self.supports(context):
            return TransformationResult(
                success=False,
                transformation_name=self.name,
                summary=f"Unsupported language: {context.document.language}",
            )
        # First check if symbol exists - if not, fail (not idempotent)
        target_sym = next(
            (
                s
                for s in context.document.symbols
                if s.qualified_name == self._target_symbol or s.name == self._target_symbol
            ),
            None,
        )

        if not target_sym:
            return TransformationResult(
                success=False,  # Should fail when symbol doesn't exist
                transformation_name=self.name,
                summary=f"Symbol '{self._target_symbol}' not found in source document.",
            )

        # Check references - if there are references, fail
        ref_count = sum(
            1
            for ref in context.document.references
            if ref.target == target_sym.qualified_name or ref.target == target_sym.name
        )

        if ref_count > 0:
            return TransformationResult(
                success=False,
                transformation_name=self.name,
                summary=f"Cannot delete '{self._target_symbol}': still has {ref_count} references.",
            )

        try:
            tree = ast.parse(context.content)
            # Find the node to delete
            node_to_delete = None
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    if node.name == target_sym.name:
                        node_to_delete = node
                        break

            if node_to_delete is None:
                # Try to find as a variable assignment
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name) and target.id == target_sym.name:
                                node_to_delete = node
                                break
                        if node_to_delete:
                            break

            if node_to_delete is None:
                return TransformationResult(
                    success=False,
                    transformation_name=self.name,
                    summary=f"Could not find definition for '{self._target_symbol}'.",
                )

            # Get the line range for this node
            start_line = node_to_delete.lineno - 1  # Convert to 0-indexed
            end_line = getattr(node_to_delete, "end_lineno", node_to_delete.lineno)

            # Remove the node by deleting lines
            lines = context.content.splitlines(keepends=True)
            # Remove the lines containing the node
            del lines[start_line:end_line]
            new_content = "".join(lines)

            # Validate the new content
            if new_content.strip():
                try:
                    ast.parse(new_content)
                except SyntaxError:
                    # If removing causes syntax error, try to keep a pass statement
                    # Insert a pass statement at the location
                    lines = context.content.splitlines(keepends=True)
                    # Keep the first line but replace the rest with pass
                    if start_line < len(lines):
                        lines[start_line] = (
                            f"{lines[start_line].split(':')[0]}:{lines[start_line].split(':')[1] if ':' in lines[start_line] else ''}\n"
                        )
                        lines[start_line + 1] = "    pass\n"
                        # Remove the rest
                        del lines[start_line + 2 : end_line]
                        new_content = "".join(lines)

            return TransformationResult(
                success=True,
                transformation_name=self.name,
                edits=(SourceEdit(path=context.document.path, new_content=new_content),),
                files_modified=(str(context.document.path),),
                undo_metadata={
                    "target": self._target_symbol,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "original_content": context.content,
                },
                summary=f"Deleted '{self._target_symbol}'.",
            )
        except Exception as e:
            return TransformationResult(
                success=False, transformation_name=self.name, summary=f"Transformation failed: {e}"
            )

    def undo(
        self, context: TransformationContext, result: TransformationResult
    ) -> TransformationResult:
        original = result.undo_metadata.get("original_content")
        if original:
            return TransformationResult(
                success=True,
                transformation_name=f"undo_{self.name}",
                edits=(SourceEdit(path=context.document.path, new_content=original),),
                files_modified=(str(context.document.path),),
                summary=f"Restored '{self._target_symbol}'.",
            )
        return TransformationResult(
            success=False, transformation_name=f"undo_{self.name}", summary="Missing undo metadata."
        )
