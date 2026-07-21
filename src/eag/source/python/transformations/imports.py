"""Organize Imports transformation for EAG."""

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


class OrganizeImportsTransformation:
    """Sorts, groups, and removes unused imports."""

    @property
    def descriptor(self) -> TransformationDescriptor:
        return TransformationDescriptor(
            name="organize_imports",
            category=TransformationCategory.SYNTACTIC,
            supported_languages=(Language.PYTHON,),
            risk=RiskLevel.LOW,
            requires_workspace=False,
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
        imports = getattr(context.document, "imports", [])
        unused = sum(1 for i in imports if not getattr(i, "used", False))
        warnings = (f"Found {unused} unused imports.",) if unused else ()

        return TransformationPreview(
            transformation_name=self.name,
            affected_files=(str(context.document.path),),
            affected_imports=tuple(getattr(i, "module", "") for i in imports),
            warnings=warnings,
            risk=RiskLevel.LOW,
            summary=f"Organize {len(imports)} imports.",
        )

    def validate(self, context: TransformationContext) -> tuple[str, ...]:
        return ()

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

        lines = context.content.splitlines(keepends=True)
        if not lines:
            return TransformationResult(
                success=True,
                transformation_name=self.name,
                edits=(SourceEdit(path=context.document.path, new_content=context.content),),
                summary="Empty file.",
            )

        tree = ast.parse(context.content)

        # Extract all import nodes
        import_nodes = [
            node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))
        ]
        if not import_nodes:
            return TransformationResult(
                success=True,
                transformation_name=self.name,
                edits=(SourceEdit(path=context.document.path, new_content=context.content),),
                summary="No imports to organize.",
            )

        # Determine the span of the import block
        start_line = import_nodes[0].lineno - 1
        end_line = getattr(import_nodes[-1], "end_lineno", import_nodes[-1].lineno)

        # Parse used names from document
        used_names = {r.target.split(".")[-1] for r in context.document.references}
        used_names.update({s.name for s in context.document.symbols})

        # Rebuild imports
        new_imports: list[str] = []
        for node in import_nodes:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    check_name = alias.asname or alias.name.split(".")[0]
                    if check_name in used_names:
                        imp_str = f"import {alias.name}"
                        if alias.asname:
                            imp_str += f" as {alias.asname}"
                        new_imports.append(imp_str + "\n")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    check_name = alias.asname or alias.name
                    if check_name in used_names:
                        imp_str = f"from {module} import {alias.name}"
                        if alias.asname:
                            imp_str += f" as {alias.asname}"
                        new_imports.append(imp_str + "\n")

        # Sort imports (simple alphabetical sort for this skeleton)
        new_imports.sort()

        # Reconstruct file
        new_content = "".join(lines[:start_line]) + "".join(new_imports) + "".join(lines[end_line:])

        ast.parse(new_content)

        edit = SourceEdit(path=context.document.path, new_content=new_content)
        return TransformationResult(
            success=True,
            transformation_name=self.name,
            edits=(edit,),
            files_modified=(str(context.document.path),),
            undo_metadata={"timestamp": datetime.now(UTC).isoformat(), "original": context.content},
            summary=f"Organized {len(new_imports)} imports.",
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
