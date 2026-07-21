"""Transformation validator for EAG."""

import keyword

from eag.source.python.transformations.models import TransformationContext


class TransformationValidator:
    """Validates transformation rules and context."""

    def validate_identifier(self, name: str) -> tuple[str, ...]:
        errors: list[str] = []
        if not name.isidentifier():
            errors.append(f"'{name}' is not a valid Python identifier.")
        if keyword.iskeyword(name):
            errors.append(f"'{name}' is a reserved Python keyword.")
        return tuple(errors)

    def validate_symbol_exists(
        self, context: TransformationContext, symbol_name: str
    ) -> tuple[str, ...]:
        errors: list[str] = []
        symbol_names = {s.name for s in context.document.symbols}
        symbol_qnames = {s.qualified_name for s in context.document.symbols}

        if symbol_name not in symbol_names and symbol_name not in symbol_qnames:
            errors.append(f"Symbol '{symbol_name}' not found in source document.")
        return tuple(errors)

    def validate_no_collision(
        self, context: TransformationContext, new_name: str
    ) -> tuple[str, ...]:
        errors: list[str] = []
        symbol_names = {s.name for s in context.document.symbols}
        if new_name in symbol_names:
            errors.append(f"Symbol '{new_name}' already exists in source document.")
        return tuple(errors)
