"""Transformation registry for EAG."""

from eag.source.errors import SourceError
from eag.source.python.transformations.models import TransformationContext
from eag.source.python.transformations.protocol import Transformation


class TransformationRegistry:
    """Discovers and manages available source transformations."""

    def __init__(self) -> None:
        self._transformations: dict[str, Transformation] = {}

    def register(self, transformation: Transformation) -> None:
        name = transformation.name
        if name in self._transformations:
            raise SourceError(f"Transformation '{name}' is already registered.")
        self._transformations[name] = transformation

    def find(self, name: str, context: TransformationContext) -> Transformation:
        if name not in self._transformations:
            raise SourceError(f"Transformation '{name}' not found.")
        return self._transformations[name]

    def list(self) -> tuple[Transformation, ...]:
        return tuple(self._transformations.values())
