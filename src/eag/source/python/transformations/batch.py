"""Batch transformations for EAG."""

from eag.source.python.transformations.models import TransformationContext, TransformationResult
from eag.source.python.transformations.protocol import Transformation

class TransformationBatch:
    """Coordinates multiple transformations as a single unit."""
    
    def __init__(self, transformations: list[Transformation]):
        self._transformations = transformations
        
    def execute(self, context: TransformationContext) -> list[TransformationResult]:
        """Execute all transformations in order, stopping on failure."""
        results = []
        for t in self._transformations:
            if not t.supports(context):
                continue
            result = t.apply(context)
            results.append(result)
            if not result.success:
                break
        return results