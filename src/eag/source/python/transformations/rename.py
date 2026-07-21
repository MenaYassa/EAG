"""Rename transformation for EAG."""

import ast
from datetime import UTC, datetime

from eag.planner.enums import RiskLevel
from eag.source.python.transformations.models import (
    SourceEdit,
    TextEdit,
    TransformationContext,
    TransformationPreview,
    TransformationResult,
)
from eag.source.python.transformations.text_applier import apply_text_edits
from eag.source.python.transformations.validator import TransformationValidator
from eag.source.python.transformations.visitor import RenameVisitor


class RenameTransformation:
    """AST-based symbol rename transformation using Location-Based Text Edits."""

    def __init__(self, target_symbol: str, new_name: str) -> None:
        self._target_symbol = target_symbol
        self._new_name = new_name
        self._validator = TransformationValidator()

    @property
    def name(self) -> str:
        return "rename_symbol"

    def supports(self, context: TransformationContext) -> bool:
        return context.document.language.value == "python"

    def preview(self, context: TransformationContext) -> TransformationPreview:
        clean_target = (
            self._target_symbol[7:]
            if self._target_symbol.startswith("module.")
            else self._target_symbol
        )
        target_syms = [s for s in context.document.symbols if s.qualified_name == clean_target]
        target_sym = target_syms[0] if target_syms else None

        if not target_sym:
            return TransformationPreview(
                transformation_name=self.name,
                warnings=(f"Symbol '{self._target_symbol}' not found.",),
                risk=RiskLevel.HIGH,
                summary="Preview failed: symbol missing.",
            )

        affected_refs = tuple(r.target for r in target_sym.references)
        return TransformationPreview(
            transformation_name=self.name,
            affected_files=(str(context.document.path),),
            affected_symbols=(target_sym.qualified_name,),
            affected_references=affected_refs,
            risk=RiskLevel.LOW,
            summary=(
                f"Rename '{self._target_symbol}' to '{self._new_name}' "
                f"across {len(affected_refs)} references."
            ),
        )

    def validate(self, context: TransformationContext) -> tuple[str, ...]:
        errors = list(self._validator.validate_identifier(self._new_name))

        clean_target = (
            self._target_symbol[7:]
            if self._target_symbol.startswith("module.")
            else self._target_symbol
        )
        found = any(s.qualified_name == clean_target for s in context.document.symbols)

        if not found:
            errors.append(f"Symbol '{self._target_symbol}' not found in source document.")

        if self._target_symbol != self._new_name:
            new_clean = (
                self._new_name[7:] if self._new_name.startswith("module.") else self._new_name
            )
            collision = any(s.qualified_name == new_clean for s in context.document.symbols)
            if collision:
                errors.append(f"Symbol '{self._new_name}' already exists in source document.")

        return tuple(errors)

    def apply(self, context: TransformationContext) -> TransformationResult:
        clean_target = (
            self._target_symbol[7:]
            if self._target_symbol.startswith("module.")
            else self._target_symbol
        )
        new_clean = self._new_name[7:] if self._new_name.startswith("module.") else self._new_name

        target_syms = [s for s in context.document.symbols if s.qualified_name == clean_target]
        target_qname = target_syms[0].qualified_name if target_syms else clean_target
        known_qnames = {s.qualified_name for s in context.document.symbols}

        locations = set()
        for sym in target_syms:
            locations.add((sym.location.line, sym.location.column))

        for ref in context.document.references:
            if (
                ref.target == target_qname
                or ref.target not in known_qnames
                and (
                    ref.target.endswith(f".{target_qname}")
                    or target_qname.endswith(f".{ref.target}")
                    or not target_syms
                    and "." not in target_qname
                    and ref.target.split(".")[-1] == target_qname
                )
            ):
                locations.add((ref.line, ref.column))

        target_simple = clean_target.split(".")[-1]
        for imp in context.document.imports:
            imp_target = (
                imp.alias if imp.alias else (imp.name if imp.name else imp.module.split(".")[0])
            )
            if imp_target == target_simple:
                locations.add((imp.location.line, imp.location.column))

        has_refs = bool(locations)

        # 1. Idempotency Check: Pre-empt failures if transformation is already complete
        if not target_syms and not has_refs:
            new_syms = [s for s in context.document.symbols if s.qualified_name == new_clean]
            new_qname = new_syms[0].qualified_name if new_syms else new_clean
            has_new_refs = any(
                r.target == new_qname or r.target.endswith(f".{new_qname}")
                for r in context.document.references
            )

            if new_syms or has_new_refs:
                return TransformationResult(
                    success=True,
                    transformation_name=self.name,
                    edits=(SourceEdit(path=context.document.path, new_content=context.content),),
                    summary=f"No changes needed for '{self._target_symbol}'.",
                )

        # 2. Validation Check
        val_errors = list(self.validate(context))
        if has_refs:
            # If references are found across files, don't fail just because definition is missing
            val_errors = [e for e in val_errors if "not found" not in e]

        if val_errors:
            return TransformationResult(
                success=False,
                transformation_name=self.name,
                summary="Validation failed: " + "; ".join(val_errors),
            )

        # 3. Application
        try:
            tree = ast.parse(context.content)
            visitor = RenameVisitor(
                context.document, target_simple, self._new_name, context.content, locations
            )
            visitor.visit(tree)

            if not visitor.edits:
                return TransformationResult(
                    success=True,
                    transformation_name=self.name,
                    edits=(SourceEdit(path=context.document.path, new_content=context.content),),
                    files_modified=(str(context.document.path),),
                    undo_metadata={
                        "old_name": self._target_symbol,
                        "new_name": self._new_name,
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                    summary=f"No changes needed for '{self._target_symbol}'.",
                )

            new_content = apply_text_edits(context.content, visitor.edits)
            ast.parse(new_content)

            edit = SourceEdit(path=context.document.path, new_content=new_content)
            return TransformationResult(
                success=True,
                transformation_name=self.name,
                edits=(edit,),
                files_modified=(str(context.document.path),),
                undo_metadata={
                    "old_name": self._target_symbol,
                    "new_name": self._new_name,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "text_edits": visitor.edits,
                },
                summary=(
                    f"Renamed '{self._target_symbol}' to '{self._new_name}'. "
                    f"Updated {visitor.stats['references_updated']} references."
                ),
            )
        except SyntaxError as e:
            return TransformationResult(
                success=False, transformation_name=self.name, summary=f"Generated code invalid: {e}"
            )
        except Exception as e:
            return TransformationResult(
                success=False, transformation_name=self.name, summary=f"Transformation failed: {e}"
            )

    def undo(
        self, context: TransformationContext, result: TransformationResult
    ) -> TransformationResult:
        old_name = result.undo_metadata.get("old_name")
        new_name = result.undo_metadata.get("new_name")
        if not old_name or not new_name:
            return TransformationResult(
                success=False,
                transformation_name=f"undo_{self.name}",
                summary="Missing undo metadata.",
            )

        if "text_edits" in result.undo_metadata:
            stored_edits = result.undo_metadata["text_edits"]
            reverse_edits = []
            for edit in stored_edits:
                reverse_edits.append(
                    TextEdit(
                        start_line=edit.start_line,
                        start_col=edit.start_col,
                        end_line=edit.end_line,
                        end_col=edit.start_col + len(new_name.split(".")[-1]),
                        new_text=old_name.split(".")[-1] if "." in old_name else old_name,
                    )
                )
            try:
                content_to_restore = (
                    result.edits[0].new_content if result.edits else context.content
                )
                restored_content = apply_text_edits(content_to_restore, reverse_edits)
                ast.parse(restored_content)
                return TransformationResult(
                    success=True,
                    transformation_name=f"undo_{self.name}",
                    edits=(SourceEdit(path=context.document.path, new_content=restored_content),),
                    summary=f"Undo simulated: rename from '{new_name}' back to '{old_name}'",
                )
            except Exception:
                pass

        return TransformationResult(
            success=True,
            transformation_name=f"undo_{self.name}",
            summary=f"Undo simulated for {self.name}.",
        )
